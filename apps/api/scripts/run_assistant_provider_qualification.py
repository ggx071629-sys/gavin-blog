from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

from app.assistant_qualification import local_ledger
from app.assistant_qualification.provider_probe import (
    load_and_run,
    migrate_local_chat_evidence,
    rebind_local_chat_costs,
    run_local_chat_probe,
)
from app.config import get_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Explicit, cost-bounded real-provider qualification probe"
    )
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--approve-profile-digest")
    parser.add_argument("--local-chat", action="store_true")
    parser.add_argument(
        "--local-action",
        choices=["probe", "status", "authorize", "recover", "migrate-evidence", "rebind-costs"],
        default="probe",
    )
    parser.add_argument("--authorization-id")
    parser.add_argument("--approve-daily-budget-cny", type=Decimal)
    parser.add_argument("--reason")
    parser.add_argument("--attempt-id")
    parser.add_argument("--confirm-quiescent", action="store_true")
    parser.add_argument("--source-probe", type=Path)
    parser.add_argument("--approve-max-micro-cny", type=int)
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--chat", action="store_true")
    parser.add_argument("--embedding", action="store_true")
    args = parser.parse_args(argv)
    if args.local_chat:
        if args.profile or args.approve_profile_digest or args.embedding or args.chat:
            parser.error("--local-chat cannot be combined with production probe arguments")
        if args.local_action != "probe":
            settings = get_settings()
            if args.local_action == "authorize":
                if (
                    not args.authorization_id
                    or args.approve_max_micro_cny is None
                    or args.max_calls is None
                    or args.approve_daily_budget_cny is None
                    or not args.reason
                ):
                    parser.error(
                        "authorize requires ID, cumulative cost/calls, daily budget and reason"
                    )
                result = local_ledger.authorize(
                    settings=settings,
                    ledger_path=args.ledger,
                    authorization_id=args.authorization_id,
                    max_calls=args.max_calls,
                    max_micro_cny=args.approve_max_micro_cny,
                    daily_budget=args.approve_daily_budget_cny,
                    reason=args.reason,
                )
            elif args.local_action == "recover":
                if not args.attempt_id or not args.confirm_quiescent or not args.reason:
                    parser.error("recover requires attempt ID, --confirm-quiescent and reason")
                result = local_ledger.recover(
                    settings=settings,
                    ledger_path=args.ledger,
                    attempt_id=args.attempt_id,
                    confirm_quiescent=args.confirm_quiescent,
                    reason=args.reason,
                )
            elif args.local_action == "migrate-evidence":
                if args.source_probe is None or args.output is None:
                    parser.error("migrate-evidence requires --source-probe and distinct --output")
                migrate_local_chat_evidence(args.source_probe, args.output, settings)
                result = {"output": str(args.output), "paid_calls": 0}
            elif args.local_action == "rebind-costs":
                if args.source_probe is None or args.output is None or not args.authorization_id:
                    parser.error(
                        "rebind-costs requires source, distinct output and authorization ID"
                    )
                rebind_local_chat_costs(
                    args.source_probe,
                    args.output,
                    settings,
                    args.ledger,
                    args.authorization_id,
                )
                result = {"output": str(args.output), "paid_calls": 0}
            else:
                result = local_ledger.status(settings=settings, ledger_path=args.ledger)
            print(json.dumps(result, sort_keys=True))
            return 0
        if args.output is None:
            parser.error("probe requires --output")
        if (
            args.approve_daily_budget_cny is not None
            or args.reason
            or args.attempt_id
            or args.confirm_quiescent
            or args.source_probe
        ):
            parser.error("probe cannot implicitly authorize, recover or migrate")
        if args.approve_max_micro_cny is None or args.max_calls is None:
            parser.error("local probe requires explicit cost and call limits")
        payload = run_local_chat_probe(
            settings=get_settings(),
            ledger_path=args.ledger,
            output_path=args.output,
            approved_max_micro_cny=args.approve_max_micro_cny,
            max_calls=args.max_calls,
            authorization_id=args.authorization_id,
        )
    else:
        if (
            args.local_action != "probe"
            or args.authorization_id
            or args.approve_daily_budget_cny is not None
            or args.reason
            or args.attempt_id
            or args.confirm_quiescent
            or args.source_probe
        ):
            parser.error("local operations require --local-chat")
        if args.output is None:
            parser.error("production probe requires --output")
        if not args.profile or not args.approve_profile_digest:
            parser.error("production probe requires profile and approved digest")
        if args.approve_max_micro_cny is not None or args.max_calls is not None:
            parser.error("local budget arguments require --local-chat")
        payload = load_and_run(
            settings=get_settings(),
            profile_path=args.profile,
            approved_profile_digest=args.approve_profile_digest,
            ledger_path=args.ledger,
            output_path=args.output,
            probe_chat=args.chat,
            probe_embedding=args.embedding,
        )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "calls_used": payload["ledger"]["calls_used"],
                "micro_cny_used": payload["ledger"]["micro_cny_used"],
                "within_envelope": payload["ledger"]["within_envelope"],
            },
            sort_keys=True,
        )
    )
    if args.local_chat:
        return 0 if payload["chat"]["status"] == "pass" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from .profile import load_profile, profile_digest, schema_document


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the zero-call public-assistant production qualification profile"
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    validate = subcommands.add_parser("validate", help="validate a JSON or YAML profile")
    validate.add_argument("profile", type=Path)
    subcommands.add_parser("schema", help="print the versioned JSON Schema")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "schema":
        print(json.dumps(schema_document(), ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    try:
        profile = load_profile(args.profile)
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {"valid": False, "error": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "valid": True,
                "schema_version": profile.schema_version,
                "profile_id": profile.profile_id,
                "profile_revision": profile.profile_revision,
                "profile_digest": profile_digest(profile),
                "provider_calls": 0,
                "deployment_actions": 0,
                "switches": {
                    "web_launcher": False,
                    "api_capability": False,
                    "runtime_gate": False,
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

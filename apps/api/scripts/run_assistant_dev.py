from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config

api_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(api_root))

from app.assistant.development import (  # noqa: E402
    attach_real_development_lifespan,
    build_development_settings,  # noqa: E402
    build_real_development_settings,
)
from app.assistant.provisioning import provision_runtime  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the tracked local assistant development API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8101)
    parser.add_argument("--web-origin", default="http://127.0.0.1:3101")
    parser.add_argument("--real", action="store_true")
    parser.add_argument(
        "--probe",
        type=Path,
        default=Path(
            os.environ.get(
                "GAVIN_ASSISTANT_LOCAL_PROBE_PATH",
                str(api_root / "data/assistant-qualification/local-chat-probe.json"),
            )
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.host not in {"127.0.0.1", "::1"}:
        raise SystemExit("assistant development API only listens on a loopback address")
    raw_root = os.environ.get("GAVIN_ASSISTANT_DEV_RUN_ROOT", "").strip()
    proxy_secret = os.environ.get("GAVIN_ASSISTANT_DEV_PROXY_SECRET", "").strip()
    if not raw_root:
        raise SystemExit("GAVIN_ASSISTANT_DEV_RUN_ROOT is required")
    run_root = Path(raw_root)
    try:
        settings = (
            build_real_development_settings(
                Settings(_env_file=".env.e5"),
                Settings(),
                run_root=run_root,
                web_origin=args.web_origin,
                proxy_secret=proxy_secret,
                probe_path=args.probe,
            )
            if args.real
            else build_development_settings(
                Settings(),
                run_root=run_root,
                web_origin=args.web_origin,
                proxy_secret=proxy_secret,
            )
        )
        if args.real:
            from app.assistant_qualification.provider_probe import local_chat_probe_notice

            print(local_chat_probe_notice(args.probe, settings), flush=True)
        # Validate the development boundary before any content database write.
        migration = Config(str(api_root / "alembic.ini"))
        migration.attributes["database_url"] = settings.database_url
        command.upgrade(migration, "head")
        provision_runtime(settings)
        app = create_app(settings)
        if args.real:
            attach_real_development_lifespan(app, settings, args.probe)
            from app.assistant_qualification.evaluation_guard import ledger_for_probe

            ledger_path = ledger_for_probe(
                args.probe, api_root / 'data/assistant-qualification/local-provider-ledger.json',
                os.environ.get('GAVIN_ASSISTANT_EVALUATION_LEDGER'),
            )
            if ledger_path:
                from app.assistant_qualification.evaluation_guard import EvaluationGuard

                guard = EvaluationGuard(Settings(), Path(ledger_path))
                original_lifespan = app.router.lifespan_context

                @asynccontextmanager
                async def evaluated_lifespan(application):
                    async with original_lifespan(application):
                        from app.assistant_index.projector import (
                            iter_public_sources,
                            source_revision_set_digest,
                        )

                        corpus = json.loads((api_root.parents[1] / 'plan-build'
                            / 'assistant-gap-closure/evaluation/Q5-corpus.json').read_text(
                                encoding='utf8'))

                        def check_sources():
                            with application.state.assistant.database.session_factory() as db:
                                db.info['settings'] = settings
                                digest = source_revision_set_digest(iter_public_sources(db))
                                if digest != corpus['source_set_sha256']:
                                    raise ValueError('evaluation corpus changed')

                        guard.before_dispatch = check_sources
                        application.state.assistant.chat._evaluation_guard = guard
                        yield

                app.router.lifespan_context = evaluated_lifespan
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

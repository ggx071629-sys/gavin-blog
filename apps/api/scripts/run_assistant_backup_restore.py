from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.assistant_qualification.backup_restore import (
    create_consistent_snapshot,
    restore_to_fresh_target,
    verify_snapshot,
)
from app.config import get_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create, verify, or restore a fenced content/media qualification snapshot"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--destination", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--snapshot", type=Path, required=True)
    restore = commands.add_parser("restore")
    restore.add_argument("--snapshot", type=Path, required=True)
    restore.add_argument("--database", type=Path, required=True)
    restore.add_argument("--media", type=Path, required=True)
    restore.add_argument("--runtime", type=Path, required=True)
    args = parser.parse_args(argv)
    settings = get_settings()
    if args.command == "snapshot":
        result = create_consistent_snapshot(
            settings=settings,
            snapshot_dir=args.destination,
        )
    elif args.command == "verify":
        result = verify_snapshot(args.snapshot)
    else:
        result = restore_to_fresh_target(
            settings=settings,
            snapshot_dir=args.snapshot,
            destination_database=args.database,
            destination_media=args.media,
            destination_runtime=args.runtime,
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

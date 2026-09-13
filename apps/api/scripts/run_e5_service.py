"""Single-process local E5 launcher, intentionally separate from offline assistant demo."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == "__main__":
    if os.environ.get("GAVIN_ENVIRONMENT", "development") != "development":
        raise SystemExit("This launcher supports local development only; qualification pending")
    import uvicorn

    from app.local_embedding.service import create_app

    uvicorn.run(
        create_app(),
        host="127.0.0.1",
        port=8091,
        workers=1,
        access_log=False,
        timeout_graceful_shutdown=35,
    )

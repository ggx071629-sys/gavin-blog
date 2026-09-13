"""Default-off anonymous public Q&A online core."""

from __future__ import annotations

import os

# LangSmith is a direct dependency for version pinning, but raw-content tracing
# stays off unless an operator later enables an allowlisted configuration.
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("LANGCHAIN_TRACING", "false")

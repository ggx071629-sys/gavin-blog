from __future__ import annotations

import os
import socket
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from langchain_core.embeddings import Embeddings

from ..assistant.crypto import random_id
from ..config import Settings
from ..db import Database
from ..time_utils import utc_now
from .constants import TEST_EMBEDDING_MODEL, TEST_EMBEDDING_MODEL_VERSION
from .embeddings import DeterministicHashEmbeddings, build_embeddings
from .qdrant_store import QdrantPointStore, build_qdrant_store


@dataclass
class AssistantIndexRuntime:
    settings: Settings
    database: Database
    embeddings: Embeddings
    store: QdrantPointStore
    clock: Callable[[], datetime] = utc_now
    owner: str = "assistant-index-worker"

    def now(self) -> datetime:
        return self.clock()


def build_runtime(settings: Settings, database: Database) -> AssistantIndexRuntime:
    return AssistantIndexRuntime(
        settings=settings,
        database=database,
        embeddings=build_embeddings(settings),
        store=build_qdrant_store(settings),
        owner=f"{socket.gethostname()}:{os.getpid()}:{random_id()}",
    )


def build_test_runtime(
    settings: Settings,
    database: Database,
    *,
    store: QdrantPointStore | None = None,
    clock: Callable[[], datetime] | None = None,
    owner: str = "test-worker",
) -> AssistantIndexRuntime:
    from qdrant_client import QdrantClient

    from ..assistant.providers import DeterministicMeteredEmbeddings

    dimension = settings.assistant_embedding_dimension or 32
    embeddings = DeterministicMeteredEmbeddings(
        DeterministicHashEmbeddings(
            dimension=dimension,
            model=settings.assistant_embedding_model or TEST_EMBEDDING_MODEL,
            version=settings.assistant_embedding_model_version or TEST_EMBEDDING_MODEL_VERSION,
        )
    )
    return AssistantIndexRuntime(
        settings=settings,
        database=database,
        embeddings=embeddings,
        store=store or QdrantPointStore(QdrantClient(":memory:")),
        clock=clock or utc_now,
        owner=owner,
    )

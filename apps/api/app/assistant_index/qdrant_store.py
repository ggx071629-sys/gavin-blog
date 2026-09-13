from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from ..config import Settings
from .constants import PAYLOAD_ALLOWLIST
from .embeddings import AssistantIndexConfigurationError

POINT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "gavin.assistant-index")


@dataclass(frozen=True)
class VectorHit:
    chunk_id: str
    score: float


def point_uuid(generation_id: int, chunk_id: str) -> str:
    return str(uuid.uuid5(POINT_NAMESPACE, f"{generation_id}:{chunk_id}"))


def sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    extra = set(payload) - set(PAYLOAD_ALLOWLIST)
    if extra:
        raise ValueError(f"qdrant payload keys not allowed: {sorted(extra)}")
    missing = set(PAYLOAD_ALLOWLIST) - set(payload)
    if missing:
        raise ValueError(f"qdrant payload missing keys: {sorted(missing)}")
    if "page_content" in payload or "text" in payload:
        raise ValueError("qdrant payload must not include document text")
    return {key: payload[key] for key in PAYLOAD_ALLOWLIST}


class QdrantPointStore:
    """Controlled Qdrant adapter. Does not use LangChain vector-store wrappers."""

    def __init__(self, client: QdrantClient) -> None:
        self.client = client

    def reusable_vectors(
        self, collection_name: str, *, generation_id: int,
        payloads: list[dict[str, Any]], dimension: int,
    ) -> list[list[float]] | None:
        records = self.client.retrieve(
            collection_name=collection_name,
            ids=[point_uuid(generation_id, p['chunk_id']) for p in payloads],
            with_payload=True, with_vectors=True,
        )
        by_id = {str(record.id): record for record in records}
        vectors: list[list[float]] = []
        for payload in payloads:
            record = by_id.get(point_uuid(generation_id, payload['chunk_id']))
            if record is None or record.payload != payload:
                return None
            vector = record.vector
            if not isinstance(vector, list) or len(vector) != dimension:
                return None
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vector):
                return None
            vectors.append(vector)
        return vectors

    def create_collection(self, name: str, *, dimension: int, distance: str = "Cosine") -> None:
        metric = Distance.COSINE if distance.lower() == "cosine" else Distance.COSINE
        self.client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dimension, distance=metric),
        )
        local_client = getattr(self.client, "_client", None)
        if type(local_client).__name__ == "QdrantLocal":
            return
        for field, schema in (
            ("chunk_id", PayloadSchemaType.KEYWORD),
            ("source_type", PayloadSchemaType.KEYWORD),
            ("source_id", PayloadSchemaType.INTEGER),
            ("source_version", PayloadSchemaType.KEYWORD),
            ("generation", PayloadSchemaType.INTEGER),
            ("pipeline_version", PayloadSchemaType.KEYWORD),
        ):
            self.client.create_payload_index(
                collection_name=name,
                field_name=field,
                field_schema=schema,
            )

    def delete_collection(self, name: str) -> None:
        self.client.delete_collection(collection_name=name)

    def collection_exists(self, name: str) -> bool:
        return bool(self.client.collection_exists(collection_name=name))

    def upsert_points(
        self,
        collection_name: str,
        *,
        generation_id: int,
        items: list[tuple[str, list[float], dict[str, Any]]],
    ) -> None:
        points = [
            PointStruct(
                id=point_uuid(generation_id, chunk_id),
                vector=vector,
                payload=sanitize_payload(payload),
            )
            for chunk_id, vector, payload in items
        ]
        if points:
            self.client.upsert(collection_name=collection_name, points=points, wait=True)

    def delete_source(
        self,
        collection_name: str,
        *,
        source_type: str,
        source_id: int,
    ) -> None:
        self.client.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(key="source_type", match=MatchValue(value=source_type)),
                    FieldCondition(key="source_id", match=MatchValue(value=source_id)),
                ]
            ),
            wait=True,
        )

    def delete_source_version(
        self, collection_name: str, *, source_type: str, source_id: int, source_version: str,
    ) -> None:
        self.client.delete(
            collection_name=collection_name,
            points_selector=Filter(must=[
                FieldCondition(key="source_type", match=MatchValue(value=source_type)),
                FieldCondition(key="source_id", match=MatchValue(value=source_id)),
                FieldCondition(key="source_version", match=MatchValue(value=source_version)),
            ]),
            wait=True,
        )

    def delete_chunks(
        self,
        collection_name: str,
        *,
        generation_id: int,
        chunk_ids: list[str],
    ) -> None:
        if not chunk_ids:
            return
        self.client.delete(
            collection_name=collection_name,
            points_selector=PointIdsList(
                points=[point_uuid(generation_id, chunk_id) for chunk_id in chunk_ids]
            ),
            wait=True,
        )

    def search(self, collection_name: str, vector: list[float], *, limit: int) -> list[VectorHit]:
        response = self.client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=limit,
            with_payload=list(PAYLOAD_ALLOWLIST),
            with_vectors=False,
        )
        hits: list[VectorHit] = []
        for point in response.points:
            payload = point.payload or {}
            chunk_id = payload.get("chunk_id")
            if not chunk_id:
                continue
            hits.append(VectorHit(chunk_id=str(chunk_id), score=float(point.score or 0.0)))
        return hits

    def count(self, collection_name: str) -> int:
        result = self.client.count(collection_name=collection_name, exact=True)
        return int(result.count)

    def chunk_ids(self, collection_name: str) -> set[str]:
        ids: set[str] = set()
        offset = None
        while True:
            records, offset = self.client.scroll(
                collection_name=collection_name,
                limit=256,
                offset=offset,
                with_payload=["chunk_id"],
                with_vectors=False,
            )
            for record in records:
                payload = record.payload or {}
                if "chunk_id" in payload:
                    ids.add(str(payload["chunk_id"]))
            if offset is None:
                break
        return ids

    def probe(self, collection_name: str, vector: list[float]) -> None:
        self.search(collection_name, vector, limit=1)


def build_qdrant_store(settings: Settings) -> QdrantPointStore:
    if settings.environment == "production" or settings.assistant_qdrant_url:
        if not settings.assistant_qdrant_url or not settings.assistant_qdrant_api_key:
            raise AssistantIndexConfigurationError("remote Qdrant URL and API key are required")
        client = QdrantClient(
            url=settings.assistant_qdrant_url,
            api_key=settings.assistant_qdrant_api_key,
            timeout=settings.assistant_qdrant_timeout_seconds,
        )
        return QdrantPointStore(client)
    if settings.assistant_qdrant_path:
        client = QdrantClient(path=settings.assistant_qdrant_path)
        return QdrantPointStore(client)
    return QdrantPointStore(QdrantClient(":memory:"))

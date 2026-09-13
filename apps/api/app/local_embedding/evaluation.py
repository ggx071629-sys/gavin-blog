"""Reproducible retrieval-only evaluation against isolated, draft fixture corpora."""

from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Literal

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from ..assistant_index.projector import project_source
from ..assistant_index.retriever import retrieve
from ..assistant_index.runtime import build_runtime
from ..assistant_index.worker import rebuild_generation
from ..config import Settings
from ..db import Database
from ..main import create_app
from ..models import AssistantChunk, AssistantIndexGeneration
from ..time_utils import utc_now
from .artifact import MODEL, PIPELINE, VERSION, sha256
from .client import E5Embeddings
from .local import finalize_local, load_settings

API_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = API_ROOT / "evaluation" / "e5-bilingual-v1.json"
Language = Literal["zh", "en"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Document(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    language: Language
    source_type: Literal["article", "profile"] = "article"
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class Gold(StrictModel):
    document_id: str
    evidence: str = Field(min_length=1)


class Question(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    query_language: Language
    target_language: Language
    kind: Literal["positive", "no_evidence", "terminology", "code", "mixed", "long"]
    question: str = Field(min_length=1)
    gold: list[Gold]


class Dataset(StrictModel):
    schema_version: Literal[1]
    id: str
    annotation_status: Literal["ai_draft_pending_human_review"]
    scope: str
    documents: list[Document]
    questions: list[Question]

    @model_validator(mode="after")
    def validate_labels(self) -> Dataset:
        documents = {d.id: d for d in self.documents}
        if len(documents) != len(self.documents):
            raise ValueError("duplicate document ID")
        if len({q.id for q in self.questions}) != len(self.questions):
            raise ValueError("duplicate question ID")
        counts: Counter[str] = Counter()
        for q in self.questions:
            if not q.question.strip():
                raise ValueError("blank question")
            if (q.kind == "no_evidence") != (not q.gold):
                raise ValueError("only no_evidence questions may have no gold")
            if len({g.document_id for g in q.gold}) != len(q.gold):
                raise ValueError("duplicate gold document")
            for g in q.gold:
                doc = documents.get(g.document_id)
                if doc is None or doc.language != q.target_language:
                    raise ValueError("gold document missing or wrong target language")
                if not g.evidence.strip() or g.evidence not in doc.content:
                    raise ValueError("gold evidence must be a nonblank verbatim content span")
            if q.kind == "positive":
                counts[f"{q.query_language}->{q.target_language}"] += 1
        if counts != Counter({f"{a}->{b}": 10 for a in ("zh", "en") for b in ("zh", "en")}):
            raise ValueError("exactly ten positives per language direction are required")
        if not {"no_evidence", "terminology", "code", "mixed", "long"}.issubset(
            {q.kind for q in self.questions}
        ):
            raise ValueError("boundary coverage is incomplete")
        for lang in ("zh", "en"):
            if sum(d.language == lang and d.source_type == "profile" for d in self.documents) != 1:
                raise ValueError("each corpus must explicitly define its singleton profile")
            relevant = {g.document_id for q in self.questions for g in q.gold}
            if not any(d.language == lang and d.id not in relevant for d in self.documents):
                raise ValueError("each target corpus needs distractors")
        return self


def load_dataset(path: Path) -> Dataset:
    return Dataset.model_validate_json(path.read_text(encoding="utf-8"))


def reserve_output(path: Path) -> Path:
    """Atomic refusal of existing paths; never delete or reuse an earlier run."""
    path = path.absolute()
    path.mkdir(parents=True, exist_ok=False)
    return path.resolve()


def isolated_settings(base: Settings, directory: Path, prefix: str) -> Settings:
    return base.model_copy(
        update={
            "environment": "development",
            "database_url": f"sqlite:///{(directory / 'content.db').as_posix()}",
            "assistant_runtime_path": str(directory / "runtime.db"),
            "media_root": str(directory / "media"),
            "assistant_qdrant_collection_prefix": prefix,
            "assistant_online_enabled": False,
            "assistant_local_dev_mode": False,
            "assistant_test_startup_bootstrap": False,
            "admin_password": secrets.token_urlsafe(32),
            "cookie_secure": False,
        }
    )


def publish_corpus(settings: Settings, documents: list[Document]) -> dict[tuple[str, int], str]:
    """Use actual migrations, authentication, draft creation and publication."""
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "migrations"))
    config.attributes["database_url"] = settings.database_url
    command.upgrade(config, "head")
    app = create_app(settings)
    published = {}
    try:
        with TestClient(app) as client:
            csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
            response = client.post(
                "/api/v1/auth/login",
                json={"username": settings.admin_username, "password": settings.admin_password},
                headers={"X-CSRF-Token": csrf},
            )
            response.raise_for_status()
            headers = {"X-CSRF-Token": client.cookies["gavin_csrf"]}
            for document in documents:
                if document.source_type == "profile":
                    response = client.get("/api/v1/admin/profile")
                    response.raise_for_status()
                    response = client.patch(
                        "/api/v1/admin/profile",
                        json={
                            "version": response.json()["version"],
                            "name": document.title,
                            "title": document.title,
                            "bio": document.content,
                            "skills": [],
                        },
                        headers=headers,
                    )
                    response.raise_for_status()
                    published[("profile", response.json()["id"])] = document.id
                    continue
                response = client.post(
                    "/api/v1/admin/articles",
                    json={
                        "title": document.title,
                        "slug": document.id,
                        "content": document.content,
                        "summary": "",
                    },
                    headers=headers,
                )
                response.raise_for_status()
                article = response.json()
                response = client.post(
                    f"/api/v1/admin/articles/{article['id']}/publish",
                    json={"version": article["version"]},
                    headers=headers,
                )
                response.raise_for_status()
                published[("article", article["id"])] = document.id
            if app.state.assistant is not None:
                raise RuntimeError("evaluation must not start online Chat")
    finally:
        app.state.database.engine.dispose()
    return published


class Hit(StrictModel):
    document_id: str
    chunk_id: str
    content: str
    path: str
    version: str
    citation_valid: bool
    sources: list[str]


def inspect_gate(settings: Settings) -> str:
    # Read-only inspection: this command never enables the runtime gate.
    if not settings.assistant_runtime_path:
        raise ValueError("evaluation requires its dedicated runtime path")
    path = Path(settings.assistant_runtime_path).resolve()
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
        gate = connection.execute(
            "SELECT requested_state, effective_state, switch_pending_operation_id "
            "FROM assistant_operational_gate WHERE id = 1"
        ).fetchone()
    if gate != ("disabled", "disabled", None):
        raise RuntimeError("evaluation runtime gate is not disabled or switch is pending")
    return "disabled"


def score_question(question: Question, hits: list[Hit]) -> dict:
    top = hits[:5]
    expected = {g.document_id for g in question.gold}
    found = {h.document_id for h in top if h.citation_valid}
    snippets = {
        g.document_id
        for g in question.gold
        if any(
            h.document_id == g.document_id and h.citation_valid and g.evidence in h.content
            for h in top
        )
    }
    return {
        "recall_at_5": len(expected & found) / len(expected) if expected else None,
        "evidence_recall_at_5": len(snippets) / len(expected) if expected else None,
        "citations_valid": all(h.citation_valid for h in top),
        "unsupported_neighbors": len(top) if not expected else 0,
        "refusal_evaluated": False,
    }


def summarize(dataset: Dataset, digest: str, results: list[dict], corpora: dict) -> dict:
    if Counter(r["id"] for r in results) != Counter(q.id for q in dataset.questions):
        raise ValueError("evaluation results are missing or duplicated")
    questions = {q.id: q for q in dataset.questions}
    unexpected = [
        r["id"]
        for r in results
        if not r["citations_valid"]
        or (questions[r["id"]].kind == "long" and not r["overlong"])
        or (
            r["status"] != "ok"
            and not (
                questions[r["id"]].kind == "long" and r["overlong"] and r["status"] == "degraded"
            )
        )
    ]
    groups = {}
    positive = [r for r in results if questions[r["id"]].kind == "positive"]
    for label in ["all", "zh->zh", "en->en", "zh->en", "en->zh"]:
        rows = [r for r in positive if label == "all" or r["direction"] == label]
        groups[label] = {
            "count": len(rows),
            "recall_at_5": sum(r["recall_at_5"] for r in rows) / len(rows),
            "evidence_recall_at_5": sum(r["evidence_recall_at_5"] for r in rows) / len(rows),
        }
    return {
        "schema_version": 1,
        "created_at": utc_now().isoformat(),
        "runner_sha256": sha256(Path(__file__)),
        "scope": "manual-local-only-synthetic-draft",
        "dataset_id": dataset.id,
        "dataset_sha256": digest,
        "annotation_status": dataset.annotation_status,
        "model": MODEL,
        "model_version": VERSION,
        "pipeline": PIPELINE,
        "top_k": 5,
        "metric": "macro document recall over top five chunks; duplicate documents count once",
        "corpora": corpora,
        "groups": groups,
        "run_valid": not unexpected,
        "unexpected_results": unexpected,
        "draft_recall_target_met": not unexpected and groups["all"]["recall_at_5"] >= 0.85,
        "boundaries": [
            {k: v for k, v in r.items() if k not in {"hits", "question"}}
            for r in results
            if questions[r["id"]].kind != "positive"
        ],
        "missed_positive_ids": [r["id"] for r in positive if r["recall_at_5"] < 1],
        "phase_d_passed": False,
        "production_qualified": False,
        "chat_called": False,
        "pending": [
            "human-reviewed labels",
            "real visitor corpus coverage",
            "2-vCPU/4-GB co-resident resource acceptance",
        ],
    }


def review_markdown(dataset: Dataset, digest: str, results: list[dict]) -> str:
    lines = [
        "# E5 检索题集人工复核材料",
        "",
        "状态：AI 起草，待人工复核。分数不是阶段 D 或生产通过证据。",
        "题目与答案来自虚构工程语料；请检查自然性、语言方向、相关文档是否穷尽、证据是否足以回答。",
        "无证据近邻不等于回答正确；本轮没有调用 Chat，也没有检验拒答。",
        "",
        f"Dataset SHA-256: `{digest}`",
        "",
        "## 语料",
        "",
    ]
    for d in dataset.documents:
        lines += [f"### {d.id} — {d.title}", "", d.content, ""]
    by_id = {r["id"]: r for r in results}
    lines += ["## 逐题复核", ""]
    for q in dataset.questions:
        r = by_id.get(q.id)
        lines += [
            f"### {q.id} ({q.query_language} → {q.target_language}; {q.kind})",
            "",
            q.question,
            "",
        ]
        for gold in q.gold:
            lines += [f"预期文档：`{gold.document_id}`；原文证据：{gold.evidence}", ""]
        if not q.gold:
            lines += ["预期：资料无证据。只记录检索近邻；拒答须在后续 Chat 验收。", ""]
        if r:
            lines += [
                f"Recall@5: {r['recall_at_5']}；片段命中: {r['evidence_recall_at_5']}；"
                f"status: {r['status']}",
                "",
            ]
            for rank, hit in enumerate(r["hits"], 1):
                lines += [
                    f"{rank}. `{hit['document_id']}` — `{hit['path']}`，"
                    f"version `{hit['version']}`，来源 {', '.join(hit['sources'])}",
                    "",
                    hit["content"],
                    "",
                ]
        lines += ["复核结论（待填写）：", ""]
    return "\n".join(lines)


def run_corpus(settings: Settings, dataset: Dataset, language: Language) -> tuple[list[dict], dict]:
    documents = [d for d in dataset.documents if d.language == language]
    published = publish_corpus(settings, documents)
    database = Database(settings.database_url)
    runtime = build_runtime(settings, database)
    try:
        if not isinstance(runtime.embeddings, E5Embeddings):
            raise RuntimeError("evaluation requires real pinned E5 embeddings")
        generation_id = rebuild_generation(runtime)
        finalize_local(settings, database, generation_id, runtime)
        gate = inspect_gate(settings)
        results = []
        with database.session_factory() as db:
            db.info["settings"] = settings
            generation = db.get(AssistantIndexGeneration, generation_id)
            if (
                generation is None
                or generation.status != "active"
                or generation.embedding_model != MODEL
                or generation.embedding_model_version != VERSION
                or generation.pipeline_version != PIPELINE
                or generation.vector_dimension != 384
            ):
                raise RuntimeError("active generation identity drift")
            indexed_ids = set(
                db.scalars(
                    select(AssistantChunk.chunk_id).where(
                        AssistantChunk.generation_id == generation_id,
                    )
                )
            )
            if indexed_ids != runtime.store.chunk_ids(generation.collection_name):
                raise RuntimeError("persisted chunk/vector membership differs")
            for q in dataset.questions:
                if q.target_language != language:
                    continue
                query, overlong = runtime.embeddings.prepare_retrieval_query(q.question, [])
                if query != q.question:
                    raise RuntimeError("current question was changed")
                result = retrieve(db, runtime, query, limit=5, skip_dense=overlong)
                hits = []
                for candidate in result.candidates:
                    chunk = db.scalar(
                        select(AssistantChunk).where(
                            AssistantChunk.generation_id == generation_id,
                            AssistantChunk.chunk_id == candidate.chunk_id,
                        )
                    )
                    if chunk is None:
                        raise RuntimeError("retrieved chunk disappeared")
                    current = project_source(db, chunk.source_type, chunk.source_id)
                    source_key = (chunk.source_type, chunk.source_id)
                    document_id = published.get(source_key)
                    valid = (
                        current is not None
                        and current.source_version == chunk.source_version
                        and current.public_path == chunk.public_path
                        and document_id is not None
                        and (
                            (chunk.source_type == "profile" and chunk.public_path == "/")
                            or (
                                chunk.source_type == "article"
                                and chunk.public_path.endswith("/" + document_id)
                            )
                        )
                    )
                    hits.append(
                        Hit(
                            document_id=document_id or "unknown",
                            chunk_id=chunk.chunk_id,
                            content=chunk.page_content,
                            path=chunk.public_path,
                            version=chunk.source_version,
                            citation_valid=valid,
                            sources=list(candidate.sources),
                        )
                    )
                results.append(
                    {
                        "id": q.id,
                        "direction": f"{q.query_language}->{q.target_language}",
                        "kind": q.kind,
                        "question": q.question,
                        "status": result.status,
                        "overlong": overlong,
                        "query_tokens": runtime.embeddings.tokenizer.count("query: " + query),
                        **score_question(q, hits),
                        "hits": [h.model_dump() for h in hits],
                    }
                )
            return results, {
                "generation": generation_id,
                "collection": generation.collection_name,
                "documents": len(documents),
                "chunks": len(indexed_ids),
                "vectors": len(indexed_ids),
                "gate": gate,
            }
    finally:
        runtime.store.client.close()
        database.engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--env-file", default=".env.e5")
    parser.add_argument(
        "--output", type=Path, required=True, help="new directory; existing paths refused"
    )
    parser.add_argument(
        "--review-only", action="store_true", help="validate labels and render without services"
    )
    args = parser.parse_args(argv)
    dataset = load_dataset(args.dataset)
    digest = sha256(args.dataset)
    base = None if args.review_only else load_settings(args.env_file)
    output = reserve_output(args.output)
    (output / "review.md").write_text(review_markdown(dataset, digest, []), encoding="utf-8")
    if base is None:
        print(json.dumps({"review": str(output / "review.md"), "dataset_sha256": digest}))
        return 0
    results: list[dict] = []
    corpora = {}
    try:
        for language in ("zh", "en"):
            directory = output / language
            directory.mkdir()
            settings = isolated_settings(
                base, directory, f"e5_eval_{secrets.token_hex(12)}_{language}"
            )
            rows, identity = run_corpus(settings, dataset, language)
            results.extend(rows)
            corpora[language] = identity
        summary = summarize(dataset, digest, results, corpora)
        if sha256(args.dataset) != digest:
            raise RuntimeError("dataset changed during evaluation")
        (output / "results.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (output / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (output / "review.md").write_text(
            review_markdown(dataset, digest, results), encoding="utf-8"
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["run_valid"] and summary["draft_recall_target_met"] else 1
    except Exception as exc:
        # Do not serialize provider URLs, credentials, prompts or exception messages.
        (output / "failure.json").write_text(
            json.dumps(
                {
                    "dataset_sha256": digest,
                    "run_valid": False,
                    "error_type": type(exc).__name__,
                    "phase_d_passed": False,
                    "production_qualified": False,
                }
            ),
            encoding="utf-8",
        )
        print(json.dumps({"run_valid": False, "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

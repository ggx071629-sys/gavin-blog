from __future__ import annotations

import copy
import json

import pytest
from pydantic import ValidationError

from app.local_embedding.evaluation import (
    DEFAULT_DATASET,
    Dataset,
    Gold,
    Hit,
    inspect_gate,
    isolated_settings,
    load_dataset,
    main,
    publish_corpus,
    reserve_output,
    review_markdown,
    score_question,
    summarize,
)


def test_dataset_rejects_invalid_labels_and_renders_all_cases():
    dataset = load_dataset(DEFAULT_DATASET)
    assert len(dataset.questions) == 46
    assert len(dataset.documents) == 42
    review = review_markdown(dataset, "digest", [])
    assert "待人工复核" in review and "拒答须在后续 Chat 验收" in review
    assert all(q.id in review and q.question in review for q in dataset.questions)
    mutations = [
        lambda d: d["documents"].append(d["documents"][0]),
        lambda d: d["questions"].append(d["questions"][0]),
        lambda d: d["questions"].pop(0),
        lambda d: d["questions"][0]["gold"][0].update(document_id="missing"),
        lambda d: d["questions"][0]["gold"][0].update(evidence="invented answer"),
        lambda d: d["questions"][0]["gold"][0].update(evidence=" "),
        lambda d: d["questions"][0].update(target_language="en"),
        lambda d: d["questions"][0].update(gold=[]),
        lambda d: d["questions"].pop(-1),
        lambda d: d.update(annotation_status="human_approved"),
    ]
    for mutate in mutations:
        invalid = copy.deepcopy(dataset.model_dump())
        mutate(invalid)
        with pytest.raises(ValidationError):
            Dataset.model_validate(invalid)


def test_isolation_publishes_only_to_fresh_database(tmp_path, client):
    import sqlite3

    from sqlalchemy import select

    from app.db import Database
    from app.models import Article

    base = client.app.state.settings
    original = base.model_dump()
    sentinel = tmp_path / "sentinel"
    sentinel.mkdir()
    (sentinel / "keep.txt").write_text("unchanged")
    with pytest.raises(FileExistsError):
        reserve_output(sentinel)
    assert (sentinel / "keep.txt").read_text() == "unchanged"
    output = reserve_output(tmp_path / "evaluation")
    settings = isolated_settings(base, output, "eval_test_unique")
    assert base.model_dump() == original
    assert settings.database_url != base.database_url
    assert settings.media_root != base.media_root
    assert not settings.assistant_online_enabled
    dataset = load_dataset(DEFAULT_DATASET)
    docs = dataset.documents[:2] + [dataset.documents[-2]]
    mapping = publish_corpus(settings, docs)
    assert set(mapping.values()) == {d.id for d in docs}
    assert mapping[("article", 1)] != mapping[("profile", 1)]
    db = Database(settings.database_url)
    try:
        with db.session_factory() as session:
            articles = list(session.scalars(select(Article)))
            assert len(articles) == 2 and all(a.status == "published" for a in articles)
        with client.app.state.database.session_factory() as session:
            assert list(session.scalars(select(Article))) == []
    finally:
        db.engine.dispose()
    with sqlite3.connect(settings.assistant_runtime_path) as connection:
        connection.execute(
            "CREATE TABLE assistant_operational_gate (id INTEGER, requested_state TEXT, "
            "effective_state TEXT, switch_pending_operation_id TEXT)"
        )
        connection.execute(
            "INSERT INTO assistant_operational_gate VALUES (1, 'disabled', 'disabled', NULL)"
        )
    assert inspect_gate(settings) == "disabled"
    for state, pending in [("enabled", None), ("blocked", None), ("disabled", "pending")]:
        with sqlite3.connect(settings.assistant_runtime_path) as connection:
            connection.execute(
                "UPDATE assistant_operational_gate SET effective_state=?, "
                "switch_pending_operation_id=?",
                (state, pending),
            )
        with pytest.raises(RuntimeError, match="gate"):
            inspect_gate(settings)


def test_metrics_deduplicate_documents_and_require_evidence_and_current_citation():
    dataset = load_dataset(DEFAULT_DATASET)
    question = dataset.questions[0].model_copy(deep=True)
    first = question.gold[0]
    question.gold.append(Gold(document_id="second-relevant", evidence="second span"))

    def hit(doc, text, valid=True):
        return Hit(
            document_id=doc,
            content=text,
            chunk_id="chunk",
            path="/notes/example",
            version="2",
            citation_valid=valid,
            sources=["dense"],
        )

    hits = [hit(first.document_id, "wrong span")] * 2
    score = score_question(question, hits)
    assert score["recall_at_5"] == 0.5 and score["evidence_recall_at_5"] == 0
    hits += [hit("second-relevant", "second span", False)]
    assert score_question(question, hits)["recall_at_5"] == 0.5
    assert not score_question(question, hits)["citations_valid"]
    hits += [hit(first.document_id, first.evidence), hit("second-relevant", "second span")]
    assert score_question(question, hits)["evidence_recall_at_5"] == 1
    assert score_question(question, [hit("other", "noise")] * 5 + hits)["recall_at_5"] == 0
    negative = next(q for q in dataset.questions if q.kind == "no_evidence")
    score = score_question(negative, hits)
    assert score["recall_at_5"] is None and score["evidence_recall_at_5"] is None
    assert score["unsupported_neighbors"] == 5 and not score["refusal_evaluated"]


def test_reports_never_qualify_drafts_and_fail_on_drift(tmp_path, monkeypatch):
    from app.local_embedding import evaluation

    dataset = load_dataset(DEFAULT_DATASET)
    rows = [
        {
            "id": q.id,
            "direction": f"{q.query_language}->{q.target_language}",
            "status": "degraded" if q.kind == "long" else "ok",
            "overlong": q.kind == "long",
            "recall_at_5": 1 if q.gold else None,
            "evidence_recall_at_5": 1 if q.gold else None,
            "citations_valid": True,
        }
        for q in dataset.questions
    ]
    summary = summarize(dataset, "digest", rows, {"zh": {"generation": 7}})
    assert summary["run_valid"] and summary["draft_recall_target_met"]
    assert not summary["phase_d_passed"] and not summary["production_qualified"]
    assert summary["dataset_sha256"] == "digest"
    assert summary["corpora"]["zh"]["generation"] == 7
    for changed in [{"status": "degraded"}, {"citations_valid": False}, {"status": "not_ready"}]:
        broken = copy.deepcopy(rows)
        broken[0].update(changed)
        assert not summarize(dataset, "digest", broken, {})["run_valid"]
    with pytest.raises(ValueError, match="missing or duplicated"):
        summarize(dataset, "digest", rows[:-1], {})
    review_dir = tmp_path / "review"
    assert main(["--review-only", "--output", str(review_dir)]) == 0
    assert (review_dir / "review.md").exists()
    # A provider exception must leave an explicit failed run, without leaking its message.
    monkeypatch.setattr(evaluation, "load_settings", lambda _: object())
    monkeypatch.setattr(evaluation, "isolated_settings", lambda *args: object())

    def fail(*args):
        raise RuntimeError("secret-provider-token")

    monkeypatch.setattr(evaluation, "run_corpus", fail)
    failed = tmp_path / "failed"
    assert main(["--output", str(failed)]) == 1
    report = (failed / "failure.json").read_text()
    assert "secret-provider-token" not in report
    assert not json.loads(report)["run_valid"]
    assert not (failed / "summary.json").exists()

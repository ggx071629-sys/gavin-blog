"""Offline candidate comparison. No changes to the runtime validator or policy.

Run from apps/api with its virtualenv Python. Results are diagnostics, not a
population accuracy estimate, independent benchmark or production approval.
"""
from __future__ import annotations

import json
import re
import socket
import sys
import time
import unicodedata
from pathlib import Path


def deny_network(*_args, **_kwargs):
    raise RuntimeError("network disabled for grounding comparison")


socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps/api"))

from app.assistant.hydrate import Evidence  # noqa: E402
from app.assistant.output import validate_model_answer  # noqa: E402
from app.assistant.providers import ModelAnswer  # noqa: E402


def baseline(row):
    def item(body, alias):
        return Evidence(alias, "synthetic-" + alias, "合成资料", "说明",
                        "/projects/demo", body, row["source_type"], 1, "v1", 1, ("fts",))

    evidence = [item(row["source"], "c1")]
    if row["other_source"]:
        evidence.append(item(row["other_source"], "c2"))
    parsed = ModelAnswer.model_validate({"blocks": [{
        "text": row["answer"], "citation_ids": ["c1"],
        "supports": [{"citation_id": "c1", "quote": row["quote"]}],
    }]})
    result = validate_model_answer(parsed, evidence, finish_reason="stop")
    return not isinstance(result, str)


def key(text, *, normalize=False):
    text = unicodedata.normalize("NFKC", text)
    if normalize:
        # A deliberately limited alternative, not a general semantic model.
        text = re.sub(r"使用|采用", "用", text)
        text = text.replace("与", "和")
        text = text.replace("SQLite 数据库", "SQLite").replace("SQLite数据库", "SQLite")
    return re.sub(r"\s+|[。！？!?；;]", "", text).casefold().rstrip(".")


def exact_support(row, *, normalize=False):
    if not row["quote"].strip() or row["quote"] not in row["source"]:
        return False
    # Full source clauses are retained; arbitrary substring inclusion would
    # accept removal of a leading negation or qualifying phrase.
    clauses = re.split(r"[。！？!?；;\n]", row["source"])
    supported = {key(c, normalize=normalize) for c in [row["source"], *clauses] if c.strip()}
    return key(row["answer"], normalize=normalize) in supported


def main():
    source = Path(__file__).with_name("grounding-pairs.json")
    rows = json.loads(source.read_text(encoding="utf-8"))["cases"]
    strategies = {
        "current_runtime": baseline,
        "exact_complete_clause": exact_support,
        "bounded_paraphrase": lambda row: exact_support(row, normalize=True),
    }
    report = {"live_provider_calls": 0, "network": "denied", "cases": len(rows),
              "scope": "diagnostic sample only; no production accuracy claim",
              "strategies": {}}
    for name, strategy in strategies.items():
        started = time.perf_counter()
        outcomes = [{"id": r["id"], "expected_accept": r["expected_accept"],
                     "accepted": strategy(r)} for r in rows]
        report["strategies"][name] = {
            "false_accepts": [r["id"] for r in outcomes if r["accepted"] and not r["expected_accept"]],
            "false_rejections": [r["id"] for r in outcomes if not r["accepted"] and r["expected_accept"]],
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "outcomes": outcomes,
        }
    target = ROOT / "apps/api/data/qa-gap-closure-q2-01-comparison.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: {"false_accepts": v["false_accepts"],
                            "false_rejections": v["false_rejections"],
                            "elapsed_ms": v["elapsed_ms"]}
                      for name, v in report["strategies"].items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()

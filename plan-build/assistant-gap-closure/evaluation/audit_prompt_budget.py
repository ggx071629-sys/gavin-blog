"""Offline calibration using local official data and retained synthetic G07 results."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps/api"))

from app.assistant.prompt import build_prompt  # noqa: E402
from app.assistant.prompt_budget import (  # noqa: E402
    input_accounting,
    output_accounting,
    wire_messages,
)
from app.config import Settings  # noqa: E402

TOKENIZER_SHA = "89085f12ef79460ac5f66d1119325ddfc694b4ab209d80bbd81d35f081dc9614"
CONFIG_SHA = "841f8cf146e3f0ad1082594a31f68ecf7608c20467ef355081333d85bbaeb1cb"


def read_verified(path: Path, expected_sha: str) -> bytes:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise ValueError("calibration input digest mismatch")
    return data


def official_text_template(messages: list[dict[str, str]], config: dict) -> str:
    # Text-only branch of the SHA-pinned official template. No downloaded code
    # or template is executed. Tool and assistant-history branches are excluded.
    if [m["role"] for m in messages] != ["system", "system", "user"]:
        raise ValueError("unsupported calibration message shape")
    return (config["bos_token"]["content"]
            + "\n\n".join(m["content"] for m in messages[:2])
            + "<\uff5cUser\uff5c>" + messages[-1]["content"] + "<\uff5cAssistant\uff5c>")


def main() -> None:
    from tokenizers import Tokenizer

    local = ROOT / "apps/api/data/g12-tokenizer"
    data = read_verified(local / "tokenizer.json", TOKENIZER_SHA)
    config = json.loads(read_verified(local / "tokenizer_config.json", CONFIG_SHA))
    tokenizer = Tokenizer.from_str(data.decode("utf-8"))
    def count(text):
        return len(tokenizer.encode(text, add_special_tokens=False).ids)
    # Retained controls already have byte-identical prompt provenance recorded
    # by G07. Reject drift in both prompt and challenge construction before reuse.
    for path in ["apps/api/app/assistant/prompt.py",
                 "plan-build/assistant-gap-closure/evaluation/run_injection_challenges.py"]:
        old = subprocess.check_output(["git", "show", f"484f00c:{path}"], cwd=ROOT)
        if old.replace(b"\r\n", b"\n") != (ROOT / path).read_bytes().replace(b"\r\n", b"\n"):
            raise ValueError("retained prompt construction has changed")
    spec = importlib.util.spec_from_file_location("g12_g07", Path(__file__).with_name(
        "run_injection_challenges.py"))
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    settings = Settings(_env_file=ROOT / "apps/api/.env")
    contract, chat, prepared = runner.prepare(settings)
    status = json.loads(Path(__file__).with_name("G07-status.json").read_text(encoding="utf-8"))
    acceptance = status["final_acceptance"]
    sources = {r["case_id"]: (ROOT / "apps/api" / r["raw_file"], r["raw_sha256"])
               for r in acceptance["rows"]}
    attack = next((row for row in status["revalidation_attempts"]
                   if row.get("review_status") == "bounded_attack_sample_passed"), None)
    if not attack or attack["source_commit"] != "484f00c":
        raise ValueError("missing reviewed attack source")
    results = []
    for row, question, evidence, messages, _ in prepared:
        path, sha = sources.get(
            row["id"], (ROOT / attack["raw_result_local_path"], attack["sha256"]),
        )
        raw = next(r for r in json.loads(read_verified(path, sha))["rows"] if r["id"] == row["id"])
        if raw.get("text") != row["text"] or not raw["transport_ok"]:
            raise ValueError("retained sample identity or usage invalid")
        history = ([{"question": "继续说明", "answer": row["text"]}]
                   if row["surface"] == "history" else [])
        built = build_prompt(question=question, evidence=evidence, history=history, provider=chat,
                             max_input_tokens=8000, max_output_tokens=512,
                             context_window_tokens=contract.context_window_tokens)
        built = replace(built, messages=messages)
        metrics = input_accounting(question=question, candidates=evidence, built=built,
                                   provider=chat, count_text=count)
        local_tokens = count(official_text_template(wire_messages(messages, chat), config))
        results.append({"id": row["id"], "kind": row["kind"], "input": metrics,
                        "official_template_tokens": local_tokens,
                        "provider_input_tokens": raw["input_tokens"],
                        "template_minus_provider_tokens": local_tokens - raw["input_tokens"],
                        "provider_output_tokens": raw["output_tokens"],
                        "output": output_accounting(raw["raw_output"], count_text=count),
                        "finish_reason": raw["finish_reason"],
                        "raw_sha256": sha})
    minimum = []
    evidence = prepared[0][2][:1]
    evidence = [replace(evidence[0], body=runner.BODY)]
    for language, question in [("zh", "文章如何介绍邮件通知？"),
                               ("en", "How does the article describe email notifications?")]:
        for availability in [None, False]:
            args = dict(question=question, evidence=evidence, history=[], provider=chat,
                        max_output_tokens=512, resume_available=availability)
            built = build_prompt(**args, max_input_tokens=100000, context_window_tokens=100512)
            bound = built.estimated_tokens
            assert build_prompt(**args, max_input_tokens=bound, context_window_tokens=bound + 512)
            assert build_prompt(**args, max_input_tokens=bound - 1,
                                context_window_tokens=bound + 512) is None
            assert build_prompt(**args, max_input_tokens=bound,
                                context_window_tokens=bound + 511) is None
            minimum.append({"language": language, "resume_available": availability,
                            "minimum_example_input": bound, "output_reserved": 512,
                            "fits_current_8000": bound <= 8000})
    report = {"scope": "24 retained synthetic responses; calibration only, no admission change",
              "tokenizer_source": "https://cdn.deepseek.com/api-docs/deepseek_v4_tokenizer.zip",
              "tokenizer_sha256": TOKENIZER_SHA, "config_sha256": CONFIG_SHA,
              "provider_version_proven": False, "new_model_calls": 0,
              "minimum_examples": minimum,
              "two_chat_attempt_reserve_micro_cny": 2 * (
                  runner.probe._micro_cost(contract.max_input_tokens,
                                          contract.input_price_micro_cny_per_million)
                  + runner.probe._micro_cost(contract.max_output_tokens,
                                            contract.output_price_micro_cny_per_million)),
              "rows": results}
    output = ROOT / "apps/api/data/g12-budget-calibration.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(results), "output": str(output), "new_model_calls": 0}))


if __name__ == "__main__":
    main()

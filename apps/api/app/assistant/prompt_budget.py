"""Offline numeric accounting. This does not change prompt selection or admission."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .hydrate import Evidence
from .prompt import PromptBuild, _escaped, _evidence_block, _history_block, estimate_tokens
from .providers import LocalDeepSeekChatOpenAI, ModelAnswer, _JsonAnswer, answer_schema_instruction


def wire_messages(messages: list[tuple[str, str]], provider: Any) -> list[dict[str, str]]:
    values = list(messages)
    if isinstance(provider, LocalDeepSeekChatOpenAI):
        values.insert(0, ("system", answer_schema_instruction()))
    return [{"role": "user" if role == "human" else role, "content": body}
            for role, body in values]


def input_accounting(
    *, question: str, candidates: list[Evidence], built: PromptBuild,
    provider: Any, count_text: Callable[[str], int],
) -> dict:
    wire = wire_messages(built.messages, provider)
    # Reconstruct the existing estimator envelope without interpreting tokenizer
    # counts as additive or weakening its byte fallback.
    schema = json.dumps(ModelAnswer.model_json_schema(), sort_keys=True, separators=(",", ":"))
    roles = ["human" if m["role"] == "user" else m["role"] for m in wire]
    serialized = schema + "\n" + "\n".join(
        f"{role}:{m['content']}" for role, m in zip(roles, wire, strict=True)
    )
    parts = {
        "system_prompt": built.messages[0][1],
        "question": _escaped(question),
        "selected_history": "\n\n".join(
            _history_block(i + 1, pair) for i, pair in enumerate(built.history)
        ),
        "selected_evidence": "\n\n".join(_evidence_block(e) for e in built.evidence),
    }
    byte_parts = {name: len(text.encode("utf-8")) for name, text in parts.items()}
    byte_parts["framing_and_schema"] = len(serialized.encode("utf-8")) - sum(byte_parts.values())
    assert byte_parts["framing_and_schema"] >= 0
    candidate_text = "\n\n".join(_evidence_block(e) for e in candidates)
    return {
        "component_utf8_bytes": byte_parts,
        "component_text_tokens_nonadditive": {k: count_text(v) for k, v in parts.items()},
        "candidate_evidence_utf8_bytes": len(candidate_text.encode("utf-8")),
        "candidate_evidence_text_tokens": count_text(candidate_text),
        "candidate_evidence_count": len(candidates),
        "selected_evidence_count": len(built.evidence),
        "selected_history_pairs": len(built.history),
        "serialized_utf8_bytes": len(serialized.encode("utf-8")),
        "byte_fallback_tokens": len(serialized.encode("utf-8")) + 16 + 4 * len(wire),
        "admission_estimated_tokens": estimate_tokens(built.messages, provider),
        "serialized_text_tokens": count_text(serialized),
    }


def output_accounting(raw: str, *, count_text: Callable[[str], int]) -> dict:
    result = {"utf8_bytes": len(raw.encode("utf-8")), "text_tokens": count_text(raw)}
    try:
        parsed = _JsonAnswer.model_validate_json(raw, strict=True)
    except ValueError:
        return {**result, "valid_structure": False, "nonempty": False}
    answers = "".join(b.text for b in parsed.blocks)
    quotes = "".join(s.quote for b in parsed.blocks for s in b.supports)
    encoded = json.dumps(parsed.model_dump(), ensure_ascii=False, separators=(",", ":"))
    text_bytes = len(answers.encode("utf-8"))
    quote_bytes = len(quotes.encode("utf-8"))
    return {
        **result, "valid_structure": True,
        "nonempty": bool(parsed.blocks) and all(b.text.strip() for b in parsed.blocks),
        "answer_utf8_bytes": text_bytes, "supports_utf8_bytes": quote_bytes,
        "json_and_citations_utf8_bytes": len(encoded.encode("utf-8")) - text_bytes - quote_bytes,
        "canonical_json_utf8_bytes": len(encoded.encode("utf-8")),
        "answer_text_tokens": count_text(answers), "supports_text_tokens": count_text(quotes),
    }

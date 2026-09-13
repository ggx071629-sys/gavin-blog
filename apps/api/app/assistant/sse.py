from __future__ import annotations

import json

from .constants import (
    STAGE_EVENTS,
    TERMINAL_ANSWER,
    TERMINAL_ERROR,
    TERMINAL_EVENTS,
    TERMINAL_REFUSAL,
)

ALLOWED_EVENTS = set(STAGE_EVENTS) | set(TERMINAL_EVENTS)
_STAGE_FIELDS = frozenset({"event_id", "turn_id", "stage"})
_REFUSAL_FIELDS = frozenset({"event_id", "turn_id", "type", "code", "message"})
_ANSWER_FIELDS = _REFUSAL_FIELDS | frozenset({"answer", "citations", "sources"})


def project_public_event(event_name: str, data: dict) -> dict:
    """Strip internal journal fields before they leave the process."""
    if event_name in STAGE_EVENTS:
        allowed = _STAGE_FIELDS
    elif event_name in {TERMINAL_REFUSAL, TERMINAL_ERROR}:
        allowed = _REFUSAL_FIELDS
    elif event_name == TERMINAL_ANSWER:
        allowed = _ANSWER_FIELDS
    else:
        raise ValueError("unsupported assistant event")
    projected = {key: data[key] for key in allowed if key in data}
    if event_name in STAGE_EVENTS:
        projected.setdefault("stage", event_name)
    if event_name in TERMINAL_EVENTS:
        projected.setdefault("type", event_name)
    return projected


def encode_sse(*, event_id: int, event_name: str, data: dict) -> str:
    if event_name not in ALLOWED_EVENTS:
        raise ValueError("unsupported assistant event")
    projected = project_public_event(event_name, data)
    payload = json.dumps(projected, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("\r", "\\r").replace("\n", "\\n")
    if "\n" in payload or "\r" in payload:
        raise ValueError("SSE data must be single-line JSON")
    return f"id: {event_id}\nevent: {event_name}\ndata: {payload}\n\n"


def parse_event_payload(data_json: str) -> dict:
    payload = json.loads(data_json)
    if not isinstance(payload, dict):
        raise ValueError("assistant event payload must be an object")
    return payload

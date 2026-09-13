"""Renew an approved configuration for an audited index, inside the API owner.

This is not initial production qualification: the previous signed receipt must
still verify against every non-generation binding. No Chat or embedding calls.
"""

from __future__ import annotations

import json
from contextlib import nullcontext

from sqlalchemy import text

from ..assistant_index.integrity import active_generation, audit_generation
from ..content_write_fence import content_write_fence
from ..http_errors import ApiException
from .admin_scope import admin_stopped
from .crypto import hmac_hex, random_id
from .operational import gate_row
from .readiness import _Gen, receipt_payload, verify_receipt
from .recovery import online_lock_until
from .store import breaker_open, current_receipt


def _conditions(conn, online, expected_version):
    gate = gate_row(conn)
    if gate is None or gate["version"] != expected_version:
        raise ApiException(409, "readiness_state_changed", "运行状态已变化，请刷新后重新校验。")
    if gate.get("switch_pending_operation_id"):
        raise ApiException(409, "readiness_switch_pending", "索引仍在切换，请等待切换完成。")
    if (
        gate["requested_state"] != "disabled"
        or gate["effective_state"] == "enabled"
        or not admin_stopped(conn)
    ):
        raise ApiException(409, "readiness_stop_required", "请先停止全部问答，再校验运行资格。")
    until = online_lock_until(conn)
    if breaker_open(conn) or (until is not None and online.now() < until):
        raise ApiException(
            409, "readiness_maintenance_blocked", "清理或恢复保护尚未解除，请稍后再试。"
        )
    busy = sum(
        conn.execute(query).fetchone()[0]
        for query in (
            "SELECT COUNT(*) FROM assistant_attempts WHERE status IN ('prepared', 'sending')",
            "SELECT COUNT(*) FROM assistant_turns WHERE status IN ('accepted', 'running')",
            "SELECT COUNT(*) FROM checkpoints",
            "SELECT COUNT(*) FROM writes",
        )
    )
    if busy:
        raise ApiException(
            409, "readiness_cleanup_pending", "仍有在途问答或会话等待清理，请稍后重试。"
        )
    receipt = current_receipt(conn)
    if receipt is None:
        raise ApiException(
            409, "readiness_initial_required", "缺少已批准的资格，请先在服务器完成首次资格验证。"
        )
    try:
        payload = json.loads(receipt["receipt_json"])
        verify_receipt(online.settings, conn, _Gen(payload["generation"]))
    except Exception as exc:
        raise ApiException(
            409,
            "readiness_configuration_changed",
            "原资格无法验证或运行配置已变化，需要在服务器重新完成部署资格验证。",
        ) from exc
    return receipt


def renew_index_readiness(
    online,
    *,
    expected_generation_id: int,
    expected_version: int,
    content_fence_held=False,
) -> dict:
    if online is None:
        raise ApiException(503, "assistant_runtime_unavailable", "问答服务尚未启动。")
    # Middleware owns this fence for the HTTP route. CLI/test callers acquire it here.
    fence = nullcontext() if content_fence_held else content_write_fence(online.settings)
    with fence, online.database.session_factory() as db:
        # The shared content fence excludes publishers, Worker and index switches.
        # A read snapshot also lets runtime settlement hooks update budget rows.
        db.execute(text("BEGIN"))
        try:
            generation = active_generation(db)
        except RuntimeError as exc:
            raise ApiException(
                409, "readiness_index_missing", "当前没有可校验的活动索引。"
            ) from exc
        if generation.id != expected_generation_id:
            raise ApiException(
                409, "readiness_generation_changed", "活动索引已变化，请刷新后重新校验。"
            )
        before = online.control.read(lambda conn: _conditions(conn, online, expected_version))
        try:
            online.settings.validate_runtime()
        except Exception as exc:
            raise ApiException(
                409,
                "readiness_configuration_invalid",
                "运行配置校验未通过，请检查服务器部署配置。",
            ) from exc
        try:
            report = audit_generation(db, online.index_runtime, generation)
            report.require_passed()
        except Exception as exc:
            raise ApiException(
                409,
                "readiness_index_invalid",
                "索引完整性校验未通过，请检查内容同步、切片和向量服务后重试。",
            ) from exc

        def issue(conn):
            current = _conditions(conn, online, expected_version)
            if current["id"] != before["id"]:
                raise ApiException(409, "readiness_state_changed", "资格已变化，请刷新后重新校验。")
            payload = receipt_payload(
                online.settings, probed_at=online.now(), generation=generation
            )
            old_payload = json.loads(current["receipt_json"])
            if old_payload["generation"] != payload["generation"]:
                canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
                signature = hmac_hex(
                    str(online.settings.assistant_readiness_hmac_secret),
                    canonical,
                    context="assistant-receipt",
                )
                conn.execute(
                    "UPDATE assistant_readiness_receipts SET revoked_at=? WHERE revoked_at IS NULL",
                    (online.now(),),
                )
                conn.execute(
                    "INSERT INTO assistant_readiness_receipts "
                    "(id,receipt_json,receipt_hmac,created_at) VALUES (?,?,?,?)",
                    (random_id(), canonical, signature, online.now()),
                )
            verify_receipt(online.settings, conn, generation)
            return {"qualified": True, "generation_id": generation.id}

        # Recheck emergency-stop/version, cleanup and receipt races after the audit.
        # All writes are in one runtime transaction; both execution gates stay stopped.
        return online.control.immediate(issue)

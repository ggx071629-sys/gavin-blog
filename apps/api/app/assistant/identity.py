from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .admin_scope import scope_permitted


@dataclass(frozen=True)
class ExecutionIdentity:
    session_id: str
    fencing_epoch: int
    turn_id: str
    thread_id: str
    fencing_token: str
    operational_epoch: int

    def as_state(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "fencing_epoch": self.fencing_epoch,
            "turn_id": self.turn_id,
            "thread_id": self.thread_id,
            "fencing_token": self.fencing_token,
            "operational_epoch": self.operational_epoch,
        }


def identity_from_turn(turn: dict[str, Any]) -> ExecutionIdentity | None:
    epoch = turn.get("execution_epoch")
    token = turn.get("execution_token")
    thread_id = turn.get("thread_id")
    operational_epoch = turn.get("operational_epoch")
    if epoch is None or operational_epoch is None or not token or not thread_id:
        return None
    return ExecutionIdentity(
        session_id=str(turn["session_id"]),
        fencing_epoch=int(epoch),
        turn_id=str(turn["id"]),
        thread_id=str(thread_id),
        fencing_token=str(token),
        operational_epoch=int(operational_epoch),
    )


def normal_mutation_permit(conn, identity: ExecutionIdentity, now: datetime) -> bool:
    row = conn.execute(
        """
        SELECT t.status, t.thread_id, t.execution_epoch, t.execution_token, t.ip_hmac,
               t.operational_epoch, s.fencing_epoch, s.tombstoned_at,
               s.idle_expires_at, s.absolute_expires_at
        FROM assistant_turns AS t
        JOIN assistant_sessions AS s ON s.id = t.session_id
        WHERE t.id = ? AND t.session_id = ?
        """,
        (identity.turn_id, identity.session_id),
    ).fetchone()
    if row is None or row["status"] not in {"accepted", "running"}:
        return False
    if row["thread_id"] != identity.thread_id:
        return False
    if int(row["execution_epoch"] if row["execution_epoch"] is not None else -1) != int(
        identity.fencing_epoch
    ):
        return False
    if row["execution_token"] != identity.fencing_token:
        return False
    gate = conn.execute(
        "SELECT effective_state, operational_epoch, switch_pending_operation_id "
        "FROM assistant_operational_gate WHERE id = 1"
    ).fetchone()
    if (
        gate is None
        or not scope_permitted(conn, gate, identity.session_id, identity.operational_epoch)
        or int(row["operational_epoch"] if row["operational_epoch"] is not None else -1)
        != identity.operational_epoch
    ):
        return False
    if int(row["fencing_epoch"]) != identity.fencing_epoch or row["tombstoned_at"] is not None:
        return False
    idle = row["idle_expires_at"]
    absolute = row["absolute_expires_at"]
    if isinstance(idle, str):
        idle = datetime.fromisoformat(idle)
    if isinstance(absolute, str):
        absolute = datetime.fromisoformat(absolute)
    if idle <= now or absolute <= now:
        return False
    leases = conn.execute(
        """
        SELECT scope, scope_key FROM assistant_leases
        WHERE owner_turn_id = ? AND fencing_token = ? AND expires_at > ?
        """,
        (identity.turn_id, identity.fencing_token, now),
    ).fetchall()
    expected = {
        ("session", identity.session_id),
        ("ip", str(row["ip_hmac"] or "")),
        ("global", "all"),
    }
    actual = {(str(item["scope"]), str(item["scope_key"])) for item in leases}
    return bool(row["ip_hmac"]) and len(leases) == 3 and actual == expected


def publish_receipt_valid(conn, receipt: dict[str, Any], now: datetime) -> bool:
    identity = ExecutionIdentity(
        session_id=str(receipt["session_id"]),
        fencing_epoch=int(receipt["fencing_epoch"]),
        turn_id=str(receipt["turn_id"]),
        thread_id=str(receipt["thread_id"]),
        fencing_token=str(receipt["fencing_token"]),
        operational_epoch=int(receipt["operational_epoch"]),
    )
    row = conn.execute(
        "SELECT status, terminal_event, session_id, thread_id, execution_epoch, "
        "execution_token FROM assistant_turns WHERE id = ?",
        (identity.turn_id,),
    ).fetchone()
    if row is None:
        return False
    if receipt.get("terminal"):
        gate = conn.execute(
            "SELECT effective_state, operational_epoch, switch_pending_operation_id "
            "FROM assistant_operational_gate WHERE id = 1"
        ).fetchone()
        session = conn.execute(
            "SELECT fencing_epoch, tombstoned_at FROM assistant_sessions WHERE id = ?",
            (identity.session_id,),
        ).fetchone()
        return bool(
            session
            and gate
            and scope_permitted(conn, gate, identity.session_id, identity.operational_epoch)
            and session["tombstoned_at"] is None
            and int(session["fencing_epoch"]) == identity.fencing_epoch
            and row["session_id"] == identity.session_id
            and row["thread_id"] == identity.thread_id
            and int(row["execution_epoch"] if row["execution_epoch"] is not None else -1)
            == identity.fencing_epoch
            and row["execution_token"] == identity.fencing_token
            and row["status"] == "terminal"
            and row["terminal_event"] == receipt.get("event_name")
        )
    return normal_mutation_permit(conn, identity, now)

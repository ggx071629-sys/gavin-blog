"""One body-free vote per live answer, with the answer's original expiry."""

from __future__ import annotations

from datetime import timedelta

from .constants import BODY_RETENTION_SECONDS
from .errors import assistant_error, invalid_request, session_expired
from .time_beijing import beijing_date


def set_feedback(conn, *, session, turn_id, value, now):
    from .store import get_session, get_turn, public_completed_turn_at, session_is_live

    if value not in {None, "helpful", "unhelpful"}:
        raise invalid_request()
    current = get_session(conn, session["id"])
    if (
        not current
        or not session_is_live(conn, session["id"], now)
        or current["fencing_epoch"] != session["fencing_epoch"]
    ):
        raise session_expired()
    turn = get_turn(conn, turn_id)
    if (
        not turn
        or turn["session_id"] != session["id"]
        or turn["status"] != "terminal"
        or turn["terminal_event"] != "answer"
        or not public_completed_turn_at(turn, now)["body_available"]
    ):
        raise assistant_error(404, "feedback_unavailable", "This answer cannot receive feedback.")
    event_id = f"{turn_id}:feedback"
    conn.execute("DELETE FROM assistant_activity_events WHERE event_id = ?", (event_id,))
    if value is not None:
        # created_at is the original terminal time: changing a vote never extends TTL.
        conn.execute(
            "INSERT INTO assistant_activity_events "
            "(event_id, beijing_date, kind, outcome, created_at) VALUES (?, ?, 'feedback', ?, ?)",
            (event_id, beijing_date(now).isoformat(), value, turn["terminal_at"]),
        )
    return {"turn_id": turn_id, "value": value}


def feedback_summary(conn, now):
    rows = conn.execute(
        "SELECT a.outcome, COUNT(*) AS n FROM assistant_activity_events a "
        "JOIN assistant_turns t ON a.event_id = t.id || ':feedback' "
        "JOIN assistant_sessions s ON s.id = t.session_id "
        "WHERE a.kind = 'feedback' AND t.body_purged_at IS NULL "
        "AND t.terminal_at > ? AND s.tombstoned_at IS NULL "
        "AND s.idle_expires_at > ? AND s.absolute_expires_at > ? GROUP BY a.outcome",
        (now - timedelta(seconds=BODY_RETENTION_SECONDS), now, now),
    ).fetchall()
    counts = {row["outcome"]: row["n"] for row in rows}
    return {"helpful": counts.get("helpful", 0), "unhelpful": counts.get("unhelpful", 0)}

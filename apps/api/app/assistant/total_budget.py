"""One atomic spending authority, shared with Worker through the content DB.

Runtime reservations commit here BEFORE runtime admission. A crash can strand a
reservation, never release it. Terminal receipts are copied only AFTER runtime
commit. Missing/rolled-back runtime rows never release common reservations.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select, text

from ..http_errors import ApiException
from ..models import AssistantBudgetPolicy, AssistantBudgetReservation
from .money import cny_to_micro, tokens_cost_micro
from .time_beijing import beijing_date

ZERO = Decimal("0")


def ceiling(settings) -> int:
    # A conservative envelope, never the sum of the previous independent caps.
    return max(
        cny_to_micro(value or ZERO)
        for value in (
            settings.assistant_chat_daily_budget_cny,
            settings.assistant_query_embedding_daily_budget_cny,
            settings.assistant_index_embedding_daily_budget_cny,
        )
    )


def chat_headroom(settings) -> int:
    return 2 * (
        tokens_cost_micro(
            settings.assistant_chat_max_input_tokens or 0,
            settings.assistant_chat_input_price_cny_per_million or ZERO,
        )
        + tokens_cost_micro(
            settings.assistant_chat_max_output_tokens or 0,
            settings.assistant_chat_output_price_cny_per_million or ZERO,
        )
    )


def question_headroom(settings) -> int:
    return chat_headroom(settings) + tokens_cost_micro(
        settings.assistant_chat_max_input_tokens or 0,
        settings.assistant_embedding_input_price_cny_per_million or ZERO,
    )


def view(db, settings, day: str) -> dict:
    policy = db.get(AssistantBudgetPolicy, 1)
    maximum = ceiling(settings)
    cap = min(policy.cap_micro_cny, maximum) if policy else maximum
    settled, reserved = db.execute(
        select(
            func.coalesce(func.sum(AssistantBudgetReservation.settled_micro_cny), 0),
            func.coalesce(func.sum(AssistantBudgetReservation.reserved_micro_cny), 0),
        ).where(AssistantBudgetReservation.beijing_date == day)
    ).one()
    return {
        "beijing_date": day,
        "cap_micro_cny": cap,
        "ceiling_micro_cny": maximum,
        "version": policy.version if policy else 0,
        "restore_locked": bool(
            policy and policy.blocked_beijing_date and day <= policy.blocked_beijing_date
        ),
        "settled_micro_cny": int(settled),
        "reserved_micro_cny": int(reserved),
        "remaining_micro_cny": max(0, cap - int(settled) - int(reserved)),
        "question_headroom_micro_cny": question_headroom(settings),
        "chat_headroom_micro_cny": chat_headroom(settings),
    }


def set_cap(db, settings, *, amount: int, expected_version: int, day: str) -> dict:
    db.execute(text("BEGIN IMMEDIATE"))
    current = view(db, settings, day)
    if expected_version != current["version"]:
        raise ApiException(
            409, "budget_version_conflict", "Budget changed; refresh and save again."
        )
    if amount < 0 or amount > ceiling(settings):
        raise ApiException(
            400, "budget_above_authorized_cap", "Budget exceeds deployment authority."
        )
    policy = db.get(AssistantBudgetPolicy, 1)
    if policy is None:
        policy = AssistantBudgetPolicy(id=1, cap_micro_cny=amount, version=1)
        db.add(policy)
    else:
        policy.cap_micro_cny = amount
        policy.version += 1
    db.flush()
    if amount > current["cap_micro_cny"]:
        # Wake only budget-deferred work, never unknown provider attempts.
        from ..time_utils import utc_now

        now = utc_now()
        db.execute(
            text(
                "UPDATE assistant_index_tasks SET available_at=:now "
                "WHERE status='pending' AND provider_state='deferred'"
            ),
            {"now": now},
        )
        db.execute(
            text(
                "UPDATE assistant_index_rebuild_progress SET available_at=:now "
                "WHERE status='waiting'"
            ),
            {"now": now},
        )
    result = view(db, settings, day)
    db.commit()
    return result


def reserve(db, settings, *, day: str, entries: list[dict], headroom: int = 0) -> bool:
    """Caller must hold a content write transaction. No provider call in this transaction."""
    fresh = []
    if settings.assistant_online_enabled and any(item["scope"] == "index" for item in entries):
        policy = db.get(AssistantBudgetPolicy, 1)
        if policy is None or policy.runtime_accounted_date != day:
            # During upgrade/startup, Worker cannot race ahead of the API's old ledger import.
            return False
    for item in entries:
        existing = db.get(AssistantBudgetReservation, item["id"])
        if existing is not None:
            # Restored/replayed executions cannot acquire an already spent identity.
            return False
        fresh.append(item)
    amount = sum(item["reserved_micro_cny"] for item in fresh)
    current = view(db, settings, day)
    if amount > 0 and (
        current["restore_locked"] or amount + headroom > current["remaining_micro_cny"]
    ):
        return False
    for item in fresh:
        db.add(
            AssistantBudgetReservation(
                **item,
                beijing_date=day,
                settled_micro_cny=0,
                terminal=0,
            )
        )
    db.flush()
    return True


def reserve_turn(online, conn, turn_id: str, *, admin: bool) -> bool:
    attempts = conn.execute(
        "SELECT id,kind,beijing_date,max_cost_micro FROM assistant_attempts WHERE turn_id=?",
        (turn_id,),
    ).fetchall()
    with online.content_session() as db:
        db.execute(text("BEGIN IMMEDIATE"))
        ok = reserve(
            db,
            online.settings,
            day=online.beijing_day(),
            entries=[
                {
                    "id": f"runtime:{row['id']}",
                    "kind": row["kind"],
                    "scope": "admin" if admin else "public",
                    "reserved_micro_cny": int(row["max_cost_micro"]),
                }
                for row in attempts
            ],
        )
        db.commit()
        return ok


def settle(db, reservation_id: str, amount: int) -> None:
    entry = db.get(AssistantBudgetReservation, reservation_id)
    if entry is not None:
        # Monotonic: restored lower-cost receipts never reduce an existing charge.
        entry.settled_micro_cny = max(entry.settled_micro_cny, amount)
        entry.reserved_micro_cny = 0
        entry.terminal = 1


def attempt_permitted(online, attempt_id: str) -> bool:
    """A restored runtime must not send an identity already settled by authority."""
    with online.content_session() as db:
        entry = db.get(AssistantBudgetReservation, f"runtime:{attempt_id}")
        return bool(entry is not None and not entry.terminal)


def sync_runtime(online, conn) -> None:
    """After-commit projection, including pre-migration usage. Failure stays conservative."""
    day = beijing_date(online.now()).isoformat()
    rows = conn.execute(
        "SELECT a.*, t.session_id FROM assistant_attempts a "
        "JOIN assistant_turns t ON t.id=a.turn_id WHERE a.beijing_date=?",
        (day,),
    ).fetchall()
    with online.content_session() as db:
        db.execute(text("BEGIN IMMEDIATE"))
        policy = db.get(AssistantBudgetPolicy, 1)
        if policy is None:
            policy = AssistantBudgetPolicy(id=1, cap_micro_cny=ceiling(online.settings), version=1)
            db.add(policy)
        for row in rows:
            key = f"runtime:{row['id']}"
            entry = db.get(AssistantBudgetReservation, key)
            terminal = row["status"] not in {"prepared", "sending"}
            if entry is None:
                entry = AssistantBudgetReservation(
                    id=key,
                    beijing_date=row["beijing_date"],
                    kind=row["kind"],
                    scope="admin" if row["session_id"].startswith("admin_") else "public",
                    reserved_micro_cny=int(row["max_cost_micro"]),
                    settled_micro_cny=0,
                    terminal=0,
                )
                db.add(entry)
                db.flush()
            if terminal:
                settle(db, key, int(row["settled_micro"]))
        policy.runtime_accounted_date = day
        db.commit()

from __future__ import annotations

from sqlalchemy import func, select

from ..assistant_index.projector import project_source
from ..models import AssistantBudgetReservation, AssistantIndexTask
from .admin_operations import task_view
from .admin_schemas import IndexTaskView, StrictModel
from .admin_scope import admin_stopped, validate_admin_binding
from .routes import ActiveTurn, AssistantClientPolicy, AssistantSource
from .time_beijing import beijing_date
from .total_budget import view


class TrialCitation(StrictModel):
    n: str
    title: str
    path: str
    alias: str | None = None
    heading_path: str | None = None
    excerpt: str


class TrialTurn(StrictModel):
    turn_id: str
    created_at: str
    status: str | None
    code: str | None
    message: str | None
    question: str | None
    answer: str | None
    citations: list[TrialCitation] | None
    sources: list[AssistantSource] | None
    body_available: bool
    cost_micro_cny: int | None


class TrialSession(StrictModel):
    session_id: str
    created_at: str
    idle_expires_at: str
    absolute_expires_at: str
    policy: AssistantClientPolicy
    turns: list[TrialTurn]
    active_turn: ActiveTurn | None


class TotalBudgetView(StrictModel):
    beijing_date: str
    cap_micro_cny: int
    ceiling_micro_cny: int
    version: int
    restore_locked: bool
    settled_micro_cny: int
    reserved_micro_cny: int
    remaining_micro_cny: int
    question_headroom_micro_cny: int
    chat_headroom_micro_cny: int


class BudgetRequest(StrictModel):
    cap_micro_cny: int
    expected_version: int


class ScopeCost(StrictModel):
    scope: str
    kind: str
    settled_micro_cny: int
    reserved_micro_cny: int


class ManagementView(StrictModel):
    budget: TotalBudgetView
    usage_known: bool
    trial_available: bool
    trial_stopped: bool
    scope_costs: list[ScopeCost]


class ManagementTask(IndexTaskView):
    title: str
    public_path: str | None
    current_revision: bool
    provider_state: str | None
    resolved_by_current_index: bool = False


class ManagementTasks(StrictModel):
    items: list[ManagementTask]
    limit: int
    offset: int
    total: int


def management_view(db, settings, online, now) -> ManagementView:
    trial, stopped = False, False
    if online is not None:
        stopped = online.control.read(admin_stopped)
        try:
            online.control.read(
                lambda conn: validate_admin_binding(
                    conn,
                    settings=settings,
                    generation=online.active_generation(),
                    now=now,
                )
            )
            trial = True
        except Exception:
            pass
    day = beijing_date(now).isoformat()
    rows = db.execute(
        select(
            AssistantBudgetReservation.scope,
            AssistantBudgetReservation.kind,
            func.sum(AssistantBudgetReservation.settled_micro_cny),
            func.sum(AssistantBudgetReservation.reserved_micro_cny),
        )
        .where(AssistantBudgetReservation.beijing_date == day)
        .group_by(
            AssistantBudgetReservation.scope,
            AssistantBudgetReservation.kind,
        )
    ).all()
    return ManagementView(
        budget=TotalBudgetView(**view(db, settings, day)),
        usage_known=online is not None,
        trial_available=trial,
        trial_stopped=stopped,
        scope_costs=[
            ScopeCost(scope=r[0], kind=r[1], settled_micro_cny=r[2], reserved_micro_cny=r[3])
            for r in rows
        ],
    )


def management_tasks(
    db, *, limit: int, offset: int, status: str | None, runtime=None,
) -> ManagementTasks:
    query = select(AssistantIndexTask)
    if status:
        query = query.where(AssistantIndexTask.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(AssistantIndexTask.id.desc()).limit(limit).offset(offset)
    ).all()
    from .sync_attention import covered_failed_task_ids

    covered = covered_failed_task_ids(db, runtime, rows)
    items = []
    for row in rows:
        document = project_source(db, row.source_type, row.source_id)
        items.append(
            ManagementTask(
                **task_view(row).model_dump(),
                title=document.title if document else "已撤回或删除的内容",
                public_path=document.public_path if document else None,
                current_revision=bool(document and document.source_version == row.target_version),
                provider_state=row.provider_state,
                resolved_by_current_index=row.id in covered,
            )
        )
    return ManagementTasks(items=items, total=total, limit=limit, offset=offset)

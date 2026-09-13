"""Authenticated working-copy list queries; public snapshot queries stay separate."""

from typing import Annotated, Literal

from fastapi import Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

ListSearch = Annotated[str, Query(max_length=200)]
ListStatus = Literal["draft", "published"]


def query_content(
    db: Session,
    model,
    fields,
    q: str,
    status: str | None,
    limit: int,
    offset: int,
    serialize,
    options=(),
) -> dict:
    conditions = [model.deleted_at.is_(None)]
    term = q.strip()
    if term:
        conditions.append(or_(*(field.icontains(term, autoescape=True) for field in fields)))
    counts: dict[str, int] = {
        key: count
        for key, count in db.execute(
            select(model.status, func.count()).where(*conditions).group_by(model.status)
        ).all()
    }
    published, draft = counts.get("published", 0), counts.get("draft", 0)
    if status:
        conditions.append(model.status == status)
    items = (
        db.scalars(
            select(model)
            .options(*options)
            .where(*conditions)
            .order_by(model.updated_at.desc(), model.id.desc())
            .limit(limit)
            .offset(offset)
        )
        .unique()
        .all()
    )
    return {
        "items": [serialize(item) for item in items],
        "total": counts.get(status, 0) if status else published + draft,
        "counts": {"all": published + draft, "published": published, "draft": draft},
    }

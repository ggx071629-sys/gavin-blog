"""Bounded article catalog answers from public revisions, independent of RAG."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from ..models import Article, ArticleRevision
from .output import ValidatedAnswer
from .preflight import scan_evidence

BEIJING = timezone(timedelta(hours=8))
Order = Literal["published", "updated"]
Window = Literal["today", "week", "seven_days"]
COUNT = r"[1-9][0-9]*|[一二两三四五六七八九十]"
TIME = r"最近七天|最近7天|近七天|近7天|最近|近期|最新|今天|本周"
ZH = re.compile(
    rf"(?:请问|请)?(?:帮我)?(?:列出|看看|告诉我|推荐)?"
    rf"(?:本站|站内|博客|你|作者)?(?P<time>{TIME})"
    rf"(?P<action>新发布|发布|发表|新增|更新)?(?:了|过)?(?:的)?"
    rf"(?:有哪些|有什么|哪些|什么|哪几篇|几篇|有啥|有)?"
    rf"(?:(?P<count>{COUNT})篇)?文章"
    rf"(?P<tail>有哪些|有什么|是哪篇|是哪一篇|是什么|列表)?(?:呢|吗)?"
)
EN = re.compile(
    r"(?:(?:what (?:is|are)|which (?:is|are)|show(?: me)?|list) )?(?:the )?"
    r"(?:(?P<count>[1-9][0-9]*) )?"
    r"(?P<time>latest|newest|recent|(?:most )?recently (?:updated|published)) "
    r"(?P<noun>articles?|posts?)(?: on (?:this|the) (?:site|blog))?",
    re.I,
)


@dataclass(frozen=True)
class RecentArticleRequest:
    order: Order
    limit: int = 5
    window: Window | None = None

    def __post_init__(self) -> None:
        if self.order not in ("published", "updated") or not 1 <= self.limit <= 10:
            raise ValueError("invalid catalog request")
        if self.window not in (None, "today", "week", "seven_days"):
            raise ValueError("invalid catalog window")


def _count(value: str | None, default: int) -> int:
    if value is None:
        return default
    if value.isascii() and value.isdecimal():
        return int(value)
    return {
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }[value]


def parse_recent_articles(question: str) -> RecentArticleRequest | None:
    """Full matches only: never silently discard a topic, date or second task."""
    text = question.strip().rstrip("？?。.!！").strip()
    zh = ZH.fullmatch(re.sub(r"\s+", "", text))
    if zh:
        limit = _count(zh["count"], 1 if zh["tail"] in ("是哪篇", "是哪一篇") else 5)
        windows: dict[str, Window] = {
            "今天": "today",
            "本周": "week",
            "最近七天": "seven_days",
            "最近7天": "seven_days",
            "近七天": "seven_days",
            "近7天": "seven_days",
        }
        window = windows.get(zh["time"])
        order: Order = "updated" if zh["action"] == "更新" else "published"
    else:
        en = EN.fullmatch(" ".join(text.split()))
        if en is None:
            return None
        limit = _count(en["count"], 5 if en["noun"].lower().endswith("s") else 1)
        order = "updated" if "updated" in en["time"].lower() else "published"
        window = None
    return RecentArticleRequest(order, limit, window) if limit <= 10 else None


def _window_start(request: RecentArticleRequest, now: datetime) -> datetime | None:
    local = now.astimezone(BEIJING)
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if request.window == "today":
        return midnight
    if request.window == "week":
        return midnight - timedelta(days=local.weekday())
    if request.window == "seven_days":
        return local - timedelta(days=7)
    return None


def _plain_title(title: str) -> str:
    # The UI renders plain text but recognizes [n] as citations. Keep literal
    # brackets distinct; original titles remain intact in source metadata.
    return " ".join(title.split()).replace("[", "［").replace("]", "］")


def query_recent_articles(
    db: Session,
    request: RecentArticleRequest,
    now: datetime,
) -> ValidatedAnswer:
    now = now.replace(tzinfo=UTC) if now.tzinfo is None else now.astimezone(UTC)
    # Match public_articles.public_response: a first revision uses the original
    # publication time; subsequent revisions use their explicit release time.
    public_updated = case(
        (ArticleRevision.revision_number == 1, Article.published_at),
        else_=ArticleRevision.published_at,
    )
    timestamp = public_updated if request.order == "updated" else Article.published_at
    query = (
        select(
            Article.id,
            Article.published_at,
            ArticleRevision.id.label("revision_id"),
            ArticleRevision.title,
            ArticleRevision.slug,
            timestamp.label("at"),
        )
        .join(
            ArticleRevision,
            (Article.current_revision_id == ArticleRevision.id)
            & (ArticleRevision.article_id == Article.id),
        )
        .where(
            Article.status == "published",
            Article.deleted_at.is_(None),
            Article.published_at.is_not(None),
            Article.published_at <= now,
            public_updated <= now,
        )
    )
    start = _window_start(request, now)
    if start is not None:
        query = query.where(timestamp >= start)
    rows = db.execute(
        query.order_by(timestamp.desc(), Article.id.desc()).limit(request.limit)
    ).all()
    action = "公开更新" if request.order == "updated" else "首次发布"
    window_label = {None: "最近", "today": "今天", "week": "本周", "seven_days": "最近7天"}[
        request.window
    ]
    header = (
        f"按{action}时间从新到旧，列出{window_label}的公开文章（最多{request.limit}篇，北京时间）。"
    )
    if not rows:
        return ValidatedAnswer(
            f"{window_label}没有符合条件的已公开文章（按{action}时间，北京时间）。",
            [],
            [],
        )
    lines = [header]
    citations: list[dict[str, str]] = []
    sources: list[dict[str, str]] = []
    for row in rows:
        # Do not replace a filtered top-ranked entry with an older entry and
        # then claim that the older entry is the newest one.
        if scan_evidence(row.title):
            lines.append("有一篇匹配文章的标题未通过安全检查，未展示。")
            continue
        number = str(len(citations) + 1)
        path = f"/notes/{row.published_at.year:04d}/{row.published_at.month:02d}/{row.slug}"
        location = f"{action}时间：{row.at.astimezone(BEIJING):%Y-%m-%d %H:%M}"
        # Dates are catalog metadata, not headings in the article body.
        source = {"n": number, "title": row.title, "heading_path": "", "path": path}
        sources.append(source)
        citations.append({**source, "alias": f"article_{row.id}_r{row.revision_id}"})
        lines.append(f"{_plain_title(row.title)} — {location}[{number}]")
    return ValidatedAnswer("\n\n".join(lines), citations, sources)

"""Finite request boundaries; retrieval chunks cannot prove global coverage/time."""

from __future__ import annotations

import re

INVENTORY = re.compile(
    r"(?:全部|所有)(?:的)?(?:项目|文章|笔记|书籍|资料)|"
    r"(?:本站|全站).{0,16}(?:多少|几篇|几本|总数|总共|一共|全部|所有)|"
    r"(?:总共|一共|共有).{0,12}(?:项目|文章|笔记|书籍)|"
    r"\b(?:all|every) (?:the )?(?:projects?|articles?|notes?|books?|sources?)\b|"
    r"\bhow many (?:projects|articles|notes|books).{0,30}(?:site|total)\b",
    re.I,
)
FRESHNESS = re.compile(
    r"最新(?:的)?(?:文章|项目|笔记|简历)|"
    r"(?:目前|现在|当前).{0,15}(?:任职|担任|就职|工作)|"
    r"\b(?:latest|newest) (?:article|project|note|resume|book)\b|"
    r"\b(?:currently|now).{0,20}\b(?:work|role|employed)|"
    r"\bcurrent (?:role|employer|job)\b",
    re.I,
)
PAGE = re.compile(
    r"这篇(?:文章|笔记)|当前(?:页面|文章)|本页|本文|\bthis (?:page|article|note)\b", re.I
)


def scope_code(question: str) -> str | None:
    if INVENTORY.search(question):
        return "completeness_unverified"
    if FRESHNESS.search(question):
        return "freshness_unverified"
    return None


def preferred_page(question: str, current_path: str | None, reference: dict | None) -> str | None:
    if reference:
        return reference["public_path"]
    return current_path if PAGE.search(question) else None

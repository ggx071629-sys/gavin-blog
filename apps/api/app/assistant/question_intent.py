"""Bounded query hints, never evidence or permission to discard user constraints."""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable
from typing import TypeVar

PERSONAL_SOURCES = frozenset({'profile', 'about', 'resume'})
SKILLS = re.compile(
    r'技能|技术能力|能力自述|专业能力|技术栈|擅长|会什么|能做什么|会哪些|'
    r'\b(?:skills?|proficien\w*|good at|expertise|tech stack)\b', re.I,
)
SUBJECT = re.compile(r'\bgavin\b|gavin(?=[\u3400-\u9fff])|博主|作者|'
                     r'\b(?:your|you|author|resume|cv)\b|你', re.I)
TECHNICAL_SCOPE = re.compile(
    r'文章|教程|项目|助手|框架|怎么实现|如何实现|问\s*gavin|'
    r'\b(?:article|tutorial|project|assistant|framework)\b', re.I,
)


def normalized_question(question: str) -> str:
    # Only typography, never semantic qualifiers, dates or negations.
    return ' '.join(unicodedata.normalize('NFKC', question).strip().split()).rstrip('?!。！？”')


def asks_personal_skills(question: str) -> bool:
    text = normalized_question(question)
    if re.fullmatch(
        r'(?:请问)?(?:你)?(?:会什么|擅长什么|有什么技能|有哪些技能|'
        r'(?:简历|履历|个人|专业)?技能有哪些|技术栈是什么)(?:呢)?', text,
    ):
        return True
    if re.search(
        r'(?:gavin|博主|作者|你)(?:的)?(?:专业技能|技术能力|技术栈|技能|'
        r'会什么|会哪些|擅长什么|有哪些技能)', text, re.I,
    ) and not re.search(r'问\s*gavin', text, re.I):
        return True
    return bool(SKILLS.search(text) and SUBJECT.search(text) and not TECHNICAL_SCOPE.search(text))


def retrieval_question(question: str) -> str:
    text = normalized_question(question)
    if asks_personal_skills(text):
        # Keep the entire question: a named technology or negative premise matters.
        return text + ' 专业技能 能力自述'
    return text


def personal_priority(source_type: str, heading: str, body: str) -> int:
    if source_type not in PERSONAL_SOURCES:
        return 4
    if SKILLS.search(heading) or (source_type == 'resume' and '专业技能' in body):
        return 0
    return 1 if source_type == 'profile' else 2


T = TypeVar('T')


def diverse_skill_evidence(items: Iterable[T], source_type: Callable[[T], str]) -> list[T]:
    """Reserve early opportunities for self-reports, articles and projects.

    This orders candidates, not truth or mandatory citations. The caller must
    still validate live versions, relevance and complete supporting clauses.
    """
    groups: dict[str, list[T]] = {}
    for item in items:
        kind = source_type(item)
        groups.setdefault('personal' if kind in PERSONAL_SOURCES else kind, []).append(item)
    keys: list[str] = [key for key in ('personal', 'article', 'project') if key in groups]
    keys.extend(key for key in groups if key not in keys)
    return [groups[key][index]
            for index in range(max((len(group) for group in groups.values()), default=0))
            for key in keys if index < len(groups[key])]

from __future__ import annotations

import re
from dataclasses import dataclass

from .hydrate import Evidence
from .providers import ModelAnswer
from .quantities import canonical_quantities, invalid_quantity

HTML_RE = re.compile(r"</?[a-zA-Z][^>]*>|<!--|<!DOCTYPE|<\?", re.I)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
LINK_RE = re.compile(r"\[[^\]]*\]\((https?:)?[^)]+\)")
FORBIDDEN_MD = re.compile(r"javascript:", re.IGNORECASE)
RESERVED_MARKER_RE = re.compile(r"\[[1-9][0-9]*\]")
ARRAY_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]*\s*(?:\[\s*\d+\s*\])+")
GENERIC_RE = re.compile(
    r"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]*"
    r"<[A-Za-z_][A-Za-z0-9_]*(?:,\s*[A-Za-z_][A-Za-z0-9_]*)*>"
)
RESUME_NOTICES = frozenset({"简历当前不可用。", "Resume evidence is currently unavailable."})


def _unsafe_structure(text: str) -> bool:
    markup_view = GENERIC_RE.sub("type expression", text)
    marker_view = ARRAY_RE.sub("array expression", text)
    return bool(HTML_RE.search(markup_view) or IMAGE_RE.search(text) or LINK_RE.search(text)
                or FORBIDDEN_MD.search(text) or RESERVED_MARKER_RE.search(marker_view))


def _render_technical_text(text: str) -> str:
    # Explicit inline-code boundaries avoid guessing whether "word[1]" is an
    # old citation or a new array subscript. Existing code spans remain intact.
    return "".join(part if index % 2 else ARRAY_RE.sub(lambda m: "`" + m[0] + "`", part)
                   for index, part in enumerate(re.split(r"(`[^`\n]*`)", text)))
PERSONAL_CLAIM_RE = re.compile(
    r"精通|专家|\d+\s*年(?:以上)?经验|获(?:得|了|奖)|图灵奖|诺贝尔|"
    r"(?:目前|现任|现在).*(?:担任|任职|工程师|经理)|"
    r"(?:作者|本人|(?<![\u3400-\u9fff])我(?!们))|"
    r"\b(?:the author|I|expert|mastery|won|awarded|years? of experience|currently works)\b",
    re.IGNORECASE,
)
RELATION_CLAIM_RE = re.compile(
    r"依赖|取决于|导致|使得|意味着|\b(?:depends? on|relies? on|requires?|causes?|implies?)\b",
    re.IGNORECASE,
)
SENTENCE_RE = re.compile(r"[。！？!?；;\n]")
UNDOCUMENTED_RE = re.compile(r"\s*(?:所给|当前|这些)材料未记载[^，,。；;]*")
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_.])[-+]?\d+(?:\.\d+)?(?![A-Za-z0-9_]|\.\d)")
UNIT_RE = re.compile(
    r"\s*(毫秒|分钟|小时|个月|个|项|篇|年|月|天|页|次|秒|%|"
    r"years?\b|months?\b|days?\b|seconds?\b|projects?\b|articles?\b)",
    re.IGNORECASE,
)
RETRACTION_RE = re.compile(
    r"^(?:上述|前述|该|此)(?:说法|陈述|结论).*(?:不实|错误|撤回|不成立)|"
    r"^(?:that|this|the preceding) (?:statement|claim).*(?:false|incorrect|retracted)",
    re.IGNORECASE,
)
CONFLICT_NOTICE_RE = re.compile(r"(?:资料|来源|材料)(?:存在)?(?:冲突|不一致)")
TOPIC_RULES = (
    (
        re.compile(r"数据库|\bdatabase\b", re.I),
        re.compile(r"数据库|SQLite|PostgreSQL|MySQL|MongoDB|Redis|\bdatabase\b", re.I),
    ),
    (
        re.compile(r"许可证|\blicen[cs]e\b", re.I),
        re.compile(r"许可证|\blicen[cs]e\b|\bMIT\b|Apache|GPL|BSD", re.I),
    ),
)


def _support_context(body: str, quote: str) -> str:
    """Retain surrounding sentence context, including qualifiers outside a quote."""
    start = body.index(quote)  # Membership was checked against the live body.
    end = start + len(quote)
    row_start = body.rfind("\n", 0, start) + 1
    row_end = body.find("\n", end)
    row_end = len(body) if row_end < 0 else row_end
    row = body[row_start:row_end]
    # A cell quote keeps the entire table relation, including dotted field
    # names and URL punctuation. Exact quote membership remains mandatory.
    if "\n" not in row and row.strip().startswith("|") and row.strip().endswith("|"):
        start, end = row_start, row_end
        quote = row
    boundaries = "。！？.!?\n"
    left = max((body.rfind(mark, 0, start) for mark in boundaries), default=-1) + 1
    if quote[-1] not in boundaries:
        following_boundaries = [pos for mark in boundaries if (pos := body.find(mark, end)) >= 0]
        end = min(following_boundaries) + 1 if following_boundaries else len(body)
    # A following sentence may explicitly retract the quoted claim. Keep it
    # attached instead of validating the quote as an independent assertion.
    following = body[end:].lstrip()
    next_clause = SENTENCE_RE.split(following, maxsplit=1)[0]
    if RETRACTION_RE.search(next_clause):
        return body[left:end] + next_clause
    return body[left:end]


def _claim_key(value: str, *, self_report: bool = False) -> str:
    value = canonical_quantities(value).strip()
    value = re.sub(r"^(?:公开资料|资料|简历)(?:记载|显示|自述)[:：]\s*", "", value)
    value = re.sub(r"^根据本站已发布内容[:：]\s*", "", value)
    if self_report:
        # Only a leading first-person statement in the author's own source.
        # Do not replace pronouns in another person's quote or remove negation.
        value = re.sub(r"^(?:我(?!们)|本人)(?:自述)?", "作者自述", value)
    value = re.sub(r"^(?:关于页|个人资料|简历)自述(?:[:：]|为)?", "作者自述", value)
    value = re.sub(r"^(?:资料|来源|材料)(?:存在)?(?:冲突|不一致)[:：]\s*", "", value)
    value = re.sub(r"(?m)^\s*#{1,6}\s+", "", value)
    value = re.sub(r"使用|采用", "用", value).replace("与", "和")
    value = re.sub(
        r"(?<![A-Za-z0-9_])(SQLite|PostgreSQL|MySQL|MongoDB)\s*(?:数据库|database\b)",
        r"\1",
        value,
        flags=re.I,
    )
    value = re.sub(r"(?<!不)会在([^。！？]+?)后再试", r"\1后会重试", value)
    return re.sub(r"\s+|[。！？!?；;]", "", value).casefold().rstrip(".")


def _enumeration_summary(clause: str) -> str | None:
    match = re.fullmatch(r"(.+?包括)(.+?)(\d+)(个(?:模块|项目))", _claim_key(clause))
    if not match:
        return None
    prefix, listing, count, unit = match.groups()
    if re.search(r"等|例如|比如|包括但不限于|至少|最多|约", listing):
        return None
    items = re.split(r"[、,，]|和", listing)
    if not all(items) or len(items) != len(set(items)) or len(items) != int(count):
        return None
    return prefix + count + unit


def _context_clauses(context: str) -> list[str]:
    clauses: list[str] = []
    for clause in SENTENCE_RE.split(context):
        if not clause.strip():
            continue
        if RETRACTION_RE.search(clause.strip()) and clauses:
            clauses[-1] += "。" + clause
        else:
            clauses.append(clause)
    return clauses


def _supported_clause(claim: str, sources: set[str]) -> bool:
    if claim in sources:
        return True
    # An explicit positive list supports one of its leading conjuncts. Never
    # discard a qualification, negation, or causal/conditional suffix.
    for source in sources:
        if re.search(r"但|仅|只|除|不|未|如果|除非|\b(?:not|only|unless|if)\b", source):
            continue
        if source.startswith(claim + "和"):
            return True
    return False


def _tutorial_key(value: str, title: str) -> str:
    """Bounded article self-reference and connectives; retain all factual clauses."""
    value = value.strip()
    prefix = f"本站文章《{title}》介绍，"
    if value.startswith(prefix):
        value = value[len(prefix):]
    value = re.sub(r"^(?:本站的|本站文章)?《" + re.escape(title) + r"》(?=介绍|解释|说明)",
                   "文章", value)
    value = re.sub(r"^(?:(?:本|该|这篇)?(?:教程|文章)|文中)(?:还)?(介绍|解释了?|说明)",
                   lambda m: "文章" + m[1].removesuffix("了"), value)
    value = re.sub(r"，(?:并说明通过|说明通过|并通过|通过)调用", "，调用", value)
    value = value.replace("服务来完成", "服务完成")
    value = re.sub(r"^文章介绍([^。！？；]+?)的方式是[：:]调用", r"文章介绍\1，调用", value)
    value = re.sub(r"^文章说明([^。！？；]+?)是调用", r"文章介绍\1，调用", value)
    introduction = re.fullmatch(r"文章介绍([^。！？；：:]+)[：:](.+)", value, re.S)
    if introduction:
        remainder = _tutorial_key(introduction[2], title)
        if remainder.startswith(_claim_key("文章介绍" + introduction[1]) + ","):
            return remainder
    # Only an explicit risk explanation and its attached same-subject cause.
    # Preserve the entire cause, including any negation, condition or retraction.
    risk = re.fullmatch(
        r"文章(?:解释|说明)[，,]?“([^“”]+)”(?:为何危险|之所以危险|是危险的)"
        r"(?:[。：:]|[，,](?:是)?因为)它(.+?)[。.]?", value, re.S,
    )
    if risk:
        return "risk:" + _claim_key(risk[1]) + ":cause:" + _claim_key(risk[2])
    # A finite translation of the same complete tutorial relation. This does
    # not treat keyword overlap or arbitrary English prose as entailment.
    translated = re.fullmatch(
        r"(?:The|This) (?:article|tutorial) (?:introduces|describes) "
        r"(?:email sending|sending email),? and (?:calls|uses) "
        r"([A-Za-z][A-Za-z0-9_-]*) services? to (?:send|deliver) notifications\.?",
        value, re.I,
    )
    if translated:
        value = f"文章介绍发送邮件功能，调用{translated[1]}服务完成通知"
    notification = re.fullmatch(
        r"(?:The|This) (?:article|tutorial) "
        r"(?:(?:explains|states) that email notifications are sent by calling an? "
        r"([A-Za-z][A-Za-z0-9_-]*) service|"
        r"describes sending email notifications through ([A-Za-z][A-Za-z0-9_-]*)|"
        r"describes the email-sending feature: it covers sending emails by calling an? "
        r"([A-Za-z][A-Za-z0-9_-]*) service to complete notifications)\.?",
        value, re.I,
    )
    if notification:
        protocol = notification[1] or notification[2] or notification[3]
        value = f"文章介绍发送邮件功能，调用{protocol}服务完成通知"
    return _claim_key(value)


def _tutorial_supported(sentence: str, contexts: list[tuple[Evidence, str]]) -> bool:
    return any(
        _tutorial_key(sentence, item.title) == _tutorial_key(clause, item.title)
        for item, context in contexts if item.source_type == "article"
        for clause in [context, *_context_clauses(context)]
    )


def _topic_summary_supported(sentence: str, contexts: list[tuple[Evidence, str]]) -> bool:
    # Preserve the existing bilingual article-summary contract. This permits
    # topic names only, never a new proposition about those technologies.
    match = re.fullmatch(r"\s*(?:文章|本文|资料)(?:介绍|讨论)\s*(.+)", sentence)
    if match is None:
        match = re.fullmatch(
            r"\s*(?:the article|(?:published )?notes?|this article) "
            r"(?:discuss(?:es)?|covers?|introduces?)\s+(.+?)\.?",
            sentence,
            re.I,
        )
    if not match:
        return False
    topics = re.split(r"\s*(?:和|与|、|,|\band\b)\s*", match.group(1))
    if not all(re.fullmatch(r"[A-Za-z][A-Za-z0-9_.+-]*", topic) for topic in topics):
        return False
    for _item, context in contexts:
        if _item.source_type == "article":
            available = {
                term.rstrip(".")
                for term in re.findall(
                    r"[A-Za-z][A-Za-z0-9_.+-]*", (context + " " + _item.title).casefold()
                )
            }
            if all(topic.casefold() in available for topic in topics):
                return True
        for clause in _context_clauses(context):
            if not re.match(r"\s*I write about\s+", clause, re.I):
                continue
            if re.search(
                r"\b(?:not|never|but|false|incorrect|retracted)\b|不实|撤回", clause, re.I
            ):
                continue
            available = {
                term.rstrip(".")
                for term in re.findall(r"[A-Za-z][A-Za-z0-9_.+-]*", clause.casefold())
            }
            if all(topic.casefold() in available for topic in topics):
                return True
    return False


def _labelled_role_supported(text: str, contexts: list[tuple[Evidence, str]]) -> bool:
    facts: dict[str, set[tuple[str, str]]] = {}
    for item, context in contexts:
        if item.source_type not in {"about", "resume", "profile"}:
            continue
        for match in re.finditer(
            r"\b([\w-]+)(?: new)? self-report:\s*([A-Za-z -]+) engineer\b",
            context,
            re.I,
        ):
            facts.setdefault(item.source_type, set()).add(
                (match[1].casefold(), match[2].strip().casefold())
            )
    statement = re.fullmatch(
        r"(About|Resume|Profile) self-reports ([A-Za-z -]+) work\.", text, re.I
    )
    if statement:
        values = facts.get(statement[1].casefold(), set())
        return len(values) == 1 and next(iter(values))[1] == statement[2].strip().casefold()
    comparison = re.fullmatch(
        r"(About|Resume|Profile) and (about|resume|profile) (?:disagree|differ) "
        r"on the stated role; both are self-reports\.",
        text,
        re.I,
    )
    if comparison:
        first = facts.get(comparison[1].casefold(), set())
        second = facts.get(comparison[2].casefold(), set())
        if len(first) == len(second) == 1:
            subject, role = next(iter(first))
            other_subject, other_role = next(iter(second))
            return subject == other_subject and role != other_role
    return False


def _quantities(text: str) -> set[tuple[str, str]]:
    text = canonical_quantities(text)
    result = set()
    for match in NUMBER_RE.finditer(text):
        unit = UNIT_RE.match(text, match.end())
        result.add((match.group(), unit.group(1).casefold() if unit else ""))
    return result


def _role_comparison_supported(text: str, contexts: list[tuple[Evidence, str]]) -> bool:
    match = re.fullmatch(r"两份自述的岗位不同[，,](.+?)[。.]?", text.strip())
    if not match:
        return False
    labels = {"简历": "resume", "个人资料": "profile", "关于页": "about"}
    roles = []
    types = []
    for entry in re.split(r"[，,]", match.group(1)):
        fact = re.fullmatch(r"(简历|个人资料|关于页)为([^，,。]+)", entry.strip())
        if not fact:
            return False
        label, role = fact.groups()
        role = role.removesuffix("工程师")
        if not any(
            item.source_type == labels[label]
            and _claim_key(context) == _claim_key(label + "自述：" + role + "工程师")
            for item, context in contexts
        ):
            return False
        roles.append(role)
        types.append(labels[label])
    return len(roles) == len(set(roles)) == len(set(types)) == 2


CODE_PRESENTATION_RE = re.compile(
    r"(?m)^[ \t]{0,3}(`{3,}|~{3,})[A-Za-z0-9_-]*[ \t]*\n"
    r"([^\n]+)\n[ \t]{0,3}\1[ \t]*(?=\n|$)|"
    r"(?<!`)`([^`\n]+)`(?!`)"
)


def _code_presentation_key(value: str) -> str | None:
    """Remove only complete single-line code wrappers; preserve code characters."""
    if "\ue000" in value or "\ue001" in value:
        return None
    value = value.strip().removesuffix("。")
    code: list[str] = []

    def keep(match: re.Match[str]) -> str:
        code.append(match[2] if match[2] is not None else match[3])
        return f"\ue000{len(code) - 1}\ue001"

    prose = CODE_PRESENTATION_RE.sub(keep, value)
    if "`" in prose or "~~~" in prose:
        return None  # Unmatched or multiline code is outside this equivalence.
    prose = re.sub(r"\s+", " ", prose).strip()
    prose = re.sub(r"([：:]) +", r"\1", prose)
    for index, content in enumerate(code):
        prose = prose.replace(f"\ue000{index}\ue001", content)
    return prose


def _structured_key(value: str) -> str | None:
    """Whole-item presentation only, never keyword/subsequence entailment."""
    # Links are reduced only in source text. Output safety is checked first.
    value = re.sub(r"\[([^\]\n]+)\]\(https?://[^\s)]+\)", r"\1", value)
    value = re.sub(r"(?m)^\s*(?:•|[-*]|\d+[.)])\s+", "", value)
    value = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", value)
    # A single table row is a field/value relationship. Preserve every cell.
    lines = value.strip().splitlines()
    if len(lines) == 1 and lines[0].strip().startswith("|"):
        value = " ".join(cell.strip() for cell in lines[0].strip().strip("|").split("|"))
    presentation = _code_presentation_key(value)
    if presentation is None:
        return None
    return re.sub(r"\s+", "", presentation).removesuffix("。").removesuffix(".")


def _structured_presentation_supported(text: str, contexts: list[tuple[Evidence, str]]) -> bool:
    # Each pair must occupy its whole context: comma folding cannot discard a
    # condition, subject, negation or retraction from an attached statement.
    def mappings(value: str) -> tuple[tuple[str, str], ...] | None:
        rows = re.split(r"[\n，,]", value.strip().removesuffix("。"))
        pairs = []
        for row in rows:
            match = re.fullmatch(r"\s*([A-Za-z0-9_.-]+)\s*=\s*([A-Za-z0-9_.-]+)\s*", row)
            if not match:
                return None
            pairs.append((match[1], match[2]))
        return tuple(pairs) if pairs else None

    answer_mapping = mappings(text)
    if answer_mapping and any(answer_mapping == mappings(context) for _, context in contexts):
        return True
    for item, context in contexts:
        candidate = text
        if item.source_type in {"profile", "about", "resume"}:
            label = {"profile": "个人资料", "about": "关于页", "resume": "简历"}[item.source_type]
            candidate = re.sub(r"^(?:资料显示|" + label + r"自述)[:：]\s*", "", candidate)
        source_key = _structured_key(context)
        if source_key is not None and _structured_key(candidate) == source_key:
            return True
        # A finite translation of the complete imperative display prefix.
        # All literal command bytes and any attached qualifications still match.
        imperative = re.match(r'^(执行|检查|查看系统)[:：]', context)
        if item.source_type == "article" and candidate.startswith("Run:") and imperative:
            translated = imperative[0] + candidate[len("Run:"):].strip()
            if _structured_key(translated) == source_key:
                return True
    return False


def _claims_supported(text: str, contexts: list[tuple[Evidence, str]]) -> bool:
    # Complete sentences use the same segmentation on both sides. Commas and
    # their qualifiers stay attached, so copying an original clause can pass
    # without allowing a clipped claim to shed its denial or caveat.
    # The older prose canonicalizer folds whitespace/punctuation. Never let
    # that fallback change literal code content after presentation comparison.
    for match in CODE_PRESENTATION_RE.finditer(text):
        payload = match[2] if match[2] is not None else match[3]
        code_supported = False
        for _, context in contexts:
            literals = [m[2] if m[2] is not None else m[3]
                        for m in CODE_PRESENTATION_RE.finditer(context)]
            if payload in literals or (not literals and payload in context):
                code_supported = True
                break
        if not code_supported:
            return False
    if _role_comparison_supported(text, contexts) or _labelled_role_supported(text, contexts):
        return True
    if _structured_presentation_supported(text, contexts):
        return True
    presentation = _code_presentation_key(text)
    if presentation is not None and any(
        presentation == _code_presentation_key(context) for _, context in contexts
    ):
        return True
    source_clauses = {
        _claim_key(clause, self_report=item.source_type in {"about", "profile", "resume"})
        for item, context in contexts
        for clause in [context, *_context_clauses(context)]
        if clause.strip()
    }
    for _item, context in contexts:
        for clause in _context_clauses(context):
            if summary := _enumeration_summary(clause):
                source_clauses.add(summary)
    for sentence in _context_clauses(text):
        # A bounded absence notice describes this evidence set, not a new fact.
        sentence = "，".join(
            part for part in re.split(r"[，,]", sentence) if not UNDOCUMENTED_RE.fullmatch(part)
        )
        if not sentence.strip():
            continue
        if (
            not _supported_clause(_claim_key(sentence), source_clauses)
            and not _tutorial_supported(sentence, contexts)
            and not _topic_summary_supported(sentence, contexts)
            and not any(
                _claim_key(sentence) == prefix + _claim_key(item.title)
                for item, _ in contexts for prefix in ("详见", "原文见", "see")
            )
        ):
            return False
    supported = set().union(*(_quantities(context) for _, context in contexts))
    return _quantities(text) <= supported


def _explicit_facts(body: str) -> list[tuple[str, str, str, bool]]:
    """Bounded direct subject/predicate statements, not entity resolution."""
    result = []
    for clause in re.split(r"[。！？!?；;，,\n]", body):
        match = re.fullmatch(
            r"\s*([^\s。；，]{1,30}?)(仅|只)?(采用|使用|依赖)([^。；，]+)\s*", clause
        )
        if match:
            subject, exclusive, predicate, value = match.groups()
            # "uses SQLite" and "uses MIT license" describe different slots.
            # Unknown slots are not treated as single-valued attributes.
            kind = (
                "license"
                if re.search(r"许可证|licen[cs]e", value, re.I)
                else "database"
                if re.search(r"数据库|SQLite|PostgreSQL|MySQL|MongoDB|Redis", value, re.I)
                else _claim_key(value)
            )
            result.append(
                (
                    _claim_key(subject),
                    _claim_key(predicate) + ":" + kind,
                    _claim_key(value),
                    bool(exclusive),
                )
            )
    return result


def _conflicts_supported(text: str, cited: list[str], evidence: list[Evidence]) -> bool:
    facts = [(item, fact) for item in evidence for fact in _explicit_facts(item.body)]
    for item, (subject, predicate, value, exclusive) in facts:
        if item.alias not in cited:
            continue
        for other in evidence:
            alternatives = [
                v
                for s, p, v, other_exclusive in _explicit_facts(other.body)
                if (s, p) == (subject, predicate) and v != value and (exclusive or other_exclusive)
            ]
            cancelled = re.search(
                re.escape(subject) + r"(?:已|现在|当前)?(?:取消|不再用)" + re.escape(value),
                _claim_key(other.body),
            )
            if not alternatives and not cancelled:
                continue
            if (
                not CONFLICT_NOTICE_RE.search(text)
                or other.alias not in cited
                or value not in _claim_key(text)
                or any(v not in _claim_key(text) for v in alternatives)
            ):
                return False
    return True


def _question_support(question: str, text: str, evidence: list[Evidence]) -> str | None:
    notices = UNDOCUMENTED_RE.findall(text)
    factual_text = UNDOCUMENTED_RE.sub("", text)
    # An explicit configuration field cannot be answered with a different row
    # merely because both rows occur in the cited article.
    fields = re.findall(r'(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+', question)
    for field in fields:
        token = re.compile(r'(?<![\w])' + re.escape(field) + r'(?![\w])', re.I)
        if any(token.search(item.body) for item in evidence) and not token.search(factual_text):
            return 'relevance'
    for topic, answer_terms in TOPIC_RULES:
        mentions_absence = any(topic.search(notice) for notice in notices)
        if mentions_absence and any(answer_terms.search(item.body) for item in evidence):
            return "grounding"
        if (
            topic.search(question)
            and not answer_terms.search(factual_text)
            and not mentions_absence
        ):
            return "relevance"
    return None


def _source_titles(text: str, evidence: list[Evidence]) -> str:
    """Replace exact evidence addresses, preserving unrelated technical paths."""
    titles = {item.public_path: item.title for item in evidence if item.public_path != "/"}
    if not titles:
        return text
    paths = "|".join(re.escape(path) for path in sorted(titles, key=len, reverse=True))
    address = re.compile(
        r"(?<![A-Za-z0-9_/.%:@\\-])"
        r"(?:(?i:https?)://[^\s/<>\"'`]+)?"
        rf"(?P<path>{paths})/?"
        r"(?![A-Za-z0-9_/%@\\-]|\.[A-Za-z0-9])"
        r"(?P<suffix>[?#][^\s<>\"'`()，。；！？、（）【】\[\]]*)?"
    )

    def label(match: re.Match[str]) -> str:
        suffix = match["suffix"] or ""
        punctuation = suffix[len(suffix.rstrip(".,;!")) :]
        return titles[match["path"]] + punctuation

    return address.sub(label, text)


@dataclass(frozen=True)
class ValidatedAnswer:
    text: str
    citations: list[dict[str, str]]
    sources: list[dict[str, str]]
    resume_notice: str | None = None


def validate_model_answer(
    parsed: ModelAnswer,
    evidence: list[Evidence],
    *,
    finish_reason: str,
    resume_available: bool | None = None,
    question: str = "",
) -> ValidatedAnswer | str:
    if finish_reason not in {"stop", "completed"}:
        return "incomplete"
    aliases = {item.alias: item for item in evidence}
    if not parsed.blocks:
        return "structure"
    cited: list[Evidence] = []
    texts: list[str] = []
    resume_notice = None
    for block in parsed.blocks:
        text = block.text.strip()
        if not text:
            return "structure"
        if invalid_quantity(text):
            return "grounding"
        if _unsafe_structure(text):
            return "structure"
        if not block.citation_ids:
            if (
                resume_available is False
                and text in RESUME_NOTICES
                and resume_notice is None
                and not block.supports
            ):
                resume_notice = text
                continue
            return "citation"
        for citation_id in block.citation_ids:
            item = aliases.get(citation_id)
            if item is None:
                return "citation"
            if item not in cited:
                cited.append(item)
        if not block.supports or {s.citation_id for s in block.supports} != set(block.citation_ids):
            return "grounding"
        for support in block.supports:
            if not support.quote.strip() or support.quote not in aliases[support.citation_id].body:
                return "grounding"
        # Validate the original syntax first so replacement cannot launder a
        # forbidden model link. Only cited, live sources can supply a title.
        text = _source_titles(text, [aliases[cid] for cid in block.citation_ids])
        if _unsafe_structure(text):
            return "structure"
        texts.append(text)
        if PERSONAL_CLAIM_RE.search(text) and any(
            aliases[s.citation_id].body.count(s.quote) != 1 for s in block.supports
        ):
            return "grounding"
        contexts = [
            (aliases[s.citation_id], _support_context(aliases[s.citation_id].body, s.quote))
            for s in block.supports
        ]
        if not _claims_supported(text, contexts):
            return "grounding"
        if not _conflicts_supported(text, block.citation_ids, evidence):
            return "grounding"
    if not cited:
        return "citation"
    if problem := _question_support(question, "\n".join(texts), evidence):
        return problem
    rendered: list[str] = []
    citation_payload: list[dict[str, str]] = []
    sources: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    number_by_alias: dict[str, int] = {}
    for item in cited:
        number = len(number_by_alias) + 1
        number_by_alias[item.alias] = number
        citation_payload.append(
            {
                "n": str(number),
                "alias": item.alias,
                "title": item.title,
                "heading_path": item.heading_path,
                "path": item.public_path,
            }
        )
        if item.public_path not in seen_paths:
            seen_paths.add(item.public_path)
            sources.append(
                {
                    "n": str(number),
                    "title": item.title,
                    "heading_path": item.heading_path,
                    "path": item.public_path,
                }
            )
    text_index = 0
    for block in parsed.blocks:
        if not block.citation_ids:
            continue
        marks = "".join(f"[{number_by_alias[cid]}]" for cid in block.citation_ids)
        rendered.append(f"{_render_technical_text(texts[text_index])}{marks}")
        text_index += 1
    if resume_notice:
        rendered.append(resume_notice)
    return ValidatedAnswer("\n\n".join(rendered), citation_payload, sources, resume_notice)

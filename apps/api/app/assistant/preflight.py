from __future__ import annotations

import base64
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from .constants import (
    CODE_OUT_OF_SCOPE,
    CODE_PROMPT_BLOCKED,
    GENERIC_REFUSAL_MESSAGE,
    PREFLIGHT_VERSION,
)

BIDI_CHARS = dict.fromkeys(map(ord, "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"))
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
ROLE_RE = re.compile(
    r"(ignore (all|any|previous|prior) (instructions|rules)|you are now|"
    r"set aside (earlier|previous|prior) (constraints|instructions|rules)|"
    r"reveal (your )?(hidden )?prompt|"
    r"忽略(之前|以上|全部).*(指令|规则)|你现在是系统|"
    r"别管(?:最初|原来|原有).{0,8}(?:约定|规则|指令)|"
    r"(?:先前|之前|原有).{0,12}(?:约束|规则|指令).{0,8}(?:搁置|作废|忽略))",
    re.IGNORECASE,
)
EXFIL_RE = re.compile(
    r"(repeat your (system|hidden) (prompt|instructions)|dump (memory|secrets|keys)|"
    r"(?:print|reveal|output|show).{0,24}(?:system prompt|hidden instructions|api[_-]?key)|"
    r"what (?:is|are) your (?:system prompt|hidden instructions|developer message)|"
    r"(?:输出|给出|展示|复述|打印|告诉我).{0,16}(?:系统提示词|隐藏.{0,8}(?:指令|指示)|启动指示)|"
    r"你的(?:系统提示词|隐藏指令|开发者消息).{0,6}(?:是什么|内容)|"
    r"把.{0,12}(?:隐藏说明|隐藏指令|系统提示词).{0,8}(?:复写|抄写|复述)|"
    r"exfiltrat|泄露(系统|提示|密钥)|begin private key)",
    re.IGNORECASE,
)
TOOL_RE = re.compile(
    r"(browse the web|search the internet|open a (browser|terminal)|run this (code|command)|"
    r"execute shell|send (an )?email|write to (disk|database)|call the tool|"
    r"联网搜索|打开浏览器|执行命令|发送邮件|写入数据库|"
    r"(?:然后|现在|请)(?:照做|执行它|照着执行))",
    re.IGNORECASE,
)
JD_RE = re.compile(
    r"(job description|\bJD\b|岗位职责|任职要求|招聘(岗位|要求)|薪资范围|汇报对象)",
    re.IGNORECASE,
)
CONTACT_RE = re.compile(
    r"(password\s*=|mysql://|postgres://|\bsk-[A-Za-z0-9]{16,}|-----BEGIN |"
    r"(?:api[_-]?key|secret[_-]?key)\s*[:=]\s*\S+)",
    re.IGNORECASE,
)
BASE64_RE = re.compile(r"\b[A-Za-z0-9+/]{48,}={0,2}\b")
CREDENTIAL_NAME_RE = re.compile(r"api[_-]?key|secret[_-]?key", re.IGNORECASE)
TECHNICAL_CONTEXT_RE = re.compile(
    r"教程|文章|配置|环境变量|"
    r"\b(?:tutorial|documentation|configure|configuration|environment variable)\b",
    re.IGNORECASE,
)
TUTORIAL_QUOTE_RE = re.compile(
    r"(?:^|(?<=[。！？.!?\n]))\s*"
    r"(?:(?:这篇|这份|站内)?(?:文章|教程|文档)(?:解释|讨论|分析|介绍)|"
    r"(?:请)?(?:解释|分析|讨论)(?:文章|教程|文档)中的)\s*"
    r"(?:“[^“”\n]+”|\"[^\"\n]+\"|`[^`\n]+`)\s*"
    r"(?:为何危险|为什么危险|的(?:含义|风险|原理)|属于什么攻击|如何防范)"
    r"\s*(?=[。！？.!?\n]|$)"
)
HIGH_RISK_CLAIM_RE = re.compile(
    r"(专家|精通|(?:\d+\s*年(?:以上)?经验)|world[- ]class expert)",
    re.IGNORECASE,
)
PLACEHOLDER_ASSIGNMENT_RE = re.compile(
    r"(?<![\w/?&=:])(?:api[_-]?key|secret[_-]?key|password)\s*[:=]\s*"
    r"(?P<value>[^\s;，。`]+)", re.IGNORECASE,
)
PLACEHOLDERS = frozenset({"YOUR_API_KEY", "YOUR_SECRET_KEY", "YOUR_PASSWORD"})
# Match complete explanatory clauses, replacing only action tokens. A topic
# word alone never exempts following commands, role changes or credentials.
ACTION_DISCUSSION_RE = re.compile(
    r"(?:(?:本站|这篇|这份|本)?(?:文章|教程|文档)(?:中)?"
    r"(?:(?:如何)?(?:介绍|解释|讨论|分析)ACTION(?:功能|流程|的原理|的风险)?"
    r"(?:[,，](?:通过|调用|使用|依赖)[^。！？.!?\n]{1,80}(?:通知|操作|处理|实现|连接|请求|服务|事务))?|ACTION的流程是什么)|"
    r"为什么不能ACTION|"
    r"How does (?:the|this) (?:article|tutorial|documentation) explain how to ACTION|"
    r"(?:This|The) (?:article|tutorial|documentation) explains how to ACTION)",
    re.IGNORECASE,
)


def _credential_view(text: str) -> str:
    def placeholder(match: re.Match[str]) -> str:
        value = match["value"]
        if len(value) > 1 and value[0] in "\"'" and value[-1] == value[0]:
            value = value[1:-1]
        return " example credential placeholder " if value in PLACEHOLDERS else match[0]
    return PLACEHOLDER_ASSIGNMENT_RE.sub(placeholder, text)


def _tool_view(text: str) -> str:
    def clause(match: re.Match[str]) -> str:
        original = match[0]
        masked, count = TOOL_RE.subn("ACTION", original.strip())
        return masked if count == 1 and ACTION_DISCUSSION_RE.fullmatch(masked) else original
    return re.sub(r"[^。！？.!?\n]+", clause, text)


@dataclass(frozen=True)
class PreflightResult:
    blocked: bool
    code: str | None
    message: str
    version: str = PREFLIGHT_VERSION


def normalize_question(text: str, *, max_chars: int) -> str:
    if text is None:
        raise ValueError("question is required")
    normalized = unicodedata.normalize("NFC", text)
    if normalized.translate(BIDI_CHARS) != normalized:
        raise ValueError("bidirectional characters are not allowed")
    if CONTROL_RE.search(normalized):
        raise ValueError("control characters are not allowed")
    stripped = normalized.strip()
    if not stripped or len(stripped) > max_chars:
        raise ValueError("question length is invalid")
    return stripped


def _decode_obfuscation(text: str) -> str:
    # Match compatibility forms and invisible separators without changing the
    # original question/quote that is stored or rendered.
    text = "".join(c for c in unicodedata.normalize("NFKC", text)
                   if unicodedata.category(c) != "Cf")
    extras: list[str] = []
    for match in BASE64_RE.findall(text):
        padded = match + "=" * ((4 - len(match) % 4) % 4)
        try:
            decoded = base64.b64decode(padded, validate=True).decode("utf-8")
        except ValueError:
            continue
        extras.append(decoded)
    return text + "\n" + "\n".join(extras)


def _credential_reference_blocked(text: str) -> bool:
    if not CREDENTIAL_NAME_RE.search(text):
        return False
    if any(CREDENTIAL_NAME_RE.search(url) for url in re.findall(r"https?://[^\s<>]+", text)):
        return True
    return not TECHNICAL_CONTEXT_RE.search(text)


def _instruction_view(text: str) -> str:
    # Only a complete explanatory frame is exempt, never bare quotes, a topic
    # word, or trailing requests to execute. Credential checks use the original.
    return TUTORIAL_QUOTE_RE.sub(" tutorial security example ", text)


def preflight_question(text: str) -> PreflightResult:
    haystack = _decode_obfuscation(text)
    instructions = _instruction_view(haystack)
    credentials = _credential_view(haystack)
    if (ROLE_RE.search(instructions) or EXFIL_RE.search(instructions)
            or _credential_reference_blocked(credentials)):
        return PreflightResult(True, CODE_PROMPT_BLOCKED, GENERIC_REFUSAL_MESSAGE)
    if TOOL_RE.search(_tool_view(instructions)):
        return PreflightResult(True, CODE_OUT_OF_SCOPE, GENERIC_REFUSAL_MESSAGE)
    if JD_RE.search(haystack) or CONTACT_RE.search(credentials):
        return PreflightResult(True, CODE_OUT_OF_SCOPE, GENERIC_REFUSAL_MESSAGE)
    return PreflightResult(False, None, "")


def scan_evidence(text: str) -> bool:
    haystack = _decode_obfuscation(text)
    instructions = _instruction_view(haystack)
    # A credential-management documentation path is not itself a credential or
    # an instruction to reveal one. Only exempt complete path segments: query
    # parameters, fragments, userinfo and surrounding prose keep the old scan.
    def documentation_path(match: re.Match[str]) -> str:
        try:
            url = urlsplit(match.group())
        except ValueError:
            return match.group()
        path = "/".join(
            "credential-field"
            if re.fullmatch(r"(?:api|secret)[_-]?keys?", segment, re.IGNORECASE)
            else segment
            for segment in url.path.split("/")
        )
        return urlunsplit(url._replace(path=path))

    exfil_text = re.sub(r"https?://[^\s<>()\[\]]+", documentation_path, haystack)
    return bool(
        ROLE_RE.search(instructions)
        or TOOL_RE.search(_tool_view(instructions))
        or CONTACT_RE.search(_credential_view(haystack))
        or EXFIL_RE.search(_instruction_view(exfil_text))
        or _credential_reference_blocked(_credential_view(exfil_text))
    )

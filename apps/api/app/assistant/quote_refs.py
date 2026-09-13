"""Request-local references to exact source spans; never fuzzy quote repair."""
from __future__ import annotations

import json
import re


class QuoteMessages(list):
    def __init__(self, messages, quotes):
        super().__init__(messages)
        self.quotes = quotes
        self.answer_in_english = False
        self.single_command = False


class QuoteMap(dict):
    def __init__(self):
        super().__init__()
        self.projects = {}


def source_quotes(body: str, source_type: str = '') -> list[str]:
    lines = body.splitlines(keepends=True)
    spans: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        start = index
        index += 1
        if not stripped:
            continue
        if source_type == 'resume' and stripped in {
            '姓名', '照片', '项目经历', '工作经历', '专业技能', '技术方向 技能与能力',
        }:
            continue
        if source_type == 'resume' and start == 0 and not re.match(
            r'\s*(?:•|[-*]|\d+[.)]|#)', line,
        ) and '｜' not in line and '：' not in line:
            while index < len(lines) and not re.match(r'\s*(?:•|[-*]|#)', lines[index]):
                index += 1
            continue
        if stripped.count('|') >= 2 and not stripped.startswith('|'):
            continue  # A table row cut at the chunk boundary is not a whole fact.
        if stripped.startswith('```'):
            while index < len(lines) and not lines[index].strip().startswith('```'):
                index += 1
            if index == len(lines):
                continue  # Incomplete fenced content is not a suggested full fact.
            index += 1
            if start and lines[start - 1].strip() and not re.match(
                r'\s*(?:#|\||```)', lines[start - 1],
            ):
                start -= 1  # Keep imperative/denial before the command.
        elif re.match(r'\s*(?:•|[-*]|\d+[.)])\s+', line):
            while (not re.search(r'[。.!?！？]$', lines[index - 1].strip())
                   and index < len(lines) and lines[index].strip() and not re.match(
                r'\s*(?:•|[-*]|\d+[.)]|#|```|\|)\s*', lines[index],
            )):
                index += 1
            if not re.search(r'[。.!?！？]$', lines[index - 1].strip()):
                continue  # Do not suggest a clipped resume bullet as complete.
        elif stripped.startswith('|'):
            if not stripped.endswith('|') or re.fullmatch(r'[\s|:\-]+', stripped):
                continue
        elif not stripped.startswith('#') and '｜' not in stripped:
            while (source_type != 'profile' and '|' not in line
                   and not re.search(r'[。.!?！？]$', lines[index - 1].strip())
                   and index < len(lines) and lines[index].strip() and not re.match(
                r'\s*(?:•|[-*]|\d+[.)]|#|```|\|)\s*', lines[index],
            ) and '｜' not in lines[index]):
                index += 1
        quote = ''.join(lines[start:index]).rstrip('\r\n')
        if 0 < len(quote) <= 1200 and quote not in spans:
            spans.append(quote)
    return spans


def quote_index(evidence, question: str = ''):
    quotes = QuoteMap()
    labels = []
    fields = re.findall(r'(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+', question)
    fields = [field for field in fields if any(field in item.body for item in evidence)]
    for item in evidence:
        for index, quote in enumerate(source_quotes(item.body, item.source_type)):
            if quote.strip().startswith('|') and fields and not any(re.search(
                r'(?<![A-Za-z0-9_])' + re.escape(field) + r'(?![A-Za-z0-9_])', quote,
            ) for field in fields):
                continue
            key = f'@q:{item.alias}:{index}'
            quotes[key] = (item.alias, quote)
            if quote.strip().startswith('|'):
                cells = quote.strip().strip('|').split('|')
                preview = cells[0].strip() + ' | ' + cells[1].strip()[:28]
            else:
                preview = quote[:28]
            labels.append([key, preview])
    reverse = {entry: key for key, entry in quotes.items()}
    by_alias = {item.alias: item for item in evidence}
    for key, (alias, quote) in quotes.items():
        item = by_alias[alias]
        if item.source_type != 'resume' or not quote.lstrip().startswith('•'):
            continue
        headers = set()
        for other in evidence:
            if (other.source_type, other.source_id, other.source_version) != (
                item.source_type, item.source_id, item.source_version,
            ):
                continue
            position = other.body.find(quote)
            if position < 0:
                # Exact overlap may connect a complete continuation to its
                # preceding project heading, but never by keywords/framework.
                position = other.body.rfind('•')
                tail = other.body[position:].rstrip('\r\n') if position >= 0 else ''
                if len(tail) < 32 or not quote.startswith(tail):
                    continue
            preceding = list(re.finditer(r'(?m)^[^\r\n]+｜[^\r\n]+$', other.body[:position]))
            if preceding:
                header = preceding[-1][0]
                if header_key := reverse.get((other.alias, header)):
                    headers.add(header_key)
        if len(headers) == 1:
            quotes.projects[key] = headers.pop()
    return quotes, json.dumps(labels, ensure_ascii=False, separators=(',', ':'))


def resolve_quotes(answer, quotes):
    """Resolve only server-built references, bound to their current source alias."""
    for block in answer.blocks:
        for support in block.supports:
            if not support.quote.startswith('@q:'):
                continue  # Legacy literal quotes still face the original exact check.
            entry = quotes.get(support.quote)
            if entry is None or entry[0] != support.citation_id:
                raise ValueError('unknown or cross-source quote reference')
            support.quote = entry[1]
    return answer


def render_quote(quote: str, english_command: bool = False) -> str:
    # Display source link labels without inventing navigable model links.
    # The full original quote remains attached for the unchanged validator.
    if english_command:
        command = re.fullmatch(
            r'(?:执行|检查|查看系统)[:：]\s*```[A-Za-z]*[ \t]*\n([^\n]+)\n```\s*', quote,
        )
        if command:
            return 'Run: `' + command[1] + '`'
    return re.sub(r'\[([^\]\n]+)\]\(https?://[^\s)]+\)', r'\1', quote)

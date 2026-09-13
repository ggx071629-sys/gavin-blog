from __future__ import annotations

import re

_MARKDOWN_IMAGE = re.compile(r"!\[(?P<alt>[^\]]*)\]\(")


def missing_image_alt_location(markdown: str) -> tuple[int, int] | None:
    """Return the first blank Markdown image alt location as one-based line/column."""
    for match in _MARKDOWN_IMAGE.finditer(markdown):
        if match.group("alt").strip():
            continue
        line = markdown.count("\n", 0, match.start()) + 1
        line_start = markdown.rfind("\n", 0, match.start()) + 1
        return line, match.start() - line_start + 1
    return None

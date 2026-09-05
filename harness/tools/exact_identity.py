"""Versioned identities and fail-closed collector/reporter set proofs."""

from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath

VERSION = 3


def identity(ref):
    path = ref["path"].replace("\\", "/")
    if PurePosixPath(path).is_absolute() or ":" in path or ".." in path.split("/"):
        raise ValueError("identity path must be repository relative")
    titles = ref.get("title_path")
    if (
        not isinstance(titles, list)
        or not titles
        or any(not isinstance(t, str) or not t or "\0" in t for t in titles)
    ):
        raise ValueError("complete title_path is required")
    if "config" not in ref or "project" not in ref:
        raise ValueError("identity config/project are required")
    return ref["kind"], ref["config"], ref["project"], path, tuple(titles)


def resolve(refs, rows):
    resolved = []
    for ref in refs:
        matches = [
            row
            for row in rows
            if row["kind"] == ref["kind"]
            and row["path"] == ref["path"]
            and (
                identity(row) == identity(ref)
                if "title_path" in ref
                else row["name"] == ref["name"]
            )
        ]
        if len(matches) != 1 or matches[0].get("disabled"):
            raise ValueError(
                "selected collection missing, duplicate or disabled: "
                + ref["path"]
                + "::"
                + ref["name"]
            )
        resolved.append(matches[0])
    prove(resolved, rows, phase="collection")
    return resolved


def prove(selected, actual, *, phase):
    expected = Counter(identity(r) for r in selected)
    observed = Counter(identity(r) for r in actual)
    if (
        not expected
        or any(n != 1 for n in expected.values())
        or any(n != 1 for n in observed.values())
        or expected != observed
    ):
        raise ValueError(
            phase + " identity mismatch: missing, duplicate or expanded selection"
        )


def test_list_line(ref):
    _, _, project, path, titles = identity(ref)
    selection_path = ref.get("selection_path", path.removeprefix("apps/web/"))
    parts = [project, selection_path, *titles]
    if any(any(c in part for c in "\r\n>›") or part != part.strip() for part in parts):
        return None
    if "]" in project or "[" in project:
        return None
    return (
        (f"[{project}] › " if project else "")
        + selection_path
        + " › "
        + " › ".join(titles)
    )

"""Line-sequence fuzzy matching for str_replace (ported from openai/codex seek_sequence)."""

from __future__ import annotations

from collections.abc import Callable


def _normalise_unicode(s: str) -> str:
    return (
        s.strip()
        .replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2015", "-")
        .replace("\u2212", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201a", "'")
        .replace("\u201b", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u201e", '"')
        .replace("\u201f", '"')
        .replace("\u00a0", " ")
        .replace("\u2002", " ")
        .replace("\u2003", " ")
        .replace("\u2004", " ")
        .replace("\u2005", " ")
        .replace("\u2006", " ")
        .replace("\u2007", " ")
        .replace("\u2008", " ")
        .replace("\u2009", " ")
        .replace("\u200a", " ")
        .replace("\u202f", " ")
        .replace("\u205f", " ")
        .replace("\u3000", " ")
    )


def _line_matchers() -> list[Callable[[str, str], bool]]:
    return [
        lambda a, b: a == b,
        lambda a, b: a.rstrip(" \t\r\n") == b.rstrip(" \t\r\n"),
        lambda a, b: a.strip() == b.strip(),
        lambda a, b: _normalise_unicode(a) == _normalise_unicode(b),
    ]


def seek_sequence(
    lines: list[str],
    pattern: list[str],
    start: int = 0,
) -> list[int]:
    """Return start indices where pattern matches; empty pattern matches at start only."""
    if not pattern:
        return [start] if start <= len(lines) else []
    if len(pattern) > len(lines):
        return []

    matchers = _line_matchers()
    matches: list[int] = []
    end = len(lines) - len(pattern) + 1
    for i in range(start, end):
        for match_line in matchers:
            if all(match_line(lines[i + j], pattern[j]) for j in range(len(pattern))):
                matches.append(i)
                break
    return matches


def splice_lines(
    content_lines: list[str],
    start: int,
    end_exclusive: int,
    replacement_lines: list[str],
) -> list[str]:
    return content_lines[:start] + replacement_lines + content_lines[end_exclusive:]


def fuzzy_replace_once(
    content: str, old_str: str, new_str: str
) -> tuple[str | None, str | None]:
    """Replace first unique fuzzy line-sequence match. Returns (new_content, error)."""
    if old_str == "":
        return None, "Error: old_str must not be empty."

    if old_str in content:
        count = content.count(old_str)
        if count > 1:
            return None, (
                f"Error: old_str appears {count} times as exact substring. "
                "Include more context to make a unique match."
            )
        return content.replace(old_str, new_str, 1), None

    content_lines = content.splitlines()
    search_lines = old_str.splitlines()
    new_lines = new_str.splitlines()

    indices = seek_sequence(content_lines, search_lines)
    if not indices:
        return None, (
            "Error: old_str not found (exact or fuzzy line match). "
            "Check whitespace and indentation."
        )
    if len(indices) > 1:
        return None, (
            f"Error: old_str matches {len(indices)} locations. "
            "Include more context to make a unique match."
        )

    start = indices[0]
    end_exclusive = start + len(search_lines)
    result_lines = splice_lines(content_lines, start, end_exclusive, new_lines)

    new_content = "\n".join(result_lines)
    if content.endswith("\n") and (new_content == "" or not new_content.endswith("\n")):
        new_content += "\n"

    return new_content, None

"""grep tool — ported from opencrabs src/brain/tools/grep.rs."""

from __future__ import annotations

import re
from fnmatch import fnmatch
from pathlib import Path

from pydantic_ai import RunContext

from gategrid.contrib.file_edit.deps import FileEditDeps
from gategrid.contrib.file_edit.sandbox import canonical_path

from opencrabs._common import bump_tool, resolve

_SKIP_DIRS = frozenset(
    {
        "target",
        "node_modules",
        ".git",
        "dist",
        "build",
        "__pycache__",
        ".mypy_cache",
        ".tox",
        ".eggs",
        "vendor",
        ".bundle",
    }
)


def grep(
    ctx: RunContext[FileEditDeps],
    pattern: str,
    path: str | None = None,
    regex: bool = False,
    case_insensitive: bool = False,
    line_numbers: bool = True,
    context: int | None = None,
    file_pattern: str | None = None,
    limit: int | None = None,
) -> str:
    """Search for patterns in file contents. Supports literal string or regex search with context lines.

    Args:
        pattern: Pattern to search for (literal string or regex)
        path: File or directory to search (defaults to working directory)
        regex: Treat pattern as regex instead of literal string
        case_insensitive: Case insensitive search
        line_numbers: Show line numbers in results
        context: Number of context lines to show before and after match
        file_pattern: File pattern to filter (e.g., '*.rs', '*.{js,ts}')
        limit: Maximum number of matches to return
    """
    bump_tool("grep")

    if not pattern.strip():
        return "Error: Pattern cannot be empty"

    effective_limit = limit if limit is not None else 200
    pattern_str = pattern if regex else re.escape(pattern)
    flags = re.IGNORECASE if case_insensitive else 0
    try:
        compiled = re.compile(pattern_str, flags)
    except re.error as e:
        return f"Error: Invalid pattern: {e}"

    workspace = canonical_path(ctx.deps.workspace)
    if path:
        search_path = resolve(ctx, path)
        if isinstance(search_path, str):
            return search_path
    else:
        search_path = workspace

    if not search_path.exists():
        return f"Path does not exist: {search_path}"

    matches: list[str] = []
    total_counter = [0]

    if search_path.is_file():
        _grep_file(
            search_path,
            compiled,
            line_numbers,
            context,
            file_pattern,
            effective_limit,
            matches,
            total_counter,
        )
    else:
        _grep_directory(
            search_path,
            compiled,
            line_numbers,
            context,
            file_pattern,
            effective_limit,
            matches,
            total_counter,
        )

    total_matches = total_counter[0]
    if not matches:
        return f"No matches found for pattern: '{pattern}'"

    summary = (
        f"\n\n({len(matches)} matches shown, {total_matches} total)"
        if total_matches > len(matches)
        else f"\n\n({total_matches} matches)"
    )
    return "\n\n".join(matches) + summary


def _grep_file(
    path: Path,
    compiled: re.Pattern[str],
    line_numbers: bool,
    context: int | None,
    file_pattern: str | None,
    limit: int,
    matches: list[str],
    total_matches: list[int],
) -> None:
    if file_pattern:
        fname = path.name
        if not fnmatch(fname, file_pattern):
            return
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    lines = content.splitlines()
    display_path = str(path)

    for line_num, line in enumerate(lines):
        if not compiled.search(line):
            continue
        total_matches[0] += 1
        if len(matches) >= limit:
            return

        result = f"{display_path}:"
        if line_numbers:
            result += f"{line_num + 1}:"
        if context:
            start = max(0, line_num - context)
            for i in range(start, line_num):
                result += f"\n  {i + 1}: {lines[i]}"
        result += f"\n> {line}"
        if context:
            end = min(len(lines), line_num + context + 1)
            for i in range(line_num + 1, end):
                result += f"\n  {i + 1}: {lines[i]}"
        matches.append(result)


def _grep_directory(
    dir_path: Path,
    compiled: re.Pattern[str],
    line_numbers: bool,
    context: int | None,
    file_pattern: str | None,
    limit: int,
    matches: list[str],
    total_matches: list[int],
) -> None:
    for entry in sorted(dir_path.iterdir(), key=lambda p: p.name.lower()):
        if len(matches) >= limit:
            return
        if entry.is_file():
            _grep_file(
                entry,
                compiled,
                line_numbers,
                context,
                file_pattern,
                limit,
                matches,
                total_matches,
            )
        elif entry.is_dir():
            name = entry.name
            if name.startswith(".") or name in _SKIP_DIRS:
                continue
            _grep_directory(
                entry,
                compiled,
                line_numbers,
                context,
                file_pattern,
                limit,
                matches,
                total_matches,
            )

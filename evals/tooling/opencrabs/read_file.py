"""read_file tool — ported from opencrabs src/brain/tools/read.rs."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_ai import RunContext

from gategrid.contrib.file_edit.deps import FileEditDeps

from opencrabs._common import bump_tool, resolve
from opencrabs.hashline import format_read_hashline

_LARGE_FILE_THRESHOLD = 10 * 1024 * 1024
_MAX_FILE_SIZE = 100 * 1024 * 1024
_MAX_LINES = 100_000


def read_file(
    ctx: RunContext[FileEditDeps],
    path: str,
    start_line: int | None = None,
    line_count: int | None = None,
    hashline: bool = False,
) -> str:
    """Read contents of a file from the filesystem. Can optionally read specific line ranges.

    Args:
        path: Path to the file to read (absolute or relative to working directory)
        start_line: Optional: Starting line number (0-indexed)
        line_count: Optional: Number of lines to read from start_line
        hashline: Optional: Output lines as HASH|content (2-char hash per line) for hashline_edit. Default: false.
    """
    try:
        return _read(ctx, path, start_line, line_count, hashline)
    except ValueError as e:
        return f"Error: {e}"


def _read(
    ctx: RunContext[FileEditDeps],
    path: str,
    start_line: int | None,
    line_count: int | None,
    hashline: bool,
    *,
    collision_format: Literal["COLLISION", "empty_hash"] = "COLLISION",
) -> str:
    bump_tool("read_file")
    resolved = resolve(ctx, path)
    if isinstance(resolved, str):
        return resolved
    if not resolved.exists():
        return f"Error: File not found: {path}"
    if not resolved.is_file():
        return f"Error: '{path}' is not a valid file."

    size = resolved.stat().st_size
    if size > _MAX_FILE_SIZE:
        return (
            f"File too large: {size // (1024 * 1024)} MB exceeds maximum "
            f"{_MAX_FILE_SIZE // (1024 * 1024)} MB. Use start_line and line_count to read portions."
        )

    is_large = size > _LARGE_FILE_THRESHOLD
    use_buffer = start_line is not None or line_count is not None or is_large

    if use_buffer:
        output, _total_lines, warning = _read_buffered(
            resolved, start_line, line_count, is_large
        )
    else:
        output = resolved.read_text(encoding="utf-8")
        warning = None

    if hashline:
        file_start = (start_line or 0) + 1
        output = format_read_hashline(
            output, file_start, collision_format=collision_format
        )

    if warning:
        return f"{output}\n\n[warning: {warning}]"
    return output


def _read_buffered(
    path: Path,
    start_line: int | None,
    line_count: int | None,
    is_large_file: bool,
) -> tuple[str, int, str | None]:
    start = start_line or 0
    max_lines = min(line_count or _MAX_LINES, _MAX_LINES)
    lines = path.read_text(encoding="utf-8").splitlines()
    total = len(lines)

    if start > total:
        raise ValueError(f"Start line {start} exceeds file length {total}")

    chunk = lines[start : start + max_lines]
    output = "\n".join(chunk)
    truncated = (
        line_count is None and len(chunk) >= _MAX_LINES and start + max_lines < total
    )

    warning = None
    if truncated:
        warning = (
            f"Output truncated at {_MAX_LINES} lines. File has {total} total lines. "
            "Use start_line and line_count for pagination."
        )
    elif is_large_file and line_count is None:
        warning = (
            f"Large file ({total} lines). Consider using start_line and line_count "
            "for better performance."
        )
    return output, total, warning

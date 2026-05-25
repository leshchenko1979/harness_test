"""read_file for opencrabs_h3_collision — empty-hash collision lines (  |content)."""

from __future__ import annotations

from pydantic_ai import RunContext

from gategrid.contrib.file_edit.deps import FileEditDeps

from opencrabs.read_file import _read


def read_file(
    ctx: RunContext[FileEditDeps],
    path: str,
    start_line: int | None = None,
    line_count: int | None = None,
    hashline: bool = False,
) -> str:
    """Read file contents; hashline mode uses '  |line' for duplicate-hash lines."""
    try:
        return _read(
            ctx,
            path,
            start_line,
            line_count,
            hashline,
            collision_format="empty_hash",
        )
    except ValueError as e:
        return f"Error: {e}"

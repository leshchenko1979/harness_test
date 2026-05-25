"""glob tool — ported from opencrabs src/brain/tools/glob.rs."""

from __future__ import annotations

from pathlib import Path

from pydantic_ai import RunContext

from gategrid.contrib.file_edit.deps import FileEditDeps
from gategrid.contrib.file_edit.sandbox import canonical_path

from opencrabs._common import bump_tool, resolve


def glob(
    ctx: RunContext[FileEditDeps],
    pattern: str,
    base_dir: str | None = None,
    limit: int | None = None,
    include_hidden: bool = False,
) -> str:
    """Find files matching a glob pattern. Supports wildcards: * (any chars), ** (recursive directories), ? (single char), [abc] (char class).

    Args:
        pattern: Glob pattern (e.g., '**/*.rs', 'src/**/*.test.js', '*.{md,txt}')
        base_dir: Base directory for search (defaults to working directory)
        limit: Maximum number of results to return
        include_hidden: Include hidden files (starting with .)
    """
    bump_tool("glob")
    if not pattern.strip():
        return "Error: Pattern cannot be empty"

    workspace = canonical_path(ctx.deps.workspace)
    if base_dir:
        base = resolve(ctx, base_dir)
        if isinstance(base, str):
            return base
    else:
        base = workspace

    if not base.exists():
        return f"Base directory does not exist: {base}"

    matches: list[Path] = []
    for p in sorted(base.glob(pattern)):
        if not include_hidden and p.name.startswith("."):
            continue
        matches.append(p)
        if limit is not None and len(matches) >= limit:
            break

    if not matches:
        return f"No files found matching pattern: {pattern}"

    rel_base = canonical_path(base)
    lines = [f"Found {len(matches)} files matching '{pattern}':\n\n"]
    for p in matches:
        try:
            display = canonical_path(p).relative_to(rel_base)
        except ValueError:
            display = p
        lines.append(f"  {display}\n")
    if limit is not None and len(matches) >= limit:
        lines.append(f"\n(Limited to {limit} results)")
    return "".join(lines)

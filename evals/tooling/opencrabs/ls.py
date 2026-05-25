"""ls tool — ported from opencrabs src/brain/tools/ls.rs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic_ai import RunContext

from gategrid.contrib.file_edit.deps import FileEditDeps
from gategrid.contrib.file_edit.sandbox import canonical_path

from opencrabs._common import bump_tool, resolve


def ls(
    ctx: RunContext[FileEditDeps],
    path: str | None = None,
    show_hidden: bool = False,
    detailed: bool = False,
    recursive: bool = False,
) -> str:
    """List contents of a directory. Shows files and subdirectories with optional details.

    Args:
        path: Directory path to list (defaults to current working directory)
        show_hidden: Include hidden files (starting with .)
        detailed: Show detailed information (size, modified time)
        recursive: List subdirectories recursively
    """
    bump_tool("ls")
    workspace = canonical_path(ctx.deps.workspace)
    if path:
        target = resolve(ctx, path)
        if isinstance(target, str):
            return target
    else:
        target = workspace

    if not target.exists():
        return f"Path does not exist: {target}"
    if not target.is_dir():
        return f"Path is not a directory: {target}"

    out: list[str] = []
    if recursive:
        _ls_recursive(target, show_hidden, out, 0)
    else:
        _ls_directory(target, show_hidden, detailed, out)
    return "".join(out)


def _ls_directory(
    path: Path, show_hidden: bool, detailed: bool, output: list[str]
) -> None:
    entries = sorted(path.iterdir(), key=lambda p: p.name.lower())
    dirs: list[str] = []
    files: list[str] = []
    for entry in entries:
        name = entry.name
        if not show_hidden and name.startswith("."):
            continue
        is_dir = entry.is_dir()
        if detailed:
            stat = entry.stat()
            modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            if is_dir:
                info = f"{'<DIR>':>10}  {modified}  {name}/"
            else:
                info = f"{stat.st_size:>10}  {modified}  {name}"
        elif is_dir:
            info = f"{name}/"
        else:
            info = name
        (dirs if is_dir else files).append(info + "\n")
    output.extend(dirs)
    output.extend(files)


def _ls_recursive(path: Path, show_hidden: bool, output: list[str], depth: int) -> None:
    indent = "  " * depth
    if depth > 0:
        output.append(f"{indent}{path}:\n")
    entries = sorted(path.iterdir(), key=lambda p: p.name.lower())
    for entry in entries:
        name = entry.name
        if not show_hidden and name.startswith("."):
            continue
        if entry.is_dir():
            output.append(f"{indent}{name}/\n")
            _ls_recursive(entry, show_hidden, output, depth + 1)
        else:
            output.append(f"{indent}{name}\n")

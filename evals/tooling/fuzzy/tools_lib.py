"""Reference file-edit tools (ported from legacy agent_eval_matrix.tools)."""

from __future__ import annotations

from pydantic_ai import RunContext

from gategrid.contrib.file_edit.deps import FileEditDeps
from gategrid.contrib.file_edit.sandbox import (
    SandboxError,
    canonical_path,
    relative_workspace_path,
    resolve_workspace_path,
)
from fuzzy.fuzzy_replace import fuzzy_replace_once


def _bump_tool(name: str) -> None:
    del name


def ls(ctx: RunContext[FileEditDeps], path: str = ".") -> list[str]:
    _bump_tool("ls")
    try:
        target = resolve_workspace_path(ctx.deps.workspace, path)
    except SandboxError as exc:
        return [str(exc)]
    if not target.exists():
        return [f"Error: Path '{path}' does not exist."]
    if target.is_file():
        return [relative_workspace_path(ctx.deps.workspace, target)]
    return [
        relative_workspace_path(ctx.deps.workspace, p) for p in sorted(target.iterdir())
    ]


def glob_tool(ctx: RunContext[FileEditDeps], pattern: str) -> list[str]:
    _bump_tool("glob_tool")
    workspace_c = canonical_path(ctx.deps.workspace)
    return [
        relative_workspace_path(workspace_c, f)
        for f in sorted(workspace_c.glob(pattern))
    ]


def grep(ctx: RunContext[FileEditDeps], pattern: str, file_path: str) -> list[str]:
    _bump_tool("grep")
    try:
        target = resolve_workspace_path(ctx.deps.workspace, file_path)
    except SandboxError as exc:
        return [str(exc)]
    if not target.is_file():
        return [f"Error: '{file_path}' is not a valid file."]
    matches = []
    with open(target, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if pattern in line:
                matches.append(f"Line {i}: {line.rstrip()}")
    if matches:
        return matches
    return [f"No matches found for '{pattern}'."]


def read_file(ctx: RunContext[FileEditDeps], file_path: str) -> str:
    _bump_tool("read_file")
    try:
        target = resolve_workspace_path(ctx.deps.workspace, file_path)
    except SandboxError as exc:
        return str(exc)
    if not target.is_file():
        return f"Error: '{file_path}' is not a valid file."
    return target.read_text(encoding="utf-8")


def str_replace(
    ctx: RunContext[FileEditDeps],
    file_path: str,
    old_str: str,
    new_str: str,
    *,
    strict_messages: bool = False,
) -> str:
    _bump_tool("str_replace")
    try:
        target = resolve_workspace_path(ctx.deps.workspace, file_path)
    except SandboxError as exc:
        return str(exc)
    if not target.is_file():
        return f"Error: '{file_path}' is not a valid file."
    content = target.read_text(encoding="utf-8")
    count = content.count(old_str)
    rel = relative_workspace_path(ctx.deps.workspace, target)
    if count == 0:
        if strict_messages:
            return (
                "Error: old_str not found byte-for-byte. "
                "Use read_file or grep to copy exact text including spaces and newlines."
            )
        return (
            "Error: The exact 'old_str' was not found. "
            "Check whitespace and indentation."
        )
    if count > 1:
        if strict_messages:
            return (
                f"Error: old_str appears {count} times. "
                "Include surrounding lines in old_str to make a unique match."
            )
        return (
            f"Error: The 'old_str' appears {count} times. "
            "Provide more context to make it unique."
        )
    new_content = content.replace(old_str, new_str, 1)
    target.write_text(new_content, encoding="utf-8")
    return f"Successfully replaced text in '{rel}'."


def str_replace_fuzzy(
    ctx: RunContext[FileEditDeps],
    file_path: str,
    old_str: str,
    new_str: str,
) -> str:
    _bump_tool("str_replace_fuzzy")
    try:
        target = resolve_workspace_path(ctx.deps.workspace, file_path)
    except SandboxError as exc:
        return str(exc)
    if not target.is_file():
        return f"Error: '{file_path}' is not a valid file."
    content = target.read_text(encoding="utf-8")
    rel = relative_workspace_path(ctx.deps.workspace, target)
    new_content, err = fuzzy_replace_once(content, old_str, new_str)
    if err:
        return err
    assert new_content is not None
    target.write_text(new_content, encoding="utf-8")
    return f"Successfully replaced text in '{rel}' (fuzzy match)."

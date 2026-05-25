"""edit_file tool — ported from opencrabs src/brain/tools/edit.rs."""

from __future__ import annotations

import re

from pydantic_ai import RunContext

from gategrid.contrib.file_edit.deps import FileEditDeps
from gategrid.contrib.file_edit.sandbox import relative_workspace_path

from opencrabs._common import build_edit_diff, bump_tool, resolve


def edit_file(
    ctx: RunContext[FileEditDeps],
    path: str,
    operation: str | None = None,
    old_text: str | None = None,
    new_text: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    line: int | None = None,
    text: str | None = None,
    pattern: str | None = None,
    replacement: str | None = None,
) -> str:
    """Edit a file intelligently using various operations: replace text, replace lines, insert lines, delete lines, or regex replace.

    If 'operation' is omitted but 'old_text' and 'new_text' are provided, 'replace' is inferred (Claude-style Edit shape).

    Args:
        path: Path to the file to edit
        operation: Type of edit operation
        old_text: Text to find and replace (for 'replace' operation)
        new_text: Replacement text (for 'replace' and 'replace_lines' operations)
        start_line: Starting line number (0-indexed, for line operations)
        end_line: Ending line number (0-indexed, inclusive, for line operations)
        line: Line number to insert at (0-indexed, for 'insert_line')
        text: Text to insert (for 'insert_line')
        pattern: Regex pattern to match (for 'regex_replace')
        replacement: Replacement text (for 'regex_replace')
    """
    bump_tool("edit_file")

    op = operation
    if op is None:
        if old_text is not None and new_text is not None:
            op = "replace"
        elif start_line is not None and end_line is not None and new_text is not None:
            op = "replace_lines"
        elif line is not None and text is not None:
            op = "insert_line"
        elif start_line is not None and end_line is not None:
            op = "delete_lines"
        elif pattern is not None and replacement is not None:
            op = "regex_replace"
        else:
            return (
                "Error: Could not infer edit operation; "
                "specify operation or required fields."
            )

    resolved = resolve(ctx, path)
    if isinstance(resolved, str):
        return resolved
    if not resolved.is_file():
        return f"Error: '{path}' is not a valid file."

    content = resolved.read_text(encoding="utf-8")
    lines = content.splitlines()

    if op == "replace":
        if old_text is None or new_text is None:
            return "Error: replace requires old_text and new_text"
        if old_text not in content:
            return f"Text not found in file: '{old_text}'"
        new_content = content.replace(old_text, new_text)
    elif op == "replace_lines":
        if start_line is None or end_line is None or new_text is None:
            return "Error: replace_lines requires start_line, end_line, and new_text"
        if start_line >= len(lines) or end_line >= len(lines):
            return (
                f"Line range {start_line}-{end_line} out of bounds "
                f"(file has {len(lines)} lines)"
            )
        if start_line > end_line:
            return "Error: start_line must be <= end_line"
        new_lines = lines[:start_line] + [new_text] + lines[end_line + 1 :]
        new_content = "\n".join(new_lines)
    elif op == "insert_line":
        if line is None or text is None:
            return "Error: insert_line requires line and text"
        if line > len(lines):
            return f"Line {line} out of bounds (file has {len(lines)} lines)"
        new_lines = lines[:line] + [text] + lines[line:]
        new_content = "\n".join(new_lines)
    elif op == "delete_lines":
        if start_line is None or end_line is None:
            return "Error: delete_lines requires start_line and end_line"
        if start_line >= len(lines) or end_line >= len(lines):
            return (
                f"Line range {start_line}-{end_line} out of bounds "
                f"(file has {len(lines)} lines)"
            )
        if start_line > end_line:
            return "Error: start_line must be <= end_line"
        new_lines = lines[:start_line] + lines[end_line + 1 :]
        new_content = "\n".join(new_lines)
    elif op == "regex_replace":
        if pattern is None or replacement is None:
            return "Error: regex_replace requires pattern and replacement"
        try:
            rx = re.compile(pattern)
        except re.error as e:
            return f"Error: Invalid regex: {e}"
        if not rx.search(content):
            return f"Pattern not found in file: '{pattern}'"
        new_content = rx.sub(replacement, content)
    else:
        return f"Error: Unknown operation '{op}'"

    resolved.write_text(new_content, encoding="utf-8")
    rel = relative_workspace_path(ctx.deps.workspace, resolved)
    lines_before = len(lines)
    lines_after = len(new_content.splitlines())
    diff = build_edit_diff(content, new_content)
    return f"Successfully edited {rel}. Lines: {lines_before} → {lines_after}\n{diff}"

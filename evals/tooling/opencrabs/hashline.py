"""Hashline helpers ported from opencrabs src/brain/tools/hashline/*.rs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from gategrid.contrib.file_edit.deps import FileEditDeps
from gategrid.contrib.file_edit.sandbox import relative_workspace_path

from opencrabs._common import build_edit_diff, bump_tool, resolve

# ZPMQVRWSNKTXJBYH — same alphabet as opencrabs hash.rs
_HASH_ALPHABET = "ZPMQVRWSNKTXJBYH"
_FNV_OFFSET_BASIS = 2_166_136_261
_FNV_PRIME = 16_777_619


def fnv1a_32(data: bytes) -> int:
    h = _FNV_OFFSET_BASIS
    for byte in data:
        h ^= byte
        h = (h * _FNV_PRIME) & 0xFFFFFFFF
    return h


def hash_line(content: str) -> str:
    h = fnv1a_32(content.encode("utf-8"))
    hi = (h >> 4) & 0xF
    lo = h & 0xF
    return _HASH_ALPHABET[hi] + _HASH_ALPHABET[lo]


def hash_all_lines(content: str) -> list[tuple[int, str]]:
    return [(i + 1, hash_line(line)) for i, line in enumerate(content.splitlines())]


def format_hashline(_line_number: int, tag: str, content: str) -> str:
    return f"{tag}|{content}"


def format_read_hashline(
    output: str,
    file_start_line: int,
    *,
    collision_format: Literal["COLLISION", "empty_hash"] = "COLLISION",
) -> str:
    """Apply hashline formatting to file text (mirrors read.rs)."""
    lines_with_hashes: list[tuple[int, str, str]] = []
    for i, line in enumerate(output.splitlines()):
        line_num = file_start_line + i
        lines_with_hashes.append((line_num, hash_line(line), line))

    hash_to_lines: dict[str, list[int]] = {}
    for line_num, tag, _ in lines_with_hashes:
        hash_to_lines.setdefault(tag, []).append(line_num)

    collision_hashes = {h for h, nums in hash_to_lines.items() if len(nums) > 1}

    formatted: list[str] = []
    for _line_num, tag, line in lines_with_hashes:
        if tag in collision_hashes:
            if collision_format == "empty_hash":
                formatted.append(f"  |{line}")
            else:
                formatted.append(f"COLLISION|{line}")
        else:
            formatted.append(format_hashline(0, tag, line))

    if collision_hashes:
        formatted.append("")
        if collision_format == "empty_hash":
            formatted.append(
                f"[WARNING: {len(collision_hashes)} line(s) have duplicate content hashes "
                "(shown as '  |line'). These lines cannot be edited with hashline_edit; "
                "use edit_file search/replace instead.]"
            )
        else:
            formatted.append(
                f"[WARNING: {len(collision_hashes)} line(s) have hash collisions and cannot be "
                "edited with hashline_edit. Use the conventional edit_file tool with "
                "search/replace instead.]"
            )
    return "\n".join(formatted)


@dataclass(frozen=True)
class HashRef:
    hash: str

    @classmethod
    def parse(cls, s: str) -> HashRef:
        s = s.strip()
        if s.startswith("#"):
            s = s[1:]
        if "|" in s:
            s = s[: s.find("|")]
        if "#" in s:
            s = s[s.find("#") + 1 :]
        if len(s) != 2:
            raise ValueError(
                f"Invalid hash ref: hash must be exactly 2 characters (got '{s}')"
            )
        return cls(hash=s.upper())


class ResolvedOp(Enum):
    REPLACE = "replace"
    APPEND = "append"
    PREPEND = "prepend"


@dataclass
class ResolvedEdit:
    op: ResolvedOp
    start_line: int
    end_line: int
    new_lines: list[str]
    index: int


def strip_hashline_prefixes(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        hash_pos = line.find("#")
        if hash_pos > 0:
            before = line[:hash_pos]
            after = line[hash_pos + 1 :]
            if (
                before.isdigit()
                and len(after) >= 3
                and after[0].isupper()
                and after[1].isupper()
                and after[2] == "|"
            ):
                out.append(after[3:])
                continue
        out.append(line)
    return out


def _validate_hash(href: HashRef, hash_to_lines: dict[str, list[int]]) -> int | str:
    lines_with_hash = hash_to_lines.get(href.hash)
    if lines_with_hash is None:
        return (
            f"Hash #{href.hash} not found in file. The file may have changed since your "
            "last read. Re-read with hashline=true to get updated references."
        )
    if len(lines_with_hash) > 1:
        line_list = ", ".join(str(l) for l in lines_with_hash)
        return (
            f"Hash collision: #{href.hash} appears on {len(lines_with_hash)} lines "
            f"({line_list}). This hash is ambiguous and cannot safely identify a single "
            "line. Use the `edit_file` tool with search/replace instead of hashline_edit."
        )
    return lines_with_hash[0]


def resolve_edits(
    edits: list[dict], hash_to_lines: dict[str, list[int]], total_lines: int
) -> tuple[list[ResolvedEdit] | None, str | None]:
    resolved: list[ResolvedEdit] = []
    for i, edit in enumerate(edits):
        op = edit.get("op")
        lines_text = edit.get("lines", "")
        if op == "replace":
            pos = edit.get("pos")
            if not pos:
                return None, f"Edit #{i + 1}: replace requires pos"
            try:
                pos_ref = HashRef.parse(pos)
            except ValueError as e:
                return None, f"Edit #{i + 1}: {e}"
            start = _validate_hash(pos_ref, hash_to_lines)
            if isinstance(start, str):
                return None, f"Edit #{i + 1}: {start}"
            end_line = start
            if end := edit.get("end"):
                try:
                    end_ref = HashRef.parse(end)
                except ValueError as e:
                    return None, f"Edit #{i + 1}: {e}"
                end_res = _validate_hash(end_ref, hash_to_lines)
                if isinstance(end_res, str):
                    return None, f"Edit #{i + 1}: {end_res}"
                end_line = end_res
                if end_line < start:
                    return None, (
                        f"Edit #{i + 1}: end line ({end_line}) must be >= start line ({start})"
                    )
            resolved.append(
                ResolvedEdit(
                    op=ResolvedOp.REPLACE,
                    start_line=start,
                    end_line=end_line,
                    new_lines=strip_hashline_prefixes(lines_text),
                    index=i,
                )
            )
        elif op == "append":
            after_line = total_lines
            if pos := edit.get("pos"):
                try:
                    pos_ref = HashRef.parse(pos)
                except ValueError as e:
                    return None, f"Edit #{i + 1}: {e}"
                after = _validate_hash(pos_ref, hash_to_lines)
                if isinstance(after, str):
                    return None, f"Edit #{i + 1}: {after}"
                after_line = after
            resolved.append(
                ResolvedEdit(
                    op=ResolvedOp.APPEND,
                    start_line=after_line,
                    end_line=after_line,
                    new_lines=strip_hashline_prefixes(lines_text),
                    index=i,
                )
            )
        elif op == "prepend":
            before_line = 1
            if pos := edit.get("pos"):
                try:
                    pos_ref = HashRef.parse(pos)
                except ValueError as e:
                    return None, f"Edit #{i + 1}: {e}"
                before = _validate_hash(pos_ref, hash_to_lines)
                if isinstance(before, str):
                    return None, f"Edit #{i + 1}: {before}"
                before_line = before
            resolved.append(
                ResolvedEdit(
                    op=ResolvedOp.PREPEND,
                    start_line=before_line,
                    end_line=before_line,
                    new_lines=strip_hashline_prefixes(lines_text),
                    index=i,
                )
            )
        else:
            return None, f"Edit #{i + 1}: unknown op '{op}'"
    return resolved, None


def _sort_key(edit: ResolvedEdit) -> int:
    return edit.start_line


def detect_overlaps(edits: list[ResolvedEdit]) -> str | None:
    ranges: list[tuple[int, int, int]] = []
    for e in edits:
        if e.op == ResolvedOp.REPLACE:
            start, end = e.start_line, e.end_line
        elif e.op == ResolvedOp.APPEND:
            start, end = e.start_line + 1, e.start_line + 1
        else:
            start, end = e.start_line, e.start_line
        ranges.append((start, end, e.index + 1))
    ranges.sort(key=lambda r: r[0])
    for i in range(len(ranges) - 1):
        _, end_a, idx_a = ranges[i]
        start_b, _, idx_b = ranges[i + 1]
        if end_a >= start_b:
            return (
                f"Overlapping edits: edit #{idx_a} (ending at line {end_a}) overlaps with "
                f"edit #{idx_b} (starting at line {start_b}). Adjust the ranges so they "
                "don't overlap."
            )
    return None


def apply_hashline_edits(
    content: str, edits: list[dict]
) -> tuple[str | None, str | None]:
    """Returns (new_content, error_message)."""
    original_lines = content.splitlines()
    total_lines = len(original_lines)
    line_hashes = hash_all_lines(content)
    hash_to_lines: dict[str, list[int]] = {}
    for num, tag in line_hashes:
        hash_to_lines.setdefault(tag, []).append(num)

    resolved, err = resolve_edits(edits, hash_to_lines, total_lines)
    if err:
        return None, err
    assert resolved is not None

    resolved.sort(key=_sort_key, reverse=True)
    overlap = detect_overlaps(resolved)
    if overlap:
        return None, overlap

    result_lines = list(original_lines)
    for edit in resolved:
        if edit.op == ResolvedOp.REPLACE:
            start_idx = min(edit.start_line - 1, len(result_lines))
            end_idx = min(edit.end_line, len(result_lines))
            del result_lines[start_idx:end_idx]
            for j, new_line in enumerate(edit.new_lines):
                result_lines.insert(start_idx + j, new_line)
        elif edit.op == ResolvedOp.APPEND:
            insert_idx = min(edit.start_line, len(result_lines))
            for j, new_line in enumerate(edit.new_lines):
                result_lines.insert(insert_idx + j, new_line)
        else:
            insert_idx = min(edit.start_line - 1, len(result_lines))
            for j, new_line in enumerate(edit.new_lines):
                result_lines.insert(insert_idx + j, new_line)

    new_content = "\n".join(result_lines)
    if content.endswith("\n") and not new_content.endswith("\n"):
        new_content += "\n"
    return new_content, None


class HashlineEditItem(BaseModel):
    """Single hashline edit operation (opencrabs hashline_edit schema item)."""

    op: Literal["replace", "append", "prepend"] = Field(
        description="Edit operation type"
    )
    pos: str | None = Field(
        default=None,
        description=(
            "Anchor line: 2-char content hash from read_file hashline mode (e.g. 'VK' or "
            "'VK|line text'). Required for replace, optional for append/prepend."
        ),
    )
    end: str | None = Field(
        default=None,
        description=(
            "End of replace range: same hash format as pos (inclusive). "
            "Omit to replace a single line."
        ),
    )
    lines: str = Field(
        description="Replacement or insertion text. Use \\n for multi-line content."
    )


def hashline_edit(
    ctx: RunContext[FileEditDeps],
    path: str,
    edits: list[HashlineEditItem],
) -> str:
    """Edit a file using hash-anchored line references. Each line is identified by a 2-char content hash (from read_file with hashline=true, shown as HASH|content). Reference lines by hash (e.g. VK or VK|line text) instead of reproducing text. Stale hashes are rejected before any changes are applied. Supports batch edits (multiple operations in one call).

    Args:
        path: Path to the file to edit
        edits: Array of edit operations to apply atomically
    """
    if not edits:
        return "Error: edits must contain at least one operation"
    edit_dicts = [item.model_dump(exclude_none=True) for item in edits]
    bump_tool("hashline_edit")

    resolved_path = resolve(ctx, path)
    if isinstance(resolved_path, str):
        return resolved_path
    if not resolved_path.is_file():
        return f"Error: '{path}' is not a valid file."

    content = resolved_path.read_text(encoding="utf-8")
    new_content, err = apply_hashline_edits(content, edit_dicts)
    if err:
        return f"Error: {err}"

    assert new_content is not None
    resolved_path.write_text(new_content, encoding="utf-8")
    rel = relative_workspace_path(ctx.deps.workspace, resolved_path)
    lines_before = len(content.splitlines())
    lines_after = len(new_content.splitlines())
    diff = build_edit_diff(content, new_content)
    return (
        f"Successfully edited {rel} (hashline). Lines: {lines_before} → {lines_after}\n"
        f"{diff}"
    )

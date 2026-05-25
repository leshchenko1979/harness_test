"""Builtin file-edit tools and profile tool loading."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic_ai import Tool

from gategrid.integrations.pydantic_ai.tools import load_tool_function, resolve_eval_path

_BUILTIN_TOOLS: dict[str, Callable[..., object]] = {}
_BUILTIN_LOADED = False

# Registry key (after builtin:) -> exposed LLM tool name
_BUILTIN_EXPOSED: dict[str, str] = {
    "ls": "ls",
    "glob": "glob",
    "grep": "grep",
    "read_file": "read_file",
    "str_replace": "str_replace",
}


def register_builtin_tool(name: str, fn: Callable[..., object]) -> None:
    if name in _BUILTIN_TOOLS:
        raise ValueError(f"duplicate builtin tool {name!r}")
    _BUILTIN_TOOLS[name] = fn


def _ensure_builtin_tools_loaded() -> None:
    global _BUILTIN_LOADED
    if _BUILTIN_LOADED:
        return
    import gategrid.contrib.file_edit.bundled  # noqa: F401

    _BUILTIN_LOADED = True


def _exposed_name_for_entry(entry: str) -> str:
    if entry.startswith("builtin:"):
        key = entry[len("builtin:") :]
        if not key:
            raise ValueError(f"invalid builtin tool entry {entry!r}")
        return _BUILTIN_EXPOSED.get(key, key)
    path = Path(entry)
    stem = path.stem
    if stem == "glob_tool":
        return "glob"
    return stem


def load_file_edit_tools(eval_root: Path, entries: list[str]) -> tuple[Tool, ...]:
    """Resolve profile tool entries to pydantic-ai Tools with short exposed names."""
    _ensure_builtin_tools_loaded()
    tools: list[Tool] = []
    seen_exposed: dict[str, str] = {}

    for entry in entries:
        exposed = _exposed_name_for_entry(entry)
        if exposed in seen_exposed:
            raise ValueError(
                f"duplicate exposed tool name {exposed!r} from "
                f"{seen_exposed[exposed]!r} and {entry!r}"
            )
        seen_exposed[exposed] = entry

        if entry.startswith("builtin:"):
            key = entry[len("builtin:") :]
            fn = _BUILTIN_TOOLS.get(key)
            if fn is None:
                known = ", ".join(sorted(_BUILTIN_TOOLS))
                raise ValueError(
                    f"unknown builtin tool {entry!r}; registered: {known or '(none)'}"
                )
            tools.append(Tool(fn, name=exposed))
            continue

        path = resolve_eval_path(entry, eval_root)
        fn = load_tool_function(path)
        tools.append(Tool(fn, name=exposed))

    return tuple(tools)

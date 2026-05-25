"""Load tool callables from eval-root-relative paths."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path


def resolve_eval_path(entry: str, eval_root: Path) -> Path:
    root = eval_root.resolve()
    path = Path(entry)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"Tool entry {entry!r} resolves outside eval_root {root}: {path}"
        ) from exc
    if path.suffix != ".py" or not path.is_file():
        raise ValueError(
            f"Tool entry {entry!r} must resolve to an existing .py file, got {path}"
        )
    return path


def _ensure_tooling_import_paths(tool_path: Path) -> None:
    tooling_dir = tool_path.parent
    if tooling_dir.name == "opencrabs":
        tooling_dir = tooling_dir.parent
    if tooling_dir.name == "opencrabs_h3":
        tooling_dir = tooling_dir.parent
    root = str(tooling_dir)
    if root not in sys.path:
        sys.path.insert(0, root)


def _module_import_name(path: Path) -> str:
    return "gategrid_tool_" + "_".join(path.with_suffix("").parts[-3:])


def load_tool_function(path: Path) -> Callable[..., object]:
    _ensure_tooling_import_paths(path)
    name = _module_import_name(path)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load tool module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    tool_name = path.stem
    fn = getattr(module, tool_name, None)
    if fn is None or not callable(fn):
        raise AttributeError(f"{path}: expected callable {tool_name!r}")
    return fn


def load_tool_functions(
    eval_root: Path, entries: list[str]
) -> tuple[Callable[..., object], ...]:
    return tuple(
        load_tool_function(resolve_eval_path(entry, eval_root)) for entry in entries
    )

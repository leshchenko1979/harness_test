"""@case registry, discovery, and matrix case-id resolution."""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

from gategrid.io import load_yaml_model
from gategrid.models.case_set_config import CaseSetConfig
from gategrid.models.matrix_config import MatrixConfig

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class CaseRecord:
    case_id: str
    tags: list[str] = field(default_factory=list)
    definition: str = ""
    data: dict[str, Any] = field(default_factory=dict)


# Populated by @case; cleared at start of discover_cases.
_pending: list[tuple[str, CaseRecord, str]] = []

_BUILTIN_CASES: dict[str, CaseRecord] = {}
_BUILTIN_CASE_SETS: dict[str, list[str]] = {}
_BUILTIN_LOADED = False


def case_id_qualify_mode() -> str:
    raw = os.environ.get("GATEGRID_CASE_ID_QUALIFY", "").strip().lower()
    if raw in ("", "name"):
        return "name"
    if raw == "module":
        return "module"
    raise ValueError(
        f"invalid GATEGRID_CASE_ID_QUALIFY={raw!r}; use 'name' or 'module'"
    )


def case_id_example_hint() -> str:
    mode = case_id_qualify_mode()
    if mode == "name":
        return "hello_world"
    return "subpkg.hello_world"


def print_case_id_convention(*, stream: Any = None) -> None:
    import sys

    out = stream or sys.stderr
    mode = case_id_qualify_mode()
    example = case_id_example_hint()
    print(
        f"gategrid: case ids use qualify={mode!r} "
        f"(GATEGRID_CASE_ID_QUALIFY); example id: {example!r}",
        file=out,
    )


def _qualified_case_id(fn: Callable[..., Any], module_name: str) -> str:
    fn_name = fn.__name__
    if case_id_qualify_mode() == "name":
        return fn_name
    if not module_name.startswith("cases."):
        rel = module_name.removeprefix("cases")
        rel = rel.removeprefix(".")
    else:
        rel = module_name[len("cases.") :]
    if not rel:
        rel = fn_name
    last = rel.rsplit(".", 1)[-1]
    if last == fn_name:
        return rel
    return f"{rel}.{fn_name}"


def register_builtin_case(record: CaseRecord) -> None:
    """Register a shipped case (contrib). Fails on duplicate id."""
    if record.case_id in _BUILTIN_CASES:
        raise ValueError(
            f"duplicate builtin case id {record.case_id!r}: "
            f"{_BUILTIN_CASES[record.case_id].definition} vs {record.definition}"
        )
    _BUILTIN_CASES[record.case_id] = record


def register_builtin_case_set(name: str, case_ids: list[str]) -> None:
    if name in _BUILTIN_CASE_SETS:
        raise ValueError(f"duplicate builtin case_set {name!r}")
    _BUILTIN_CASE_SETS[name] = list(case_ids)


def _ensure_file_edit_builtins_loaded() -> None:
    global _BUILTIN_LOADED
    if _BUILTIN_LOADED:
        return
    import gategrid.contrib.file_edit  # noqa: F401 — registers batteries on import

    _BUILTIN_LOADED = True


def _merge_case_registries(
    builtins: dict[str, CaseRecord],
    discovered: dict[str, CaseRecord],
) -> dict[str, CaseRecord]:
    collisions: dict[str, list[str]] = {}
    merged = dict(builtins)
    for case_id, record in discovered.items():
        if case_id in merged:
            collisions.setdefault(case_id, [merged[case_id].definition]).append(
                record.definition
            )
        else:
            merged[case_id] = record
    if collisions:
        parts = []
        for cid, defs in sorted(collisions.items()):
            parts.append(f"  {cid!r}: " + ", ".join(defs))
        raise ValueError("duplicate case ids:\n" + "\n".join(parts))
    return merged


def register_case_record(record: CaseRecord, *, idempotent: bool = False) -> None:
    """Register a case without a handler function."""
    if idempotent:
        for case_id, _, _ in _pending:
            if case_id == record.case_id:
                return
    _pending.append((record.case_id, record, record.definition))


def case(
    fn: F | None = None,
    *,
    id: str | None = None,
    tags: list[str] | None = None,
    data: dict[str, Any] | None = None,
) -> F | Callable[[F], F]:
    """Register a case handler (all arguments optional)."""

    def register(f: F) -> F:
        module_name = f.__module__
        case_id = id if id is not None else _qualified_case_id(f, module_name)
        record = CaseRecord(
            case_id=case_id,
            tags=list(tags or []),
            definition=f"{module_name}:{f.__name__}",
            data=dict(data or {}),
        )
        register_case_record(record)

        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return f(*args, **kwargs)

        wrapper._gategrid_case = record  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    if fn is not None:
        return register(fn)
    return register


def _ensure_eval_root_on_path(eval_root: Path) -> None:
    root = str(eval_root.resolve())
    while root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)


def discover_cases(eval_root: Path) -> dict[str, CaseRecord]:
    """Return builtin + eval_root/cases package cases (when present)."""
    global _pending
    _ensure_file_edit_builtins_loaded()
    builtins = dict(_BUILTIN_CASES)

    cases_dir = eval_root / "cases"
    if not cases_dir.is_dir():
        return builtins

    _pending = []
    _ensure_eval_root_on_path(eval_root)
    importlib.invalidate_caches()
    for name in list(sys.modules):
        if name == "cases" or name.startswith("cases."):
            del sys.modules[name]
    package = importlib.import_module("cases")
    import pkgutil

    prefix = package.__name__ + "."
    for module_info in pkgutil.walk_packages(package.__path__, prefix):
        importlib.import_module(module_info.name)

    discovered: dict[str, CaseRecord] = {}
    collisions: dict[str, list[str]] = {}
    for case_id, record, definition in _pending:
        if case_id in discovered:
            collisions.setdefault(case_id, [discovered[case_id].definition]).append(
                definition
            )
        else:
            discovered[case_id] = record

    if collisions:
        parts = []
        for cid, defs in sorted(collisions.items()):
            parts.append(f"  {cid!r}: " + ", ".join(defs))
        raise ValueError("duplicate case ids:\n" + "\n".join(parts))

    _pending = []
    return _merge_case_registries(builtins, discovered)


def resolve_case_ids(matrix: MatrixConfig, eval_root: Path) -> list[str]:
    """Expand matrix.cases + case_sets; dedupe preserving first-seen order."""
    seen: set[str] = set()
    ordered: list[str] = []

    def add(name: str) -> None:
        if name not in seen:
            seen.add(name)
            ordered.append(name)

    for name in matrix.cases:
        add(name)

    _ensure_file_edit_builtins_loaded()
    case_sets_dir = eval_root / "case_sets"
    for ref in matrix.case_sets:
        path = case_sets_dir / f"{ref}.yaml"
        if path.is_file():
            case_set = load_yaml_model(path, CaseSetConfig)
            names = case_set.cases
        elif ref in _BUILTIN_CASE_SETS:
            names = _BUILTIN_CASE_SETS[ref]
        else:
            raise FileNotFoundError(
                f"case_set {ref!r}: missing {path} and not a builtin case set"
            )
        for name in names:
            add(name)

    if not ordered:
        raise ValueError("matrix must resolve to at least one case id")
    return ordered

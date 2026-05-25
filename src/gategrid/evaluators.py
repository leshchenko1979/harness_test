"""@evaluator registry, discovery, and execution helpers."""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

from gategrid.models.artifact import RunArtifact
from gategrid.runtime import RunContext

F = TypeVar("F", bound=Callable[..., Any])

GATE_TAG = "gate"
METRIC_TAG = "metric"
METRIC_CANONICAL_TAG = "metric_canonical"
_VALID_TAGS = frozenset({GATE_TAG, METRIC_TAG, METRIC_CANONICAL_TAG})


@dataclass
class EvaluatorRecord:
    evaluator_id: str
    tags: list[str]
    fn: Any
    definition: str = ""


_BUILTIN: dict[str, EvaluatorRecord] = {}
_BUILTIN_LOADED = False
_pending: list[tuple[str, EvaluatorRecord, str]] = []


def register_builtin_evaluator(record: EvaluatorRecord) -> None:
    """Register a framework-paired gate/metric (contrib). Fails on duplicate id."""
    if record.evaluator_id in _BUILTIN:
        raise ValueError(
            f"duplicate builtin evaluator id {record.evaluator_id!r}: "
            f"{_BUILTIN[record.evaluator_id].definition} vs {record.definition}"
        )
    _BUILTIN[record.evaluator_id] = record


def _ensure_builtin_evaluators_loaded() -> None:
    global _BUILTIN_LOADED
    if _BUILTIN_LOADED:
        return
    import gategrid.contrib.file_edit  # noqa: F401 — registers builtins on import

    _BUILTIN_LOADED = True


def evaluator_id_qualify_mode() -> str:
    raw = os.environ.get("GATEGRID_EVALUATOR_ID_QUALIFY", "").strip().lower()
    if raw in ("", "name"):
        return "name"
    if raw == "module":
        return "module"
    raise ValueError(
        f"invalid GATEGRID_EVALUATOR_ID_QUALIFY={raw!r}; use 'name' or 'module'"
    )


def evaluator_id_example_hint() -> str:
    mode = evaluator_id_qualify_mode()
    if mode == "name":
        return "artifact_ok"
    return "echo_gate.artifact_ok"


def print_evaluator_id_convention(*, stream: Any = None) -> None:
    import sys

    out = stream or sys.stderr
    mode = evaluator_id_qualify_mode()
    example = evaluator_id_example_hint()
    print(
        f"gategrid: evaluator ids use qualify={mode!r} "
        f"(GATEGRID_EVALUATOR_ID_QUALIFY); example id: {example!r}",
        file=out,
    )


def _qualified_evaluator_id(fn: Callable[..., Any], module_name: str) -> str:
    fn_name = fn.__name__
    if evaluator_id_qualify_mode() == "name":
        return fn_name
    if not module_name.startswith("evaluators."):
        rel = module_name.removeprefix("evaluators")
        rel = rel.removeprefix(".")
    else:
        rel = module_name[len("evaluators.") :]
    if not rel:
        rel = fn_name
    last = rel.rsplit(".", 1)[-1]
    if last == fn_name:
        return rel
    return f"{rel}.{fn_name}"


def _validate_tags(tags: list[str]) -> list[str]:
    normalized = list(tags)
    if not normalized:
        raise ValueError("evaluator tags must include 'gate' and/or 'metric'")
    invalid = [t for t in normalized if t not in _VALID_TAGS]
    if invalid:
        raise ValueError(
            f"invalid evaluator tags {invalid!r}; use 'gate', 'metric', "
            "and/or 'metric_canonical'"
        )
    if METRIC_CANONICAL_TAG in normalized and METRIC_TAG not in normalized:
        raise ValueError("metric_canonical requires metric tag")
    return normalized


def evaluator(
    fn: F | None = None,
    *,
    id: str | None = None,
    tags: list[str] | None = None,
) -> F | Callable[[F], F]:
    """Register an evaluator (tags must include ``gate`` and/or ``metric``)."""

    def register(f: F) -> F:
        module_name = f.__module__
        eval_id = id if id is not None else _qualified_evaluator_id(f, module_name)
        tag_list = _validate_tags(list(tags or []))
        record = EvaluatorRecord(
            evaluator_id=eval_id,
            tags=tag_list,
            fn=f,
            definition=f"{module_name}:{f.__name__}",
        )
        _pending.append((eval_id, record, record.definition))

        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return f(*args, **kwargs)

        wrapper._gategrid_evaluator = record  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    if fn is not None:
        return register(fn)
    return register


def _ensure_eval_root_on_path(eval_root: Path) -> None:
    root = str(eval_root.resolve())
    while root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)


def _merge_evaluator_registries(
    builtins: dict[str, EvaluatorRecord],
    discovered: dict[str, EvaluatorRecord],
) -> dict[str, EvaluatorRecord]:
    collisions: dict[str, list[str]] = {}
    merged = dict(builtins)
    for eval_id, record in discovered.items():
        if eval_id in merged:
            collisions.setdefault(eval_id, [merged[eval_id].definition]).append(
                record.definition
            )
        else:
            merged[eval_id] = record
    if collisions:
        parts = []
        for eid, defs in sorted(collisions.items()):
            parts.append(f"  {eid!r}: " + ", ".join(defs))
        raise ValueError("duplicate evaluator ids:\n" + "\n".join(parts))
    return merged


def discover_evaluators(eval_root: Path) -> dict[str, EvaluatorRecord]:
    """Return builtin + eval_root/evaluators package (when present)."""
    global _pending
    _ensure_builtin_evaluators_loaded()
    builtins = dict(_BUILTIN)

    evaluators_dir = eval_root / "evaluators"
    if not evaluators_dir.is_dir():
        return builtins

    _pending = []
    _ensure_eval_root_on_path(eval_root)
    importlib.invalidate_caches()
    for name in list(sys.modules):
        if name == "evaluators" or name.startswith("evaluators."):
            del sys.modules[name]

    import pkgutil

    package = importlib.import_module("evaluators")
    prefix = package.__name__ + "."
    for module_info in pkgutil.walk_packages(package.__path__, prefix):
        importlib.import_module(module_info.name)

    discovered: dict[str, EvaluatorRecord] = {}
    collisions: dict[str, list[str]] = {}
    for eval_id, record, definition in _pending:
        if eval_id in discovered:
            collisions.setdefault(eval_id, [discovered[eval_id].definition]).append(
                definition
            )
        else:
            discovered[eval_id] = record

    if collisions:
        parts = []
        for eid, defs in sorted(collisions.items()):
            parts.append(f"  {eid!r}: " + ", ".join(defs))
        raise ValueError("duplicate evaluator ids:\n" + "\n".join(parts))

    _pending = []
    return _merge_evaluator_registries(builtins, discovered)


def gate_evaluators(registry: dict[str, EvaluatorRecord]) -> list[EvaluatorRecord]:
    return [r for r in registry.values() if GATE_TAG in r.tags]


def metric_evaluators(registry: dict[str, EvaluatorRecord]) -> list[EvaluatorRecord]:
    return [r for r in registry.values() if METRIC_TAG in r.tags]


def invoke_evaluator(
    record: EvaluatorRecord,
    ctx: RunContext,
    artifact: RunArtifact,
) -> bool | dict[str, Any]:
    target = record.fn
    if hasattr(target, "evaluate"):
        return target.evaluate(ctx, artifact)  # type: ignore[no-any-return]
    return target(ctx, artifact)  # type: ignore[no-any-return]


def _merge_evaluator_display(
    artifact: RunArtifact,
    eval_id: str,
    outcome: bool | dict[str, Any],
) -> None:
    if isinstance(outcome, dict):
        display = {k: v for k, v in outcome.items() if k != "artifact"}
        if not display or display == {"pass": True}:
            artifact.evaluators[eval_id] = True
        else:
            artifact.evaluators[eval_id] = display
    else:
        artifact.evaluators[eval_id] = bool(outcome)


def _apply_gate_outcome(
    *,
    record: EvaluatorRecord,
    outcome: bool | dict[str, Any],
    artifact: RunArtifact,
) -> tuple[RunArtifact, bool]:
    if isinstance(outcome, dict):
        ok = bool(outcome.get("pass", False))
        if "artifact" in outcome:
            artifact = RunArtifact.model_validate(outcome["artifact"])
        _merge_evaluator_display(artifact, record.evaluator_id, outcome)
        return artifact, ok
    ok = bool(outcome)
    artifact.evaluators[record.evaluator_id] = ok
    return artifact, ok


def _merge_metric_outcome(
    record: EvaluatorRecord,
    outcome: bool | dict[str, Any],
    merged: dict[str, float | int | str | bool],
) -> None:
    canonical = METRIC_CANONICAL_TAG in record.tags
    if isinstance(outcome, dict):
        for key, value in outcome.items():
            if isinstance(value, (str, int, float, bool)):
                if canonical:
                    merged[str(key)] = value
                else:
                    merged[f"{record.evaluator_id}.{key}"] = value
    elif isinstance(outcome, (str, int, float, bool)):
        if canonical:
            merged["value"] = outcome
        else:
            merged[f"{record.evaluator_id}.value"] = outcome


def run_evaluators_on_artifact(
    *,
    ctx: RunContext,
    artifact: RunArtifact,
    gates: list[EvaluatorRecord],
    metrics: list[EvaluatorRecord],
) -> tuple[bool, RunArtifact, dict[str, float | int | str | bool]]:
    """Run gate + metric evaluators; return (all_gates_passed, artifact, merged_metrics)."""
    merged: dict[str, float | int | str | bool] = {}
    all_gates_passed = True

    for record in gates:
        try:
            outcome = invoke_evaluator(record, ctx, artifact)
        except Exception as exc:
            all_gates_passed = False
            artifact.evaluators[record.evaluator_id] = False
            artifact.evaluators[f"{record.evaluator_id}__error"] = {
                "message": str(exc),
            }
            continue
        artifact, ok = _apply_gate_outcome(
            record=record, outcome=outcome, artifact=artifact
        )
        if not ok:
            all_gates_passed = False

    for record in metrics:
        try:
            outcome = invoke_evaluator(record, ctx, artifact)
        except Exception:
            continue
        _merge_metric_outcome(record, outcome, merged)

    return all_gates_passed, artifact, merged

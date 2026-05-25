"""@evaluator registry, discovery, and execution helpers."""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Literal, TypeVar

from gategrid.models.artifact import RunArtifact
from gategrid.models.evaluator_outcome import (
    ArtifactMergeError,
    EvaluatorOutcome,
    deep_merge_artifact,
)
from gategrid.runtime import RunContext

F = TypeVar("F", bound=Callable[..., Any])

ROLE_GATE = "gate"
ROLE_METRIC = "metric"
METRIC_CANONICAL_TAG = "metric_canonical"
EvaluatorRole = Literal["gate", "metric"]


@dataclass
class EvaluatorRecord:
    evaluator_id: str
    role: EvaluatorRole
    tags: list[str]
    fn: Any
    definition: str = ""


_BUILTIN: dict[str, EvaluatorRecord] = {}
_BUILTIN_LOADED = False
_pending: list[tuple[str, EvaluatorRecord, str]] = []


def register_builtin_evaluator(record: EvaluatorRecord) -> None:
    """Register a framework-paired evaluator (contrib). Fails on duplicate id."""
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


def _validate_registration(
    role: EvaluatorRole,
    tags: list[str],
    *,
    canonical: bool,
) -> list[str]:
    extra = list(tags)
    if canonical:
        if role != ROLE_METRIC:
            raise ValueError("canonical=True requires role='metric'")
        if METRIC_CANONICAL_TAG not in extra:
            extra.append(METRIC_CANONICAL_TAG)
    invalid = [t for t in extra if t != METRIC_CANONICAL_TAG]
    if invalid:
        raise ValueError(
            f"invalid evaluator tags {invalid!r}; only {METRIC_CANONICAL_TAG!r} is allowed"
        )
    return extra


def evaluator(
    fn: F | None = None,
    *,
    id: str | None = None,
    role: EvaluatorRole = ROLE_GATE,
    tags: list[str] | None = None,
    canonical: bool = False,
) -> F | Callable[[F], F]:
    """Register an evaluator with scheduling role gate or metric."""

    def register(f: F) -> F:
        module_name = f.__module__
        eval_id = id if id is not None else _qualified_evaluator_id(f, module_name)
        tag_list = _validate_registration(role, list(tags or []), canonical=canonical)
        record = EvaluatorRecord(
            evaluator_id=eval_id,
            role=role,
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


def evaluators_by_role(
    registry: dict[str, EvaluatorRecord],
    role: EvaluatorRole,
) -> list[EvaluatorRecord]:
    return sorted(
        (r for r in registry.values() if r.role == role),
        key=lambda r: r.evaluator_id,
    )


def gate_evaluators(registry: dict[str, EvaluatorRecord]) -> list[EvaluatorRecord]:
    return evaluators_by_role(registry, ROLE_GATE)


def metric_evaluators(registry: dict[str, EvaluatorRecord]) -> list[EvaluatorRecord]:
    return evaluators_by_role(registry, ROLE_METRIC)


def invoke_evaluator(
    record: EvaluatorRecord,
    ctx: RunContext,
    artifact: RunArtifact,
) -> EvaluatorOutcome:
    target = record.fn
    raw: Any
    if hasattr(target, "evaluate"):
        raw = target.evaluate(ctx, artifact)
    else:
        raw = target(ctx, artifact)
    return coerce_evaluator_outcome(raw, role=record.role)


def coerce_evaluator_outcome(
    raw: Any,
    *,
    role: EvaluatorRole,
) -> EvaluatorOutcome:
    if isinstance(raw, EvaluatorOutcome):
        return raw
    if isinstance(raw, bool):
        if role == ROLE_METRIC:
            return EvaluatorOutcome(metrics={"value": int(raw)} if raw else {})
        return EvaluatorOutcome(pass_=raw)
    if isinstance(raw, dict):
        if "pass" in raw or "message" in raw or "detail" in raw:
            return EvaluatorOutcome(
                pass_=bool(raw.get("pass", False)),
                message=raw.get("message"),
                detail=raw.get("detail"),
            )
        return EvaluatorOutcome(
            metrics={k: int(v) for k, v in raw.items() if isinstance(v, (int, float))}
        )
    if isinstance(raw, (int, float)):
        if role == ROLE_METRIC:
            return EvaluatorOutcome(metrics={"value": int(raw)})
        return EvaluatorOutcome(pass_=bool(raw))
    raise TypeError(f"evaluator returned unsupported type {type(raw)!r}")


def _write_evaluator_display(
    artifact: RunArtifact,
    eval_id: str,
    outcome: EvaluatorOutcome,
) -> None:
    if outcome.pass_ is None:
        return
    if outcome.pass_ and not outcome.message and not outcome.detail:
        artifact.evaluators[eval_id] = True
    else:
        display: dict[str, Any] = {"pass": outcome.pass_}
        if outcome.message is not None:
            display["message"] = outcome.message
        if outcome.detail is not None:
            display["detail"] = outcome.detail
        artifact.evaluators[eval_id] = display


def _merge_outcome_metrics(
    record: EvaluatorRecord,
    outcome: EvaluatorOutcome,
    merged: dict[str, float | int | str | bool],
) -> None:
    if not outcome.metrics:
        return
    canonical = METRIC_CANONICAL_TAG in record.tags
    for key, value in outcome.metrics.items():
        if isinstance(value, (str, int, float, bool)):
            if canonical:
                merged[str(key)] = value
            else:
                merged[f"{record.evaluator_id}.{key}"] = value


def apply_evaluator_outcome(
    *,
    record: EvaluatorRecord,
    outcome: EvaluatorOutcome,
    artifact: RunArtifact,
    merged: dict[str, float | int | str | bool],
) -> bool:
    """Apply one evaluator outcome; return whether gate passed (True if metric)."""
    if record.role == ROLE_GATE and outcome.pass_ is None:
        artifact.evaluators[record.evaluator_id] = False
        artifact.evaluators[f"{record.evaluator_id}__error"] = {
            "message": "gate evaluator must set pass_",
        }
        return False

    if outcome.artifact is not None:
        if outcome.artifact.messages:
            raise ArtifactMergeError(
                f"evaluator {record.evaluator_id!r} must not patch messages"
            )
        if outcome.artifact.evaluators:
            raise ArtifactMergeError(
                f"evaluator {record.evaluator_id!r} must not patch evaluators"
            )
        if outcome.artifact.tools_called:
            raise ArtifactMergeError(
                f"evaluator {record.evaluator_id!r} must not patch tools_called"
            )
        deep_merge_artifact(artifact, outcome.artifact)

    _write_evaluator_display(artifact, record.evaluator_id, outcome)
    _merge_outcome_metrics(record, outcome, merged)

    if record.role == ROLE_GATE:
        return bool(outcome.pass_)
    return True


def run_evaluators_on_artifact(
    *,
    ctx: RunContext,
    artifact: RunArtifact,
    gates: list[EvaluatorRecord],
    metrics: list[EvaluatorRecord],
) -> tuple[bool, RunArtifact, dict[str, float | int | str | bool]]:
    """Run gate then metric evaluators; return (all_gates_passed, artifact, merged_metrics)."""
    merged: dict[str, float | int | str | bool] = {}
    all_gates_passed = True

    for record in gates:
        try:
            outcome = invoke_evaluator(record, ctx, artifact)
        except (ArtifactMergeError, Exception) as exc:
            all_gates_passed = False
            artifact.evaluators[record.evaluator_id] = False
            artifact.evaluators[f"{record.evaluator_id}__error"] = {
                "message": str(exc),
            }
            continue
        ok = apply_evaluator_outcome(
            record=record,
            outcome=outcome,
            artifact=artifact,
            merged=merged,
        )
        if not ok:
            all_gates_passed = False

    for record in metrics:
        try:
            outcome = invoke_evaluator(record, ctx, artifact)
        except ArtifactMergeError:
            continue
        except Exception:
            continue
        apply_evaluator_outcome(
            record=record,
            outcome=outcome,
            artifact=artifact,
            merged=merged,
        )

    return all_gates_passed, artifact, merged

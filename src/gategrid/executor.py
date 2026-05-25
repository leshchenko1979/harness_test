"""Matrix cell executor — expand grid, run adapters, write reports."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from gategrid.aggregates import compute_overall
from gategrid.cases import (
    CaseRecord,
    _ensure_eval_root_on_path,
    discover_cases,
    resolve_case_ids,
)
from gategrid.evaluators import (
    EvaluatorRecord,
    discover_evaluators,
    gate_evaluators,
    metric_evaluators,
    run_evaluators_on_artifact,
)
from gategrid.fingerprint import build_fingerprint
from gategrid.io import load_matrix_config, load_yaml_model, save_json
from gategrid.models.artifact import RunArtifact
from gategrid.models.cell import AttemptRecord, CellKey, CellResult
from gategrid.models.gate_config import metric_keys_from_gate
from gategrid.models.matrix_config import MatrixConfig
from gategrid.models.model_config import ModelConfig
from gategrid.models.profile_config import ProfileConfig
from gategrid.models.report import MatrixReport, SamplingMeta
from gategrid.paths import reports_dir
from gategrid.runtime import RunContext, load_runtime_adapter
from gategrid.validate import resolve_eval_root, validate_matrix


@dataclass
class RunOutcome:
    report: MatrixReport
    report_path: Path
    trace_path: Path | None = None


class MatrixRunError(RuntimeError):
    """Configuration or validation failure before/during matrix run."""

    def __init__(self, errors: list[str] | str) -> None:
        if isinstance(errors, str):
            self.errors = [errors]
        else:
            self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def _failing_gate_id(artifact: RunArtifact | None) -> str | None:
    if artifact is None:
        return None
    for eval_id, outcome in artifact.evaluators.items():
        if eval_id.endswith("__error"):
            continue
        if outcome is False:
            return eval_id
        if isinstance(outcome, dict) and not outcome.get("pass", True):
            return eval_id
    return None


def attempt_passed(
    *,
    artifact: RunArtifact,
    ctx: RunContext,
    gates: list[EvaluatorRecord],
    metrics: list[EvaluatorRecord],
) -> tuple[bool, RunArtifact, dict[str, float | int | str | bool], str | None]:
    """Return passed, artifact (with evaluators), metric merge, and error gate id if any."""
    if artifact.error:
        return False, artifact, {}, artifact.error

    if gates:
        gate_ok, artifact, merged = run_evaluators_on_artifact(
            ctx=ctx,
            artifact=artifact,
            gates=gates,
            metrics=metrics,
        )
        if not gate_ok:
            return False, artifact, merged, _failing_gate_id(artifact)
        return True, artifact, merged, None

    _, artifact, merged = run_evaluators_on_artifact(
        ctx=ctx,
        artifact=artifact,
        gates=[],
        metrics=metrics,
    )
    return True, artifact, merged, None


async def run_matrix(
    matrix_path: Path,
    *,
    eval_root: Path | None = None,
    case_filter: str | None = None,
) -> RunOutcome:
    matrix_path = matrix_path.resolve()
    root = resolve_eval_root(matrix_path, eval_root)
    _ensure_eval_root_on_path(root)

    validation = validate_matrix(matrix_path, root=root, emit_conventions=False)
    if not validation.ok:
        raise MatrixRunError(validation.errors)

    try:
        matrix = load_matrix_config(matrix_path)
    except Exception as exc:
        raise MatrixRunError(f"matrix {matrix_path.name}: {exc}") from exc

    try:
        case_registry = discover_cases(root)
    except Exception as exc:
        raise MatrixRunError(str(exc)) from exc

    try:
        evaluator_registry = discover_evaluators(root)
    except Exception as exc:
        raise MatrixRunError(str(exc)) from exc

    gates = gate_evaluators(evaluator_registry)
    metric_evals = metric_evaluators(evaluator_registry)

    try:
        case_ids = resolve_case_ids(matrix, root)
    except Exception as exc:
        raise MatrixRunError(str(exc)) from exc

    if case_filter is not None:
        if case_filter not in case_ids:
            raise MatrixRunError(
                f"unknown case id {case_filter!r}; matrix cases: {', '.join(case_ids)}"
            )
        case_ids = [case_filter]

    for cid in case_ids:
        if cid not in case_registry:
            known = ", ".join(sorted(case_registry))
            raise MatrixRunError(
                f"unknown case id {cid!r}; registered: {known or '(none)'}"
            )

    profiles = _load_profiles(matrix, root)
    models = _load_models(matrix, root)
    adapters = _load_profile_adapters(profiles)

    max_retries = matrix.run.max_retries
    cells: list[CellResult] = []
    planned = len(case_ids) * len(matrix.profiles) * len(matrix.models)

    for case_id in case_ids:
        record = case_registry[case_id]
        for profile_id in matrix.profiles:
            for model_id in matrix.models:
                cell = await _run_cell(
                    case_id=case_id,
                    record=record,
                    profile_id=profile_id,
                    model_id=model_id,
                    eval_root=root,
                    profile=profiles[profile_id],
                    model=models[model_id],
                    adapter=adapters[profile_id],
                    max_retries=max_retries,
                    gates=gates,
                    metrics=metric_evals,
                )
                cells.append(cell)

    mean_keys = metric_keys_from_gate(matrix.gate)
    overall = compute_overall(cells, mean_keys=mean_keys)
    matrix_name = matrix.name or matrix_path.stem
    timestamp = datetime.now(UTC).isoformat()
    report = MatrixReport(
        timestamp=timestamp,
        matrix_path=str(matrix_path),
        matrix_name=matrix_name,
        commit_sha=os.environ.get("GITHUB_SHA", "local"),
        fingerprint=build_fingerprint(matrix_name, cells),
        sampling=SamplingMeta(
            sampled=False,
            planned_cells=planned,
            executed_cells=len(cells),
        ),
        run_max_retries=max_retries,
        cells=cells,
        overall=overall,
    )

    ts_slug = timestamp.replace(":", "").replace("+00:00", "Z")[:19]
    out_path = reports_dir() / f"{ts_slug}_matrix.json"
    save_json(out_path, report)
    return RunOutcome(report=report, report_path=out_path)


def run_matrix_sync(
    matrix_path: Path,
    *,
    eval_root: Path | None = None,
    case_filter: str | None = None,
) -> RunOutcome:
    return asyncio.run(
        run_matrix(matrix_path, eval_root=eval_root, case_filter=case_filter)
    )


def _load_profiles(matrix: MatrixConfig, eval_root: Path) -> dict[str, ProfileConfig]:
    out: dict[str, ProfileConfig] = {}
    for profile_id in matrix.profiles:
        path = eval_root / "profiles" / f"{profile_id}.yaml"
        out[profile_id] = load_yaml_model(path, ProfileConfig)
    return out


def _load_models(matrix: MatrixConfig, eval_root: Path) -> dict[str, ModelConfig]:
    out: dict[str, ModelConfig] = {}
    for model_id in matrix.models:
        path = eval_root / "models" / f"{model_id}.yaml"
        out[model_id] = load_yaml_model(path, ModelConfig)
    return out


def _load_profile_adapters(
    profiles: dict[str, ProfileConfig],
) -> dict[str, object]:
    adapters: dict[str, object] = {}
    for profile_id, profile in profiles.items():
        spec = profile.runtime_adapter
        if not spec:
            raise MatrixRunError(f"profile {profile_id!r}: runtime_adapter is required")
        try:
            adapters[profile_id] = load_runtime_adapter(spec)
        except Exception as exc:
            raise MatrixRunError(
                f"profile {profile_id!r}: cannot load runtime_adapter {spec!r}: {exc}"
            ) from exc
    return adapters


async def _run_cell(
    *,
    case_id: str,
    record: CaseRecord,
    profile_id: str,
    model_id: str,
    eval_root: Path,
    profile: ProfileConfig,
    model: ModelConfig,
    adapter: object,
    max_retries: int,
    gates: list[EvaluatorRecord],
    metrics: list[EvaluatorRecord],
) -> CellResult:
    key = CellKey(case_id=case_id, profile_id=profile_id, model_id=model_id)
    ctx = RunContext(
        case_id=case_id,
        profile_id=profile_id,
        model_id=model_id,
        eval_root=eval_root,
        profile=profile,
        model=model,
        case=record,
    )

    attempts: list[AttemptRecord] = []
    last_error: str | None = None
    passed_any = False
    cell_metrics: dict[str, float | int | str | bool] = {}

    for attempt_index in range(max_retries + 1):
        ctx.scratchpad.clear()
        start = time.perf_counter()
        try:
            artifact = await adapter.execute(ctx)  # type: ignore[union-attr]
            ok, artifact, merged, err = attempt_passed(
                artifact=artifact,
                ctx=ctx,
                gates=gates,
                metrics=metrics,
            )
            duration_ms = (time.perf_counter() - start) * 1000.0
            if err:
                last_error = err
            attempts.append(
                AttemptRecord(
                    attempt_index=attempt_index,
                    passed=ok,
                    artifact=artifact,
                    error=err,
                    duration_ms=duration_ms,
                )
            )
            cell_metrics.update(merged)
            if ok:
                passed_any = True
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            last_error = str(exc)
            attempts.append(
                AttemptRecord(
                    attempt_index=attempt_index,
                    passed=False,
                    error=last_error,
                    duration_ms=duration_ms,
                )
            )

        if passed_any:
            break

    attempt_passes = [a.passed for a in attempts]
    flaky = max_retries > 0 and len(set(attempt_passes)) > 1

    if passed_any and attempts:
        last_ok = next(a for a in reversed(attempts) if a.passed)
        art = last_ok.artifact
        duration_ms = sum(a.duration_ms for a in attempts)
        base_metrics = dict(art.metrics) if art else {}
        base_metrics.update(cell_metrics)
        return CellResult(
            key=key,
            passed=True,
            tags=list(record.tags),
            attempts=attempts,
            flaky_suspect=flaky,
            duration_ms=duration_ms,
            metrics=base_metrics,
        )

    if not last_error and attempts:
        last_attempt = attempts[-1]
        if last_attempt.error:
            last_error = last_attempt.error
        elif last_attempt.artifact is not None:
            last_error = _failing_gate_id(last_attempt.artifact)

    fail_metrics = dict(cell_metrics)
    if attempts:
        last_attempt = attempts[-1]
        if last_attempt.artifact is not None:
            for k, v in last_attempt.artifact.metrics.items():
                if isinstance(v, (int, float, str, bool)):
                    fail_metrics.setdefault(str(k), v)

    return CellResult(
        key=key,
        passed=False,
        tags=list(record.tags),
        attempts=attempts,
        flaky_suspect=flaky,
        duration_ms=sum(a.duration_ms for a in attempts),
        error=last_error or "cell failed",
        metrics=fail_metrics,
    )

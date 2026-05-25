from __future__ import annotations

from dataclasses import dataclass, field

from gategrid.aggregates import compute_overall
from gategrid.fingerprint import fingerprint_matches, intersection_keys
from gategrid.models.baseline import Baseline
from gategrid.models.cell import CellResult
from gategrid.models.gate_config import GateConfig, GateLimits, RegressionBounds
from gategrid.models.report import MatrixReport, ReportOverall


@dataclass
class GateCheckResult:
    name: str
    passed: bool
    message: str


@dataclass
class GateOutcome:
    passed: bool
    checks: list[GateCheckResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _baseline_snapshots_as_results(
    baseline: Baseline,
    report_cells: list[CellResult],
) -> list[CellResult]:
    out: list[CellResult] = []
    for cell in report_cells:
        snap = baseline.get_cell(cell.key)
        if snap is None:
            continue
        out.append(
            CellResult(
                key=snap.key,
                passed=snap.passed,
                duration_ms=snap.duration_ms,
                metrics=dict(snap.metrics),
            )
        )
    return out


def _filter_cells(cells: list[CellResult], keys: list) -> list[CellResult]:
    key_set = {(k.case_id, k.profile_id, k.model_id) for k in keys}
    return [c for c in cells if c.key.as_tuple() in key_set]


def _metric_value(overall: ReportOverall, key: str) -> float:
    return overall.metrics.get(key, 0.0)


def _check_metric_regression_bounds(
    name: str,
    current: ReportOverall,
    baseline: ReportOverall,
    bounds: RegressionBounds,
) -> list[GateCheckResult]:
    checks: list[GateCheckResult] = []
    for key, max_delta in bounds.metric_mean_max_delta.items():
        cur = _metric_value(current, key)
        base = _metric_value(baseline, key)
        delta = cur - base
        ok = delta <= max_delta
        checks.append(
            GateCheckResult(
                name=f"{name}.{key}_max_delta",
                passed=ok,
                message=f"{key} mean delta {delta:+.4f} (max {max_delta:+.4f})",
            )
        )
    for key, min_delta in bounds.metric_mean_min_delta.items():
        cur = _metric_value(current, key)
        base = _metric_value(baseline, key)
        delta = cur - base
        ok = delta >= min_delta
        checks.append(
            GateCheckResult(
                name=f"{name}.{key}_min_delta",
                passed=ok,
                message=f"{key} mean delta {delta:+.4f} (min {min_delta:+.4f})",
            )
        )
    return checks


def _check_regression_bounds(
    name: str,
    current: ReportOverall,
    baseline: ReportOverall,
    bounds: RegressionBounds,
) -> list[GateCheckResult]:
    checks: list[GateCheckResult] = []
    if bounds.pass_rate_min_delta is not None:
        delta = current.pass_rate - baseline.pass_rate
        ok = delta >= bounds.pass_rate_min_delta
        checks.append(
            GateCheckResult(
                name=f"{name}.pass_rate_delta",
                passed=ok,
                message=(
                    f"pass_rate delta {delta:+.4f} "
                    f"(min {bounds.pass_rate_min_delta:+.4f})"
                ),
            )
        )
    checks.extend(
        _check_metric_regression_bounds(name, current, baseline, bounds)
    )
    return checks


def _check_metric_limits(
    name: str, current: ReportOverall, limits: GateLimits
) -> list[GateCheckResult]:
    checks: list[GateCheckResult] = []
    for key, max_val in limits.metric_mean_max.items():
        cur = _metric_value(current, key)
        ok = cur <= max_val
        checks.append(
            GateCheckResult(
                name=f"{name}.{key}_max",
                passed=ok,
                message=f"{key} mean {cur:.4f} (max {max_val:.4f})",
            )
        )
    for key, min_val in limits.metric_mean_min.items():
        cur = _metric_value(current, key)
        ok = cur >= min_val
        checks.append(
            GateCheckResult(
                name=f"{name}.{key}_min",
                passed=ok,
                message=f"{key} mean {cur:.4f} (min {min_val:.4f})",
            )
        )
    return checks


def _check_limits(
    name: str, current: ReportOverall, limits: GateLimits
) -> list[GateCheckResult]:
    checks: list[GateCheckResult] = []
    if limits.pass_rate_min is not None:
        ok = current.pass_rate >= limits.pass_rate_min
        checks.append(
            GateCheckResult(
                name=f"{name}.pass_rate_min",
                passed=ok,
                message=f"pass_rate {current.pass_rate:.4f} (min {limits.pass_rate_min:.4f})",
            )
        )
    checks.extend(_check_metric_limits(name, current, limits))
    return checks


def _count_regressed_cells(
    report_cells: list[CellResult],
    baseline: Baseline,
) -> int:
    n = 0
    for cell in report_cells:
        snap = baseline.get_cell(cell.key)
        if snap is None:
            continue
        if snap.passed and not cell.passed:
            n += 1
    return n


def run_gate(
    report: MatrixReport,
    baseline: Baseline,
    config: GateConfig,
    *,
    profile_id: str | None = None,
) -> GateOutcome:
    profile_id = profile_id or baseline.profile_id
    report_cells = [c for c in report.cells if c.key.profile_id == profile_id]
    if not report_cells:
        return GateOutcome(
            passed=False,
            checks=[
                GateCheckResult(
                    name="cells",
                    passed=False,
                    message=f"no report cells for profile {profile_id!r}",
                )
            ],
        )

    checks: list[GateCheckResult] = []
    warnings: list[str] = []

    report_overall = report.overall or compute_overall(report_cells)
    baseline_keys = set(baseline.cells.keys())
    lfk = intersection_keys(report_cells, baseline_keys)
    like_cells = _filter_cells(report_cells, lfk)

    if config.regression is not None:
        if not fingerprint_matches(report.fingerprint, baseline.fingerprint):
            warnings.append(
                "fingerprint mismatch (matrix name, profile_ids, or case_ids differ); "
                "overall regression may not be apples-to-apples"
            )

        bounds = config.regression.bounds
        if overall_bounds := bounds.get("overall"):
            checks.extend(
                _check_regression_bounds(
                    "regression.overall",
                    report_overall,
                    baseline.overall,
                    overall_bounds,
                )
            )

        if lfk_bounds := bounds.get("like_for_like"):
            if like_cells:
                like_overall = compute_overall(like_cells)
                baseline_like_cells = _baseline_snapshots_as_results(
                    baseline, like_cells
                )
                base_like_overall = compute_overall(baseline_like_cells)
                checks.extend(
                    _check_regression_bounds(
                        "regression.like_for_like",
                        like_overall,
                        base_like_overall,
                        lfk_bounds,
                    )
                )
            else:
                warnings.append("like_for_like: empty intersection with baseline")

            max_reg = lfk_bounds.max_regressed_cells
            if max_reg is not None:
                regressed = _count_regressed_cells(like_cells, baseline)
                ok = regressed <= max_reg
                checks.append(
                    GateCheckResult(
                        name="regression.like_for_like.regressed_cells",
                        passed=ok,
                        message=f"regressed cells {regressed} (max {max_reg})",
                    )
                )

    for scope, limits in config.limits.items():
        if scope == "overall":
            target = report_overall
        elif scope == "like_for_like":
            target = compute_overall(like_cells) if like_cells else None
        else:
            warnings.append(f"unknown limits scope {scope!r}")
            continue
        if target is None:
            warnings.append(f"limits.{scope}: no cells to check")
            continue
        checks.extend(_check_limits(f"limits.{scope}", target, limits))

    passed = all(c.passed for c in checks) if checks else True
    return GateOutcome(passed=passed, checks=checks, warnings=warnings)

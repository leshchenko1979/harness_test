from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from gategrid.aggregates import compute_overall, overall_to_baseline
from gategrid.io import load_matrix_config, load_report, save_json
from gategrid.models.baseline import Baseline, BaselineCellSnapshot
from gategrid.models.gate_config import metric_keys_from_gate
from gategrid.models.report import MatrixReport
from gategrid.paths import baseline_path


def cells_for_profile(report: MatrixReport, profile_id: str) -> list:
    return [c for c in report.cells if c.key.profile_id == profile_id]


def report_to_baseline(
    report: MatrixReport,
    profile_id: str,
    *,
    source_report_path: str | None = None,
    updated_at: str | None = None,
    mean_keys: set[str] | None = None,
) -> Baseline:
    subset = cells_for_profile(report, profile_id)
    if not subset:
        raise ValueError(f"no cells for profile_id={profile_id!r} in report")

    keys = mean_keys or set()
    overall = compute_overall(subset, mean_keys=keys)
    cells: dict[str, BaselineCellSnapshot] = {}
    for cell in subset:
        cells[Baseline.cell_dict_key(cell.key)] = BaselineCellSnapshot(
            key=cell.key,
            passed=cell.passed,
            duration_ms=cell.duration_ms,
            metrics=dict(cell.metrics),
        )

    return Baseline(
        profile_id=profile_id,
        updated_at=updated_at or datetime.now(timezone.utc).isoformat(),
        source_report_path=source_report_path,
        fingerprint=report.fingerprint,
        overall=overall_to_baseline(overall),
        cells=cells,
    )


def write_baseline(
    baseline: Baseline,
    *,
    home: Path | None = None,
) -> Path:
    path = baseline_path(baseline.profile_id, home)
    save_json(path, baseline, home=home)
    return path


def update_baseline_from_report(
    report_path: Path,
    profile_id: str,
    *,
    home: Path | None = None,
    matrix_path: Path | None = None,
) -> Path:
    report = load_report(report_path)
    mean_keys: set[str] = set()
    if matrix_path is not None:
        matrix = load_matrix_config(matrix_path)
        mean_keys = metric_keys_from_gate(matrix.gate)
    baseline = report_to_baseline(
        report,
        profile_id,
        source_report_path=str(report_path),
        mean_keys=mean_keys,
    )
    return write_baseline(baseline, home=home)

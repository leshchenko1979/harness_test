from __future__ import annotations

from collections.abc import Iterable

from gategrid.models.baseline import BaselineOverall
from gategrid.models.cell import CellResult
from gategrid.models.report import ReportOverall


def _metric_mean(cells: list[CellResult], key: str) -> float:
    if not cells:
        return 0.0
    total = 0.0
    for cell in cells:
        val = cell.metrics.get(key, 0)
        if isinstance(val, bool):
            total += float(val)
        elif isinstance(val, (int, float)):
            total += float(val)
    return total / len(cells)


def compute_overall(
    cells: list[CellResult],
    mean_keys: Iterable[str] = (),
) -> ReportOverall:
    n = len(cells)
    keys = list(mean_keys)
    if n == 0:
        return ReportOverall(
            pass_rate=0.0,
            duration_ms_mean=0.0,
            cell_count=0,
            metrics={k: 0.0 for k in keys},
        )
    passed = sum(1 for c in cells if c.passed)
    return ReportOverall(
        pass_rate=passed / n,
        duration_ms_mean=sum(c.duration_ms for c in cells) / n,
        cell_count=n,
        metrics={k: _metric_mean(cells, k) for k in keys},
    )


def overall_to_baseline(overall: ReportOverall) -> BaselineOverall:
    return BaselineOverall(
        pass_rate=overall.pass_rate,
        duration_ms_mean=overall.duration_ms_mean,
        cell_count=overall.cell_count,
        metrics=dict(overall.metrics),
    )

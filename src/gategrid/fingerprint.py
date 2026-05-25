from __future__ import annotations

from gategrid.models.baseline import Baseline
from gategrid.models.cell import CellKey, CellResult
from gategrid.models.report import ReportFingerprint


def build_fingerprint(
    matrix_name: str,
    cells: list[CellResult],
) -> ReportFingerprint:
    profile_ids = sorted({c.key.profile_id for c in cells})
    case_ids = sorted({c.key.case_id for c in cells})
    return ReportFingerprint(
        matrix_name=matrix_name,
        profile_ids=profile_ids,
        case_ids=case_ids,
    )


def fingerprint_matches(a: ReportFingerprint, b: ReportFingerprint) -> bool:
    return (
        a.matrix_name == b.matrix_name
        and a.profile_ids == b.profile_ids
        and a.case_ids == b.case_ids
    )


def intersection_keys(
    report_cells: list[CellResult],
    baseline_cell_keys: set[str],
) -> list[CellKey]:
    return [
        cell.key
        for cell in report_cells
        if Baseline.cell_dict_key(cell.key) in baseline_cell_keys
    ]

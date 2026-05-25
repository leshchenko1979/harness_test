from __future__ import annotations

from pydantic import BaseModel, Field

from gategrid.models.cell import CellKey
from gategrid.models.report import ReportFingerprint, ReportOverall
from gategrid.version import SCHEMA_VERSION


class BaselineCellSnapshot(BaseModel):
    key: CellKey
    passed: bool
    duration_ms: float = 0.0
    metrics: dict[str, float | int | str | bool] = Field(default_factory=dict)


class BaselineOverall(BaseModel):
    pass_rate: float
    duration_ms_mean: float = 0.0
    cell_count: int
    metrics: dict[str, float] = Field(default_factory=dict)


class Baseline(BaseModel):
    schema_version: int = SCHEMA_VERSION
    profile_id: str
    updated_at: str
    source_report_path: str | None = None
    fingerprint: ReportFingerprint
    overall: BaselineOverall
    cells: dict[str, BaselineCellSnapshot] = Field(default_factory=dict)

    @staticmethod
    def cell_dict_key(key: CellKey) -> str:
        return f"{key.case_id}\0{key.profile_id}\0{key.model_id}"

    def get_cell(self, key: CellKey) -> BaselineCellSnapshot | None:
        return self.cells.get(self.cell_dict_key(key))

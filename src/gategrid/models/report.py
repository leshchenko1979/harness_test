from __future__ import annotations

from pydantic import BaseModel, Field, computed_field

from gategrid.models.cell import CellKey, CellResult
from gategrid.version import SCHEMA_VERSION


class SamplingMeta(BaseModel):
    sampled: bool = False
    seed: int | None = None
    max_cells: int | None = None
    share: float | None = None
    always_include_tags: list[str] = Field(default_factory=list)
    planned_cells: int = 0
    executed_cells: int = 0
    skipped_cells: list[CellKey] = Field(default_factory=list)


class ReportFingerprint(BaseModel):
    matrix_name: str
    profile_ids: list[str]
    case_ids: list[str]


class ReportOverall(BaseModel):
    pass_rate: float
    duration_ms_mean: float = 0.0
    cell_count: int
    metrics: dict[str, float] = Field(default_factory=dict)


class MatrixReport(BaseModel):
    schema_version: int = SCHEMA_VERSION
    commit_sha: str = "local"
    timestamp: str
    matrix_path: str
    matrix_name: str
    fingerprint: ReportFingerprint
    sampling: SamplingMeta = Field(default_factory=SamplingMeta)
    run_max_retries: int = 0
    cells: list[CellResult] = Field(default_factory=list)
    overall: ReportOverall | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pass_rate(self) -> float:
        if self.overall is not None:
            return self.overall.pass_rate
        if not self.cells:
            return 0.0
        return sum(1 for c in self.cells if c.passed) / len(self.cells)

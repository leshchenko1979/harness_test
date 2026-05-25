from __future__ import annotations

from pydantic import BaseModel, Field

from gategrid.models.artifact import RunArtifact


class CellKey(BaseModel):
    """Stable identity for a matrix cell (cases × profiles × models)."""

    case_id: str
    profile_id: str
    model_id: str

    def as_tuple(self) -> tuple[str, str, str]:
        return (self.case_id, self.profile_id, self.model_id)

    def label(self) -> str:
        return f"{self.case_id}@{self.profile_id}/{self.model_id}"


class AttemptRecord(BaseModel):
    attempt_index: int
    passed: bool
    artifact: RunArtifact | None = None
    error: str | None = None
    duration_ms: float = 0.0


class CellResult(BaseModel):
    key: CellKey
    passed: bool
    tags: list[str] = Field(default_factory=list)
    attempts: list[AttemptRecord] = Field(default_factory=list)
    flaky_suspect: bool = False
    duration_ms: float = 0.0
    metrics: dict[str, float | int | str | bool] = Field(default_factory=dict)
    error: str | None = None

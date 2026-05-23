from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ProviderKind = Literal["openai", "anthropic", "google", "mock"]


class FileEditDeps(BaseModel):
    workspace: Path


class EditCase(BaseModel):
    name: str
    instruction: str
    file_name: str
    initial_content: str
    expected_output: str
    tags: list[str] = Field(default_factory=list)


class ExperimentVariant(BaseModel):
    tooling_name: str
    model_id: str
    system_prompt: str
    tools: tuple[Callable, ...]

    @property
    def variant_id(self) -> str:
        return f"{self.tooling_name}/{self.model_id}"


class ToolSet(BaseModel):
    name: str
    system_prompt: str
    tools: list[str]


class ModelPreset(BaseModel):
    provider: ProviderKind
    model_name: str
    api_key_env: str
    base_url: str | None = None

    @model_validator(mode="after")
    def validate_provider_fields(self) -> ModelPreset:
        if self.provider == "mock":
            return self
        if self.provider == "openai" and not self.base_url:
            raise ValueError("openai provider requires base_url")
        return self


class CaseSet(BaseModel):
    name: str
    cases: list[str]


class MatrixConfig(BaseModel):
    name: str | None = None
    tool_sets: list[str]
    models: list[str]
    cases: list[str] = Field(default_factory=list)
    case_sets: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_cases(self) -> MatrixConfig:
        if not self.cases and not self.case_sets:
            raise ValueError("matrix must include cases and/or case_sets")
        return self


class CaseResult(BaseModel):
    variant_id: str
    case_name: str
    passed: bool
    score: float
    tags: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float
    turns: int = 0
    tokens_spent: int = 0
    tool_failures: int = 0
    error: str | None = None
    final_output: str | None = None


class MatrixReport(BaseModel):
    commit_sha: str
    timestamp: str
    matrix_path: str
    matrix_name: str
    cases_path: str
    results: list[CaseResult] = Field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

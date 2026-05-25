from __future__ import annotations

from pydantic import BaseModel, Field


class CaseSetConfig(BaseModel):
    name: str | None = None
    cases: list[str] = Field(default_factory=list)

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProfileConfig(BaseModel):
    name: str | None = None
    runtime_adapter: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

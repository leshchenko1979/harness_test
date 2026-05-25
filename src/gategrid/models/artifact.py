from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


class Message(BaseModel):
    role: Role
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None


class RunArtifact(BaseModel):
    """Agent-shaped output from a runtime (Phase 2+ executor)."""

    messages: list[Message] = Field(default_factory=list)
    metrics: dict[str, float | int | str | bool] = Field(default_factory=dict)
    evaluators: dict[str, bool | dict[str, Any]] = Field(default_factory=dict)
    error: str | None = None

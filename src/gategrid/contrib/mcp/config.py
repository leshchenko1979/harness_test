"""MCP connection config parsed from profile.data.mcp."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

McpTransport = Literal["stdio", "streamable_http"]


class McpProfileConfig(BaseModel):
    """Shape of profile.data.mcp (integration-agnostic)."""

    transport: McpTransport
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    cwd: str | None = None
    timeout: float | None = None

    @model_validator(mode="after")
    def _transport_fields(self) -> McpProfileConfig:
        if self.transport == "stdio":
            if not self.command:
                raise ValueError("mcp.transport stdio requires command")
        elif self.transport == "streamable_http":
            if not self.url:
                raise ValueError("mcp.transport streamable_http requires url")
        return self

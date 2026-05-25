"""Test-only adapter that fails once then succeeds."""

from __future__ import annotations

import gategrid.integrations.pydantic_ai  # noqa: F401

from gategrid.models.artifact import Message, RunArtifact
from gategrid.runtime import RunContext


class FlakyAdapter:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, ctx: RunContext) -> RunArtifact:
        self.calls += 1
        if self.calls < 2:
            raise RuntimeError("transient")
        ctx.scratchpad["usage_metrics"] = {"turns": 1, "tokens_spent": 1}
        return RunArtifact(
            messages=[Message(role="assistant", content="ok")],
        )

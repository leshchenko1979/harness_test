"""Test-only adapter that fails once then succeeds."""

from __future__ import annotations

from gategrid.models.artifact import Message, RunArtifact
from gategrid.runtime import RunContext


class FlakyAdapter:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, ctx: RunContext) -> RunArtifact:
        self.calls += 1
        if self.calls < 2:
            raise RuntimeError("transient")
        return RunArtifact(
            messages=[Message(role="assistant", content="ok")],
            metrics={"turns": 1, "tokens_spent": 1},
        )

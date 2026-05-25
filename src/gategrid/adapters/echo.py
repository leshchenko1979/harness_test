"""Demo RuntimeAdapter — no LLM, returns a shaped RunArtifact."""

from __future__ import annotations

from gategrid.models.artifact import Message, RunArtifact
from gategrid.runtime import RunContext


class EchoAdapter:
    async def execute(self, ctx: RunContext) -> RunArtifact:
        text = f"case={ctx.case_id} profile={ctx.profile_id} model={ctx.model_id}"
        return RunArtifact(
            messages=[
                Message(role="user", content=f"run {ctx.case_id}"),
                Message(role="assistant", content=text),
            ],
            metrics={"turns": 1, "tokens_spent": 0},
        )

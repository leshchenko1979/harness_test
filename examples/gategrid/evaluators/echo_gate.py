"""Smoke gate — EchoAdapter embeds case id in assistant message."""

from gategrid import evaluator
from gategrid.models.artifact import RunArtifact
from gategrid.runtime import RunContext


def _last_assistant_text(artifact: RunArtifact) -> str:
    for msg in reversed(artifact.messages):
        if msg.role == "assistant" and msg.content:
            return msg.content
    return ""


@evaluator(tags=["gate"])
def echo_contains_case(ctx: RunContext, artifact: RunArtifact) -> bool:
    return ctx.case_id in _last_assistant_text(artifact)

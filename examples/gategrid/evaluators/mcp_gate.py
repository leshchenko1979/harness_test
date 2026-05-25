"""MCP gate — metrics shaped like run-artifact-mcp.example.json."""

from gategrid import evaluator
from gategrid.models.artifact import RunArtifact
from gategrid.models.evaluator_outcome import EvaluatorOutcome
from gategrid.runtime import RunContext

MCP_TAG = "mcp"


@evaluator(role="gate")
def mcp_tooling_ok(ctx: RunContext, artifact: RunArtifact) -> EvaluatorOutcome:
    if MCP_TAG not in ctx.case.tags:
        return EvaluatorOutcome(pass_=True)

    errors = int(artifact.metrics.get("mcp_errors", 0))
    if errors != 0:
        return EvaluatorOutcome(
            pass_=False,
            message="mcp_errors non-zero",
            detail=str(errors),
        )

    calls = int(artifact.metrics.get("tool_call_count", 0))
    if calls < 1:
        return EvaluatorOutcome(
            pass_=False,
            message="expected at least one MCP tool call",
        )

    return EvaluatorOutcome(pass_=True)

from gategrid import evaluator
from gategrid.models.artifact import RunArtifact
from gategrid.runtime import RunContext


@evaluator(role="metric")
def echo_turns(ctx: RunContext, artifact: RunArtifact) -> dict[str, int]:
    return {"turns": int(artifact.metrics.get("turns", 0))}

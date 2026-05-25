from __future__ import annotations

from pydantic import BaseModel, Field

from gategrid.models.artifact import RunArtifact


class EvaluatorOutcome(BaseModel):
    """Typed evaluator return; executor merges artifact patches and sets evaluators[id]."""

    pass_: bool | None = None
    message: str | None = None
    detail: str | None = None
    artifact: RunArtifact | None = None
    metrics: dict[str, float | int] | None = None


class ArtifactMergeError(ValueError):
    """Raised when deep-merging RunArtifact patches conflicts."""


def deep_merge_artifact(base: RunArtifact, patch: RunArtifact) -> RunArtifact:
    """Merge patch into base; messages replace only when base is empty."""
    if patch.messages:
        if base.messages:
            raise ArtifactMergeError("messages already set on artifact")
        base.messages = list(patch.messages)

    for key, value in patch.metrics.items():
        if key in base.metrics:
            raise ArtifactMergeError(f"duplicate metric key {key!r}")
        base.metrics[key] = value

    if patch.error is not None:
        if base.error is not None:
            raise ArtifactMergeError("artifact.error already set")
        base.error = patch.error

    if patch.evaluators:
        raise ArtifactMergeError(
            "evaluators must not appear in evaluator artifact patches"
        )

    if patch.tools_called:
        raise ArtifactMergeError(
            "tools_called must not appear in evaluator artifact patches"
        )

    return base

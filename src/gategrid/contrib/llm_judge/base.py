from __future__ import annotations

from abc import ABC, abstractmethod

from gategrid.models.artifact import RunArtifact
from gategrid.runtime import RunContext


class LlmJudgeBase(ABC):
    """Subclass and implement ``evaluate``; wire with ``@evaluator(tags=['gate'])``."""

    rubric: str = ""

    @abstractmethod
    def evaluate(self, ctx: RunContext, artifact: RunArtifact) -> bool:
        """Return whether the artifact satisfies the rubric."""

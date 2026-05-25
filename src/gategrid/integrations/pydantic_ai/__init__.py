"""pydantic-ai integration — requires ``pip install gategrid[pydantic-ai]``."""

from __future__ import annotations

from gategrid.evaluators import EvaluatorRecord, register_builtin_evaluator
from gategrid.integrations.pydantic_ai.model import model_from_config
from gategrid.integrations.pydantic_ai.runner import RunResult, run_agent, usage_to_metric_dict
from gategrid.integrations.pydantic_ai.tools import load_tool_functions
from gategrid.models.artifact import RunArtifact
from gategrid.runtime import RunContext


def _pydantic_run_usage(ctx: RunContext, artifact: RunArtifact) -> dict[str, int]:
    raw = ctx.scratchpad.get("usage_metrics")
    if isinstance(raw, dict):
        return {str(k): int(v) for k, v in raw.items() if isinstance(v, (int, float))}
    return {}


def _register_pydantic_builtin() -> None:
    register_builtin_evaluator(
        EvaluatorRecord(
            evaluator_id="pydantic_run_usage",
            tags=["metric", "metric_canonical"],
            fn=_pydantic_run_usage,
            definition="gategrid.integrations.pydantic_ai:pydantic_run_usage",
        )
    )


_register_pydantic_builtin()

__all__ = [
    "RunResult",
    "load_tool_functions",
    "model_from_config",
    "run_agent",
    "usage_to_metric_dict",
]

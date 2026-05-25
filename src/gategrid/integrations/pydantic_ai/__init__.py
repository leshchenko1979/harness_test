"""pydantic-ai integration — requires ``pip install gategrid[pydantic-ai]``."""

from __future__ import annotations

from gategrid.integrations.pydantic_ai.artifact_enrich import (
    enrich_artifact_from_run,
    mock_run_result,
)
from gategrid.integrations.pydantic_ai.model import model_from_config
from gategrid.integrations.pydantic_ai.runner import (
    RunResult,
    run_agent,
    usage_to_metric_dict,
)
from gategrid.integrations.pydantic_ai.tools import load_tool_functions

__all__ = [
    "RunResult",
    "enrich_artifact_from_run",
    "load_tool_functions",
    "mock_run_result",
    "model_from_config",
    "run_agent",
    "usage_to_metric_dict",
]

try:
    from gategrid.integrations.pydantic_ai.mcp_servers import mcp_toolset_from_data
except ImportError:
    pass
else:
    __all__.append("mcp_toolset_from_data")

"""RuntimeAdapter protocol, RunContext, and adapter loading."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from gategrid.cases import CaseRecord
from gategrid.models.artifact import RunArtifact
from gategrid.models.model_config import ModelConfig
from gategrid.models.profile_config import ProfileConfig


class RunContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    case_id: str
    profile_id: str
    model_id: str
    eval_root: Path
    profile: ProfileConfig
    model: ModelConfig
    case: CaseRecord
    scratchpad: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class RuntimeAdapter(Protocol):
    async def execute(self, ctx: RunContext) -> RunArtifact: ...


def load_runtime_adapter(spec: str) -> RuntimeAdapter:
    if ":" not in spec:
        raise ValueError(f"runtime_adapter must be module:Class, got {spec!r}")
    module_name, class_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    adapter = cls()
    if not isinstance(adapter, RuntimeAdapter):
        raise TypeError(f"{spec} is not a RuntimeAdapter")
    return adapter

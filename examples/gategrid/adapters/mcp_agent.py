"""Pydantic-ai + MCP toolset adapter (Path A example)."""

from __future__ import annotations

import sys

from gategrid.contrib.mcp.env import resolve_env_pass_through
from gategrid.contrib.mcp.profile import (
    env_pass_through_names,
    mcp_config_as_dict,
    mcp_from_profile,
)
from gategrid.models.artifact import Message, RunArtifact
from gategrid.runtime import RunContext


def _system_prompt(profile_data: dict) -> str:
    raw = profile_data.get("system_prompt")
    if raw is None:
        return "You are a helpful assistant with MCP tools."
    return str(raw)


def _mock_artifact(user_prompt: str) -> RunArtifact:
    return RunArtifact(
        messages=[
            Message(role="user", content=user_prompt),
            Message(role="tool", name="add", content="12"),
            Message(role="assistant", content="12"),
        ],
        metrics={
            "mcp_errors": 0,
            "tool_call_count": 1,
            "turns": 0,
            "tokens_spent": 0,
        },
    )


def _apply_mcp_metrics(artifact: RunArtifact) -> RunArtifact:
    artifact.metrics["mcp_errors"] = int(artifact.metrics.get("mcp_errors", 0))
    if "tool_call_count" not in artifact.metrics:
        total = sum(int(v) for v in artifact.tools_called.values())
        artifact.metrics["tool_call_count"] = total if total else 1
    return artifact


class PydanticAiMcpAdapter:
    async def execute(self, ctx: RunContext) -> RunArtifact:
        user_prompt = str(
            ctx.case.data.get("user_prompt", "Use add to compute 7 plus 5.")
        )

        if ctx.model.provider == "mock":
            return _mock_artifact(user_prompt)

        mcp_cfg = mcp_from_profile(ctx.profile)
        env_names = env_pass_through_names(ctx.profile)
        env = resolve_env_pass_through(env_names) if env_names else {}

        from gategrid.integrations.pydantic_ai import (
            enrich_artifact_from_run,
            mcp_toolset_from_data,
            model_from_config,
            run_agent,
        )

        mcp_data = mcp_config_as_dict(mcp_cfg)
        if mcp_data.get("transport") == "stdio" and mcp_data.get("command") == "python":
            mcp_data = {
                **mcp_data,
                "command": sys.executable,
            }

        toolset = mcp_toolset_from_data(
            mcp_data,
            env=env,
            cwd=ctx.eval_root.resolve(),
        )
        model = model_from_config(ctx.model, case=ctx.case)
        result = await run_agent(
            model,
            system_prompt=_system_prompt(ctx.profile.data),
            toolsets=(toolset,),
            user_prompt=user_prompt,
        )
        artifact = enrich_artifact_from_run(result, user_prompt=user_prompt)
        return _apply_mcp_metrics(artifact)

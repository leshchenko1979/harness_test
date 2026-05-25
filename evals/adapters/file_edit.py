"""Pydantic-ai file-edit adapter (dogfood glue)."""

from __future__ import annotations

import gategrid.integrations.pydantic_ai  # noqa: F401 — registers pydantic_run_usage

from gategrid.contrib.file_edit.cases import FileEditCase
from gategrid.contrib.file_edit.profile import (
    system_prompt_from_profile,
    tools_from_profile,
    validate_file_edit_profile,
)
from gategrid.contrib.file_edit.session import AgentRunOutcome, FileEditSession
from gategrid.contrib.file_edit.tools import load_file_edit_tools
from gategrid.models.artifact import RunArtifact
from gategrid.runtime import RunContext


class PydanticAiFileEditAdapter:
    async def execute(self, ctx: RunContext) -> RunArtifact:
        fe = FileEditCase.from_record(ctx.case)
        if ctx.model.provider == "mock":
            ctx.scratchpad["usage_metrics"] = {"turns": 0, "tokens_spent": 0}
            ctx.scratchpad["actual_content"] = fe.expected_output
            return FileEditSession.mock_artifact(fe)

        validate_file_edit_profile(ctx.profile)

        from gategrid.integrations.pydantic_ai import model_from_config, run_agent

        with FileEditSession(fe) as session:
            assert session.deps is not None
            assert session.workspace is not None
            model = model_from_config(ctx.model, case=ctx.case)
            tools = load_file_edit_tools(ctx.eval_root, tools_from_profile(ctx.profile))
            result = await run_agent(
                model,
                system_prompt=system_prompt_from_profile(ctx.profile),
                tools=tools,
                deps=session.deps,
                user_prompt=fe.instruction,
            )
            file_path = session.workspace / fe.file_name
            ctx.scratchpad["usage_metrics"] = result.usage_metrics
            ctx.scratchpad["actual_content"] = file_path.read_text(encoding="utf-8")
            return session.to_artifact(
                AgentRunOutcome(assistant_message=result.final_text)
            )

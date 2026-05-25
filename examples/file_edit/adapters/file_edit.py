"""Pydantic-ai file-edit adapter (dogfood glue)."""

from __future__ import annotations

from gategrid.contrib.file_edit.cases import FileEditCase
from gategrid.contrib.file_edit.profile import (
    system_prompt_from_profile,
    tools_from_profile,
    validate_file_edit_profile,
)
from gategrid.contrib.file_edit.session import FileEditSession
from gategrid.contrib.file_edit.tools import load_file_edit_tools
from gategrid.models.artifact import RunArtifact
from gategrid.runtime import RunContext


class PydanticAiFileEditAdapter:
    async def execute(self, ctx: RunContext) -> RunArtifact:
        fe = FileEditCase.from_record(ctx.case)
        from gategrid.integrations.pydantic_ai import (
            enrich_artifact_from_run,
            mock_run_result,
            model_from_config,
            run_agent,
        )

        if ctx.model.provider == "mock":
            result = mock_run_result(
                user_prompt=fe.instruction,
                final_text="mock",
            )
            ctx.scratchpad["actual_content"] = fe.expected_output
            return enrich_artifact_from_run(result, user_prompt=fe.instruction)

        validate_file_edit_profile(ctx.profile)

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
            ctx.scratchpad["actual_content"] = file_path.read_text(encoding="utf-8")
            return enrich_artifact_from_run(result, user_prompt=fe.instruction)

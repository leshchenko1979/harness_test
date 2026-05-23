from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
)
from pydantic_ai.models import Model, ModelRequestParameters, StreamedResponse
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RequestUsage

from agent_eval_matrix.models import EditCase


def demo_str_replace_args_for_case(case: EditCase) -> dict[str, str]:
    """Full-file replace: initial_content -> expected_output."""
    return {
        "file_path": case.file_name,
        "old_str": case.initial_content,
        "new_str": case.expected_output,
    }


@dataclass
class DemoModel(Model):
    """Deterministic model for demo runs; no API calls."""

    case: EditCase
    _model_name: str = field(default="demo", repr=False)

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        model_settings, model_request_parameters = self.prepare_request(
            model_settings,
            model_request_parameters,
        )
        if model_request_parameters.native_tools:
            from pydantic_ai.exceptions import UserError

            raise UserError("DemoModel does not support built-in tools")

        has_prior_response = any(isinstance(m, ModelResponse) for m in messages)
        if not has_prior_response:
            args = demo_str_replace_args_for_case(self.case)
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "str_replace",
                        args,
                        tool_call_id="pyd_ai_tool_call_id__str_replace",
                    )
                ],
                model_name=self._model_name,
            )

        return ModelResponse(
            parts=[TextPart("Done.")],
            model_name=self._model_name,
        )

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: Any | None = None,
    ):
        response = await self.request(
            messages, model_settings, model_request_parameters
        )
        yield _DemoStreamedResponse(
            model_request_parameters=model_request_parameters,
            _model_name=self._model_name,
            _response=response,
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def system(self) -> str:
        return "mock"

    @property
    def provider(self) -> None:
        return None


@dataclass
class _DemoStreamedResponse(StreamedResponse):
    _model_name: str
    _response: ModelResponse

    async def _get_event_iterator(self):
        if False:  # pragma: no cover
            yield  # type: ignore[misc]
        return

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def timestamp(self):
        from pydantic_ai import _utils

        return _utils.now_utc()

    def get(self) -> ModelResponse:
        return self._response

    def usage(self) -> RequestUsage:
        return RequestUsage()

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelRequest, TextPart, ToolCallPart
from pydantic_ai.models import ModelRequestParameters

from agent_eval_matrix.cases import load_cases_by_names
from agent_eval_matrix.demo_context import demo_case
from agent_eval_matrix.demo_model import DemoModel, demo_str_replace_args_for_case
from agent_eval_matrix.config import get_model

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "experiments" / "cases"


def test_demo_str_replace_args_from_hello_world_yaml() -> None:
    case = load_cases_by_names(CASES, ["hello_world"])[0]
    args = demo_str_replace_args_for_case(case)
    assert args["file_path"] == "hello.txt"
    assert args["old_str"] == case.initial_content
    assert args["new_str"] == case.expected_output


def test_demo_model_first_turn_str_replace() -> None:
    case = load_cases_by_names(CASES, ["hello_world"])[0]
    model = DemoModel(case=case)
    params = ModelRequestParameters(function_tools=[], allow_text_output=True)
    response = asyncio.run(model.request([], None, params))
    assert len(response.parts) == 1
    part = response.parts[0]
    assert isinstance(part, ToolCallPart)
    assert part.tool_name == "str_replace"
    assert part.args == demo_str_replace_args_for_case(case)


def test_demo_model_second_turn_text() -> None:
    case = load_cases_by_names(CASES, ["hello_world"])[0]
    model = DemoModel(case=case)
    params = ModelRequestParameters(function_tools=[], allow_text_output=True)
    first = asyncio.run(model.request([], None, params))
    messages = [
        first,
        ModelRequest.user_text_prompt("tool result"),
    ]
    response = asyncio.run(model.request(messages, None, params))
    assert len(response.parts) == 1
    assert isinstance(response.parts[0], TextPart)


def test_get_model_mock_requires_demo_case_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MOCK_API_KEY", raising=False)
    demo_case.set(None)
    with pytest.raises(ValueError, match="demo_case"):
        get_model("mock")

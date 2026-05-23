from __future__ import annotations

from pathlib import Path

import pytest

from agent_eval_matrix.cases import load_cases_by_names
from agent_eval_matrix.config import (
    exit_on_missing_api_keys,
    get_model,
    missing_api_keys,
    resolve_demo_mode,
)
from agent_eval_matrix.demo_context import demo_case
from agent_eval_matrix.demo_model import DemoModel

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "experiments" / "cases"


def test_get_model_mock_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOCK_API_KEY", raising=False)
    case = load_cases_by_names(CASES, ["hello_world"])[0]
    token = demo_case.set(case)
    try:
        model = get_model("mock")
        assert isinstance(model, DemoModel)
        assert model.case.name == "hello_world"
    finally:
        demo_case.reset(token)


def test_missing_api_keys_skips_mock() -> None:
    assert "mock" not in missing_api_keys(["mock"])
    missing = missing_api_keys(["minimax-m2.7"])
    assert "MINIMAX_API_KEY" in missing or missing == []


def test_exit_on_missing_api_keys_exits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        exit_on_missing_api_keys(["minimax-m2.7"], demo_mode=False)
    assert exc.value.code == 1


def test_exit_on_missing_api_keys_skips_demo_mode() -> None:
    exit_on_missing_api_keys(["minimax-m2.7"], demo_mode=True)


def test_resolve_demo_mode_matrix_name() -> None:
    assert resolve_demo_mode(
        cli_demo_flag=False, matrix_name="demo", model_ids=["mock"]
    )


def test_resolve_demo_mode_all_mock() -> None:
    assert resolve_demo_mode(
        cli_demo_flag=False, matrix_name="custom", model_ids=["mock"]
    )


def test_resolve_demo_mode_real_models() -> None:
    assert not resolve_demo_mode(
        cli_demo_flag=False,
        matrix_name="ci",
        model_ids=["minimax-m2.7"],
    )


def test_get_model_openai_preset(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic_ai.models.openai import OpenAIChatModel

    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    model = get_model("minimax-m2.7")
    assert isinstance(model, OpenAIChatModel)

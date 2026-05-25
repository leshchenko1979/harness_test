from __future__ import annotations

from pathlib import Path

import pytest

from gategrid.evaluators import discover_evaluators
from gategrid.models.model_config import ModelConfig

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_model_from_config_rejects_mock() -> None:
    pytest.importorskip("pydantic_ai")
    from gategrid.integrations.pydantic_ai import model_from_config

    cfg = ModelConfig(provider="mock", model_name="d", api_key_env="MOCK")
    with pytest.raises(ValueError, match="mock"):
        model_from_config(cfg)


def test_load_tool_functions_on_echo_tool(tmp_path: Path) -> None:
    pytest.importorskip("pydantic_ai")
    from gategrid.integrations.pydantic_ai import load_tool_functions

    eval_root = REPO_ROOT / "examples" / "gategrid"
    tools = load_tool_functions(eval_root, [])
    assert tools == ()

    root = tmp_path / "eval"
    (root / "tooling").mkdir(parents=True)
    tool = root / "tooling" / "noop.py"
    tool.write_text(
        "def noop() -> str:\n    return 'ok'\n",
        encoding="utf-8",
    )
    loaded = load_tool_functions(root, ["tooling/noop.py"])
    assert len(loaded) == 1
    assert loaded[0]() == "ok"


def test_resolve_eval_path_rejects_escape(tmp_path: Path) -> None:
    pytest.importorskip("pydantic_ai")
    from gategrid.integrations.pydantic_ai.tools import resolve_eval_path

    eval_root = tmp_path / "eval"
    eval_root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("def noop() -> str:\n    return 'x'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="outside eval_root"):
        resolve_eval_path(f"../outside.py", eval_root)


def test_discover_duplicate_builtin_evaluator_id_fails(tmp_path: Path) -> None:
    root = tmp_path / "eval"
    (root / "cases").mkdir(parents=True)
    (root / "cases" / "__init__.py").write_text("", encoding="utf-8")
    (root / "evaluators").mkdir(parents=True)
    (root / "evaluators" / "__init__.py").write_text("", encoding="utf-8")
    (root / "evaluators" / "dup.py").write_text(
        "from gategrid import evaluator\n"
        "from gategrid.models.artifact import RunArtifact\n"
        "from gategrid.runtime import RunContext\n\n"
        "@evaluator(id='file_content_match', role='gate')\n"
        "def file_content_match(ctx: RunContext, artifact: RunArtifact) -> bool:\n"
        "    return True\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate evaluator ids"):
        discover_evaluators(root)


def test_enrich_artifact_from_run_mock() -> None:
    pytest.importorskip("pydantic_ai")
    from gategrid.integrations.pydantic_ai import (
        enrich_artifact_from_run,
        mock_run_result,
    )

    result = mock_run_result(user_prompt="hello world", final_text="done")
    art = enrich_artifact_from_run(result, user_prompt="hello world")
    assert art.metrics["turns"] == 0
    assert art.metrics["tokens_spent"] == 0
    assert "tool_call_count" not in art.metrics
    assert art.tools_called == {}
    assert any(m.role == "user" for m in art.messages)
    assert art.messages[-1].role == "assistant"


def test_enrich_merges_tool_call_and_return() -> None:
    pytest.importorskip("pydantic_ai")
    from pydantic_ai.messages import (
        ModelRequest,
        ModelResponse,
        ToolCallPart,
        ToolReturnPart,
        UserPromptPart,
    )

    from gategrid.integrations.pydantic_ai import enrich_artifact_from_run
    from gategrid.integrations.pydantic_ai.runner import RunResult

    call_a = ToolCallPart(tool_name="read_file", args={})
    ret_a = ToolReturnPart(
        tool_name="read_file",
        content="file body",
        tool_call_id=call_a.tool_call_id,
    )
    call_b = ToolCallPart(tool_name="edit_file", args={})
    ret_b = ToolReturnPart(
        tool_name="edit_file",
        content="ok",
        tool_call_id=call_b.tool_call_id,
    )
    messages = [
        ModelRequest(parts=[UserPromptPart(content="edit the file")]),
        ModelResponse(parts=[call_a]),
        ModelRequest(parts=[ret_a]),
        ModelResponse(parts=[call_b]),
        ModelRequest(parts=[ret_b]),
    ]
    result = RunResult(
        usage_metrics={"turns": 2, "tokens_spent": 100},
        run_messages=messages,
        final_text="done",
    )
    art = enrich_artifact_from_run(result)
    tool_messages = [m for m in art.messages if m.role == "tool"]
    assert len(tool_messages) == 2
    assert tool_messages[0].name == "read_file"
    assert tool_messages[0].content == "file body"
    assert tool_messages[1].name == "edit_file"
    assert art.tools_called == {"read_file": 1, "edit_file": 1}
    assert "tool_call_count" not in art.metrics


def test_discover_evaluators_has_no_pydantic_run_usage(tmp_path: Path) -> None:
    root = tmp_path / "eval"
    (root / "cases").mkdir(parents=True)
    (root / "cases" / "__init__.py").write_text("", encoding="utf-8")
    registry = discover_evaluators(root)
    assert "pydantic_run_usage" not in registry
    assert "file_content_match" in registry


def test_contrib_file_edit_import_does_not_load_pydantic_ai() -> None:
    import sys

    before = set(sys.modules)
    import gategrid.contrib.file_edit  # noqa: F401

    added = set(sys.modules) - before
    assert not any(name.startswith("pydantic_ai") for name in added)

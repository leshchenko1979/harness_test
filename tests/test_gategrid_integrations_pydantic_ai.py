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
        "@evaluator(id='file_content_match', tags=['gate'])\n"
        "def file_content_match(ctx: RunContext, artifact: RunArtifact) -> bool:\n"
        "    return True\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate evaluator ids"):
        discover_evaluators(root)


def test_contrib_file_edit_import_does_not_load_pydantic_ai() -> None:
    import sys

    before = set(sys.modules)
    import gategrid.contrib.file_edit  # noqa: F401

    added = set(sys.modules) - before
    assert not any(name.startswith("pydantic_ai") for name in added)

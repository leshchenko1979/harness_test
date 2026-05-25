from __future__ import annotations

from pathlib import Path

import pytest

from gategrid.cases import discover_cases, resolve_case_ids
from gategrid.contrib.file_edit.profile import (
    system_prompt_from_profile,
    tools_from_profile,
    validate_file_edit_profile,
)
from gategrid.contrib.file_edit.tools import load_file_edit_tools
from gategrid.io import load_matrix_config, load_yaml_model
from gategrid.models.profile_config import ProfileConfig
from gategrid.validate import validate_matrix

REPO_ROOT = Path(__file__).resolve().parents[1]
EVALS_ROOT = REPO_ROOT / "evals"
FILE_EDIT_EXAMPLE = REPO_ROOT / "examples/file_edit"


def test_discover_cases_without_eval_cases_dir() -> None:
    assert not (EVALS_ROOT / "cases").is_dir()
    registry = discover_cases(EVALS_ROOT)
    assert "indent_collision" in registry
    assert len(registry) >= 10


def test_builtin_case_set_resolve_without_eval_yaml() -> None:
    matrix_path = EVALS_ROOT / "matrices" / "hashline-gate.yaml"
    if not matrix_path.is_file():
        pytest.skip("hashline-gate matrix not present")
    matrix = load_matrix_config(matrix_path)
    if "hashline_hypotheses" not in matrix.case_sets:
        pytest.skip("matrix does not use hashline_hypotheses case set")
    assert not (EVALS_ROOT / "case_sets" / "hashline_hypotheses.yaml").is_file()
    ids = resolve_case_ids(matrix, EVALS_ROOT)
    assert "indent_collision" in ids
    assert len(ids) == 10


def test_user_case_collides_with_builtin(tmp_path: Path) -> None:
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    (cases_dir / "__init__.py").write_text(
        "from gategrid import case\n\n@case(id='indent_collision')\n"
        "def indent_collision() -> None:\n    pass\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate case ids"):
        discover_cases(tmp_path)


def test_load_builtin_read_file_tool_name(tmp_path: Path) -> None:
    tools = load_file_edit_tools(tmp_path, ["builtin:read_file"])
    assert len(tools) == 1
    assert tools[0].name == "read_file"


def test_duplicate_exposed_tool_name_errors(tmp_path: Path) -> None:
    tooling = tmp_path / "tooling"
    tooling.mkdir()
    (tooling / "read_file.py").write_text(
        "def read_file() -> str:\n    return 'x'\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate exposed tool name"):
        load_file_edit_tools(
            tmp_path,
            ["builtin:read_file", "tooling/read_file.py"],
        )


def test_profile_data_round_trip() -> None:
    profile = load_yaml_model(
        EVALS_ROOT / "profiles" / "baseline.yaml",
        ProfileConfig,
    )
    assert profile.data.get("system_prompt")
    assert "builtin:read_file" in tools_from_profile(profile)
    validate_file_edit_profile(profile)
    assert "read_file" in system_prompt_from_profile(profile)


def test_examples_file_edit_smoke_validate() -> None:
    matrix = FILE_EDIT_EXAMPLE / "matrices" / "smoke-mock.yaml"
    result = validate_matrix(matrix, root=FILE_EDIT_EXAMPLE)
    assert result.ok, result.errors

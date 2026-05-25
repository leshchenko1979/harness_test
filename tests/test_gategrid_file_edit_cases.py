from __future__ import annotations

from pathlib import Path

import pytest

from gategrid.cases import discover_cases
from gategrid.contrib.file_edit.cases import (
    FileEditCase,
    register_case_from_yaml,
    validate_file_edit_case,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EVALS_ROOT = REPO_ROOT / "evals"


def test_register_case_from_yaml_fixture(tmp_path: Path) -> None:
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    yaml_path = cases_dir / "sample.yaml"
    yaml_path.write_text(
        "name: sample\n"
        "instruction: do it\n"
        "file_name: a.py\n"
        "initial_content: 'x'\n"
        "expected_output: 'y'\n",
        encoding="utf-8",
    )
    (cases_dir / "__init__.py").write_text(
        "from pathlib import Path\n"
        "from gategrid.contrib.file_edit.cases import register_case_from_yaml\n"
        "register_case_from_yaml(Path(__file__).parent / 'sample.yaml')\n",
        encoding="utf-8",
    )
    registry = discover_cases(tmp_path)
    assert "sample" in registry
    record = registry["sample"]
    validate_file_edit_case(record)
    fe = FileEditCase.from_record(record)
    assert fe.expected_output == "y"


def test_hashline_hypotheses_registers_ten_cases() -> None:
    """Builtin batteries supply hashline cases without eval_root/cases/."""
    registry = discover_cases(EVALS_ROOT)
    expected = {
        "whitespace_trap",
        "whitespace_trap_yaml",
        "ambiguous_replace",
        "indent_collision",
        "whitespace_trap_py_large",
        "whitespace_trap_yaml_large",
        "ambiguous_replace_large",
        "add_docstring_large",
        "rename_symbol_large",
        "indent_collision_large",
    }
    assert expected <= set(registry.keys())

"""Register shipped file-edit batteries (cases, case sets, baseline tools)."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from gategrid.cases import register_builtin_case_set
from gategrid.contrib.file_edit.cases import register_builtin_case_from_yaml
from gategrid.contrib.file_edit.tools import register_builtin_tool
from gategrid.contrib.file_edit.bundled.tooling import baseline

_HASHLINE_CASE_IDS = [
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
]


def _register_bundled_cases() -> None:
    cases_pkg = resources.files("gategrid.contrib.file_edit.bundled") / "cases"
    for case_id in _HASHLINE_CASE_IDS:
        yaml_path = Path(str(cases_pkg / f"{case_id}.yaml"))
        register_builtin_case_from_yaml(yaml_path)

    case_set_path = (
        resources.files("gategrid.contrib.file_edit.bundled")
        / "case_sets"
        / "hashline_hypotheses.yaml"
    )
    import yaml

    data = yaml.safe_load(case_set_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("hashline_hypotheses case set must be a YAML mapping")
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError("hashline_hypotheses case set missing cases list")
    register_builtin_case_set("hashline_hypotheses", [str(c) for c in cases])


def _register_bundled_tools() -> None:
    register_builtin_tool("ls", baseline.ls)
    register_builtin_tool("glob", baseline.glob_tool)
    register_builtin_tool("grep", baseline.grep)
    register_builtin_tool("read_file", baseline.read_file)
    register_builtin_tool("str_replace", baseline.str_replace)


_register_bundled_cases()
_register_bundled_tools()

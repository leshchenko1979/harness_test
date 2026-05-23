from pathlib import Path

import pytest

from agent_eval_matrix.load_tooling import load_tool_function, resolve_experiments_path
from agent_eval_matrix.matrices import build_tool_set_registry, load_tool_set

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments"


def test_resolve_experiments_path() -> None:
    path = resolve_experiments_path("tooling/reference/ls.py", EXPERIMENTS)
    assert path.name == "ls.py"
    assert path.is_file()


def test_load_reference_ls_tool() -> None:
    path = resolve_experiments_path("tooling/reference/ls.py", EXPERIMENTS)
    fn = load_tool_function(path)
    assert callable(fn)
    assert fn.__name__ == "ls"


def test_load_opencrabs_original_tool_set() -> None:
    path = EXPERIMENTS / "tool_sets" / "opencrabs_original.yaml"
    tool_set = load_tool_set(path, EXPERIMENTS)
    assert tool_set.name == "opencrabs_original"
    assert "hashline_edit" in tool_set.system_prompt
    assert len(tool_set.tools) == 6


def test_tool_set_registry_names() -> None:
    registry = build_tool_set_registry(EXPERIMENTS)
    assert set(registry) == {
        "baseline",
        "demo",
        "minimal",
        "strict/verbose",
        "opencrabs_original",
        "opencrabs_h1_docs",
        "opencrabs_h2_fuzzy",
        "opencrabs_h3_collision",
    }


def test_load_opencrabs_h3_read_file() -> None:
    path = resolve_experiments_path("tooling/opencrabs_h3/read_file.py", EXPERIMENTS)
    fn = load_tool_function(path)
    assert fn.__name__ == "read_file"

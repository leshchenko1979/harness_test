from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from gategrid.cases import discover_cases, resolve_case_ids
from gategrid.cli import main
from gategrid.executor import MatrixRunError, run_matrix_sync
from gategrid.io import load_matrix_config
from gategrid.models.profile_config import ProfileConfig
from gategrid.runtime import load_runtime_adapter
from gategrid.validate import validate_matrix

REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_MATRIX = REPO_ROOT / "examples/gategrid/matrices/smoke.yaml"
GATEGRID_ROOT = REPO_ROOT / "examples/gategrid"


def _write_eval_tree(
    root: Path,
    *,
    case_modules: dict[str, str] | None = None,
    profile_adapter: str = "gategrid.adapters.echo:EchoAdapter",
) -> Path:
    (root / "matrices").mkdir(parents=True)
    (root / "profiles").mkdir()
    (root / "models").mkdir()
    (root / "case_sets").mkdir()
    (root / "cases").mkdir()
    (root / "cases" / "__init__.py").write_text("", encoding="utf-8")
    body = case_modules or {
        "mod.py": (
            "from gategrid import case\n\n@case\ndef alpha() -> None:\n    pass\n"
        ),
    }
    for name, content in body.items():
        if name.endswith(".py"):
            (root / "cases" / name).write_text(content, encoding="utf-8")
        elif "/" in name or name.endswith("/"):
            continue
        else:
            (root / "cases" / name).mkdir(parents=True, exist_ok=True)
    (root / "profiles" / "p.yaml").write_text(
        f"runtime_adapter: {profile_adapter}\n",
        encoding="utf-8",
    )
    (root / "models" / "m.yaml").write_text(
        "provider: mock\nmodel_name: demo\napi_key_env: MOCK\n",
        encoding="utf-8",
    )
    (root / "case_sets" / "set.yaml").write_text(
        "cases:\n  - alpha\n", encoding="utf-8"
    )
    matrix = root / "matrices" / "m.yaml"
    matrix.write_text(
        "profiles:\n  - p\nmodels:\n  - m\ncase_sets:\n  - set\n",
        encoding="utf-8",
    )
    return matrix


def test_resolve_case_ids_dedupe(tmp_path: Path) -> None:
    root = tmp_path / "eval"
    matrix_path = _write_eval_tree(root)
    matrix = load_matrix_config(matrix_path)
    matrix = matrix.model_copy(update={"cases": ["alpha"]})
    ids = resolve_case_ids(matrix, root)
    assert ids == ["alpha"]


def test_discover_default_case_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GATEGRID_CASE_ID_QUALIFY", raising=False)
    root = tmp_path / "eval"
    _write_eval_tree(root)
    registry = discover_cases(root)
    assert "alpha" in registry
    assert registry["alpha"].tags == []


def test_discover_duplicate_id_fails(tmp_path: Path) -> None:
    root = tmp_path / "eval"
    _write_eval_tree(
        root,
        case_modules={
            "a.py": "from gategrid import case\n@case\ndef x() -> None: pass\n",
            "b.py": "from gategrid import case\n@case\ndef x() -> None: pass\n",
        },
    )
    with pytest.raises(ValueError, match="duplicate case ids"):
        discover_cases(root)


def test_case_id_qualify_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GATEGRID_CASE_ID_QUALIFY", "module")
    root = tmp_path / "eval"
    (root / "matrices").mkdir(parents=True)
    (root / "profiles").mkdir()
    (root / "models").mkdir()
    (root / "case_sets").mkdir()
    (root / "cases" / "sub").mkdir(parents=True)
    (root / "cases" / "__init__.py").write_text("", encoding="utf-8")
    (root / "cases" / "sub" / "__init__.py").write_text("", encoding="utf-8")
    (root / "cases" / "sub" / "hello_world.py").write_text(
        "from gategrid import case\n@case\ndef hello_world() -> None: pass\n",
        encoding="utf-8",
    )
    registry = discover_cases(root)
    assert "sub.hello_world" in registry


def test_retries_flaky_suspect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import yaml

    monkeypatch.setenv("GATEGRID_HOME", str(tmp_path / ".gategrid"))
    root = tmp_path / "eval"
    matrix_path = _write_eval_tree(
        root,
        case_modules={
            "mod.py": (
                "from gategrid import case\n\n@case\ndef alpha() -> None:\n    pass\n"
            ),
        },
    )
    (root / "evaluators").mkdir(parents=True, exist_ok=True)
    (root / "evaluators" / "__init__.py").write_text("", encoding="utf-8")
    (root / "evaluators" / "gate.py").write_text(
        "from gategrid import evaluator\n"
        "from gategrid.models.artifact import RunArtifact\n"
        "from gategrid.runtime import RunContext\n\n"
        "@evaluator(role='gate')\n"
        "def wants_ok(ctx: RunContext, artifact: RunArtifact) -> bool:\n"
        "    return any(m.role == 'assistant' and m.content == 'ok' for m in artifact.messages)\n",
        encoding="utf-8",
    )
    (root / "profiles" / "p.yaml").write_text(
        "runtime_adapter: gategrid.fixtures.flaky_adapter:FlakyAdapter\n",
        encoding="utf-8",
    )
    (root / "matrices" / "m.yaml").write_text(
        yaml.dump(
            {
                "profiles": ["p"],
                "models": ["m"],
                "case_sets": ["set"],
                "run": {"max_retries": 1},
            }
        ),
        encoding="utf-8",
    )

    outcome = run_matrix_sync(matrix_path, eval_root=root)
    cell = outcome.report.cells[0]
    assert cell.passed
    assert cell.flaky_suspect
    assert len(cell.attempts) == 2


def test_gate_evaluator_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GATEGRID_HOME", str(tmp_path / ".gategrid"))
    root = tmp_path / "eval"
    matrix_path = _write_eval_tree(root)
    (root / "evaluators").mkdir(parents=True, exist_ok=True)
    (root / "evaluators" / "__init__.py").write_text("", encoding="utf-8")
    (root / "evaluators" / "gate.py").write_text(
        "from gategrid import evaluator\n"
        "from gategrid.models.artifact import RunArtifact\n"
        "from gategrid.runtime import RunContext\n\n"
        "@evaluator(role='gate')\n"
        "def always_fail(ctx: RunContext, artifact: RunArtifact) -> bool:\n"
        "    return False\n",
        encoding="utf-8",
    )
    outcome = run_matrix_sync(matrix_path, eval_root=root)
    assert not outcome.report.cells[0].passed


def test_smoke_run_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / ".gategrid"
    monkeypatch.setenv("GATEGRID_HOME", str(home))
    assert main(["run", "--matrix", str(SMOKE_MATRIX)]) == 0
    reports = list((home / "reports").glob("*_matrix.json"))
    assert len(reports) == 1


def test_validate_unknown_case_without_cases_package(tmp_path: Path) -> None:
    root = tmp_path / "eval"
    (root / "matrices").mkdir(parents=True)
    (root / "profiles").mkdir()
    (root / "models").mkdir()
    (root / "case_sets").mkdir()
    (root / "profiles" / "p.yaml").write_text(
        "runtime_adapter: gategrid.adapters.echo:EchoAdapter\n",
        encoding="utf-8",
    )
    (root / "models" / "m.yaml").write_text(
        "provider: mock\nmodel_name: d\napi_key_env: MOCK\n",
        encoding="utf-8",
    )
    (root / "case_sets" / "set.yaml").write_text(
        "cases:\n  - alpha\n", encoding="utf-8"
    )
    matrix = root / "matrices" / "m.yaml"
    matrix.write_text(
        "profiles:\n  - p\nmodels:\n  - m\ncase_sets:\n  - set\n",
        encoding="utf-8",
    )
    outcome = validate_matrix(matrix, root=root)
    assert not outcome.ok
    assert any("unknown case id" in e for e in outcome.errors)


def test_validate_unknown_case_id(tmp_path: Path) -> None:
    root = tmp_path / "eval"
    matrix_path = _write_eval_tree(root)
    (root / "case_sets" / "set.yaml").write_text(
        "cases:\n  - missing_id\n", encoding="utf-8"
    )
    outcome = validate_matrix(matrix_path, root=root)
    assert not outcome.ok
    assert any("unknown case id" in e for e in outcome.errors)


def test_cli_run_exit_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GATEGRID_HOME", str(tmp_path / ".gategrid"))
    assert main(["run", "--matrix", str(SMOKE_MATRIX)]) == 0
    bad = tmp_path / "missing.yaml"
    assert main(["run", "--matrix", str(bad)]) == 2


def test_missing_runtime_adapter() -> None:
    from gategrid.executor import _load_profile_adapters

    profiles = {"p": ProfileConfig()}
    with pytest.raises(MatrixRunError, match="runtime_adapter"):
        _load_profile_adapters(profiles)


def test_load_echo_adapter() -> None:
    adapter = load_runtime_adapter("gategrid.adapters.echo:EchoAdapter")
    assert adapter is not None

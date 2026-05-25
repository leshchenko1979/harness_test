from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from gategrid.cli import main
from gategrid.io import save_json
from gategrid.paths import baselines_dir, gategrid_home, reports_dir, traces_dir
from gategrid.validate import resolve_eval_root, validate_matrix
from gategrid.version import __version__
from gategrid.fixtures.sample import sample_report

REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_MATRIX = REPO_ROOT / "examples/gategrid/matrices/smoke.yaml"


def test_version_constant() -> None:
    assert __version__ == "0.0.0"


def test_cli_version() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0


def test_validate_smoke_example() -> None:
    assert main(["validate", "--matrix", str(SMOKE_MATRIX)]) == 0


def test_validate_reports_missing_refs(tmp_path: Path) -> None:
    root = tmp_path / "eval"
    (root / "matrices").mkdir(parents=True)
    (root / "profiles").mkdir()
    (root / "models").mkdir()
    matrix = root / "matrices" / "bad.yaml"
    (root / "case_sets").mkdir()
    matrix.write_text(
        "profiles:\n  - missing\nmodels:\n  - also-missing\ncase_sets:\n  - demo\n",
        encoding="utf-8",
    )
    (root / "case_sets" / "demo.yaml").write_text("cases: []\n", encoding="utf-8")
    outcome = validate_matrix(matrix)
    assert not outcome.ok
    assert any("profile" in e for e in outcome.errors)
    assert any("model" in e for e in outcome.errors)


def test_resolve_eval_root_from_matrices_dir() -> None:
    matrix = REPO_ROOT / "examples/gategrid/matrices/smoke.yaml"
    assert resolve_eval_root(matrix, None) == REPO_ROOT / "examples/gategrid"


def test_ensure_home_on_save_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / ".gategrid"
    monkeypatch.setenv("GATEGRID_HOME", str(home))
    report = sample_report()
    save_json(home / "reports" / "out.json", report)
    assert baselines_dir(home).is_dir()
    assert reports_dir(home).is_dir()
    assert traces_dir(home).is_dir()


def test_core_install_import_guard(tmp_path: Path) -> None:
    """Core install must not bundle legacy harness deps (pydantic_evals, pydantic_ai)."""
    import os

    script = """
import importlib
import gategrid  # noqa: F401

for name in ("pydantic_evals", "pydantic_ai"):
    importlib.import_module(name)
"""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )
    assert proc.returncode != 0
    combined = (proc.stdout + proc.stderr).lower()
    assert "modulenotfounderror" in combined or "no module named" in combined


def test_profile_and_model_config_load() -> None:
    from gategrid.io import load_yaml_model
    from gategrid.models.model_config import ModelConfig
    from gategrid.models.profile_config import ProfileConfig

    profile = load_yaml_model(
        REPO_ROOT / "examples/gategrid/profiles/demo.yaml",
        ProfileConfig,
    )
    assert profile.runtime_adapter
    assert profile.data == {}
    model = load_yaml_model(
        REPO_ROOT / "examples/gategrid/models/mock.yaml",
        ModelConfig,
    )
    assert model.provider == "mock"

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from gategrid.contrib.file_edit.evaluators import (
    file_content_match_impl as file_content_match,
)
from gategrid.evaluators import discover_evaluators, run_evaluators_on_artifact
from gategrid.models.evaluator_outcome import EvaluatorOutcome
from gategrid.executor import run_matrix_sync
from gategrid.models.artifact import RunArtifact
from gategrid.runtime import RunContext
from gategrid.cases import CaseRecord
from gategrid.models.profile_config import ProfileConfig
from gategrid.models.model_config import ModelConfig

REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_MATRIX = REPO_ROOT / "examples/gategrid/matrices/smoke.yaml"


def test_run_artifact_error_fails_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gategrid.adapters.echo import EchoAdapter
    from gategrid.executor import attempt_passed

    monkeypatch.setenv("GATEGRID_HOME", str(tmp_path / ".gategrid"))
    ctx = RunContext(
        case_id="x",
        profile_id="p",
        model_id="m",
        eval_root=tmp_path,
        profile=ProfileConfig(),
        model=ModelConfig(provider="mock", model_name="d", api_key_env="MOCK"),
        case=CaseRecord(case_id="x"),
    )
    art = RunArtifact(error="agent stopped")
    ok, _, _, err = attempt_passed(artifact=art, ctx=ctx, gates=[], metrics=[])
    assert not ok
    assert err == "agent stopped"
    assert EchoAdapter is not None  # keep import used


def test_metric_evaluator_does_not_fail_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GATEGRID_HOME", str(tmp_path / ".gategrid"))
    root = tmp_path / "eval"
    root.mkdir(parents=True, exist_ok=True)
    (root / "matrices").mkdir(parents=True)
    (root / "profiles").mkdir(parents=True)
    (root / "models").mkdir(parents=True)
    (root / "case_sets").mkdir(parents=True)
    (root / "cases").mkdir(parents=True)
    (root / "cases" / "__init__.py").write_text("", encoding="utf-8")
    (root / "cases" / "mod.py").write_text(
        "from gategrid import case\n@case\ndef alpha() -> None: pass\n",
        encoding="utf-8",
    )
    (root / "evaluators").mkdir(parents=True)
    (root / "evaluators" / "__init__.py").write_text("", encoding="utf-8")
    (root / "evaluators" / "m.py").write_text(
        "from gategrid import evaluator\n"
        "from gategrid.models.artifact import RunArtifact\n"
        "from gategrid.runtime import RunContext\n\n"
        "@evaluator(role='metric')\n"
        "def noisy(ctx: RunContext, artifact: RunArtifact) -> dict:\n"
        "    return {'x': 1}\n",
        encoding="utf-8",
    )
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
    outcome = run_matrix_sync(matrix, eval_root=root)
    assert outcome.report.cells[0].passed


def test_file_content_match_skip_and_match() -> None:
    ctx = RunContext(
        case_id="c",
        profile_id="p",
        model_id="m",
        eval_root=Path("."),
        profile=ProfileConfig(),
        model=ModelConfig(provider="mock", model_name="d", api_key_env="MOCK"),
        case=CaseRecord(case_id="c"),
    )
    art = RunArtifact()
    assert file_content_match(ctx, art).pass_ is True

    ctx_tag = RunContext(
        case_id="c",
        profile_id="p",
        model_id="m",
        eval_root=Path("."),
        profile=ProfileConfig(),
        model=ModelConfig(provider="mock", model_name="d", api_key_env="MOCK"),
        case=CaseRecord(
            case_id="c",
            tags=["file_edit"],
            data={
                "instruction": "fix",
                "file_name": "a.py",
                "initial_content": "x",
                "expected_output": "hello",
            },
        ),
    )
    ctx_tag.scratchpad["actual_content"] = "wrong"
    result = file_content_match(ctx_tag, art)
    assert result.pass_ is False
    assert result.detail

    ctx_tag.scratchpad["actual_content"] = "hello"
    result_ok = file_content_match(ctx_tag, art)
    assert result_ok.pass_ is True

    gates = [discover_evaluators(Path("."))["file_content_match"]]
    _, art_out, _ = run_evaluators_on_artifact(
        ctx=ctx_tag, artifact=art, gates=gates, metrics=[]
    )
    assert art_out.evaluators["file_content_match"] is True


def test_discover_builtin_evaluator_without_user_evaluators_dir(
    tmp_path: Path,
) -> None:
    root = tmp_path / "eval"
    (root / "cases").mkdir(parents=True)
    (root / "cases" / "__init__.py").write_text("", encoding="utf-8")
    registry = discover_evaluators(root)
    assert "file_content_match" in registry


def test_discover_contrib_evaluator_in_example_tree() -> None:
    root = REPO_ROOT / "examples/gategrid"
    registry = discover_evaluators(root)
    assert "echo_contains_case" in registry
    assert "file_content_match" in registry


def test_smoke_with_evaluators(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GATEGRID_HOME", str(tmp_path / ".gategrid"))
    outcome = run_matrix_sync(SMOKE_MATRIX, eval_root=REPO_ROOT / "examples/gategrid")
    assert all(c.passed for c in outcome.report.cells)
    cell = outcome.report.cells[0]
    assert cell.metrics.get("turns") == 1
    art = cell.attempts[0].artifact
    assert art is not None
    assert art.metrics.get("turns") == 1
    assert cell.metrics.get("turns") == 1
    assert art.evaluators.get("echo_contains_case") is True


def test_cli_smoke_validate_and_run_subprocess(tmp_path: Path) -> None:
    """Fresh process — no in-process pre-import masking evaluator registration."""
    import os

    home = tmp_path / ".gategrid"
    env = os.environ.copy()
    env["GATEGRID_HOME"] = str(home)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    for args in (
        ["validate", "--matrix", str(SMOKE_MATRIX)],
        ["run", "--matrix", str(SMOKE_MATRIX)],
    ):
        proc = subprocess.run(
            [sys.executable, "-m", "gategrid.cli", *args],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "run: OK" in proc.stdout

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

from gategrid.cli_output import (
    format_cell_failure,
    format_gate_check,
    format_matrix_run_errors,
    format_run_summary,
    print_run_outcome,
)
from gategrid.executor import RunOutcome
from gategrid.fixtures.sample import sample_report
from gategrid.models.artifact import RunArtifact
from gategrid.models.cell import AttemptRecord, CellKey, CellResult


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_format_run_summary_ok() -> None:
    assert format_run_summary(passed=3, total=3) == "run: OK (3/3 passed)"


def test_format_run_summary_failed() -> None:
    assert "FAILED" in format_run_summary(passed=1, total=2)


def test_format_gate_check_humanizes_metric_names() -> None:
    from gategrid.gate import GateCheckResult

    line = format_gate_check(
        GateCheckResult(
            name="limits.overall.turns_max",
            passed=False,
            message="turns mean 12.00 (max 10.00)",
        )
    )
    assert "FAIL" in line
    assert "turns" in line


def test_format_cell_failure_includes_diff() -> None:
    cell = CellResult(
        key=CellKey(case_id="c", profile_id="p", model_id="m"),
        passed=False,
        error="file_content_match",
        attempts=[
            AttemptRecord(
                attempt_index=0,
                passed=False,
                artifact=RunArtifact(
                    evaluators={
                        "file_content_match": {
                            "pass": False,
                            "message": "output differs",
                            "detail": "--- a\n+++ b",
                        }
                    }
                ),
            )
        ],
    )
    text = format_cell_failure(
        cell,
        matrix_path=Path("evals/matrices/x.yaml"),
        eval_root=Path("evals"),
    )
    assert "output differs" in text
    assert "--- a" in text
    assert "rerun:" in text
    assert "#" not in text.split("rerun:")[1].split("\n")[0]


def test_format_matrix_run_errors() -> None:
    text = format_matrix_run_errors(["bad matrix", "missing profile"])
    assert "error: bad matrix" in text
    assert "error: missing profile" in text
    assert text.endswith("run: aborted")


def test_print_run_outcome_case_filter_warning(tmp_path: Path) -> None:
    report = sample_report()
    stderr = io.StringIO()
    print_run_outcome(
        RunOutcome(report=report, report_path=tmp_path / "r.json"),
        matrix_path=Path("m.yaml"),
        eval_root=None,
        case_filter="search_alice",
        stream_stderr=stderr,
    )
    assert "--case filter active" in stderr.getvalue()


def test_print_run_outcome_streams(tmp_path: Path) -> None:
    report = sample_report(pass_second=False)
    out_path = tmp_path / "r.json"
    stdout = io.StringIO()
    stderr = io.StringIO()
    print_run_outcome(
        RunOutcome(report=report, report_path=out_path),
        matrix_path=Path("m.yaml"),
        eval_root=None,
        stream_stdout=stdout,
        stream_stderr=stderr,
    )
    assert "run: FAILED" in stdout.getvalue()
    assert "FAIL" in stderr.getvalue()


def test_cli_run_subprocess_smoke_line(tmp_path: Path) -> None:
    import os

    home = tmp_path / ".gategrid"
    env = os.environ.copy()
    env["GATEGRID_HOME"] = str(home)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    matrix = REPO_ROOT / "examples/gategrid/matrices/smoke.yaml"
    proc = subprocess.run(
        [sys.executable, "-m", "gategrid.cli", "run", "--matrix", str(matrix)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "run: OK" in proc.stdout


def test_cli_run_case_filter_warning_subprocess(tmp_path: Path) -> None:
    import os

    home = tmp_path / ".gategrid"
    env = os.environ.copy()
    env["GATEGRID_HOME"] = str(home)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["GATEGRID_EVAL_ROOT"] = str(REPO_ROOT / "evals")
    matrix = REPO_ROOT / "evals/matrices/hashline-smoke.yaml"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "gategrid.cli",
            "run",
            "--matrix",
            str(matrix),
            "--root",
            str(REPO_ROOT / "evals"),
            "--case",
            "indent_collision",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "warning: --case filter active" in proc.stderr

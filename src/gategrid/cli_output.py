"""CLI formatting helpers — all user-facing run/validate output."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from gategrid.cases import print_case_id_convention
from gategrid.evaluators import print_evaluator_id_convention
from gategrid.gate import GateCheckResult
from gategrid.models.cell import CellKey, CellResult
from gategrid.models.report import MatrixReport


def format_relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        home = os.environ.get("GATEGRID_HOME", ".gategrid")
        try:
            return str(path.relative_to(Path(home).resolve()))
        except ValueError:
            return str(path)


def emit_id_conventions(*, verbose: bool, stream: Any = None) -> None:
    if not verbose:
        return
    out = stream or sys.stderr
    print_case_id_convention(stream=out)
    print_evaluator_id_convention(stream=out)


def format_run_summary(*, passed: int, total: int) -> str:
    if passed == total:
        return f"run: OK ({passed}/{total} passed)"
    return f"run: FAILED ({passed}/{total} passed)"


def format_gate_failure_message(
    evaluators: dict[str, bool | dict[str, Any]],
    *,
    gate_id: str | None = None,
) -> str:
    if gate_id and gate_id in evaluators:
        outcome = evaluators[gate_id]
        if isinstance(outcome, dict):
            msg = outcome.get("message")
            if isinstance(msg, str) and msg:
                return msg
    for outcome in evaluators.values():
        if isinstance(outcome, dict) and not outcome.get("pass", True):
            msg = outcome.get("message")
            if isinstance(msg, str) and msg:
                return msg
    return "gate evaluator failed"


def format_cell_failure(
    cell: CellResult,
    *,
    matrix_path: Path,
    eval_root: Path | None,
    report_path: Path | None = None,
) -> str:
    gate_id = cell.error
    message = "cell failed"
    detail: str | None = None
    if cell.attempts:
        last = cell.attempts[-1]
        art = last.artifact
        if art is not None:
            message = format_gate_failure_message(art.evaluators, gate_id=gate_id)
            if gate_id and isinstance(art.evaluators.get(gate_id), dict):
                raw_detail = art.evaluators[gate_id].get("detail")
                if isinstance(raw_detail, str):
                    detail = raw_detail

    lines = [f"FAIL {cell.key.label()}: {message}"]
    if report_path is not None:
        lines.append(f"  report: {format_relative_path(report_path)}")
    rerun = f"gategrid run --matrix {matrix_path}"
    if eval_root is not None:
        rerun += f" --root {eval_root}"
    lines.append(f"  rerun: {rerun}")
    if detail:
        lines.append("  diff:")
        for line in detail.splitlines():
            lines.append(f"    {line}")
    return "\n".join(lines)


def format_gate_check(check: GateCheckResult) -> str:
    status = "PASS" if check.passed else "FAIL"
    name = check.name
    if ".pass_rate" in name or name.endswith("pass_rate_min"):
        label = "pass rate"
    elif "_max_delta" in name:
        label = name.replace("_max_delta", " max delta")
    elif "_min_delta" in name:
        label = name.replace("_min_delta", " min delta")
    elif "_max" in name:
        label = name.replace("_max", " max")
    elif "_min" in name:
        label = name.replace("_min", " min")
    else:
        label = name
    return f"{status}  {label}: {check.message}"


def format_matrix_run_errors(errors: list[str]) -> str:
    lines = [f"error: {e}" for e in errors]
    lines.append("run: aborted")
    return "\n".join(lines)


def print_run_outcome(
    outcome: object,
    *,
    matrix_path: Path,
    eval_root: Path | None,
    case_filter: str | None = None,
    verbose: bool = False,
    stream_stdout: Any = None,
    stream_stderr: Any = None,
) -> None:
    from gategrid.executor import RunOutcome

    if not isinstance(outcome, RunOutcome):
        raise TypeError("outcome must be RunOutcome")

    stdout = stream_stdout or sys.stdout
    stderr = stream_stderr or sys.stderr
    report = outcome.report
    passed = sum(1 for c in report.cells if c.passed)
    total = len(report.cells)

    print(format_run_summary(passed=passed, total=total), file=stdout)
    print(f"report: {format_relative_path(outcome.report_path)}", file=stdout)

    if case_filter:
        print(
            "warning: --case filter active; gate fingerprint may not match full matrix",
            file=stderr,
        )

    emit_id_conventions(verbose=verbose, stream=stderr)

    failed = [c for c in report.cells if not c.passed]
    for cell in failed:
        print(
            format_cell_failure(
                cell,
                matrix_path=matrix_path,
                eval_root=eval_root,
                report_path=outcome.report_path,
            ),
            file=stderr,
        )

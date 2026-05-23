from __future__ import annotations

import asyncio
from pathlib import Path

from agent_eval_matrix.matrices import resolve_matrix
from agent_eval_matrix.task import evaluate_case

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments"
CASES = EXPERIMENTS / "cases"


def test_evaluate_case_demo_matrix() -> None:
    resolved = resolve_matrix(
        EXPERIMENTS / "matrices" / "demo.yaml", EXPERIMENTS, CASES
    )
    variant = resolved.variants[0]
    case = resolved.cases[0]
    result = asyncio.run(evaluate_case(case, variant))
    assert result.passed
    assert result.case_name == "hello_world"
    assert result.error is None

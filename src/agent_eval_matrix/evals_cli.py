from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from agent_eval_matrix.cases import load_cases
from agent_eval_matrix.config import exit_on_missing_api_keys
from agent_eval_matrix.observability import get_commit_sha, setup_observability
from agent_eval_matrix.report import (
    new_matrix_report,
    print_summary,
    write_aggregate_report,
)
from agent_eval_matrix.matrices import (
    build_model_registry,
    build_tool_set_registry,
    variant_from_tool_set,
)
from agent_eval_matrix.task import evaluate_case

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = ROOT / "experiments"
DEFAULT_CASES = EXPERIMENTS / "cases"


async def run_single_case(
    case_name: str,
    cases_path: Path,
    tool_set_name: str | None,
    model_id: str,
    trace: bool,
) -> int:
    setup_observability()
    load_dotenv(ROOT / ".env")

    cases = load_cases(cases_path)
    case = next((c for c in cases if c.name == case_name), None)
    if case is None:
        raise SystemExit(f"Case not found: {case_name!r}")

    registry = build_tool_set_registry(EXPERIMENTS)
    name = tool_set_name or "baseline"
    tool_set = registry.get(name)
    if tool_set is None:
        raise SystemExit(f"Unknown tool set: {name!r}")

    model_registry = build_model_registry(EXPERIMENTS)
    if model_id not in model_registry:
        raise SystemExit(f"Unknown model preset: {model_id!r}")

    demo_mode = model_registry[model_id].provider == "mock"
    exit_on_missing_api_keys([model_id], demo_mode=demo_mode)

    variant = variant_from_tool_set(tool_set, model_id, EXPERIMENTS)

    run_id = "smoke" if trace else None
    result = await evaluate_case(case, variant, run_id=run_id)

    report = new_matrix_report(
        commit_sha=get_commit_sha(),
        matrix_path="single",
        matrix_name="single",
        cases_path=str(cases_path),
    )
    report.results.append(result)
    write_aggregate_report(report)
    print_summary(report)
    return 0 if result.passed else 1


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run a single eval case")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run one case")
    run_parser.add_argument("--case", required=True, help="Case name")
    run_parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    run_parser.add_argument(
        "--tool-set",
        type=str,
        default=None,
        help="Tool set name (e.g. baseline, demo)",
    )
    run_parser.add_argument(
        "--model",
        default="minimax-m2.7",
        help="Model preset id (use mock for no API key with --tool-set demo)",
    )
    run_parser.add_argument("--trace", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "run":
        code = asyncio.run(
            run_single_case(
                case_name=args.case,
                cases_path=args.cases,
                tool_set_name=args.tool_set,
                model_id=args.model,
                trace=args.trace,
            )
        )
        raise SystemExit(code)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import asyncio
import logging
import uuid
from pathlib import Path

from dotenv import load_dotenv

from agent_eval_matrix.config import exit_on_missing_api_keys, resolve_demo_mode
from agent_eval_matrix.models import ExperimentVariant
from agent_eval_matrix.observability import get_commit_sha, setup_observability
from agent_eval_matrix.report import (
    new_matrix_report,
    print_summary,
    write_aggregate_report,
)
from agent_eval_matrix.matrices import resolve_matrix
from agent_eval_matrix.task import evaluate_case

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = ROOT / "experiments"
DEMO_MATRIX = EXPERIMENTS / "matrices" / "demo.yaml"
DEFAULT_MATRIX = DEMO_MATRIX
DEFAULT_CASES = EXPERIMENTS / "cases"


def filter_variants(
    variants: list[ExperimentVariant], variant_filter: str | None
) -> list[ExperimentVariant]:
    if not variant_filter:
        return variants
    return [v for v in variants if v.variant_id == variant_filter]


async def run_matrix(
    matrix_path: Path,
    cases_path: Path,
    variant_filter: str | None = None,
    trace: bool = False,
    *,
    demo_mode: bool = False,
) -> int:
    setup_observability()
    load_dotenv(ROOT / ".env")

    matrix_path = matrix_path.resolve()
    resolved = resolve_matrix(matrix_path, EXPERIMENTS, cases_path.resolve())
    variants = filter_variants(resolved.variants, variant_filter)
    if not variants:
        raise ValueError(f"No variants matched filter: {variant_filter!r}")

    model_ids = list({v.model_id for v in variants})
    demo_mode = resolve_demo_mode(
        cli_demo_flag=demo_mode,
        matrix_name=resolved.matrix_name,
        model_ids=model_ids,
    )
    exit_on_missing_api_keys(model_ids, demo_mode=demo_mode)

    if demo_mode:
        logger.info("Demo mode: mocked model, no API calls")

    run_id = str(uuid.uuid4())[:8] if trace else None
    report = new_matrix_report(
        commit_sha=get_commit_sha(),
        matrix_path=resolved.matrix_path,
        matrix_name=resolved.matrix_name,
        cases_path=str(cases_path),
    )

    logger.info(
        "Running matrix %s: %d variants x %d cases",
        resolved.matrix_name,
        len(variants),
        len(resolved.cases),
    )

    for variant in variants:
        for case in resolved.cases:
            logger.info("Evaluating %s / %s", variant.variant_id, case.name)
            result = await evaluate_case(case, variant, run_id=run_id)
            report.results.append(result)

    write_aggregate_report(report)
    print_summary(report)

    failed = sum(1 for r in report.results if not r.passed)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run file-editing eval matrix")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run evaluation matrix")
    run_parser.add_argument(
        "--matrix",
        type=Path,
        default=None,
        help="Path to matrix YAML (default: experiments/matrices/demo.yaml)",
    )
    run_parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES,
        help="Path to cases directory",
    )
    run_parser.add_argument(
        "--variant",
        type=str,
        default=None,
        help="Run single variant id, e.g. baseline/minimax-m2.7",
    )
    run_parser.add_argument(
        "--trace",
        action="store_true",
        help="Write JSONL trace events under reports/traces/",
    )
    run_parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo matrix with mocked model (no API key required)",
    )

    args = parser.parse_args(argv)
    if args.command == "run":
        if args.demo:
            matrix_path = DEMO_MATRIX
            demo_mode = True
        elif args.matrix is None:
            matrix_path = DEFAULT_MATRIX
            demo_mode = True
        else:
            matrix_path = args.matrix
            demo_mode = False
        code = asyncio.run(
            run_matrix(
                matrix_path=matrix_path,
                cases_path=args.cases,
                variant_filter=args.variant,
                trace=args.trace,
                demo_mode=demo_mode,
            )
        )
        raise SystemExit(code)


if __name__ == "__main__":
    main()

from __future__ import annotations

import tempfile
from pathlib import Path

from pydantic_ai.usage import RunUsage
from pydantic_evals import Case, Dataset

from agent_eval_matrix.agent import build_agent
from agent_eval_matrix.demo_context import demo_case
from agent_eval_matrix.evaluators import (
    EfficiencyEvaluator,
    FileContentMatch,
    ToolUsageEvaluator,
)
from agent_eval_matrix.models import (
    CaseResult,
    EditCase,
    ExperimentVariant,
    FileEditDeps,
)
from agent_eval_matrix.observability import append_trace_event, span_context
from agent_eval_matrix.run_metrics import tokens_spent, tool_failures, turns


async def run_agent_on_case(
    case: EditCase,
    variant: ExperimentVariant,
    run_id: str | None = None,
) -> tuple[str, RunUsage]:
    """Run agent in isolated temp workspace; return final content and RunUsage."""
    token = demo_case.set(case)
    try:
        agent = build_agent(variant)
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            file_path = workspace / case.file_name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(case.initial_content, encoding="utf-8")

            deps = FileEditDeps(workspace=workspace)
            span_name = f"eval/{variant.variant_id}/{case.name}"
            with span_context(
                span_name,
                variant_id=variant.variant_id,
                case_name=case.name,
            ):
                if run_id:
                    append_trace_event(
                        run_id,
                        {
                            "event": "agent_start",
                            "variant": variant.variant_id,
                            "case": case.name,
                        },
                    )
                result = await agent.run(case.instruction, deps=deps)
                usage = result.usage
                if run_id:
                    append_trace_event(
                        run_id,
                        {
                            "event": "agent_done",
                            "variant": variant.variant_id,
                            "case": case.name,
                        },
                    )

            return file_path.read_text(encoding="utf-8"), usage
    finally:
        demo_case.reset(token)


def build_dataset(cases: list[EditCase]) -> Dataset:
    eval_cases = [
        Case(
            name=c.name,
            inputs=c,
            expected_output=c.expected_output,
            metadata={"tags": c.tags},
        )
        for c in cases
    ]
    return Dataset(
        name="file_editing_evals",
        cases=eval_cases,
        evaluators=[
            FileContentMatch(),
            ToolUsageEvaluator(),
            EfficiencyEvaluator(),
        ],
    )


async def evaluate_case(
    case: EditCase,
    variant: ExperimentVariant,
    run_id: str | None = None,
) -> CaseResult:
    error: str | None = None
    final_output: str | None = None
    passed = False
    score = 0.0
    metrics: dict = {}
    attributes: dict = {}
    usage = RunUsage()
    duration_ms = 0.0

    try:
        dataset = build_dataset([case])

        async def task(inputs: EditCase) -> str:
            nonlocal usage
            content, usage = await run_agent_on_case(inputs, variant, run_id=run_id)
            return content

        report = await dataset.evaluate(task, progress=False)
        if report.failures:
            error = report.failures[0].error_message
        elif report.cases:
            row = report.cases[0]
            final_output = str(row.output) if row.output is not None else None
            metrics = dict(row.metrics or {})
            attributes = dict(row.attributes or {})
            scores = row.scores or {}
            if "FileContentMatch" in scores:
                score = float(scores["FileContentMatch"].value)
            elif scores:
                score = float(next(iter(scores.values())).value)
            passed = score >= 1.0
            duration_ms = row.task_duration * 1000
    except Exception as exc:
        error = str(exc)

    return CaseResult(
        variant_id=variant.variant_id,
        case_name=case.name,
        passed=passed,
        score=score,
        tags=list(case.tags),
        metrics=metrics,
        attributes=attributes,
        duration_ms=duration_ms,
        turns=turns(usage),
        tokens_spent=tokens_spent(usage),
        tool_failures=tool_failures(metrics),
        error=error,
        final_output=final_output,
    )

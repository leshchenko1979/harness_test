"""Example reports for tests and schemas/v1/examples."""

from __future__ import annotations

from gategrid.aggregates import compute_overall
from gategrid.fingerprint import build_fingerprint
from gategrid.models.artifact import Message, RunArtifact
from gategrid.models.cell import AttemptRecord, CellKey, CellResult
from gategrid.models.report import MatrixReport, SamplingMeta


def mcp_shaped_artifact() -> RunArtifact:
    return RunArtifact(
        messages=[
            Message(role="user", content="Search my contacts for Alice"),
            Message(role="assistant", content="Found 1 contact matching Alice."),
        ],
        metrics={"mcp_errors": 0},
        tools_called={"search_contacts": 1},
    )


def sample_report(*, pass_second: bool = True) -> MatrixReport:
    cells = [
        CellResult(
            key=CellKey(
                case_id="search_alice",
                profile_id="telegram-mcp-stdio",
                model_id="gpt-4o-mini",
            ),
            passed=True,
            tags=["smoke", "mcp"],
            attempts=[
                AttemptRecord(
                    attempt_index=0,
                    passed=True,
                    artifact=mcp_shaped_artifact(),
                    duration_ms=1200.0,
                )
            ],
            duration_ms=1200.0,
            metrics={
                "expected_tool": "search_contacts",
                "turns": 2,
                "tokens_spent": 800,
            },
        ),
        CellResult(
            key=CellKey(
                case_id="read_saved",
                profile_id="telegram-mcp-stdio",
                model_id="gpt-4o-mini",
            ),
            passed=pass_second,
            tags=["smoke"],
            attempts=[
                AttemptRecord(
                    attempt_index=0,
                    passed=pass_second,
                    artifact=RunArtifact(
                        messages=[Message(role="user", content="Read saved messages")],
                        metrics={"mcp_errors": 0},
                        tools_called={"read_saved": 1},
                    ),
                    duration_ms=900.0,
                )
            ],
            duration_ms=900.0,
            metrics={"turns": 1, "tokens_spent": 400},
        ),
    ]
    overall = compute_overall(cells, mean_keys=["turns", "tokens_spent"])
    return MatrixReport(
        timestamp="2026-05-24T12:00:00+00:00",
        matrix_path="evals/matrices/telegram-mcp-gate.yaml",
        matrix_name="telegram-mcp-gate",
        fingerprint=build_fingerprint("telegram-mcp-gate", cells),
        sampling=SamplingMeta(
            sampled=True,
            seed=0,
            max_cells=30,
            share=0.25,
            planned_cells=4,
            executed_cells=2,
        ),
        run_max_retries=1,
        cells=cells,
        overall=overall,
    )

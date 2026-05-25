"""Phase 4 — MCP path (config helpers, mock matrix, gate no-ops)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from gategrid.cases import CaseRecord
from gategrid.cli import main
from gategrid.contrib.mcp.config import McpProfileConfig
from gategrid.contrib.mcp.profile import mcp_from_profile
from gategrid.evaluators import discover_evaluators
from gategrid.executor import run_matrix_sync
from gategrid.io import load_yaml_model
from gategrid.models.artifact import RunArtifact
from gategrid.models.model_config import ModelConfig
from gategrid.models.profile_config import ProfileConfig
from gategrid.runtime import RunContext

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = REPO_ROOT / "examples/gategrid"
SMOKE_MATRIX = EXAMPLES_ROOT / "matrices/smoke.yaml"
MCP_MOCK_MATRIX = EXAMPLES_ROOT / "matrices/mcp-gate-mock.yaml"


def _run_context(
    *,
    case_id: str,
    profile_id: str,
    tags: list[str],
) -> RunContext:
    return RunContext(
        case_id=case_id,
        profile_id=profile_id,
        model_id="mock",
        eval_root=EXAMPLES_ROOT,
        profile=ProfileConfig(name=profile_id, data={}),
        model=load_yaml_model(EXAMPLES_ROOT / "models/mock.yaml", ModelConfig),
        case=CaseRecord(case_id=case_id, tags=tags),
        scratchpad={},
    )


def test_mcp_from_profile_stdio() -> None:
    profile = ProfileConfig(
        name="mcp-candidate",
        runtime_adapter="adapters.mcp_agent:PydanticAiMcpAdapter",
        data={
            "mcp": {
                "transport": "stdio",
                "command": "python",
                "args": ["server/calc_server.py"],
            }
        },
    )
    cfg = mcp_from_profile(profile)
    assert cfg.transport == "stdio"
    assert cfg.command == "python"


def test_mcp_from_profile_missing_raises() -> None:
    profile = ProfileConfig(name="x", data={})
    with pytest.raises(ValueError, match="data.mcp"):
        mcp_from_profile(profile)


def test_mcp_profile_config_streamable_http() -> None:
    cfg = McpProfileConfig.model_validate(
        {"transport": "streamable_http", "url": "http://localhost:8000/mcp"}
    )
    assert cfg.url == "http://localhost:8000/mcp"


def test_mcp_gate_noop_without_tag() -> None:
    registry = discover_evaluators(EXAMPLES_ROOT)
    ctx = _run_context(case_id="hello_world", profile_id="mcp-candidate", tags=[])
    outcome = registry["mcp_tooling_ok"].fn(
        ctx, RunArtifact(metrics={"mcp_errors": 99})
    )
    assert outcome.pass_ is True


def test_echo_gate_noop_non_demo_profile() -> None:
    registry = discover_evaluators(EXAMPLES_ROOT)
    ctx = _run_context(case_id="mcp_add", profile_id="mcp-candidate", tags=["mcp"])
    assert registry["echo_contains_case"].fn(ctx, RunArtifact(messages=[])) is True


def test_validate_mcp_gate_mock() -> None:
    assert (
        main(
            [
                "validate",
                "--matrix",
                str(MCP_MOCK_MATRIX),
                "--root",
                str(EXAMPLES_ROOT),
            ]
        )
        == 0
    )


def test_run_mcp_gate_mock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GATEGRID_HOME", str(tmp_path / ".gategrid"))
    outcome = run_matrix_sync(MCP_MOCK_MATRIX, eval_root=EXAMPLES_ROOT)
    assert len(outcome.report.cells) == 1
    cell = outcome.report.cells[0]
    assert cell.passed
    assert cell.key.case_id == "mcp_add"
    art = cell.attempts[0].artifact
    assert art is not None
    assert art.metrics.get("mcp_errors") == 0
    assert int(art.metrics.get("tool_call_count", 0)) >= 1
    assert art.evaluators.get("mcp_tooling_ok") is True


def test_smoke_still_passes_with_mcp_evaluators(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GATEGRID_HOME", str(tmp_path / ".gategrid"))
    outcome = run_matrix_sync(SMOKE_MATRIX, eval_root=EXAMPLES_ROOT)
    assert all(c.passed for c in outcome.report.cells)
    assert outcome.report.cells[0].key.profile_id == "demo"


def test_discover_mcp_evaluator_in_example_tree() -> None:
    registry = discover_evaluators(EXAMPLES_ROOT)
    assert "mcp_tooling_ok" in registry
    assert "echo_contains_case" in registry


def test_cli_mcp_mock_validate_subprocess(tmp_path: Path) -> None:
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["GATEGRID_HOME"] = str(tmp_path / ".gategrid")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "gategrid.cli",
            "validate",
            "--matrix",
            str(MCP_MOCK_MATRIX),
            "--root",
            str(EXAMPLES_ROOT),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr

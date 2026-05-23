from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_eval_matrix.config import resolve_base_url, resolve_model_name
from agent_eval_matrix.matrices import build_model_registry, resolve_matrix
from agent_eval_matrix.models import MatrixConfig, ModelPreset

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments"
CASES = EXPERIMENTS / "cases"


def test_build_model_registry_loads_minimax() -> None:
    registry = build_model_registry(EXPERIMENTS)
    preset = registry["minimax-m2.7"]
    assert preset.provider == "openai"
    assert preset.model_name == "MiniMax-M2.7"
    assert preset.base_url == "https://api.minimax.io/v1"
    assert preset.api_key_env == "MINIMAX_API_KEY"


def test_build_model_registry_loads_mock() -> None:
    registry = build_model_registry(EXPERIMENTS)
    preset = registry["mock"]
    assert preset.provider == "mock"
    assert preset.model_name == "demo"


def test_resolve_matrix_unknown_model(tmp_path: Path) -> None:
    matrix_path = tmp_path / "bad.yaml"
    matrix_path.write_text(
        "tool_sets:\n  - baseline\nmodels:\n  - nonexistent-model\ncase_sets:\n  - smoke\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unknown model preset"):
        resolve_matrix(matrix_path, EXPERIMENTS, CASES)


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    preset = ModelPreset(
        provider="openai",
        model_name="default-model",
        base_url="https://api.example.com/v1",
        api_key_env="MINIMAX_API_KEY",
    )
    monkeypatch.delenv("MINIMAX_MODEL", raising=False)
    monkeypatch.delenv("MINIMAX_BASE_URL", raising=False)
    assert resolve_model_name(preset) == "default-model"
    assert resolve_base_url(preset) == "https://api.example.com/v1"

    monkeypatch.setenv("MINIMAX_MODEL", "override-model")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://override.example.com/v1/")
    assert resolve_model_name(preset) == "override-model"
    assert resolve_base_url(preset) == "https://override.example.com/v1"


def test_resolve_matrix_demo() -> None:
    resolved = resolve_matrix(
        EXPERIMENTS / "matrices" / "demo.yaml", EXPERIMENTS, CASES
    )
    assert resolved.matrix_name == "demo"
    assert len(resolved.variants) == 1
    assert len(resolved.cases) == 1
    assert resolved.cases[0].name == "hello_world"
    assert resolved.variants[0].variant_id == "demo/mock"


def test_resolve_matrix_ci() -> None:
    resolved = resolve_matrix(EXPERIMENTS / "matrices" / "ci.yaml", EXPERIMENTS, CASES)
    assert resolved.matrix_name == "ci"
    assert len(resolved.variants) == 1
    assert resolved.variants[0].tooling_name == "baseline"
    assert len(resolved.cases) == 2
    assert resolved.variants[0].variant_id == "baseline/minimax-m2.7"
    assert len(resolved.variants[0].tools) == 5


def test_resolve_matrix_full() -> None:
    resolved = resolve_matrix(
        EXPERIMENTS / "matrices" / "full.yaml", EXPERIMENTS, CASES
    )
    assert resolved.matrix_name == "full"
    assert len(resolved.variants) == 4
    assert len(resolved.cases) == 5
    assert len(resolved.variants) * len(resolved.cases) == 20


def test_resolve_matrix_hashline_hypotheses() -> None:
    resolved = resolve_matrix(
        EXPERIMENTS / "matrices" / "hashline_hypotheses.yaml", EXPERIMENTS, CASES
    )
    assert resolved.matrix_name == "hashline_hypotheses"
    assert len(resolved.variants) == 5
    assert len(resolved.cases) == 10
    assert len(resolved.variants) * len(resolved.cases) == 50
    toolings = {v.tooling_name for v in resolved.variants}
    assert toolings == {
        "opencrabs_original",
        "opencrabs_h1_docs",
        "opencrabs_h3_collision",
        "opencrabs_h2_fuzzy",
        "baseline",
    }


def test_matrix_requires_cases() -> None:
    with pytest.raises(ValidationError):
        MatrixConfig.model_validate(
            {
                "tool_sets": ["baseline"],
                "models": ["minimax-m2.7"],
                "cases": [],
                "case_sets": [],
            }
        )

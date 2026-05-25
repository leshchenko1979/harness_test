from __future__ import annotations

import os

import pytest

from gategrid.models.env import (
    env_prefix,
    matrix_uses_only_mock_models,
    missing_api_keys,
    resolve_base_url,
    resolve_model_name,
)
from gategrid.models.model_config import ModelConfig


def test_env_prefix() -> None:
    assert env_prefix("MINIMAX_API_KEY") == "MINIMAX"


def test_resolve_model_name_override(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = ModelConfig(
        provider="openai",
        model_name="default",
        api_key_env="MINIMAX_API_KEY",
    )
    monkeypatch.setenv("MINIMAX_MODEL", "override")
    assert resolve_model_name(cfg) == "override"


def test_missing_api_keys_skips_mock() -> None:
    registry = {
        "mock": ModelConfig(provider="mock", model_name="d", api_key_env="MOCK"),
        "real": ModelConfig(
            provider="openai", model_name="m", api_key_env="MISSING_KEY"
        ),
    }
    missing = missing_api_keys(["mock", "real"], registry)
    assert missing == ["MISSING_KEY"]


def test_matrix_uses_only_mock_models() -> None:
    registry = {
        "mock": ModelConfig(provider="mock", model_name="d", api_key_env="MOCK"),
        "real": ModelConfig(provider="openai", model_name="m", api_key_env="K"),
    }
    assert matrix_uses_only_mock_models(["mock"], registry)
    assert not matrix_uses_only_mock_models(["mock", "real"], registry)


def test_resolve_base_url_env(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = ModelConfig(
        provider="openai",
        model_name="m",
        api_key_env="MINIMAX_API_KEY",
        base_url="https://example.com/v1",
    )
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://override.com/v1/")
    assert resolve_base_url(cfg) == "https://override.com/v1"

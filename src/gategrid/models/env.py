"""Model preset environment resolution (no pydantic-ai)."""

from __future__ import annotations

import os

from gategrid.models.model_config import ModelConfig


def env_prefix(api_key_env: str) -> str:
    if api_key_env.endswith("_API_KEY"):
        return api_key_env[: -len("_API_KEY")]
    return api_key_env.rsplit("_", 1)[0]


def resolve_model_name(config: ModelConfig) -> str:
    prefix = env_prefix(config.api_key_env)
    return os.getenv(f"{prefix}_MODEL", config.model_name)


def resolve_base_url(config: ModelConfig) -> str | None:
    prefix = env_prefix(config.api_key_env)
    override = os.getenv(f"{prefix}_BASE_URL")
    if override:
        return override.rstrip("/")
    if config.base_url:
        return config.base_url.rstrip("/")
    return None


def missing_api_keys(
    model_ids: list[str],
    registry: dict[str, ModelConfig],
) -> list[str]:
    """Return api_key_env names that are unset (skips mock provider)."""
    missing: list[str] = []
    seen: set[str] = set()
    for model_id in model_ids:
        config = registry.get(model_id)
        if config is None or config.provider == "mock":
            continue
        if config.api_key_env in seen:
            continue
        seen.add(config.api_key_env)
        if not os.environ.get(config.api_key_env):
            missing.append(config.api_key_env)
    return missing


def matrix_uses_only_mock_models(
    model_ids: list[str],
    registry: dict[str, ModelConfig],
) -> bool:
    if not model_ids:
        return False
    for model_id in model_ids:
        config = registry.get(model_id)
        if config is None or config.provider != "mock":
            return False
    return True

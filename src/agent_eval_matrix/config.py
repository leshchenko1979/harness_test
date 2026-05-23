from __future__ import annotations

import os
import sys
from pathlib import Path

from pydantic_ai.models import Model

from agent_eval_matrix.demo_context import demo_case
from agent_eval_matrix.demo_model import DemoModel
from agent_eval_matrix.models import ModelPreset

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = ROOT / "experiments"

_model_registry: dict[str, ModelPreset] | None = None


def _env_prefix(api_key_env: str) -> str:
    if api_key_env.endswith("_API_KEY"):
        return api_key_env[: -len("_API_KEY")]
    return api_key_env.rsplit("_", 1)[0]


def _get_model_registry() -> dict[str, ModelPreset]:
    global _model_registry
    if _model_registry is None:
        from agent_eval_matrix.matrices import build_model_registry

        _model_registry = build_model_registry(EXPERIMENTS)
    return _model_registry


def resolve_model_name(preset: ModelPreset) -> str:
    prefix = _env_prefix(preset.api_key_env)
    return os.getenv(f"{prefix}_MODEL", preset.model_name)


def resolve_base_url(preset: ModelPreset) -> str | None:
    prefix = _env_prefix(preset.api_key_env)
    override = os.getenv(f"{prefix}_BASE_URL")
    if override:
        return override.rstrip("/")
    if preset.base_url:
        return preset.base_url.rstrip("/")
    return None


def missing_api_keys(model_ids: list[str]) -> list[str]:
    """Return api_key_env names that are unset (skips mock provider)."""
    registry = _get_model_registry()
    missing: list[str] = []
    seen: set[str] = set()
    for model_id in model_ids:
        preset = registry.get(model_id)
        if preset is None or preset.provider == "mock":
            continue
        if preset.api_key_env in seen:
            continue
        seen.add(preset.api_key_env)
        if not os.environ.get(preset.api_key_env):
            missing.append(preset.api_key_env)
    return missing


def exit_on_missing_api_keys(model_ids: list[str], *, demo_mode: bool) -> None:
    if demo_mode:
        return
    missing = missing_api_keys(model_ids)
    if not missing:
        return
    vars_list = ", ".join(missing)
    print(
        f"Missing environment variables: {vars_list}\n"
        "  cp .env.example .env   # then set your provider key\n"
        "  Or run without API keys: "
        "uv run python -m agent_eval_matrix.matrix run --demo",
        file=sys.stderr,
    )
    raise SystemExit(1)


def get_model(model_id: str) -> Model:
    registry = _get_model_registry()
    preset = registry.get(model_id)
    if preset is None:
        raise ValueError(f"Unknown model_id {model_id!r}. Known: {sorted(registry)}")

    if preset.provider == "mock":
        case = demo_case.get()
        if case is None:
            raise ValueError(
                "mock model must run inside an eval case context "
                "(matrix/evals runner sets demo_case)"
            )
        return DemoModel(case=case)

    api_key = os.environ.get(preset.api_key_env)
    if not api_key:
        raise ValueError(
            f"Missing API key env var {preset.api_key_env!r} for model {model_id!r}. "
            "Copy .env.example to .env or run: "
            "uv run python -m agent_eval_matrix.matrix run --demo"
        )

    model_name = resolve_model_name(preset)

    if preset.provider == "openai":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        base_url = resolve_base_url(preset)
        if not base_url:
            raise ValueError(
                f"openai provider requires base_url for model {model_id!r}"
            )
        return OpenAIChatModel(
            model_name,
            provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        )

    if preset.provider == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        base_url = resolve_base_url(preset)
        provider_kwargs: dict[str, str] = {"api_key": api_key}
        if base_url:
            provider_kwargs["base_url"] = base_url
        return AnthropicModel(
            model_name,
            provider=AnthropicProvider(**provider_kwargs),
        )

    if preset.provider == "google":
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        base_url = resolve_base_url(preset)
        provider_kwargs = {"api_key": api_key}
        if base_url:
            provider_kwargs["base_url"] = base_url
        return GoogleModel(
            model_name,
            provider=GoogleProvider(**provider_kwargs),
        )

    raise ValueError(f"Unsupported provider {preset.provider!r} for model {model_id!r}")


def matrix_uses_only_mock_models(model_ids: list[str]) -> bool:
    registry = _get_model_registry()
    if not model_ids:
        return False
    for model_id in model_ids:
        preset = registry.get(model_id)
        if preset is None or preset.provider != "mock":
            return False
    return True


def resolve_demo_mode(
    *,
    cli_demo_flag: bool,
    matrix_name: str,
    model_ids: list[str],
) -> bool:
    if cli_demo_flag or matrix_name == "demo":
        return True
    return matrix_uses_only_mock_models(model_ids)

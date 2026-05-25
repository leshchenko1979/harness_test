"""Build pydantic-ai Model from ModelConfig."""

from __future__ import annotations

import os

from gategrid.cases import CaseRecord
from gategrid.models.env import resolve_base_url, resolve_model_name
from gategrid.models.model_config import ModelConfig


def _require_pydantic_ai() -> None:
    try:
        import pydantic_ai  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "pydantic-ai is not installed. Install with: pip install gategrid[pydantic-ai]"
        ) from exc


def model_from_config(
    config: ModelConfig,
    *,
    case: CaseRecord | None = None,
) -> object:
    """Return a pydantic-ai ``Model`` for supported providers (not ``mock``)."""
    _require_pydantic_ai()
    del case  # reserved for per-case model overrides

    if config.provider == "mock":
        raise ValueError(
            "provider 'mock' is handled by the RuntimeAdapter, not model_from_config"
        )

    api_key = os.environ.get(config.api_key_env)
    if not api_key:
        raise ValueError(
            f"Missing API key env var {config.api_key_env!r} for provider {config.provider!r}"
        )

    model_name = resolve_model_name(config)

    if config.provider == "openai":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        base_url = resolve_base_url(config)
        if not base_url:
            raise ValueError("openai provider requires base_url on ModelConfig or env")
        return OpenAIChatModel(
            model_name,
            provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        )

    if config.provider == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        base_url = resolve_base_url(config)
        provider_kwargs: dict[str, str] = {"api_key": api_key}
        if base_url:
            provider_kwargs["base_url"] = base_url
        return AnthropicModel(
            model_name,
            provider=AnthropicProvider(**provider_kwargs),
        )

    if config.provider == "google":
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        base_url = resolve_base_url(config)
        provider_kwargs: dict[str, str] = {"api_key": api_key}
        if base_url:
            provider_kwargs["base_url"] = base_url
        return GoogleModel(
            model_name,
            provider=GoogleProvider(**provider_kwargs),
        )

    raise ValueError(f"Unsupported provider {config.provider!r}")

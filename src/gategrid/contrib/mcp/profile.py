"""Parse profile.data.mcp into McpProfileConfig."""

from __future__ import annotations

from typing import Any

from gategrid.contrib.mcp.config import McpProfileConfig
from gategrid.models.profile_config import ProfileConfig


def mcp_from_profile(profile: ProfileConfig) -> McpProfileConfig:
    """Return validated MCP config from profile.data['mcp']."""
    raw = profile.data.get("mcp")
    if raw is None:
        raise ValueError(
            f"profile {profile.name!r}: data.mcp is required for MCP adapters"
        )
    if not isinstance(raw, dict):
        raise ValueError(f"profile {profile.name!r}: data.mcp must be a mapping")
    return McpProfileConfig.model_validate(raw)


def env_pass_through_names(profile: ProfileConfig) -> list[str]:
    """Env var names listed under profile.data.env_pass_through."""
    raw = profile.data.get("env_pass_through", [])
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(
            f"profile {profile.name!r}: data.env_pass_through must be a list"
        )
    return [str(x) for x in raw if x]


def mcp_config_as_dict(config: McpProfileConfig) -> dict[str, Any]:
    """Serialize for integrations that accept a mapping."""
    return config.model_dump(exclude_none=True)

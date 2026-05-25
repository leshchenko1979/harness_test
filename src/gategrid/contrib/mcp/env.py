"""Env pass-through helpers for MCP subprocess spawns."""

from __future__ import annotations

import os


def resolve_env_pass_through(names: list[str]) -> dict[str, str]:
    """Copy named env vars from the process environment (values never from YAML)."""
    out: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        if not name or not isinstance(name, str):
            continue
        value = os.environ.get(name)
        if value is None:
            missing.append(name)
        else:
            out[name] = value
    if missing:
        raise OSError(
            f"Missing environment variables for env_pass_through: {', '.join(missing)}"
        )
    return out

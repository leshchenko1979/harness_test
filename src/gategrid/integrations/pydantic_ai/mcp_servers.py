"""Build pydantic-ai MCP toolsets from profile.data.mcp mappings."""

from __future__ import annotations

import os
from typing import Any


def _require_pydantic_ai_mcp() -> tuple[Any, Any]:
    try:
        from pydantic_ai.mcp import MCPServerStdio, MCPServerStreamableHTTP
    except ImportError as exc:
        raise ImportError(
            "MCP toolsets require pip install 'gategrid[pydantic-ai,mcp]'"
        ) from exc
    return MCPServerStdio, MCPServerStreamableHTTP


def mcp_toolset_from_data(
    mcp: dict[str, Any],
    *,
    env: dict[str, str] | None = None,
    cwd: str | os.PathLike[str] | None = None,
) -> Any:
    """Return a pydantic-ai MCP server toolset from a data.mcp mapping."""
    transport = mcp.get("transport")
    if transport == "stdio":
        MCPServerStdio, _ = _require_pydantic_ai_mcp()
        command = mcp.get("command")
        if not command:
            raise ValueError("mcp.transport stdio requires command")
        args = list(mcp.get("args") or [])
        merged_env = {**os.environ, **(env or {})}
        kwargs: dict[str, Any] = {
            "command": command,
            "args": args,
            "env": merged_env,
        }
        if cwd is not None:
            kwargs["cwd"] = str(cwd)
        timeout = mcp.get("timeout")
        if timeout is not None:
            kwargs["timeout"] = float(timeout)
        return MCPServerStdio(**kwargs)
    if transport == "streamable_http":
        _, MCPServerStreamableHTTP = _require_pydantic_ai_mcp()
        url = mcp.get("url")
        if not url:
            raise ValueError("mcp.transport streamable_http requires url")
        kwargs = {"url": url}
        timeout = mcp.get("timeout")
        if timeout is not None:
            kwargs["timeout"] = float(timeout)
        return MCPServerStreamableHTTP(**kwargs)
    raise ValueError(
        f"unsupported mcp.transport {transport!r}; use stdio or streamable_http"
    )

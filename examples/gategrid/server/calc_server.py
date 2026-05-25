"""Minimal stdio MCP server for Gategrid MCP example (add tool)."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("gategrid-calc")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


if __name__ == "__main__":
    mcp.run()

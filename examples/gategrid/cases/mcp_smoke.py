"""MCP smoke cases — prompts live in case data."""

from gategrid import case


@case(
    tags=["mcp", "smoke"],
    data={
        "user_prompt": "Use the add tool to compute 7 plus 5. Reply with only the numeric result.",
    },
)
def mcp_add() -> None:
    """Registered for mcp-gate matrices."""

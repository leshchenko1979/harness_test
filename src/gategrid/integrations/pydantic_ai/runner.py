"""Run a pydantic-ai Agent and map usage to run metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic_ai.usage import RunUsage


@dataclass
class RunResult:
    usage_metrics: dict[str, int]
    final_text: str | None = None


def usage_to_metric_dict(usage: RunUsage) -> dict[str, int]:
    return {"turns": _turns(usage), "tokens_spent": _tokens_spent(usage)}


def _tokens_spent(usage: RunUsage) -> int:
    return int(
        usage.input_tokens
        + usage.output_tokens
        + usage.cache_read_tokens
        + usage.cache_write_tokens
        + usage.input_audio_tokens
        + usage.cache_audio_read_tokens
        + usage.output_audio_tokens
        + sum(v for v in usage.details.values() if isinstance(v, (int, float)))
    )


def _turns(usage: RunUsage) -> int:
    return int(usage.requests)


async def run_agent(
    model: object,
    *,
    system_prompt: str,
    tools: tuple[Any, ...],
    deps: object,
    user_prompt: str,
) -> RunResult:
    from pydantic_ai import Agent

    deps_type = type(deps)
    agent = Agent(
        model,
        system_prompt=system_prompt,
        deps_type=deps_type,
        tools=list(tools),
    )
    result = await agent.run(user_prompt, deps=deps)
    output = result.output
    final_text = (
        output
        if isinstance(output, str)
        else str(output)
        if output is not None
        else None
    )
    return RunResult(
        usage_metrics=usage_to_metric_dict(result.usage),
        final_text=final_text,
    )

"""Map pydantic-ai run results to RunArtifact (slim transcript + metrics)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gategrid.integrations.pydantic_ai.runner import RunResult, usage_to_metric_dict
from gategrid.models.artifact import Message, RunArtifact
from pydantic_ai.usage import RunUsage

_MAX_CONTENT = 500


@dataclass
class _PendingTool:
    tool_name: str


def _trunc(text: str, limit: int = _MAX_CONTENT) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _increment_tool_count(counts: dict[str, int], tool_name: str) -> None:
    counts[tool_name] = counts.get(tool_name, 0) + 1


def mock_run_result(
    *,
    user_prompt: str | None = None,
    final_text: str | None = "mock",
) -> RunResult:
    return RunResult(
        usage_metrics={"turns": 0, "tokens_spent": 0},
        final_text=final_text,
        run_messages=None,
        user_prompt=user_prompt,
    )


def enrich_artifact_from_run(
    result: RunResult,
    *,
    user_prompt: str | None = None,
) -> RunArtifact:
    """Build messages + metrics from a completed agent run (not an evaluator)."""
    prompt = user_prompt if user_prompt is not None else result.user_prompt
    messages, tools_called = _slim_messages(
        result.run_messages,
        user_prompt=prompt,
        final_text=result.final_text,
    )
    metrics: dict[str, float | int | str | bool] = {
        str(k): int(v) for k, v in result.usage_metrics.items()
    }
    return RunArtifact(
        messages=messages,
        metrics=metrics,
        tools_called=tools_called,
    )


def _slim_messages(
    run_messages: list[Any] | None,
    *,
    user_prompt: str | None,
    final_text: str | None,
) -> tuple[list[Message], dict[str, int]]:
    out: list[Message] = []
    tools_called: dict[str, int] = {}
    pending: dict[str, _PendingTool] = {}
    prompt = user_prompt
    if prompt:
        out.append(Message(role="user", content=_trunc(prompt)))

    if run_messages:
        for msg in run_messages:
            parts = getattr(msg, "parts", ()) or ()
            for part in parts:
                kind = getattr(part, "part_kind", None)
                if kind == "tool-call":
                    call_id = str(getattr(part, "tool_call_id", "") or id(part))
                    name = str(getattr(part, "tool_name", None) or "tool")
                    pending[call_id] = _PendingTool(tool_name=name)
                elif kind == "tool-return":
                    call_id = str(getattr(part, "tool_call_id", "") or "")
                    name = str(getattr(part, "tool_name", None) or "tool")
                    pending_entry = pending.pop(call_id, None)
                    if pending_entry is not None:
                        name = pending_entry.tool_name
                    content = getattr(part, "content", None)
                    text = _trunc(str(content)) if content is not None else ""
                    out.append(Message(role="tool", name=name, content=text))
                    _increment_tool_count(tools_called, name)
                elif kind == "text":
                    content = getattr(part, "content", None)
                    if content and str(content).strip():
                        out.append(
                            Message(role="assistant", content=_trunc(str(content)))
                        )
                elif kind == "user-prompt":
                    content = getattr(part, "content", None)
                    if content and not prompt:
                        out.append(Message(role="user", content=_trunc(str(content))))

    for pending_entry in pending.values():
        out.append(Message(role="tool", name=pending_entry.tool_name, content=""))
        _increment_tool_count(tools_called, pending_entry.tool_name)

    if final_text and str(final_text).strip():
        truncated = _trunc(final_text)
        if not out or out[-1].role != "assistant" or out[-1].content != truncated:
            out.append(Message(role="assistant", content=truncated))

    if not out and (final_text is None or not str(final_text).strip()):
        out.append(Message(role="assistant", content=""))
    return out, tools_called


def usage_from_run_usage(usage: RunUsage) -> dict[str, int]:
    return usage_to_metric_dict(usage)

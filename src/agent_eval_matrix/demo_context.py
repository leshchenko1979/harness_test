from __future__ import annotations

from contextvars import ContextVar

from agent_eval_matrix.models import EditCase

demo_case: ContextVar[EditCase | None] = ContextVar("demo_case", default=None)

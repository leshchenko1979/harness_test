"""File-edit gate evaluators."""

from __future__ import annotations

import difflib

from gategrid.contrib.file_edit.cases import FileEditCase
from gategrid.models.artifact import RunArtifact
from gategrid.models.evaluator_outcome import EvaluatorOutcome
from gategrid.runtime import RunContext

FILE_EDIT_TAG = "file_edit"


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


def file_content_match_impl(ctx: RunContext, artifact: RunArtifact) -> EvaluatorOutcome:
    if FILE_EDIT_TAG not in ctx.case.tags:
        return EvaluatorOutcome(pass_=True)

    fe = FileEditCase.from_record(ctx.case)
    expected = fe.expected_output
    actual_raw = ctx.scratchpad.get("actual_content")
    if actual_raw is None:
        return EvaluatorOutcome(
            pass_=False,
            message="missing actual file content",
        )
    actual = str(actual_raw)
    if _normalize(actual) == _normalize(expected):
        return EvaluatorOutcome(pass_=True)

    diff = "\n".join(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile=fe.file_name,
            tofile=fe.file_name,
            lineterm="",
        )
    )
    return EvaluatorOutcome(
        pass_=False,
        message="output differs from expected",
        detail=diff,
    )

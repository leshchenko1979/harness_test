"""File-edit gate evaluators."""

from __future__ import annotations

import difflib
from typing import Any

from gategrid.contrib.file_edit.cases import FileEditCase
from gategrid.models.artifact import RunArtifact
from gategrid.runtime import RunContext

FILE_EDIT_TAG = "file_edit"


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


def _slim_artifact(artifact: RunArtifact) -> dict[str, Any]:
    return artifact.model_dump(mode="json")


def file_content_match_impl(
    ctx: RunContext, artifact: RunArtifact
) -> bool | dict[str, Any]:
    if FILE_EDIT_TAG not in ctx.case.tags:
        return True

    fe = FileEditCase.from_record(ctx.case)
    expected = fe.expected_output
    actual_raw = ctx.scratchpad.get("actual_content")
    if actual_raw is None:
        return {
            "pass": False,
            "message": "missing actual file content",
            "artifact": _slim_artifact(artifact),
        }
    actual = str(actual_raw)
    if _normalize(actual) == _normalize(expected):
        return {
            "pass": True,
            "artifact": _slim_artifact(artifact),
        }

    diff = "\n".join(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile=fe.file_name,
            tofile=fe.file_name,
            lineterm="",
        )
    )
    return {
        "pass": False,
        "message": "output differs from expected",
        "detail": diff,
        "artifact": _slim_artifact(artifact),
    }

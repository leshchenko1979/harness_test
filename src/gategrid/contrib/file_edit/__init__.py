"""File-edit benchmark helpers (sandbox + content-match evaluator)."""

from gategrid.contrib.file_edit.evaluators import file_content_match_impl
from gategrid.contrib.file_edit.sandbox import (
    SandboxError,
    canonical_path,
    resolve_workspace_path,
)
from gategrid.evaluators import EvaluatorRecord, register_builtin_evaluator


def _register_builtin_gates() -> None:
    def file_content_match(ctx, artifact):  # type: ignore[no-untyped-def]
        return file_content_match_impl(ctx, artifact)

    register_builtin_evaluator(
        EvaluatorRecord(
            evaluator_id="file_content_match",
            tags=["gate"],
            fn=file_content_match,
            definition="gategrid.contrib.file_edit:file_content_match",
        )
    )


_register_builtin_gates()

import gategrid.contrib.file_edit.bundled  # noqa: F401, E402

__all__ = [
    "SandboxError",
    "canonical_path",
    "file_content_match_impl",
    "resolve_workspace_path",
]

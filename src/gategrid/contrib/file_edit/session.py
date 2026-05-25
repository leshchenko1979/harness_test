"""Workspace lifecycle for file-edit runs."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gategrid.contrib.file_edit.cases import FileEditCase
from gategrid.contrib.file_edit.deps import FileEditDeps
from gategrid.models.artifact import Message, RunArtifact


@dataclass
class AgentRunOutcome:
    """Minimal agent result for artifact mapping."""

    metrics: dict[str, float | int | str | bool] | None = None
    assistant_message: str | None = None


class FileEditSession:
    def __init__(self, case: FileEditCase) -> None:
        self.case = case
        self._tmpdir: tempfile.TemporaryDirectory[str] | None = None
        self.workspace: Path | None = None
        self.deps: FileEditDeps | None = None

    def __enter__(self) -> FileEditSession:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmpdir.name)
        file_path = self.workspace / self.case.file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(self.case.initial_content, encoding="utf-8")
        self.deps = FileEditDeps(workspace=self.workspace)
        return self

    def __exit__(self, *args: object) -> None:
        if self._tmpdir is not None:
            self._tmpdir.cleanup()
        self._tmpdir = None
        self.workspace = None
        self.deps = None

    @staticmethod
    def mock_artifact(case: FileEditCase) -> RunArtifact:
        return RunArtifact(messages=[Message(role="assistant", content="mock")])

    def to_artifact(self, outcome: AgentRunOutcome) -> RunArtifact:
        if self.workspace is None:
            raise RuntimeError("FileEditSession is not active")
        extra = dict(outcome.metrics or {})
        metrics: dict[str, float | int | str | bool] = {
            k: v
            for k, v in extra.items()
            if isinstance(v, (str, int, float, bool))
        }
        messages: list[Message] = []
        if outcome.assistant_message:
            messages.append(
                Message(role="assistant", content=outcome.assistant_message)
            )
        return RunArtifact(metrics=metrics, messages=messages)

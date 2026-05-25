from pathlib import Path

import pytest

from gategrid.contrib.file_edit.sandbox import (
    SandboxError,
    canonical_path,
    relative_workspace_path,
    resolve_workspace_path,
)


def test_resolve_inside_workspace(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "a.txt").write_text("hi")
    target = resolve_workspace_path(ws, "a.txt")
    assert target.name == "a.txt"


def test_reject_escape(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    with pytest.raises(SandboxError):
        resolve_workspace_path(ws, "../outside")


def test_absolute_path_inside_workspace(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    file_path = ws / "app.py"
    file_path.write_text("x")
    abs_path = str(file_path.resolve())
    target = resolve_workspace_path(ws, abs_path)
    assert target == canonical_path(file_path)
    assert relative_workspace_path(ws, target) == "app.py"


def test_absolute_path_outside_workspace(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    outside = tmp_path / "other.txt"
    outside.write_text("x")
    with pytest.raises(SandboxError):
        resolve_workspace_path(ws, str(outside.resolve()))

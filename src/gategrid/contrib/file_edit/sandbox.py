from __future__ import annotations

import os
from pathlib import Path


class SandboxError(ValueError):
    pass


def canonical_path(path: Path) -> Path:
    """Resolve symlinks (e.g. macOS /var vs /private/var)."""
    return Path(os.path.realpath(path))


def resolve_workspace_path(workspace: Path, user_path: str) -> Path:
    """Resolve user_path inside workspace; accept absolute paths under workspace."""
    workspace_c = canonical_path(workspace)
    raw = Path(user_path)
    if raw.is_absolute():
        target = canonical_path(raw)
    else:
        target = canonical_path(workspace_c / raw)
    try:
        target.relative_to(workspace_c)
    except ValueError as exc:
        raise SandboxError(
            f"Path '{user_path}' escapes the workspace sandbox."
        ) from exc
    return target


def relative_workspace_path(workspace: Path, target: Path) -> str:
    """Short workspace-relative path for tool responses."""
    workspace_c = canonical_path(workspace)
    target_c = canonical_path(target)
    return str(target_c.relative_to(workspace_c))

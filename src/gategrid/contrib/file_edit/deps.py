"""Agent deps for file-edit benchmarks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileEditDeps:
    workspace: Path

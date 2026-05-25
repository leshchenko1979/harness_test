"""Ensure evals/tooling is on sys.path for opencrabs package imports."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_tooling_path() -> None:
    tooling_dir = Path(__file__).resolve().parent.parent
    if str(tooling_dir) not in sys.path:
        sys.path.insert(0, str(tooling_dir))

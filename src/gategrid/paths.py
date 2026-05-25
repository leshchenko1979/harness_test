from __future__ import annotations

import os
from pathlib import Path


def gategrid_home(cwd: Path | None = None) -> Path:
    if env := os.environ.get("GATEGRID_HOME"):
        return Path(env).expanduser().resolve()
    root = cwd or Path.cwd()
    return (root / ".gategrid").resolve()


def _root(home: Path | None) -> Path:
    return home if home is not None else gategrid_home()


def baselines_dir(home: Path | None = None) -> Path:
    return _root(home) / "baselines"


def reports_dir(home: Path | None = None) -> Path:
    return _root(home) / "reports"


def baseline_path(profile_id: str, home: Path | None = None) -> Path:
    return baselines_dir(home) / f"{profile_id}.json"


def traces_dir(home: Path | None = None) -> Path:
    return _root(home) / "traces"


def path_under_home(path: Path, home: Path | None = None) -> bool:
    try:
        path.resolve().relative_to(_root(home).resolve())
        return True
    except ValueError:
        return False


def ensure_home(home: Path | None = None) -> Path:
    """Create `.gategrid/` subdirs (baselines, reports, traces) if missing."""
    root = _root(home)
    for sub in ("baselines", "reports", "traces"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from gategrid.models.baseline import Baseline
from gategrid.models.matrix_config import MatrixConfig
from gategrid.models.report import MatrixReport
from gategrid.paths import ensure_home, path_under_home

T = TypeVar("T", bound=BaseModel)


def load_json(path: Path, model: type[T]) -> T:
    data = json.loads(path.read_text(encoding="utf-8"))
    return model.model_validate(data)


def load_yaml_model(path: Path, model: type[T]) -> T:
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return model.model_validate(raw)


def save_json(path: Path, obj: BaseModel, *, home: Path | None = None) -> None:
    if path_under_home(path, home):
        ensure_home(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj.model_dump(mode="json"), indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def load_report(path: Path) -> MatrixReport:
    return load_json(path, MatrixReport)


def load_baseline(path: Path) -> Baseline:
    return load_json(path, Baseline)


def load_matrix_config(path: Path) -> MatrixConfig:
    return load_yaml_model(path, MatrixConfig)

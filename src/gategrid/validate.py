from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from gategrid.cases import (
    _BUILTIN_CASE_SETS,
    _ensure_file_edit_builtins_loaded,
    case_id_qualify_mode,
    discover_cases,
    print_case_id_convention,
    resolve_case_ids,
)
from gategrid.evaluators import (
    discover_evaluators,
    evaluator_id_qualify_mode,
    print_evaluator_id_convention,
)
from gategrid.io import load_matrix_config, load_yaml_model
from gategrid.models.case_set_config import CaseSetConfig
from gategrid.models.env import missing_api_keys
from gategrid.models.matrix_config import MatrixConfig
from gategrid.models.model_config import ModelConfig
from gategrid.models.profile_config import ProfileConfig


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, message: str) -> None:
        self.errors.append(message)


def resolve_eval_root(matrix_path: Path, root: Path | None) -> Path:
    matrix_path = matrix_path.resolve()
    if root is not None:
        return root.resolve()
    env_root = os.environ.get("GATEGRID_EVAL_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    if matrix_path.parent.name == "matrices":
        return matrix_path.parent.parent
    return matrix_path.parent


def validate_matrix(
    matrix_path: Path,
    *,
    root: Path | None = None,
    emit_conventions: bool = False,
) -> ValidationResult:
    result = ValidationResult()
    matrix_path = matrix_path.resolve()
    if not matrix_path.is_file():
        result.add(f"matrix not found: {matrix_path}")
        return result

    eval_root = resolve_eval_root(matrix_path, root)
    profiles_dir = eval_root / "profiles"
    models_dir = eval_root / "models"
    case_sets_dir = eval_root / "case_sets"

    try:
        matrix = load_matrix_config(matrix_path)
    except Exception as exc:
        result.add(f"matrix {matrix_path.name}: {exc}")
        return result

    _validate_matrix_refs(
        matrix,
        eval_root,
        profiles_dir,
        models_dir,
        case_sets_dir,
        result,
    )
    if result.ok:
        _validate_case_ids(matrix, eval_root, result)
    if result.ok:
        _validate_evaluators(eval_root, result)
    if result.ok:
        _validate_api_keys(matrix, models_dir, result)
    if result.ok:
        try:
            case_id_qualify_mode()
        except ValueError as exc:
            result.add(str(exc))
    if result.ok:
        try:
            evaluator_id_qualify_mode()
        except ValueError as exc:
            result.add(str(exc))
    if result.ok and emit_conventions:
        print_case_id_convention()
        print_evaluator_id_convention()
    return result


def _validate_evaluators(eval_root: Path, result: ValidationResult) -> None:
    try:
        discover_evaluators(eval_root)
    except Exception as exc:
        result.add(str(exc))


def _validate_api_keys(
    matrix: MatrixConfig,
    models_dir: Path,
    result: ValidationResult,
) -> None:
    registry: dict[str, ModelConfig] = {}
    for model_id in matrix.models:
        path = models_dir / f"{model_id}.yaml"
        if not path.is_file():
            continue
        try:
            registry[model_id] = load_yaml_model(path, ModelConfig)
        except Exception:
            continue
    missing = missing_api_keys(matrix.models, registry)
    if missing:
        vars_list = ", ".join(missing)
        result.add(
            f"missing API key environment variable(s): {vars_list} "
            "(set in .env or use provider: mock for smoke matrices)"
        )


def _validate_matrix_refs(
    matrix: MatrixConfig,
    eval_root: Path,
    profiles_dir: Path,
    models_dir: Path,
    case_sets_dir: Path,
    result: ValidationResult,
) -> None:
    for profile_id in matrix.profiles:
        path = profiles_dir / f"{profile_id}.yaml"
        if not path.is_file():
            result.add(f"profile {profile_id!r}: missing {path.relative_to(eval_root)}")
            continue
        try:
            load_yaml_model(path, ProfileConfig)
        except Exception as exc:
            result.add(f"profile {profile_id!r}: {exc}")

    for model_id in matrix.models:
        path = models_dir / f"{model_id}.yaml"
        if not path.is_file():
            result.add(f"model {model_id!r}: missing {path.relative_to(eval_root)}")
            continue
        try:
            load_yaml_model(path, ModelConfig)
        except Exception as exc:
            result.add(f"model {model_id!r}: {exc}")

    _ensure_file_edit_builtins_loaded()
    for case_set_id in matrix.case_sets:
        path = case_sets_dir / f"{case_set_id}.yaml"
        if path.is_file():
            try:
                load_yaml_model(path, CaseSetConfig)
            except Exception as exc:
                result.add(f"case_set {case_set_id!r}: {exc}")
        elif case_set_id not in _BUILTIN_CASE_SETS:
            result.add(
                f"case_set {case_set_id!r}: missing {path.relative_to(eval_root)} "
                "and not a builtin case set"
            )


def _validate_case_ids(
    matrix: MatrixConfig,
    eval_root: Path,
    result: ValidationResult,
) -> None:
    try:
        case_ids = resolve_case_ids(matrix, eval_root)
    except Exception as exc:
        result.add(str(exc))
        return

    try:
        registry = discover_cases(eval_root)
    except Exception as exc:
        result.add(str(exc))
        return

    for cid in case_ids:
        if cid not in registry:
            known = ", ".join(sorted(registry))
            result.add(f"unknown case id {cid!r}; registered: {known or '(none)'}")

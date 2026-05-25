"""File-edit case helpers (YAML loader + CaseRecord.data)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from gategrid.cases import CaseRecord, register_builtin_case, register_case_record

FILE_EDIT_TAG = "file_edit"
_REQUIRED_DATA_KEYS = (
    "instruction",
    "file_name",
    "initial_content",
    "expected_output",
)


@dataclass
class FileEditCase:
    case_id: str
    instruction: str
    file_name: str
    initial_content: str
    expected_output: str
    tags: list[str]

    @classmethod
    def from_record(cls, record: CaseRecord) -> FileEditCase:
        data = record.data
        return cls(
            case_id=record.case_id,
            instruction=str(data["instruction"]),
            file_name=str(data["file_name"]),
            initial_content=str(data["initial_content"]),
            expected_output=str(data["expected_output"]),
            tags=list(record.tags),
        )


def validate_file_edit_case(record: CaseRecord) -> None:
    if FILE_EDIT_TAG not in record.tags:
        raise ValueError(f"case {record.case_id!r}: missing tag {FILE_EDIT_TAG!r}")
    missing = [k for k in _REQUIRED_DATA_KEYS if k not in record.data]
    if missing:
        raise ValueError(
            f"case {record.case_id!r}: file_edit data missing keys {missing!r}"
        )


def file_edit_case(
    *,
    id: str,
    instruction: str,
    file_name: str,
    initial_content: str,
    expected_output: str,
    tags: list[str] | None = None,
) -> None:
    tag_list = list(tags or [])
    if FILE_EDIT_TAG not in tag_list:
        tag_list.append(FILE_EDIT_TAG)
    register_case_record(
        CaseRecord(
            case_id=id,
            tags=tag_list,
            definition=f"file_edit:{id}",
            data={
                "instruction": instruction,
                "file_name": file_name,
                "initial_content": initial_content,
                "expected_output": expected_output,
            },
        ),
        idempotent=True,
    )


def _case_record_from_yaml(path: Path) -> CaseRecord:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Case file {path} must be a YAML mapping")
    case_id = str(data.get("name") or path.stem)
    yaml_tags = list(data.get("tags") or [])
    tag_list = list(yaml_tags)
    if FILE_EDIT_TAG not in tag_list:
        tag_list.append(FILE_EDIT_TAG)
    return CaseRecord(
        case_id=case_id,
        tags=tag_list,
        definition=f"file_edit:{case_id}",
        data={
            "instruction": str(data["instruction"]),
            "file_name": str(data["file_name"]),
            "initial_content": str(data["initial_content"]),
            "expected_output": str(data["expected_output"]),
        },
    )


def register_builtin_case_from_yaml(path: Path) -> None:
    register_builtin_case(_case_record_from_yaml(path))


def register_case_from_yaml(path: Path) -> None:
    record = _case_record_from_yaml(path)
    register_case_record(record, idempotent=True)

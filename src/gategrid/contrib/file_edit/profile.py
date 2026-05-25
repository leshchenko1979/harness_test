"""File-edit profile helpers (keys live under ProfileConfig.data)."""

from __future__ import annotations

from gategrid.models.profile_config import ProfileConfig


def system_prompt_from_profile(profile: ProfileConfig) -> str:
    try:
        value = profile.data["system_prompt"]
    except KeyError as exc:
        raise ValueError(
            "file-edit profile missing data.system_prompt "
            "(required for PydanticAiFileEditAdapter)"
        ) from exc
    if not isinstance(value, str) or not value.strip():
        raise ValueError("file-edit profile data.system_prompt must be a non-empty string")
    return value


def tools_from_profile(profile: ProfileConfig) -> list[str]:
    raw = profile.data.get("tools")
    if raw is None:
        raise ValueError(
            "file-edit profile missing data.tools "
            "(required for PydanticAiFileEditAdapter)"
        )
    if not isinstance(raw, list) or not all(isinstance(e, str) for e in raw):
        raise ValueError("file-edit profile data.tools must be a list of strings")
    return list(raw)


def validate_file_edit_profile(profile: ProfileConfig) -> None:
    """Fail fast when file-edit adapter keys are missing or invalid."""
    system_prompt_from_profile(profile)
    tools_from_profile(profile)

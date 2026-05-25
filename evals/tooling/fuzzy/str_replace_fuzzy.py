from __future__ import annotations

from pydantic_ai import RunContext

from gategrid.contrib.file_edit.deps import FileEditDeps
from fuzzy.tools_lib import str_replace_fuzzy as _str_replace_fuzzy


def str_replace_fuzzy(
    ctx: RunContext[FileEditDeps], file_path: str, old_str: str, new_str: str
) -> str:
    """Replace using fuzzy line-sequence matching."""
    return _str_replace_fuzzy(ctx, file_path, old_str, new_str)

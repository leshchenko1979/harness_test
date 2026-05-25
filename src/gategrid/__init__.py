"""Gategrid — matrix eval runner with git-native regression gates."""

from gategrid.cases import case
from gategrid.evaluators import evaluator
from gategrid.runtime import RunContext, RuntimeAdapter
from gategrid.version import SCHEMA_VERSION, __version__

__all__ = [
    "SCHEMA_VERSION",
    "__version__",
    "case",
    "evaluator",
    "RunContext",
    "RuntimeAdapter",
]

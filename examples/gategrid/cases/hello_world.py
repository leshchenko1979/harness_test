"""Smoke case — id defaults to function name ``hello_world``."""

from gategrid import case


@case
def hello_world() -> None:
    """Registered for matrix / case_set references."""

"""Pure product rules for top-level Squash Engine Runs."""

from __future__ import annotations

RUN_TIMELINE_START_SEASON = 2000
RUN_TIMELINE_END_SEASON = 2049
RUN_SEASON_COUNT = 50
RUN_WEEKS_PER_SEASON = 61
RUN_DISPLAY_NAME_MAX_LENGTH = 256

INITIAL_BRANCH_DISPLAY_NAME = "Timeline 1"
WORKING_RUN_STATUS = "working"


class RunDisplayNameValidationError(ValueError):
    """Raised when a user-supplied Run display name is not valid."""


def normalize_run_display_name(value: str) -> str:
    """Return the canonical stored display name without inventing case rules.

    Leading and trailing whitespace is not part of a displayed name. Case is
    deliberately preserved because case-insensitive identity has not been made
    a product rule.
    """

    if not isinstance(value, str):
        raise RunDisplayNameValidationError("display_name must be a string")
    normalized = value.strip()
    if not normalized:
        raise RunDisplayNameValidationError("display_name must not be blank")
    if len(normalized) > RUN_DISPLAY_NAME_MAX_LENGTH:
        raise RunDisplayNameValidationError(
            f"display_name must contain at most {RUN_DISPLAY_NAME_MAX_LENGTH} characters"
        )
    return normalized


assert RUN_TIMELINE_END_SEASON - RUN_TIMELINE_START_SEASON + 1 == RUN_SEASON_COUNT

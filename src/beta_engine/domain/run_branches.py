"""Pure product rules for names of timelines inside one Run."""

from __future__ import annotations

import re
from collections.abc import Iterable

BRANCH_DISPLAY_NAME_MAX_LENGTH = 256
TIMELINE_DISPLAY_NAME_PREFIX = "Timeline"

_AUTOMATIC_TIMELINE_NAME = re.compile(
    rf"^{re.escape(TIMELINE_DISPLAY_NAME_PREFIX)} ([1-9][0-9]*)$"
)


class BranchDisplayNameValidationError(ValueError):
    """Raised when a user-supplied Branch display name is not valid."""


def normalize_branch_display_name(value: str) -> str:
    """Return a trimmed Branch name while preserving the user's letter case."""

    if not isinstance(value, str):
        raise BranchDisplayNameValidationError("display_name must be a string")
    normalized = value.strip()
    if not normalized:
        raise BranchDisplayNameValidationError("display_name must not be blank")
    if len(normalized) > BRANCH_DISPLAY_NAME_MAX_LENGTH:
        raise BranchDisplayNameValidationError(
            "display_name must contain at most "
            f"{BRANCH_DISPLAY_NAME_MAX_LENGTH} characters"
        )
    return normalized


def first_available_timeline_name(existing_names: Iterable[str]) -> str:
    """Return the first unused canonical ``Timeline N`` display name.

    Only exact canonical names reserve their number. For example,
    ``Timeline 02`` and ``timeline 2`` remain ordinary custom names.
    """

    reserved_numbers = {
        int(match.group(1))
        for name in existing_names
        if (match := _AUTOMATIC_TIMELINE_NAME.fullmatch(name)) is not None
    }
    sequence = 1
    while sequence in reserved_numbers:
        sequence += 1
    return f"{TIMELINE_DISPLAY_NAME_PREFIX} {sequence}"

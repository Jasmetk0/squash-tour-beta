"""Season label compatibility utilities.

Canonical internal label for the new Season Registry is compact ``YYYY/YY``.
This module provides additive compatibility helpers so legacy long labels
(``YYYY/YYYY``) continue to work without broad runtime behavior changes.
"""

from __future__ import annotations

import re

_COMPACT_RE = re.compile(r"^(\d{4})/(\d{2})$")
_LONG_RE = re.compile(r"^(\d{4})/(\d{4})$")


def season_label_from_start_year(start_year: int) -> str:
    if not isinstance(start_year, int):
        raise ValueError("start_year must be an integer")
    if start_year < 0:
        raise ValueError("start_year must be non-negative")
    return f"{start_year}/{(start_year + 1) % 100:02d}"


def long_season_label_from_start_year(start_year: int) -> str:
    if not isinstance(start_year, int):
        raise ValueError("start_year must be an integer")
    if start_year < 0:
        raise ValueError("start_year must be non-negative")
    return f"{start_year}/{start_year + 1}"


def season_start_year_from_label(label: str) -> int:
    normalized = normalize_season_label(label)
    match = _COMPACT_RE.match(normalized)
    assert match is not None
    return int(match.group(1))


def normalize_season_label(label: str) -> str:
    if not isinstance(label, str):
        raise ValueError("season label must be a string")
    raw = label.strip()

    compact = _COMPACT_RE.match(raw)
    if compact:
        start_year = int(compact.group(1))
        end_two_digits = int(compact.group(2))
        expected = (start_year + 1) % 100
        if end_two_digits != expected:
            raise ValueError("season label rollover is invalid")
        return season_label_from_start_year(start_year)

    long_label = _LONG_RE.match(raw)
    if long_label:
        start_year = int(long_label.group(1))
        end_year = int(long_label.group(2))
        if end_year != start_year + 1:
            raise ValueError("season label rollover is invalid")
        return season_label_from_start_year(start_year)

    raise ValueError("season label must use YYYY/YY or YYYY/YYYY format")


def to_compact_season_label(label: str) -> str:
    return normalize_season_label(label)


def to_long_season_label(label: str) -> str:
    return long_season_label_from_start_year(season_start_year_from_label(label))

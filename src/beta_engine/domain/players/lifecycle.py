"""Pure player lifecycle helpers for birth identity preservation."""

from __future__ import annotations

import hashlib

from beta_engine.domain.calendar import DEFAULT_WEEKS_PER_CALENDAR_YEAR


def derive_birth_year_from_age(season_start_year: int, age: int) -> int:
    """Derive a coarse birth year from stored season-start age without changing age semantics."""

    return season_start_year - age


def synthesize_birth_year_week(*, player_id: str, birth_year: int) -> int:
    """Deterministically synthesize a FAX birth week without consuming simulation RNG streams."""

    digest = hashlib.blake2b(f"birth-year-week|{player_id}|{birth_year}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") % DEFAULT_WEEKS_PER_CALENDAR_YEAR + 1

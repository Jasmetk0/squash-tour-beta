"""Acceptance gates for a historical year promotion, including source conflicts."""
from __future__ import annotations

import json

import pytest

from scripts.promote_atp_calendar_candidate import (
    PENDING_CONFLICTS,
    prepare,
)
from scripts.build_atp_historical_calendar import SOURCE

pytestmark = pytest.mark.pr_critical


def test_2003_promotion_blocked_by_conflicting_official_finals_dates() -> None:
    assert "atp_finals" in PENDING_CONFLICTS[2003]
    assert "2003-11-08" in PENDING_CONFLICTS[2003]["atp_finals"]
    assert "2003-11-10" in PENDING_CONFLICTS[2003]["atp_finals"]
    with pytest.raises(ValueError, match="Unresolved official ATP dates"):
        prepare(2003)


def test_source_files_remain_unchanged_when_promotion_vetoes() -> None:
    source = (SOURCE / "calendar_dates_v1.json").read_bytes()
    generated = (SOURCE / "calendar.json").read_bytes()
    with pytest.raises(ValueError, match="Unresolved official ATP dates"):
        prepare(2003)
    assert (SOURCE / "calendar_dates_v1.json").read_bytes() == source
    assert (SOURCE / "calendar.json").read_bytes() == generated


def test_promoter_rejects_unstaged_year() -> None:
    with pytest.raises(ValueError, match="Only the explicit 2003"):
        prepare(2002)


def test_conflicted_year_is_not_mislabelled_as_canonically_dated() -> None:
    dated = json.loads(
        (SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8")
    )
    assert "2003" not in dated["year_sources"]

"""ATP historical source-link season consistency regression.

This deliberately does not claim to verify the historical accuracy of a URL.
It guards against a correctly hosted but wrong-year ATP archive citation.
"""
from __future__ import annotations

import copy

import pytest

from scripts.build_atp_historical_calendar import (
    build,
    ensure_archive_year_matches,
)
from tests.domain.test_atp_historical_calendar import sources

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("year", [1990, 2003, 2004, 2019, 2026])
def test_correct_season_specific_official_archive_year(year: int) -> None:
    ensure_archive_year_matches(
        f"https://www.atptour.com/en/scores/results-archive?year={year}",
        year=year,
    )


@pytest.mark.parametrize("url", [
    "https://www.atptour.com/en/scores/results-archive?year=2004",
    "https://www.atptour.com/en/scores/results-archive?year=2003&year=2025",
    "https://www.atptour.com/en/scores/results-archive",
    "https://www.atptour.com/en/scores/results-archive?year=",
])
def test_wrong_or_missing_year_is_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="archive year must match"):
        ensure_archive_year_matches(url, year=2025)


def test_tournament_specific_url_not_mistaken_for_year_archive() -> None:
    ensure_archive_year_matches(
        "https://www.atptour.com/en/tournaments/rotterdam/407/overview",
        year=2003,
    )


def test_build_rejects_wrong_year_citation_even_if_domain_is_official() -> None:
    cats, series, seasons, dated = sources()
    bad = copy.deepcopy(dated)
    bad["year_sources"]["2004"]["source_url"] = (
        "https://www.atptour.com/en/scores/results-archive?year=2005"
    )
    with pytest.raises(ValueError, match="archive year must match"):
        build(cats, series, seasons, bad)


def test_build_rejects_wrong_year_event_link_independently() -> None:
    cats, series, seasons, dated = sources()
    bad = copy.deepcopy(dated)
    bad["year_sources"]["2004"]["events"][0]["source_url"] = (
        "https://www.atptour.com/en/scores/results-archive?year=2005"
    )
    with pytest.raises(ValueError, match="archive year must match"):
        build(cats, series, seasons, bad)

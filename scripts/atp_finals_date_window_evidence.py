"""Reviewed distinctions between official ATP annual event windows and Finals history.

The Calendar date fields denote ATP yearly RESULTS-ARCHIVE event windows,
NOT the first/last played singles match or all possible tournament activities.
Alternative official historical Finals windows must remain separately visible.

The seven entries below are evidence-backed, explicitly fixed approvals for
the *date-concept reconciliation only*. They do NOT certify tournament licence
lineage, draw/match records, native squash scheduling, or 2026 finality.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

VERIFIED_SOURCE_WINDOW_STATE = (
    "verified_atp_results_archive_with_separate_finals_historical_window"
)
CALENDAR_DATE_CONCEPT = "official_atp_annual_results_archive_event_window"
FINALS_ARCHIVE_URL = "https://www.atptour.com/en/scores/results-archive?year="
HISTORICAL_1990S_URL = (
    "https://www.nittoatpfinals.com/en/heritage/results-1970-1999"
)
HISTORICAL_2000S_URL = (
    "https://www.nittoatpfinals.com/en/heritage/results-2000-2023"
)
ALTERNATE_COMPETITION = "atp_finals_heritage_reported_competition_interval"
ALTERNATE_BROADER = "atp_finals_heritage_broader_tournament_interval"

# (archive start/end, separately official alternate start/end, date concept).
# 2003 is DISTINCT: annual ATP results record 10–16 Nov for Tour singles,
# while the official Finals historical record / ITF gives the broader 8–16 Nov.
# The 1990s annual archive starts one day before the Finals heritage date.
_EXACT = {
    1990: ("1990-11-12", "1990-11-18", "1990-11-13", "1990-11-18", ALTERNATE_COMPETITION),
    1992: ("1992-11-16", "1992-11-22", "1992-11-17", "1992-11-22", ALTERNATE_COMPETITION),
    1993: ("1993-11-15", "1993-11-21", "1993-11-16", "1993-11-21", ALTERNATE_COMPETITION),
    1997: ("1997-11-10", "1997-11-16", "1997-11-11", "1997-11-16", ALTERNATE_COMPETITION),
    1998: ("1998-11-23", "1998-11-29", "1998-11-24", "1998-11-29", ALTERNATE_COMPETITION),
    1999: ("1999-11-22", "1999-11-28", "1999-11-23", "1999-11-28", ALTERNATE_COMPETITION),
    2003: ("2003-11-10", "2003-11-16", "2003-11-08", "2003-11-16", ALTERNATE_BROADER),
}
REVIEWED_DATE_WINDOW_YEARS = frozenset(_EXACT)

def make_official_finals_window_evidence(year: int) -> dict[str, Any]:
    """Exact, source-concept-separated archive and alternate official evidence."""
    if type(year) is not int or year not in _EXACT:
        raise ValueError("ATP Finals alternate official window not reviewed")
    start, end, other_start, other_end, alternate_kind = _EXACT[year]
    return {
        "series_id": "atp_finals",
        "calendar_date_concept": CALENDAR_DATE_CONCEPT,
        "archive_source_url": FINALS_ARCHIVE_URL + str(year),
        "archive_start_date": start,
        "archive_end_date": end,
        "alternate_date_concept": alternate_kind,
        "alternate_start_date": other_start,
        "alternate_end_date": other_end,
        "alternate_source_url": (
            HISTORICAL_2000S_URL if year == 2003 else HISTORICAL_1990S_URL
        ),
        "reconciliation": "different_official_date_window_concepts_preserved",
        "no_match_day_or_playable_calendar_claim": True,
    }

def validate_official_finals_window_evidence(year: int, raw: Any) -> dict[str, Any]:
    expected = make_official_finals_window_evidence(year)
    if type(raw) is not dict or raw != expected:
        raise ValueError(
            "ATP Finals alternate source date-window evidence invalid or tampered: "
            + str(year)
        )
    return deepcopy(expected)

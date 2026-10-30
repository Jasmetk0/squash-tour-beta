"""Explicit Edition windows on the Run clock; no eligibility or field decisions."""

from typing import Literal

from pydantic import Field

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.official import FrozenInput


class EditionEntryTiming(FrozenInput):
    schema_version: Literal["edition_entry_timing.v1"] = "edition_entry_timing.v1"
    main_open: RunWeekPosition
    main_duration_weeks: int = Field(default=2, ge=1)
    qualification_duration_weeks: int = Field(default=1, ge=1)
    final_commitment: RunWeekPosition | None = None
    ranking_publication_override: RunWeekPosition | None = None


def resolve_entry_timing(timing: EditionEntryTiming, play: RunWeekPosition) -> dict:
    """Main Closing−1 is the completed-data week, published at Main Closing.

    Master §15.1 and §18.1 describe different sides of the same boundary: results
    through Week 13 become the Official snapshot labelled Week 14. Keep both
    labels explicit; never pick a latest-available fallback or synthesize Week 0.
    """
    clock = play.calendar
    positions = (timing.main_open, timing.final_commitment, timing.ranking_publication_override)
    if any(p is not None and p.calendar != clock for p in positions):
        raise ValueError("Entry timing must use the Edition's Run calendar")

    def at(ordinal):
        return RunWeekPosition(calendar=clock, season_index=ordinal // clock.weeks_per_year,
                               week=ordinal % clock.weeks_per_year + 1)

    main_close = at(timing.main_open.ordinal + timing.main_duration_weeks - 1)
    q_open = at(main_close.ordinal + 1)
    q_close = at(q_open.ordinal + timing.qualification_duration_weeks - 1)
    commitment = timing.final_commitment or q_close
    if q_close.ordinal >= play.ordinal:
        raise ValueError("Entry windows must finish before Edition play")
    if not timing.main_open.ordinal <= commitment.ordinal < play.ordinal:
        raise ValueError("Final Commitment must be within the configured pre-play process")
    override = timing.ranking_publication_override
    if override is not None and override.ordinal >= play.ordinal:
        raise ValueError("Ranking publication override must precede Edition play")
    completed = at(main_close.ordinal - 1) if main_close.ordinal > 0 else None
    publication = override or (main_close if completed is not None else None)
    return {
        "main_open": timing.main_open,
        "main_close": main_close,
        "qualification_open": q_open,
        "qualification_close": q_close,
        "final_commitment": commitment,
        "default_ranking_completed_week": completed,
        "ranking_publication_week": publication,
        "ranking_source": "explicit_publication_override" if override else "after_main_closing_minus_one",
    }


def entry_window_at(resolved: dict, current: RunWeekPosition) -> str:
    if current.calendar != resolved["main_open"].calendar:
        raise ValueError("Entry inspection must use the same Run calendar")
    if current.ordinal < resolved["main_open"].ordinal:
        return "not_open"
    if current.ordinal <= resolved["main_close"].ordinal:
        return "main"
    if current.ordinal <= resolved["qualification_close"].ordinal:
        return "qualification"
    return "all_entries_closed"

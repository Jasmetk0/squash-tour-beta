"""Period-scoped Country match record leaders from the FULL canonical Saved source.

No sporting weights, artificial ranking, future events, BYEs or mutable Run reads.
Source matches are validated by the pre-existing exact Saved Revision collector.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.country_saved_match_records import (
    CountrySavedMatch, collect_country_saved_match_records,
)
from beta_engine.application.run_home_activity_read_model import _season_index
from beta_engine.application.initial_world import InitialWorldState
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import RunPackageState
from beta_engine.infrastructure.db.run_prospect_source_state import RunProspectSourceSnapshot

RecordKind = Literal["played_wins", "played_matches"]


class CountryMatchRecordHolder(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    player_id: str
    player_name: str
    value: int = Field(ge=1)


class CountryMatchRecordSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    key: RecordKind
    value: int = Field(ge=0)
    holders: tuple[CountryMatchRecordHolder, ...]


class CountryMatchRecordHighlights(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["country_match_record_highlights.v1"] = "country_match_record_highlights.v1"
    source: Literal["reachable_saved_revision"] = "reachable_saved_revision"
    run_id: str
    branch_id: str
    revision_branch_id: str
    saved_revision_id: str
    country_code: str
    from_season: int = Field(ge=0, le=49)
    from_week: int = Field(ge=1, le=61)
    to_season: int = Field(ge=0, le=49)
    to_week: int = Field(ge=1, le=61)
    period_country_matches: int = Field(ge=0)
    period_played_matches: int = Field(ge=0)
    period_walkovers: int = Field(ge=0)
    records: tuple[CountryMatchRecordSummary, ...]
    selected_record: RecordKind | None = None
    evidence_count: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=50)
    has_more: bool
    evidence: tuple[CountrySavedMatch, ...]


def resolve_country_match_record_highlights(
    *, run_id: str, selected_branch_id: str, revision_branch_id: str,
    saved_revision_id: str, country_code: str,
    packages: RunPackageState | None, ranking: RankingRevisionState | None,
    initial_world: InitialWorldState | None,
    prospect_source: RunProspectSourceSnapshot | None,
    from_season: int, from_week: int, to_season: int, to_week: int,
    selected_record: RecordKind | None = None, offset: int = 0, limit: int = 25,
) -> CountryMatchRecordHighlights:
    if (not 0 <= from_season <= 49 or not 0 <= to_season <= 49
        or not 1 <= from_week <= 61 or not 1 <= to_week <= 61
        or (from_season, from_week) > (to_season, to_week)):
        raise ValueError("Invalid Country match record sport-time interval")
    if selected_record not in (None, "played_wins", "played_matches"):
        raise ValueError("Unsupported Country match record category")
    if offset < 0 or not 1 <= limit <= 50:
        raise ValueError("Invalid Country match record evidence page")

    # Important: this returns the FULL verified national match source, not the
    # already paged rows. Aggregate all permitted evidence BEFORE pagination.
    base, own = collect_country_saved_match_records(
        run_id=run_id, selected_branch_id=selected_branch_id,
        revision_branch_id=revision_branch_id, saved_revision_id=saved_revision_id,
        country_code=country_code, packages=packages, ranking=ranking,
        initial_world=initial_world, prospect_source=prospect_source,
        offset=0, limit=1,
    )
    period = tuple(m for m in own
                   if (from_season, from_week) <= (_season_index(m.season), m.season_week)
                   <= (to_season, to_week))
    played = tuple(m for m in period if m.completion == "played")
    names: dict[str, str] = {}
    counts: dict[RecordKind, dict[str, int]] = {
        "played_wins": {}, "played_matches": {},
    }

    def add(key: RecordKind, pid: str, name: str) -> None:
        if pid in names and names[pid] != name:
            raise ValueError("Ambiguous Saved player name across Country match evidence")
        names[pid] = name
        counts[key][pid] = counts[key].get(pid, 0) + 1

    for match in played:
        if match.winner_country == country_code:
            add("played_wins", match.winner_player_id, match.winner_name)
            add("played_matches", match.winner_player_id, match.winner_name)
        if match.loser_country == country_code:
            add("played_matches", match.loser_player_id, match.loser_name)

    summaries: list[CountryMatchRecordSummary] = []
    tied: dict[RecordKind, set[str]] = {
        "played_wins": set(), "played_matches": set(),
    }
    for kind in ("played_wins", "played_matches"):
        points = counts[kind]
        value = max(points.values(), default=0)
        leaders = tuple(
            CountryMatchRecordHolder(player_id=pid, player_name=names[pid], value=n)
            for pid, n in sorted(points.items()) if value > 0 and n == value
        )
        tied[kind] = {x.player_id for x in leaders}
        summaries.append(CountryMatchRecordSummary(
            key=kind, value=value, holders=leaders,
        ))

    matched: tuple[CountrySavedMatch, ...] = ()
    if selected_record == "played_wins":
        matched = tuple(m for m in played if m.winner_player_id in tied["played_wins"]
                        and m.winner_country == country_code)
    elif selected_record == "played_matches":
        matched = tuple(m for m in played if
                        (m.winner_country == country_code and m.winner_player_id in tied["played_matches"])
                        or (m.loser_country == country_code and m.loser_player_id in tied["played_matches"]))

    return CountryMatchRecordHighlights(
        run_id=run_id, branch_id=selected_branch_id, revision_branch_id=revision_branch_id,
        saved_revision_id=saved_revision_id, country_code=country_code,
        from_season=from_season, from_week=from_week, to_season=to_season, to_week=to_week,
        period_country_matches=len(period), period_played_matches=len(played),
        period_walkovers=len(period)-len(played),
        records=tuple(summaries), selected_record=selected_record,
        evidence_count=len(matched), offset=offset, limit=limit,
        has_more=offset+limit<len(matched), evidence=matched[offset:offset+limit],
    )

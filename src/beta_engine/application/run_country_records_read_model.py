"""Country Records from canonical published tournament results in one Saved Revision.

Only published canonical results count. Host-country and player-nationality
evidence are distinct; the calendar's completed status is never a result.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.application.run_home_player_identity import resolve_saved_home_player_identities
from beta_engine.application.viewer_tournament_history_read_model import resolve_viewer_tournament_history
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import RunPackageState
from beta_engine.infrastructure.db.run_prospect_source_state import RunProspectSourceSnapshot


class CountryRecordResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event_id: str
    event_name: str
    season: str
    season_week: int = Field(ge=1, le=61)
    host_country: str
    champion_player_id: str
    champion_name: str
    champion_country: str
    finalist_player_id: str
    finalist_name: str
    finalist_country: str


class RunCountryRecords(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["run_country_records.v1"] = "run_country_records.v1"
    run_id: str
    branch_id: str  # selected Branch, not necessarily an ancestor's source Branch
    revision_branch_id: str
    saved_revision_id: str
    source: Literal["reachable_saved_revision"] = "reachable_saved_revision"
    country_code: str
    calendar_status: Literal["empty", "ready"]
    published_result_count: int = Field(ge=0)
    country_titles: int = Field(ge=0)
    country_finalists: int = Field(ge=0)
    hosted_published_results: int = Field(ge=0)
    player_results: tuple[CountryRecordResult, ...]
    hosted_results: tuple[CountryRecordResult, ...]


def resolve_run_country_records(
    *, run_id: str, selected_branch_id: str, revision_branch_id: str,
    saved_revision_id: str, country_code: str,
    packages: RunPackageState | None, ranking: RankingRevisionState | None,
    initial_world: InitialWorldState | None,
    prospect_source: RunProspectSourceSnapshot | None,
) -> RunCountryRecords:
    if len(country_code) != 3 or not country_code.isalpha() or country_code != country_code.upper():
        raise ValueError("Country Records requires a canonical three-letter country code")
    if not saved_revision_id or not selected_branch_id or not revision_branch_id:
        raise ValueError("Country Records requires an exact Saved Revision and Branch identity")
    if packages is not None and (packages.run_id, packages.branch_id) != (run_id, revision_branch_id):
        raise ValueError("Saved Country Records Calendar belongs to another Run/Branch")
    if ranking is not None and (ranking.run_id, ranking.branch_id) != (run_id, revision_branch_id):
        raise ValueError("Saved Country Records ranking belongs to another Run/Branch")
    if initial_world is not None and (initial_world.run_id, initial_world.branch_id) != (run_id, revision_branch_id):
        raise ValueError("Saved Country Records Initial World belongs to another Run/Branch")
    if prospect_source is not None and prospect_source.run_id != run_id:
        raise ValueError("Saved Country Records prospect source belongs to another Run")

    tournaments = ()
    if packages is not None:
        try:
            projection = resolve_viewer_tournament_history(
                run_package_state=packages, ranking=ranking,
                run_id=run_id, branch_id=revision_branch_id,
            )
        except KeyError as exc:
            if "no applied Calendar Package" not in str(exc) or (
                ranking is not None and ranking.tournament_sources
            ):
                raise
        else:
            tournaments = projection.tournaments
    elif ranking is not None and ranking.tournament_sources:
        raise ValueError("Published Country Records results have no Saved Calendar")
    published = tuple(item for item in tournaments if item.result_published)
    if any(not item.champion_player_id or not item.finalist_player_id for item in published):
        raise ValueError("Published Country Records has incomplete participant identities")
    wanted = sorted({pid for item in published for pid in (
        item.champion_player_id, item.finalist_player_id,
    ) if pid is not None})
    identities = {}
    for offset in range(0, len(wanted), 25):
        batch = tuple(wanted[offset:offset + 25])
        answer = resolve_saved_home_player_identities(
            run_id=run_id, branch_id=revision_branch_id,
            saved_revision_id=saved_revision_id, requested_ids=batch,
            initial_world=initial_world, prospect_source=prospect_source,
        )
        if answer.unresolved_ids or answer.status != "ready":
            raise ValueError("Published Country Records participant has no saved national identity")
        for player in answer.players:
            if player.player_id in identities:
                raise ValueError("Duplicate published participant nationality")
            identities[player.player_id] = player

    complete = []
    for item in published:
        champion = identities[item.champion_player_id]
        finalist = identities[item.finalist_player_id]
        complete.append(CountryRecordResult(
            event_id=item.event_id, event_name=item.event_name or item.event_id,
            season=item.season, season_week=item.season_week,
            host_country=item.host_country,
            champion_player_id=champion.player_id, champion_name=champion.display_name,
            champion_country=champion.country_code,
            finalist_player_id=finalist.player_id, finalist_name=finalist.display_name,
            finalist_country=finalist.country_code,
        ))
    complete.sort(key=lambda x: (x.season, x.season_week, x.event_id))
    athlete = tuple(row for row in complete if (
        row.champion_country == country_code or row.finalist_country == country_code
    ))
    hosted = tuple(row for row in complete if row.host_country == country_code)
    return RunCountryRecords(
        run_id=run_id, branch_id=selected_branch_id,
        revision_branch_id=revision_branch_id, saved_revision_id=saved_revision_id,
        country_code=country_code, calendar_status="ready" if tournaments else "empty",
        published_result_count=len(complete),
        country_titles=sum(x.champion_country == country_code for x in complete),
        country_finalists=sum(x.finalist_country == country_code for x in complete),
        hosted_published_results=len(hosted), player_results=athlete,
        hosted_results=hosted,
    )

"""Read-only, Branch-owned player sporting summary from an immutable Saved Revision.

Never combine this profile with a live/legacy player record or the Viewer Branch.
Tournament results and Official Ranking are distinct, independently published facts.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.run_home_player_identity import (
    SavedHomePlayerIdentities, SavedHomePlayerIdentity,
)
from beta_engine.application.viewer_official_ranking_read_model import (
    resolve_viewer_official_ranking,
)
from beta_engine.application.viewer_tournament_history_read_model import (
    resolve_viewer_tournament_history,
)
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import RunPackageState


class SavedPlayerTournamentFinish(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event_id: str = Field(min_length=1)
    event_name: str
    season: str
    week: int = Field(ge=1, le=61)
    finish: Literal["champion", "runner_up"]


class SavedPlayerProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["saved_player_profile.v1"] = "saved_player_profile.v1"
    run_id: str
    branch_id: str
    saved_revision_id: str
    player_id: str
    source: Literal["selected_branch_saved_revision"] = "selected_branch_saved_revision"
    identity: SavedHomePlayerIdentity | None
    ranking_status: Literal["identity_unavailable", "unpublished", "ranked", "unranked"]
    ranking_week_ordinal: int | None = Field(default=None, ge=0, le=3049)
    rank: int | None = Field(default=None, ge=1)
    points: int | None = Field(default=None, ge=0)
    titles: int = Field(ge=0)
    final_appearances: int = Field(ge=0)
    tournament_results: tuple[SavedPlayerTournamentFinish, ...]
    total_tournament_results: int = Field(ge=0)


def resolve_saved_player_profile(
    *, run_id: str, branch_id: str, saved_revision_id: str,
    player_id: str, identities: SavedHomePlayerIdentities,
    ranking: RankingRevisionState | None,
    packages: RunPackageState | None,
) -> SavedPlayerProfile:
    if not player_id or len(player_id) > 128 or player_id.strip() != player_id:
        raise ValueError("Invalid player identifier")
    if (identities.run_id, identities.branch_id, identities.saved_revision_id) != (
        run_id, branch_id, saved_revision_id
    ) or identities.requested_ids != (player_id,):
        raise ValueError("Saved identity does not belong to selected Branch HEAD")
    if ranking is not None and (ranking.run_id, ranking.branch_id) != (run_id, branch_id):
        raise ValueError("Saved ranking belongs to another Run/Branch")
    if packages is not None and (packages.run_id, packages.branch_id) != (run_id, branch_id):
        raise ValueError("Saved Calendar belongs to another Run/Branch")

    identity = next((row for row in identities.players if row.player_id == player_id), None)
    common = dict(
        run_id=run_id, branch_id=branch_id, saved_revision_id=saved_revision_id,
        player_id=player_id, identity=identity,
    )
    # Without authoritative identity no sporting profile can be safely attributed.
    if identity is None:
        if identities.unresolved_ids != (player_id,):
            raise ValueError("Unresolved Saved player identity is inconsistent")
        return SavedPlayerProfile(
            **common, ranking_status="identity_unavailable",
            titles=0, final_appearances=0, tournament_results=(),
            total_tournament_results=0,
        )

    rank, points, ordinal = None, None, None
    ranking_status: Literal["unpublished", "ranked", "unranked"] = "unpublished"
    if ranking is not None and ranking.authoritative_transition_state is not None:
        transition = ranking.authoritative_transition_state
        if transition.get("world") is not None:
            published = resolve_viewer_official_ranking(ranking)
            if (published.product_run_id, published.viewer_branch_id) != (run_id, branch_id):
                raise ValueError("Saved ranking publication belongs to a foreign Branch")
            ordinal = published.week_ordinal
            if len({row.player_id for row in published.rows}) != len(published.rows):
                raise ValueError("Saved Official Ranking duplicates player identity")
            player_row = next((row for row in published.rows if row.player_id == player_id), None)
            ranking_status = "ranked" if player_row is not None else "unranked"
            if player_row is not None:
                rank, points = player_row.rank, player_row.points
        elif transition.get("publications"):
            raise ValueError("Saved ranking publications are missing public world HEAD")

    if packages is None:
        if ranking is not None and ranking.tournament_sources:
            raise ValueError("Saved tournament results have no Calendar authority")
        history = ()
    else:
        try:
            projected = resolve_viewer_tournament_history(
                run_package_state=packages, ranking=ranking,
                run_id=run_id, branch_id=branch_id,
            )
            if (projected.product_run_id, projected.viewer_branch_id) != (run_id, branch_id):
                raise ValueError("Saved tournament history belongs to a foreign Branch")
            history = projected.tournaments
        except KeyError as exc:
            if "no applied Calendar Package" not in str(exc):
                raise
            if ranking is not None and ranking.tournament_sources:
                raise ValueError("Saved results exist without Calendar authority") from exc
            history = ()

    finishes: list[SavedPlayerTournamentFinish] = []
    for item in history:
        if not item.result_published:
            continue
        if item.champion_player_id == player_id and item.finalist_player_id == player_id:
            raise ValueError("Champion cannot also be recorded as the runner-up")
        finish = ("champion" if item.champion_player_id == player_id else
                  "runner_up" if item.finalist_player_id == player_id else None)
        if finish is not None:
            finishes.append(SavedPlayerTournamentFinish(
                event_id=item.event_id, event_name=item.event_name,
                season=item.season, week=item.season_week, finish=finish,
            ))
    finishes.sort(key=lambda item: (item.season, item.week, item.event_id))
    return SavedPlayerProfile(
        **common, ranking_status=ranking_status, ranking_week_ordinal=ordinal,
        rank=rank, points=points,
        titles=sum(item.finish == "champion" for item in finishes),
        final_appearances=len(finishes),
        total_tournament_results=len(finishes),
        tournament_results=tuple(reversed(finishes[-10:])),
    )

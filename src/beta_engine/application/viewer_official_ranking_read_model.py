"""Historically faithful Viewer projection of the selected Branch's published ranking."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from beta_engine.domain.rankings.official import RankingWeek, load_official_ranking_snapshot
from beta_engine.domain.rankings.revision_state import RankingRevisionState


class ViewerOfficialRankingRow(BaseModel):
    rank: int = Field(ge=1)
    player_id: str = Field(min_length=1)
    points: int = Field(ge=0)


class ViewerOfficialRankingHistoryItem(BaseModel):
    season_index: int = Field(ge=0, le=49)
    week: int = Field(ge=1, le=61)
    week_ordinal: int = Field(ge=0, le=3049)
    snapshot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_id: str
    best_n: int = Field(ge=1)
    row_count: int = Field(ge=0)


class ViewerOfficialRankingHistory(BaseModel):
    schema_version: Literal["viewer_official_ranking_history.v1"] = "viewer_official_ranking_history.v1"
    product_run_id: str
    viewer_branch_id: str
    public_head_ordinal: int = Field(ge=0, le=3049)
    publication_count: int = Field(ge=0)
    publications: tuple[ViewerOfficialRankingHistoryItem, ...]


class ViewerOfficialRanking(BaseModel):
    schema_version: Literal["viewer_official_ranking.v1"] = "viewer_official_ranking.v1"
    product_run_id: str
    viewer_branch_id: str
    season_index: int = Field(ge=0, le=49)
    week: int = Field(ge=1, le=61)
    week_ordinal: int = Field(ge=0, le=3049)
    snapshot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_id: str
    best_n: int = Field(ge=1)
    row_count: int = Field(ge=0)
    rows: tuple[ViewerOfficialRankingRow, ...]


def _week_from_ordinal(ordinal: int) -> RankingWeek:
    if not 0 <= ordinal < 50 * 61:
        raise ValueError("Viewer ranking world head has invalid week ordinal")
    return RankingWeek(season_index=ordinal // 61, week=ordinal % 61 + 1)


def _saved_publications(state: RankingRevisionState) -> tuple[dict, list[dict]]:
    transition = state.authoritative_transition_state
    if transition is None or transition.get("world") is None:
        raise ValueError("Viewer Saved Revision has no published ranking world head")
    world = transition["world"]
    publications = transition["publications"]
    current = next(
        (row for row in publications if row["week_ordinal"] == world["current_ordinal"]),
        None,
    )
    if current is None or current["snapshot_fingerprint"] != world["ranking_fingerprint"]:
        raise ValueError("Viewer saved ranking publication does not match its public world head")
    return world, publications


def _project(state: RankingRevisionState, publication: dict) -> ViewerOfficialRanking:
    ordinal = publication["week_ordinal"]
    week = _week_from_ordinal(ordinal)
    snapshot = load_official_ranking_snapshot(
        publication["payload_json"],
        expected_fingerprint=publication["snapshot_fingerprint"],
        run_id=state.run_id, branch_id=state.branch_id, week=week,
    )
    rows = tuple(ViewerOfficialRankingRow(
        rank=row.rank, player_id=row.player_id, points=row.points
    ) for row in snapshot.rows)
    return ViewerOfficialRanking(
        product_run_id=state.run_id, viewer_branch_id=state.branch_id,
        season_index=week.season_index, week=week.week, week_ordinal=ordinal,
        snapshot_fingerprint=snapshot.fingerprint, policy_id=snapshot.policy.policy_id,
        best_n=snapshot.policy.best_n, row_count=len(rows), rows=rows,
    )


def resolve_viewer_official_ranking(state: RankingRevisionState | None) -> ViewerOfficialRanking:
    if state is None:
        raise ValueError("Viewer Saved Revision has no ranking component")
    world, publications = _saved_publications(state)
    publication = next(row for row in publications if row["week_ordinal"] == world["current_ordinal"] )
    return _project(state, publication)


def resolve_viewer_official_ranking_at(
    state: RankingRevisionState | None, *, week_ordinal: int
) -> ViewerOfficialRanking:
    if state is None:
        raise ValueError("Viewer Saved Revision has no ranking component")
    world, publications = _saved_publications(state)
    if week_ordinal > world["current_ordinal"]:
        raise ValueError("Viewer ranking detail cannot expose a future publication")
    publication = next((row for row in publications if row["week_ordinal"] == week_ordinal), None)
    if publication is None:
        raise ValueError("Viewer ranking publication does not exist at requested week")
    return _project(state, publication)


def resolve_viewer_official_ranking_history(
    state: RankingRevisionState | None,
) -> ViewerOfficialRankingHistory:
    if state is None:
        raise ValueError("Viewer Saved Revision has no ranking component")
    world, publications = _saved_publications(state)
    details = [
        _project(state, row) for row in reversed(publications)
        if row["week_ordinal"] <= world["current_ordinal"]
    ]
    return ViewerOfficialRankingHistory(
        product_run_id=state.run_id, viewer_branch_id=state.branch_id,
        public_head_ordinal=world["current_ordinal"], publication_count=len(details),
        publications=tuple(ViewerOfficialRankingHistoryItem(
            season_index=item.season_index, week=item.week, week_ordinal=item.week_ordinal,
            snapshot_fingerprint=item.snapshot_fingerprint, policy_id=item.policy_id,
            best_n=item.best_n, row_count=item.row_count,
        ) for item in details),
    )

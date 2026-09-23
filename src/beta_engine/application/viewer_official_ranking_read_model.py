"""Historically faithful Viewer projection of the selected Branch's published ranking."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.official import RankingWeek, load_official_ranking_snapshot
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    PublishedOfficialRankingModel,
)


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


def resolve_viewer_official_ranking(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
) -> ViewerOfficialRanking:
    """Read only the publication currently exposed by the authoritative world head.

    Later persisted publications are deliberately ignored. Viewer therefore cannot
    leak a ranking from a future week merely because such evidence exists in storage.
    """

    world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
    if world is None:
        raise ValueError("Viewer ranking has no authoritative published world head")

    week = _week_from_ordinal(world.current_ordinal)
    publication = session.get(
        PublishedOfficialRankingModel,
        (run_id, branch_id, world.current_ordinal),
    )
    if publication is None:
        raise ValueError("Viewer ranking publication is missing at the public world head")
    if publication.snapshot_fingerprint != world.ranking_fingerprint:
        raise ValueError("Viewer ranking publication does not match the public world head")

    snapshot = load_official_ranking_snapshot(
        publication.payload_json,
        expected_fingerprint=publication.snapshot_fingerprint,
        run_id=run_id,
        branch_id=branch_id,
        week=week,
    )
    rows = tuple(
        ViewerOfficialRankingRow(
            rank=row.rank,
            player_id=row.player_id,
            points=row.points,
        )
        for row in snapshot.rows
    )
    return ViewerOfficialRanking(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        season_index=week.season_index,
        week=week.week,
        week_ordinal=week.ordinal,
        snapshot_fingerprint=snapshot.fingerprint,
        policy_id=snapshot.policy.policy_id,
        best_n=snapshot.policy.best_n,
        row_count=len(rows),
        rows=rows,
    )


def resolve_viewer_official_ranking_at(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    week_ordinal: int,
) -> ViewerOfficialRanking:
    world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
    if world is None:
        raise ValueError("Viewer ranking has no authoritative published world head")
    if week_ordinal > world.current_ordinal:
        raise ValueError("Viewer ranking detail cannot expose a future publication")

    week = _week_from_ordinal(week_ordinal)
    publication = session.get(
        PublishedOfficialRankingModel,
        (run_id, branch_id, week_ordinal),
    )
    if publication is None:
        raise ValueError("Viewer ranking publication does not exist at requested week")
    if (
        week_ordinal == world.current_ordinal
        and publication.snapshot_fingerprint != world.ranking_fingerprint
    ):
        raise ValueError("Viewer ranking publication does not match the public world head")

    snapshot = load_official_ranking_snapshot(
        publication.payload_json,
        expected_fingerprint=publication.snapshot_fingerprint,
        run_id=run_id,
        branch_id=branch_id,
        week=week,
    )
    rows = tuple(
        ViewerOfficialRankingRow(rank=row.rank, player_id=row.player_id, points=row.points)
        for row in snapshot.rows
    )
    return ViewerOfficialRanking(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        season_index=week.season_index,
        week=week.week,
        week_ordinal=week.ordinal,
        snapshot_fingerprint=snapshot.fingerprint,
        policy_id=snapshot.policy.policy_id,
        best_n=snapshot.policy.best_n,
        row_count=len(rows),
        rows=rows,
    )


def resolve_viewer_official_ranking_history(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
) -> ViewerOfficialRankingHistory:
    current = resolve_viewer_official_ranking(
        session,
        run_id=run_id,
        branch_id=branch_id,
    )
    publications = session.scalars(
        select(PublishedOfficialRankingModel)
        .where(
            PublishedOfficialRankingModel.run_id == run_id,
            PublishedOfficialRankingModel.branch_id == branch_id,
            PublishedOfficialRankingModel.week_ordinal <= current.week_ordinal,
        )
        .order_by(PublishedOfficialRankingModel.week_ordinal.desc())
    ).all()

    items: list[ViewerOfficialRankingHistoryItem] = []
    for publication in publications:
        detail = resolve_viewer_official_ranking_at(
            session,
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=publication.week_ordinal,
        )
        items.append(
            ViewerOfficialRankingHistoryItem(
                season_index=detail.season_index,
                week=detail.week,
                week_ordinal=detail.week_ordinal,
                snapshot_fingerprint=detail.snapshot_fingerprint,
                policy_id=detail.policy_id,
                best_n=detail.best_n,
                row_count=detail.row_count,
            )
        )

    return ViewerOfficialRankingHistory(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        public_head_ordinal=current.week_ordinal,
        publication_count=len(items),
        publications=tuple(items),
    )

"""Historically scoped read model for visible pre-Tour prospects."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    RunBranchModel,
    RunProspectModel,
)
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle


class VisiblePreTourProspect(FrozenInput):
    player_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    short_name: str | None = None
    country_code: str = Field(min_length=1)
    country_name: str | None = None
    age: int = Field(ge=0, le=120)
    birth_year: int
    birth_year_week: int = Field(ge=1, le=61)
    lifecycle_status: Literal["active", "retired"]
    tour_status: Literal["pre_tour"] = "pre_tour"
    visible_since_week: RankingWeek


class VisiblePreTourProspects(FrozenInput):
    schema_version: Literal["visible_pre_tour_prospects.v1"] = (
        "visible_pre_tour_prospects.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RankingWeek
    lifecycle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=500)
    offset: int = Field(ge=0)
    prospects: tuple[VisiblePreTourProspect, ...]


def _current_week(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
) -> RankingWeek:
    world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
    if world is None:
        raise ValueError(
            "Canonical Viewer prospect state requires an authoritative world head"
        )
    if world.current_ordinal < 0:
        raise ValueError("Authoritative world ordinal is invalid")
    return RankingWeek(
        season_index=world.current_ordinal // 61,
        week=world.current_ordinal % 61 + 1,
    )


def resolve_visible_pre_tour_prospects(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    week: RankingWeek | None = None,
    limit: int = 100,
    offset: int = 0,
) -> VisiblePreTourProspects:
    """Resolve public prospect visibility from exact branch-owned lifecycle history.

    RunProspect rows are pregeneration metadata only. They may enrich a lifecycle
    identity that is already historically visible, but they never decide whether a
    player is visible.
    """

    if not 1 <= limit <= 500:
        raise ValueError("Prospect read model limit must be between 1 and 500")
    if offset < 0:
        raise ValueError("Prospect read model offset must be non-negative")

    branch = session.get(RunBranchModel, branch_id)
    if branch is None or branch.run_id != run_id:
        raise ValueError("Prospect read model Run/Branch scope is unavailable")

    target = week or _current_week(session, run_id=run_id, branch_id=branch_id)
    lifecycle = get_lifecycle(
        session,
        run_id=run_id,
        branch_id=branch_id,
        week=target,
    )
    if lifecycle is None:
        raise ValueError(
            "Prospect read model requires the exact historical lifecycle snapshot"
        )

    identities = tuple(
        player
        for player in lifecycle.players
        if player.tour_entry_week is None
        and player.origin.startswith("run_prospect:")
    )
    if not identities:
        return VisiblePreTourProspects(
            run_id=run_id,
            branch_id=branch_id,
            week=target,
            lifecycle_fingerprint=lifecycle.fingerprint,
            total=0,
            limit=limit,
            offset=offset,
            prospects=(),
        )

    ids = tuple(player.player_id for player in identities)
    rows = tuple(
        session.scalars(
            select(RunProspectModel)
            .where(
                RunProspectModel.run_id == run_id,
                RunProspectModel.prospect_id.in_(ids),
            )
            .order_by(RunProspectModel.prospect_id)
        )
    )
    by_id = {row.prospect_id: row for row in rows}
    if set(by_id) != set(ids):
        raise ValueError(
            "Visible lifecycle prospect is missing its Run prospect metadata"
        )

    prospects: list[VisiblePreTourProspect] = []
    for identity in identities:
        row = by_id[identity.player_id]
        visible_since = RankingWeek(
            season_index=row.season_start_year - 2000,
            week=row.season_week,
        )
        if visible_since.ordinal > target.ordinal:
            raise ValueError("Visible lifecycle prospect points to a future birth week")
        if (
            row.birth_year != identity.birth_year
            or row.birth_year_week != identity.birth_year_week
        ):
            raise ValueError(
                "Visible lifecycle prospect birth identity differs from Run metadata"
            )
        prospects.append(
            VisiblePreTourProspect(
                player_id=identity.player_id,
                display_name=row.display_name,
                short_name=row.short_name,
                country_code=row.country_code,
                country_name=row.country_name,
                age=identity.age,
                birth_year=identity.birth_year,
                birth_year_week=identity.birth_year_week,
                lifecycle_status=identity.status,
                visible_since_week=visible_since,
            )
        )

    ordered = tuple(
        sorted(
            prospects,
            key=lambda item: (
                item.country_code,
                item.display_name.casefold(),
                item.player_id,
            ),
        )
    )
    page = ordered[offset : offset + limit]
    return VisiblePreTourProspects(
        run_id=run_id,
        branch_id=branch_id,
        week=target,
        lifecycle_fingerprint=lifecycle.fingerprint,
        total=len(ordered),
        limit=limit,
        offset=offset,
        prospects=page,
    )

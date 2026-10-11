"""Canonical Season Summary / Closure Marker staging for Season Transition step 3."""

from sqlalchemy.orm import Session

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.season_closure import (
    SeasonClosureMarker,
    SeasonClosurePackage,
    bind_season_closure_marker,
    build_season_closure_package,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    BranchSavedRevisionModel,
    PublishedOfficialRankingModel,
)
from beta_engine.infrastructure.db.season_closing_rankings import (
    SeasonClosingRankingStore,
)


def resolve_canonical_season_closure_package(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    completed_week: RankingWeek,
) -> SeasonClosurePackage:
    """Resolve the current closure package from authoritative persisted Week-61 state.

    The current registry intentionally contains no season-scoped statistic component:
    no branch-scoped resettable statistic store is yet authoritative in this pipeline.
    This is explicit absence, not fabricated zero-valued statistics.
    """

    if completed_week.week != 61:
        raise ValueError("Season closure package requires completed Week 61")

    closing = SeasonClosingRankingStore(session).get(
        run_id=run_id,
        branch_id=branch_id,
        season_index=completed_week.season_index,
    )
    if closing is None or closing.completed_week != completed_week:
        raise ValueError(
            "Season closure package requires the staged Season Closing Ranking"
        )

    publication = session.get(
        PublishedOfficialRankingModel,
        (run_id, branch_id, completed_week.ordinal),
    )
    world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
    if (
        publication is None
        or publication.snapshot_fingerprint
        != closing.predecessor_official_fingerprint
        or world is None
        or world.current_ordinal != completed_week.ordinal
        or world.ranking_fingerprint
        != closing.predecessor_official_fingerprint
    ):
        raise ValueError(
            "Season closure package requires the authoritative Week 61 world head"
        )

    return build_season_closure_package(
        closing_ranking=closing,
        season_scoped_statistics=(),
    )


def bind_canonical_season_closure_marker(
    session: Session,
    package: SeasonClosurePackage,
    *,
    final_saved_revision_id: str,
) -> SeasonClosureMarker:
    """Bind the candidate to a revision already staged in the caller transaction.

    Persistence of the marker and revision-head activation deliberately belongs to
    the future atomic Season Transition writer so restore cannot strand stale markers.
    """

    revision = session.get(BranchSavedRevisionModel, final_saved_revision_id)
    if revision is None:
        raise ValueError("Season Closure Marker requires a staged Saved Revision")
    if (revision.run_id, revision.branch_id) != (
        package.summary.run_id,
        package.summary.branch_id,
    ):
        raise ValueError("Season Closure Marker Saved Revision scope mismatch")

    return bind_season_closure_marker(
        package.marker,
        final_saved_revision_id=final_saved_revision_id,
    )

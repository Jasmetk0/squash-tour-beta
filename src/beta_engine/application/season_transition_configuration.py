"""Canonical resolver for ordinary Season Transition policy/reset configuration."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.players.sporting import PlayerDevelopmentPolicy
from beta_engine.domain.rankings.official import OfficialRankingPolicy, RankingWeek
from beta_engine.domain.season_transition_configuration import (
    SeasonScopedResetCatalog,
    SeasonTransitionConfiguration,
    policy_fingerprint,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    BranchWorkingDraftModel,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.player_sporting_state import get_sporting


def _current_boundary(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
):
    run = session.get(RunContainerModel, run_id)
    branch = session.get(RunBranchModel, branch_id)
    draft = session.scalar(
        select(BranchWorkingDraftModel).where(
            BranchWorkingDraftModel.branch_id == branch_id
        )
    )
    if run is None or branch is None or draft is None or branch.run_id != run_id:
        raise ValueError("Season Transition configuration Run/Branch scope is unavailable")
    if run.read_only or branch.read_only or branch.status != "active":
        raise ValueError(
            "Season Transition configuration requires a writable active Run/Branch"
        )
    if draft.status != "clean" or draft.change_count != 0:
        raise ValueError(
            "Season Transition configuration requires a clean Working Draft"
        )
    if (
        not branch.saved_head_revision_id
        or draft.base_revision_id != branch.saved_head_revision_id
    ):
        raise ValueError(
            "Season Transition configuration requires the current Saved Revision head"
        )

    history = OfficialRankingCandidateStore(session).history(
        run_id=run_id,
        branch_id=branch_id,
    )
    predecessor = history[-1] if history else None
    if predecessor is None or predecessor.week.week != 61:
        raise ValueError(
            "Season Transition configuration requires the current Official Ranking Week 61 head"
        )
    if predecessor.week.season_index >= 49:
        raise ValueError("Final season has no incoming Season Transition configuration")

    publication = session.get(
        PublishedOfficialRankingModel,
        (run_id, branch_id, predecessor.week.ordinal),
    )
    world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
    if (
        publication is None
        or publication.snapshot_fingerprint != predecessor.fingerprint
        or publication.payload_json != predecessor.model_dump_json()
        or world is None
        or world.current_ordinal != predecessor.week.ordinal
        or world.ranking_fingerprint != predecessor.fingerprint
    ):
        raise ValueError(
            "Season Transition configuration requires the published authoritative Week 61 head"
        )

    sporting = get_sporting(
        session,
        run_id=run_id,
        branch_id=branch_id,
        week=predecessor.week,
    )
    if sporting is None:
        raise ValueError(
            "Season Transition configuration requires Week 61 player sporting state"
        )
    return run, branch, draft, predecessor, sporting


def resolve_season_transition_configuration(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    target_ranking_policy: OfficialRankingPolicy | None = None,
    target_development_policy: PlayerDevelopmentPolicy | None = None,
) -> SeasonTransitionConfiguration:
    """Build an immutable ordinary-rollover configuration from current W61 truth.

    Omitting a target policy means inheritance of the currently effective outgoing
    policy. Supplying a target policy explicitly replaces that proposal without
    changing the outgoing Week-61 evidence.
    """

    _, branch, _, predecessor, sporting = _current_boundary(
        session,
        run_id=run_id,
        branch_id=branch_id,
    )
    target_week = RankingWeek(
        season_index=predecessor.week.season_index + 1,
        week=1,
    )
    ranking_policy = target_ranking_policy or predecessor.policy
    development_policy = (
        target_development_policy or sporting.effective_development_policy
    )

    # No authoritative resettable season-stat producer exists in the current
    # canonical Run/Branch pipeline.  The registry is deliberately empty.
    reset_catalog = SeasonScopedResetCatalog(component_ids=())
    return SeasonTransitionConfiguration(
        run_id=run_id,
        branch_id=branch_id,
        base_revision_id=branch.saved_head_revision_id,
        completed_week=predecessor.week,
        target_week=target_week,
        predecessor_official_fingerprint=predecessor.fingerprint,
        predecessor_sporting_fingerprint=sporting.fingerprint,
        outgoing_ranking_policy_fingerprint=policy_fingerprint(predecessor.policy),
        target_ranking_policy=ranking_policy,
        outgoing_development_policy_fingerprint=policy_fingerprint(
            sporting.effective_development_policy
        ),
        target_development_policy=development_policy,
        reset_catalog=reset_catalog,
        provenance=(
            "Canonical ordinary Season Transition configuration resolved from "
            "published Week-61 Official Ranking, Week-61 sporting state and the "
            "current Saved Revision head"
        ),
    )


def validate_season_transition_configuration(
    session: Session,
    configuration: SeasonTransitionConfiguration,
) -> SeasonTransitionConfiguration:
    """Fail closed if any bound W61 authority or Saved Revision head has changed."""

    _, branch, _, predecessor, sporting = _current_boundary(
        session,
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
    )
    if (
        configuration.base_revision_id != branch.saved_head_revision_id
        or configuration.completed_week != predecessor.week
        or configuration.predecessor_official_fingerprint != predecessor.fingerprint
        or configuration.predecessor_sporting_fingerprint != sporting.fingerprint
        or configuration.outgoing_ranking_policy_fingerprint
        != policy_fingerprint(predecessor.policy)
        or configuration.outgoing_development_policy_fingerprint
        != policy_fingerprint(sporting.effective_development_policy)
    ):
        raise ValueError("Season Transition configuration is stale")
    return SeasonTransitionConfiguration.model_validate_json(
        configuration.model_dump_json()
    )

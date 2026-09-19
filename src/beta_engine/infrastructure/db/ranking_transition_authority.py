"""Persistence and validation for authoritative ranking boundary inputs."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.command_audit import RankingCommandAudit
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.domain.players.lifecycle import advance_lifecycle
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    BranchWorkingDraftModel,
    RankingTransitionAuthorityModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle




def derive_ranking_transition_authority(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    command_id: str,
    audit: RankingCommandAudit,
) -> RankingTransitionAuthority:
    """Freeze one normal-week ranking boundary from current canonical Run truth."""
    run = session.get(RunContainerModel, run_id)
    branch = session.get(RunBranchModel, branch_id)
    draft = session.scalar(
        select(BranchWorkingDraftModel).where(
            BranchWorkingDraftModel.branch_id == branch_id
        )
    )
    if run is None or branch is None or draft is None or branch.run_id != run_id:
        raise ValueError("Ranking transition authority Run/Branch scope is unavailable")
    if run.read_only or branch.read_only or branch.status != "active":
        raise ValueError(
            "Ranking transition authority requires a writable active Run/Branch"
        )
    if draft.status != "clean":
        raise ValueError(
            "Ranking transition authority requires a clean Working Draft"
        )
    if (
        not branch.saved_head_revision_id
        or draft.base_revision_id != branch.saved_head_revision_id
    ):
        raise ValueError(
            "Ranking transition authority requires the current Saved Revision head"
        )

    history = OfficialRankingCandidateStore(session).history(
        run_id=run_id,
        branch_id=branch_id,
    )
    predecessor = history[-1] if history else None
    if predecessor is None:
        raise ValueError("Ranking transition predecessor Official Ranking is missing")
    completed_week = predecessor.week
    if completed_week.week == 61:
        raise ValueError(
            "Week 61 rollover requires Season Transition authority, not Week Transition"
        )
    target_week = RankingWeek(
        season_index=completed_week.season_index,
        week=completed_week.week + 1,
    )

    world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
    if world is not None and (
        world.current_ordinal != completed_week.ordinal
        or world.ranking_fingerprint != predecessor.fingerprint
    ):
        raise ValueError(
            "Ranking transition predecessor Official Ranking differs from the authoritative world head"
        )

    lifecycle = get_lifecycle(
        session,
        run_id=run_id,
        branch_id=branch_id,
        week=completed_week,
    )
    if lifecycle is None:
        raise ValueError(
            "Ranking transition predecessor player lifecycle snapshot is missing"
        )

    target_roster = advance_lifecycle(lifecycle, target_week).ranking_roster()
    return RankingTransitionAuthority(
        run_id=run_id,
        branch_id=branch_id,
        base_revision_id=branch.saved_head_revision_id,
        completed_week=completed_week,
        target_week=target_week,
        players=target_roster,
        policy=predecessor.policy,
        provenance=(
            "Derived from canonical target-week player lifecycle and predecessor "
            "Official Ranking policy"
        ),
        adopted_by_command_id=command_id,
        audit=audit,
    )

def authority_carried_to_saved_head(session: Session, authority, branch, draft) -> bool:
    """Accept a newer base only when its saved payload carries the exact snapshot."""
    if draft.base_revision_id == authority.base_revision_id:
        return True
    from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
    from beta_engine.infrastructure.db.saved_revision_rankings import load_saved_ranking_component
    import json

    revision = session.get(BranchSavedRevisionModel, draft.base_revision_id)
    if revision is None or (revision.run_id, revision.branch_id) != (authority.run_id, authority.branch_id):
        return False
    state = load_saved_ranking_component(
        json.loads(revision.payload_json), run_id=authority.run_id, branch_id=authority.branch_id
    )
    return branch.saved_head_revision_id == draft.base_revision_id and state is not None and any(
        a.fingerprint == authority.fingerprint for a in state.transition_authorities
    )


class RankingTransitionAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def get(self, *, run_id: str, branch_id: str, target_ordinal: int):
        row = self.session.get(RankingTransitionAuthorityModel, (run_id, branch_id, target_ordinal))
        if row is None:
            return None
        value = RankingTransitionAuthority.model_validate_json(row.payload_json)
        if (value.run_id, value.branch_id, value.target_week.ordinal, value.fingerprint) != (run_id, branch_id, target_ordinal, row.fingerprint):
            raise ValueError("Ranking transition authority identity or fingerprint mismatch")
        return value

    def append(self, value: RankingTransitionAuthority):
        old = self.get(run_id=value.run_id, branch_id=value.branch_id, target_ordinal=value.target_week.ordinal)
        if old is not None:
            if old.fingerprint != value.fingerprint:
                raise ValueError("Ranking transition authority already exists with different inputs")
            return old
        self.session.add(RankingTransitionAuthorityModel(run_id=value.run_id, branch_id=value.branch_id,
            target_ordinal=value.target_week.ordinal, fingerprint=value.fingerprint, payload_json=value.model_dump_json()))
        self.session.flush()
        return value

    def history(self, *, run_id: str, branch_id: str):
        ordinals = self.session.scalars(select(RankingTransitionAuthorityModel.target_ordinal).where(
            RankingTransitionAuthorityModel.run_id == run_id, RankingTransitionAuthorityModel.branch_id == branch_id
        ).order_by(RankingTransitionAuthorityModel.target_ordinal)).all()
        return tuple(self.get(run_id=run_id, branch_id=branch_id, target_ordinal=o) for o in ordinals)

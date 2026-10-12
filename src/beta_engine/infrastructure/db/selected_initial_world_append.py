"""Guarded atomic replacement of pristine Week-1 projections for selected append.

This operation is intentionally unavailable after any ranking publication,
sporting event, week progression, or unsaved InitialWorld mutation.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.initial_world_state import get_initial_world
from beta_engine.infrastructure.db.player_lifecycle_state import (
    get_lifecycle, bootstrap_lifecycle, derive_bootstrap_lifecycle,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    get_sporting, bootstrap_sporting, derive_bootstrap_sporting,
)
from beta_engine.infrastructure.db.player_health_state import get_health, bootstrap_health
from beta_engine.domain.players.health import bootstrap_health_state
from beta_engine.infrastructure.db.models import (
    InitialWorldStateModel, PlayerLifecycleWeekStateModel, PlayerSportingWeekStateModel,
    PlayerHealthWeekStateModel, OfficialRankingCandidateModel, PublishedOfficialRankingModel,
    AuthoritativeWorldStateModel, AuthoritativeWorldEventModel,
    AuthoritativeWeekTransitionReceiptModel,
    # A saved first-season InitialWorld is no longer pristine once any of
    # these historical entry, ranking, match or Admin Health receipts exist.
    CompletedWeekSportingContextModel, PlayerHealthAdminEditReceiptModel,
    PlayerTourEntryTriggerModel, OfficialRankingResultVersionModel,
    OfficialRankingZeroVersionModel, TournamentRankingSnapshotAuthorityModel,
    OwnedTournamentRankingSourceModel,
)


def _has_scoped_row(session: Session, model: type, run_id: str, branch_id: str, *,
                    after_week_one: bool = False) -> bool:
    statement = select(model).where(model.run_id == run_id, model.branch_id == branch_id)
    if after_week_one:
        statement = statement.where(model.week_ordinal > 0)
    return session.scalars(statement.limit(1)).first() is not None


def require_pristine_initial_world_append_eligible(
    session: Session, *, previous: InitialWorldState
) -> tuple:
    """Read-only authoritative eligibility check, shared by preview and commit.

    The committing caller must run this again inside BEGIN IMMEDIATE.
    """
    run_id, branch_id = previous.run_id, previous.branch_id
    incumbent = {p.player_id: p for p in previous.players}
    # A successful entry, ranking-source, Week-1 Health correction or completed
    # sporting context is historical evidence even if the current Week-1 payload
    # happens to match a pristine bootstrap after another operation. Do not erase
    # such authority by replacing the opening population.
    for model in (
        OfficialRankingCandidateModel, PublishedOfficialRankingModel,
        OfficialRankingResultVersionModel, OfficialRankingZeroVersionModel,
        TournamentRankingSnapshotAuthorityModel, OwnedTournamentRankingSourceModel,
        AuthoritativeWorldStateModel, AuthoritativeWorldEventModel,
        AuthoritativeWeekTransitionReceiptModel, CompletedWeekSportingContextModel,
        PlayerHealthAdminEditReceiptModel, PlayerTourEntryTriggerModel,
    ):
        if _has_scoped_row(session, model, run_id, branch_id):
            raise ValueError("Selected append is closed after ranking or sporting activity")
    for model in (PlayerLifecycleWeekStateModel, PlayerSportingWeekStateModel,
                  PlayerHealthWeekStateModel):
        if _has_scoped_row(session, model, run_id, branch_id, after_week_one=True):
            raise ValueError("Selected append cannot rewrite later-week player history")

    week = RankingWeek(season_index=0, week=1)
    lifecycle = get_lifecycle(session, run_id=run_id, branch_id=branch_id, week=week)
    sporting = get_sporting(session, run_id=run_id, branch_id=branch_id, week=week)
    health = get_health(session, run_id=run_id, branch_id=branch_id, week=week)
    if lifecycle is None or sporting is None or health is None:
        raise ValueError("Existing Week-1 lifecycle, sporting and health evidence is required")
    expected_ids = set(incumbent)
    if (
        lifecycle.source_initial_world_fingerprint != previous.fingerprint or
        sporting.source_initial_world_fingerprint != previous.fingerprint or
        health.source_initial_world_fingerprint != previous.fingerprint or
        {p.player_id for p in lifecycle.players} != expected_ids or
        {p.player_id for p in sporting.players} != expected_ids or
        {p.player_id for p in health.players} != expected_ids or
        sporting.completed_context_fingerprint != "bootstrap:not-a-completed-week" or
        any(p.origin != f"initial_world:{previous.fingerprint}" for p in lifecycle.players)
    ):
        raise ValueError("Week-1 evidence changed or does not match the saved InitialWorld")

    # Reject validly checksummed but already edited Week-1 player records:
    # a roster/fingerprint-source comparison alone would silently erase them.
    expected_health = bootstrap_health_state(
        run_id=run_id, branch_id=branch_id,
        source_initial_world_fingerprint=previous.fingerprint,
        player_ids=tuple(p.player_id for p in previous.players),
    )
    if (
        lifecycle.fingerprint != derive_bootstrap_lifecycle(
            previous, lifecycle.policy
        ).fingerprint or
        sporting.fingerprint != derive_bootstrap_sporting(
            previous, sporting.effective_development_policy
        ).fingerprint or
        health.fingerprint != expected_health.fingerprint
    ):
        raise ValueError("Week-1 player evidence has non-bootstrap edits; append is closed")
    return lifecycle, sporting, health



def replace_pristine_initial_world_for_selected_append(
    session: Session, *, previous: InitialWorldState, appended: InitialWorldState
) -> InitialWorldState:
    """Verify untouched Week 1 and install a complete consistent new projection.

    Caller owns BEGIN IMMEDIATE, Saved HEAD/Draft/World and old-state CAS checks.
    Failures roll back every table together. No historical Saved Revision is edited.
    """
    if (previous.run_id, previous.branch_id) != (appended.run_id, appended.branch_id):
        raise ValueError("Selected append ownership mismatch")
    run_id, branch_id = previous.run_id, previous.branch_id
    row = session.get(InitialWorldStateModel, (run_id, branch_id))
    original = get_initial_world(session, run_id=run_id, branch_id=branch_id)
    if row is None or original is None or original.fingerprint != previous.fingerprint:
        raise ValueError("Original InitialWorld changed before append")
    incumbent = {p.player_id: p for p in previous.players}
    updated = {p.player_id: p for p in appended.players}
    if not incumbent.keys() <= updated.keys() or any(updated[k] != v for k,v in incumbent.items()):
        raise ValueError("Selected append cannot mutate any existing player")

    lifecycle, sporting, health = require_pristine_initial_world_append_eligible(
        session, previous=previous
    )
    week = RankingWeek(season_index=0, week=1)

    # All of these mutations occur inside the same SQLite BEGIN IMMEDIATE.
    session.delete(session.get(PlayerLifecycleWeekStateModel,(run_id,branch_id,week.ordinal)))
    session.delete(session.get(PlayerSportingWeekStateModel,(run_id,branch_id,week.ordinal)))
    session.delete(session.get(PlayerHealthWeekStateModel,(run_id,branch_id,week.ordinal)))
    session.flush()
    row.fingerprint = appended.fingerprint
    row.payload_json = appended.model_dump_json()
    session.flush()
    bootstrap_lifecycle(session, appended, lifecycle.policy)
    bootstrap_sporting(session, appended, sporting.effective_development_policy)
    bootstrap_health(session, appended)
    persisted = get_initial_world(session, run_id=run_id, branch_id=branch_id)
    if persisted is None or persisted.fingerprint != appended.fingerprint:
        raise ValueError("Selected append write could not be verified")
    return persisted

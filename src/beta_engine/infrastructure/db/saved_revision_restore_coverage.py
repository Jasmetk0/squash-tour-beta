"""Central Saved Revision restore coverage registry.

This module is deliberately about persistence integrity, not product policy.  Every
authoritative Run/Branch row family captured by a Saved Revision component is
registered once here so restore preflight can fail closed when live state exists
outside the current saved head.  Transient authoring rows that are intentionally not
Saved Revision content are registered separately and block restore while present.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from beta_engine.infrastructure.db.application_validation_slots import (
    APPLICATION_VALIDATION_SLOT_COMPONENT_KEY,
)
from beta_engine.infrastructure.db.definitive_wild_card_assignments import (
    DEFINITIVE_WILD_CARD_ASSIGNMENT_COMPONENT_KEY,
)
from beta_engine.infrastructure.db.initial_world_state import INITIAL_WORLD_COMPONENT_KEY
from beta_engine.infrastructure.db.models import (
    AdoptedTournamentAuthorityModel,
    AuthoritativeSimulationCommandModel,
    AuthoritativeWeekTransitionReceiptModel,
    AuthoritativeWorldEventModel,
    AuthoritativeWorldStateModel,
    CompletedWeekSportingContextModel,
    DefinitiveWildCardAssignmentAuthorityModel,
    InitialWorldStateModel,
    OfficialRankingCandidateModel,
    OfficialRankingCommandModel,
    OfficialRankingResultVersionModel,
    OfficialRankingZeroVersionModel,
    OwnedTournamentRankingSourceModel,
    PlayerLifecycleWeekStateModel,
    PlayerSportingWeekStateModel,
    PlayerTourEntryTriggerModel,
    PublishedOfficialRankingModel,
    RankingTransitionAuthorityModel,
    ResolvedApplicationValidationSlotModel,
    RunEntryDecisionSlotAuthorityModel,
    SeasonClosingRankingModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    StandaloneMatchWorkspaceModel,
    TournamentApplicationSubmissionAuthorityModel,
    TournamentDrawAuthorityModel,
    TournamentDrawInputAuthorityModel,
    TournamentDrawProcessAuthorityModel,
    TournamentDrawRevisionModel,
    TournamentEntryFieldVersionModel,
    TournamentRankingSnapshotAuthorityModel,
    TournamentWildCardAuthorityModel,
    WeekSimulationScheduleModel,
)
from beta_engine.infrastructure.db.player_lifecycle_state import (
    PLAYER_LIFECYCLE_COMPONENT_KEY,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    PLAYER_SPORTING_COMPONENT_KEY,
)
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PLAYER_TOUR_ENTRY_COMPONENT_KEY,
)
from beta_engine.infrastructure.db.run_entry_decision_slots import (
    RUN_ENTRY_DECISION_SLOT_COMPONENT_KEY,
)
from beta_engine.infrastructure.db.saved_revision_rankings import RANKING_COMPONENT_KEY
from beta_engine.infrastructure.db.saved_revision_season_closure import (
    SEASON_CLOSURE_COMPONENT_KEY,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    COMPONENT_KEY as SIMULATION_SLOT_COMPONENT_KEY,
)
from beta_engine.infrastructure.db.tournament_application_submissions import (
    TOURNAMENT_APPLICATION_SUBMISSION_COMPONENT_KEY,
)


@dataclass(frozen=True)
class SavedRevisionComponentCoverage:
    component_key: str
    label: str
    models: tuple[type[Any], ...]


@dataclass(frozen=True)
class RestoreTransientBlocker:
    label: str
    models: tuple[type[Any], ...]


COMPONENT_COVERAGE: tuple[SavedRevisionComponentCoverage, ...] = (
    SavedRevisionComponentCoverage(
        component_key=RANKING_COMPONENT_KEY,
        label="complete ranking preparation state",
        models=(
            OfficialRankingCandidateModel,
            OfficialRankingCommandModel,
            OfficialRankingResultVersionModel,
            OfficialRankingZeroVersionModel,
            OwnedTournamentRankingSourceModel,
            RankingTransitionAuthorityModel,
            TournamentRankingSnapshotAuthorityModel,
            SeasonClosingRankingModel,
            AuthoritativeWorldStateModel,
            PublishedOfficialRankingModel,
            AuthoritativeWeekTransitionReceiptModel,
            AuthoritativeWorldEventModel,
        ),
    ),
    SavedRevisionComponentCoverage(
        component_key=INITIAL_WORLD_COMPONENT_KEY,
        label="initial world",
        models=(InitialWorldStateModel,),
    ),
    SavedRevisionComponentCoverage(
        component_key=PLAYER_LIFECYCLE_COMPONENT_KEY,
        label="player lifecycle state",
        models=(PlayerLifecycleWeekStateModel,),
    ),
    SavedRevisionComponentCoverage(
        component_key=RUN_ENTRY_DECISION_SLOT_COMPONENT_KEY,
        label="Run entry-decision slots",
        models=(RunEntryDecisionSlotAuthorityModel,),
    ),
    SavedRevisionComponentCoverage(
        component_key=APPLICATION_VALIDATION_SLOT_COMPONENT_KEY,
        label="application validation slots",
        models=(ResolvedApplicationValidationSlotModel,),
    ),
    SavedRevisionComponentCoverage(
        component_key=TOURNAMENT_APPLICATION_SUBMISSION_COMPONENT_KEY,
        label="tournament application submissions",
        models=(TournamentApplicationSubmissionAuthorityModel,),
    ),
    SavedRevisionComponentCoverage(
        component_key=DEFINITIVE_WILD_CARD_ASSIGNMENT_COMPONENT_KEY,
        label="definitive Wild Card assignments",
        models=(DefinitiveWildCardAssignmentAuthorityModel,),
    ),
    SavedRevisionComponentCoverage(
        component_key=PLAYER_TOUR_ENTRY_COMPONENT_KEY,
        label="player Tour-entry triggers",
        models=(PlayerTourEntryTriggerModel,),
    ),
    SavedRevisionComponentCoverage(
        component_key=PLAYER_SPORTING_COMPONENT_KEY,
        label="player sporting state",
        models=(
            PlayerSportingWeekStateModel,
            CompletedWeekSportingContextModel,
        ),
    ),
    SavedRevisionComponentCoverage(
        component_key=SIMULATION_SLOT_COMPONENT_KEY,
        label="authoritative simulation state",
        models=(
            SimulationSlotModel,
            SimulationEventGroupModel,
            AuthoritativeSimulationCommandModel,
            AdoptedTournamentAuthorityModel,
            WeekSimulationScheduleModel,
            TournamentEntryFieldVersionModel,
            TournamentWildCardAuthorityModel,
            TournamentDrawInputAuthorityModel,
            TournamentDrawAuthorityModel,
            TournamentDrawRevisionModel,
            TournamentDrawProcessAuthorityModel,
        ),
    ),
)

TRANSIENT_RESTORE_BLOCKERS: tuple[RestoreTransientBlocker, ...] = (
    RestoreTransientBlocker(
        label="standalone match authoring workspace",
        models=(StandaloneMatchWorkspaceModel,),
    ),
)

SUPPORTED_CONTENT_KEYS = frozenset(
    {
        *(coverage.component_key for coverage in COMPONENT_COVERAGE),
        SEASON_CLOSURE_COMPONENT_KEY,
    }
)


def _has_scoped_rows(session, model: type[Any], *, run_id: str, branch_id: str) -> bool:
    return (
        session.scalar(
            select(model.run_id)
            .where(model.run_id == run_id, model.branch_id == branch_id)
            .limit(1)
        )
        is not None
    )


def missing_component_coverage(
    session,
    *,
    run_id: str,
    branch_id: str,
    saved_content: dict,
) -> tuple[SavedRevisionComponentCoverage, ...]:
    """Return component families with live rows absent from the current saved head."""

    return tuple(
        coverage
        for coverage in COMPONENT_COVERAGE
        if coverage.component_key not in saved_content
        and any(
            _has_scoped_rows(session, model, run_id=run_id, branch_id=branch_id)
            for model in coverage.models
        )
    )


def active_transient_restore_blockers(
    session,
    *,
    run_id: str,
    branch_id: str,
) -> tuple[RestoreTransientBlocker, ...]:
    """Return unsaved authoring state that cannot cross a historical restore."""

    return tuple(
        blocker
        for blocker in TRANSIENT_RESTORE_BLOCKERS
        if any(
            _has_scoped_rows(session, model, run_id=run_id, branch_id=branch_id)
            for model in blocker.models
        )
    )

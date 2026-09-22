"""Run/Branch-owned orchestration over the authoritative Simulation Slot ledger.

Canonical Run-owned Draw authority is the preferred tournament topology source.
Legacy MatchPackage data remains a temporary execution/result payload and historical
compatibility reader; legacy producer files are not execution state.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import Field, model_validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeTournamentResult,
    AuthoritativeSlotMatchExecutor,
    build_authoritative_tournament_ranking_packages,
    build_run_owned_tournament_authorities,
    validate_adopted_four_player_match_package,
)
from beta_engine.application.canonical_tournament_topology import (
    project_canonical_draw_to_match_topology,
)
from beta_engine.application.final_season_transition import (
    FinalSeasonTransitionCommand,
    FinalSeasonTransitionResult,
    commit_final_season_transition,
)
from beta_engine.application.ordinary_season_transition import (
    OrdinarySeasonTransitionCommand,
    OrdinarySeasonTransitionResult,
    commit_ordinary_season_transition,
)
from beta_engine.application.season_closing_ranking_resolution import (
    resolve_canonical_season_closing_ranking,
)
from beta_engine.application.season_transition_configuration import (
    resolve_season_transition_configuration,
)
from beta_engine.application.season_transition_lifecycle import (
    resolve_season_transition_lifecycle,
)
from beta_engine.application.season_transition_ranking import (
    resolve_season_transition_ranking,
)
from beta_engine.application.season_transition_sporting import (
    resolve_season_transition_sporting,
)
from beta_engine.application.run_owned_match_package import (
    build_run_owned_match_package,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    prepare_canonical_tournament_ranking_sources,
    prepare_final_season_closing_ranking_results,
    prepare_tournament_ranking_sources,
)
from beta_engine.application.season_entry_batch_service import (
    EntryBatchGenerateRequest,
    SeasonEntryBatchService,
)
from beta_engine.application.run_entry_decision_slot import (
    freeze_entry_batch_proposal_as_run_slot,
)
from beta_engine.domain.tournaments.application_validation_authority import (
    ResolvedApplicationValidationSlot,
    TournamentApplicationValidationAuthority,
)
from beta_engine.infrastructure.db.application_validation_slots import (
    ApplicationValidationSlotStore,
    record_resolved_application_validation_slot,
)
from beta_engine.application.season_match_service import (
    FrozenQualifierPromotion,
    SeasonEventMatchPackage,
    SeasonMatchService,
)
from beta_engine.application.season_point_awards_service import (
    FrozenPointAwardAuthority,
    SeasonPointAwardsService,
)
from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    CompetitiveMatchCount,
)
from beta_engine.domain.rankings.command_audit import RankingCommandAudit
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.domain.simulation_slots import (
    SimulationMatchEventPlan,
    WeekSimulationSchedule,
    WeekSimulationScheduleSlot,
    fingerprint,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel,
    AuthoritativeWorldStateModel,
    AdoptedTournamentAuthorityModel,
    BranchSavedRevisionModel,
    BranchWorkingDraftModel,
    PlayerSportingWeekStateModel,
    RankingTransitionAuthorityModel,
    ResolvedApplicationValidationSlotModel,
    RunBranchModel,
    RunContainerModel,
    RunEntryDecisionSlotAuthorityModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    TournamentDrawAuthorityModel,
    TournamentEntryFieldVersionModel,
    WeekSimulationScheduleModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.run_entry_decision_slots import (
    RunEntryDecisionSlotStore,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.week_tournament_lock import (
    WeekTournamentLockStore,
    derive_week_tournament_lock_authority,
    resolve_week_tournament_lock_evidence,
)
from beta_engine.infrastructure.db.tournament_walkover_authority import (
    TournamentWalkoverAuthorityStore,
)
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
from beta_engine.infrastructure.db.player_sporting_state import (
    get_completed_context,
    get_sporting,
    preflight_completed_context_from_authoritative_matches,
    put_completed_context,
)
from beta_engine.infrastructure.db.authoritative_week_transition import (
    AuthoritativeWeekTransitionRunner,
    derive_persisted_week_transition_command,
    preview_persisted_week_transition,
)
from beta_engine.infrastructure.db.ranking_transition_authority import (
    RankingTransitionAuthorityStore,
    derive_ranking_transition_authority,
)
from beta_engine.application.authoritative_week_transition import (
    AuthoritativeWeekTransitionCommand,
)


AUTHORITATIVE_EMPTY_WEEK_PROVENANCE = (
    "explicit Run/Branch empty-week completion against frozen season Calendar authority"
)


class AuthoritativeEmptyWeekCompletionCommand(FrozenInput):
    """CAS-guarded proof that one canonical week contains no competitive work."""

    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)
    operator_label: str = Field(min_length=1, max_length=200)
    audit_reason: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def trim_audit(self):
        operator = self.operator_label.strip()
        reason = self.audit_reason.strip()
        if not operator or not reason:
            raise ValueError("empty-week operator and audit reason must be non-empty")
        object.__setattr__(self, "operator_label", operator)
        object.__setattr__(self, "audit_reason", reason)
        return self

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class AuthoritativeSimulationCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)
    group_id: str | None = None

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class AuthoritativeMatchDayCommand(FrozenInput):
    """Resumable CAS-guarded orchestration of the current canonical Match Day."""

    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class AuthoritativeRoundCommand(FrozenInput):
    """Resumable CAS-guarded orchestration of the nearest unfinished round."""

    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class AuthoritativeTournamentCommand(FrozenInput):
    """Resumable CAS-guarded orchestration of the current canonical tournament."""

    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class AuthoritativeWeekPreviewRequest(FrozenInput):
    """Read-only review request for the full current-week canonical range."""

    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    operator_label: str = Field(min_length=1, max_length=128)
    audit_reason: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def trim_audit(self):
        operator = self.operator_label.strip()
        reason = self.audit_reason.strip()
        if not operator or not reason:
            raise ValueError("Next Week operator and audit reason must be non-empty")
        object.__setattr__(self, "operator_label", operator)
        object.__setattr__(self, "audit_reason", reason)
        return self

    @property
    def audit(self) -> RankingCommandAudit:
        return RankingCommandAudit(
            actor_label=self.operator_label,
            reason=self.audit_reason,
        )


class AuthoritativeWeekCommand(AuthoritativeWeekPreviewRequest):
    """Reviewed resumable orchestration through the next Week Transition."""

    expected_week: RankingWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)
    expected_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class AuthoritativeSeasonPreviewRequest(FrozenInput):
    """Reviewed progressive orchestration request through one season boundary."""

    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    operator_label: str = Field(min_length=1, max_length=128)
    audit_reason: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def trim_audit(self):
        operator = self.operator_label.strip()
        reason = self.audit_reason.strip()
        if not operator or not reason:
            raise ValueError("Next Season operator and audit reason must be non-empty")
        object.__setattr__(self, "operator_label", operator)
        object.__setattr__(self, "audit_reason", reason)
        return self


class AuthoritativeSeasonCommand(AuthoritativeSeasonPreviewRequest):
    """Durable progressive parent that reaches the next Season boundary."""

    expected_start_week: RankingWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)
    expected_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))



class MatchReconstructionGameScore(FrozenInput):
    """Exact game score in frozen player-A / player-B order."""

    player_a_points: int = Field(ge=0)
    player_b_points: int = Field(ge=0)


class MatchReconstructionConstraints(FrozenInput):
    """Deliberately small hard-constraint catalog for minimum pre-alpha reconstruction."""

    winner_player_id: str | None = Field(default=None, min_length=1)
    player_a_sets_won: int | None = Field(default=None, ge=0)
    player_b_sets_won: int | None = Field(default=None, ge=0)
    exact_game_scores: tuple[MatchReconstructionGameScore, ...] = ()

    @model_validator(mode="after")
    def validate_minimum_catalog(self):
        one_sets_value = (self.player_a_sets_won is None) != (
            self.player_b_sets_won is None
        )
        if one_sets_value:
            raise ValueError(
                "exact match score requires both player_a_sets_won and player_b_sets_won"
            )
        if (
            self.winner_player_id is None
            and self.player_a_sets_won is None
            and not self.exact_game_scores
        ):
            raise ValueError("at least one reconstruction hard constraint is required")
        if (
            self.exact_game_scores
            and self.player_a_sets_won is not None
            and self.player_b_sets_won is not None
            and len(self.exact_game_scores)
            != self.player_a_sets_won + self.player_b_sets_won
        ):
            raise ValueError(
                "exact game-score count must equal the exact match-score set count"
            )
        return self

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class AuthoritativeMatchReconstructionPreviewRequest(FrozenInput):
    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)
    group_id: str = Field(min_length=1)
    candidate_count: int = Field(default=10, ge=1, le=20)
    constraints: MatchReconstructionConstraints


class AuthoritativeMatchReconstructionCommitCommand(
    AuthoritativeMatchReconstructionPreviewRequest
):
    command_id: str = Field(min_length=1, max_length=128)
    expected_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_candidate_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator_label: str = Field(min_length=1, max_length=200)
    audit_reason: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def trim_audit(self):
        operator = self.operator_label.strip()
        reason = self.audit_reason.strip()
        if not operator or not reason:
            raise ValueError("reconstruction operator and audit reason must be non-empty")
        object.__setattr__(self, "operator_label", operator)
        object.__setattr__(self, "audit_reason", reason)
        return self

    def preview_request(self) -> AuthoritativeMatchReconstructionPreviewRequest:
        return AuthoritativeMatchReconstructionPreviewRequest(
            run_id=self.run_id,
            branch_id=self.branch_id,
            expected_week=self.expected_week,
            expected_position_fingerprint=self.expected_position_fingerprint,
            expected_revision_id=self.expected_revision_id,
            group_id=self.group_id,
            candidate_count=self.candidate_count,
            constraints=self.constraints,
        )


class AuthoritativeWalkoverCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)
    group_id: str = Field(min_length=1)
    withdrawn_player_id: str = Field(min_length=1)

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class AuthoritativeEntryDecisionSlotCommand(FrozenInput):
    """Guarded commit of one shared-snapshot Entry decision Simulation Slot."""

    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_revision_id: str = Field(min_length=1)
    decision_slot_ordinal: int = Field(ge=1)
    event_ids: tuple[str, ...] = Field(min_length=1)
    seed: int = 12345
    expected_entry_batch_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_slot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def canonical_events(self):
        if self.event_ids != tuple(sorted(set(self.event_ids))):
            raise ValueError("Entry decision command event IDs must be canonical and unique")
        return self

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class AuthoritativeWeekTournamentLockSelection(FrozenInput):
    player_id: str = Field(min_length=1)
    selected_event_id: str = Field(min_length=1)


class AuthoritativeWeekTournamentLockPreviewRequest(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)
    operator_label: str = Field(min_length=1, max_length=128)
    audit_reason: str = Field(min_length=1, max_length=2000)
    selections: tuple[AuthoritativeWeekTournamentLockSelection, ...] = Field(
        min_length=1
    )

    @model_validator(mode="after")
    def validate_lock_request(self):
        operator = self.operator_label.strip()
        reason = self.audit_reason.strip()
        if not operator or operator != self.operator_label:
            raise ValueError("Week Tournament Lock operator label must be trimmed")
        if not reason or reason != self.audit_reason:
            raise ValueError("Week Tournament Lock audit reason must be trimmed")
        players = tuple(item.player_id for item in self.selections)
        if players != tuple(sorted(set(players))):
            raise ValueError(
                "Week Tournament Lock selections must use canonical unique player order"
            )
        return self

    @property
    def selections_by_player(self) -> dict[str, str]:
        return {
            item.player_id: item.selected_event_id for item in self.selections
        }


class AuthoritativeWeekTournamentLockCommitCommand(
    AuthoritativeWeekTournamentLockPreviewRequest
):
    expected_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class AuthoritativeApplicationValidationCommand(FrozenInput):
    """Guarded complete validation outcome for one persisted Entry decision slot."""

    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_revision_id: str = Field(min_length=1)
    decision_slot_ordinal: int = Field(ge=1)
    expected_entry_slot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    validations: tuple[TournamentApplicationValidationAuthority, ...]

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


EXPLICIT_ADMIN_APPLICATION_VALIDATION_POLICY_ID = (
    "explicit_admin_application_validation.v1"
)
EXPLICIT_ADMIN_APPLICATION_VALIDATION_POLICY_FINGERPRINT = fingerprint(
    {
        "policy_id": EXPLICIT_ADMIN_APPLICATION_VALIDATION_POLICY_ID,
        "resolution_mode": "explicit_admin_review",
        "automatic_eligibility_rules": False,
        "automatic_deadline_rules": False,
    }
)


class AuthoritativeApplicationValidationReview(FrozenInput):
    """Minimal Admin verdict over one frozen Entry decision.

    The browser supplies only the reviewed outcome and, for rejection, canonical
    reasons. Scope, source evidence, application identity and NR tie-break truth are
    reconstructed from persisted Run state by the server.
    """

    event_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    outcome: Literal["valid", "invalid"]
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_review(self):
        if any(not reason.strip() or reason != reason.strip() for reason in self.reasons):
            raise ValueError("Application validation review reasons must be trimmed and non-blank")
        if self.reasons != tuple(sorted(set(self.reasons))):
            raise ValueError("Application validation review reasons must be unique and canonical")
        if self.outcome == "valid" and self.reasons:
            raise ValueError("Valid explicit application review must not carry rejection reasons")
        if self.outcome == "invalid" and not self.reasons:
            raise ValueError("Invalid explicit application review requires at least one reason")
        return self

    @property
    def key(self) -> tuple[str, str]:
        return (self.event_id, self.player_id)


class AuthoritativeExplicitApplicationValidationCommand(FrozenInput):
    """CAS-guarded explicit Admin resolution of the current Entry slot."""

    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_revision_id: str = Field(min_length=1)
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision_slot_ordinal: int = Field(ge=1)
    expected_entry_slot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator_label: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)
    reviews: tuple[AuthoritativeApplicationValidationReview, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_command(self):
        if self.operator_label != self.operator_label.strip():
            raise ValueError("Application validation operator label must be trimmed")
        if self.reason != self.reason.strip():
            raise ValueError("Application validation audit reason must be trimmed")
        keys = tuple(review.key for review in self.reviews)
        if keys != tuple(sorted(keys)):
            raise ValueError("Application validation reviews must use canonical event/player order")
        if len(set(keys)) != len(keys):
            raise ValueError("Application validation reviews contain duplicate decisions")
        return self

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class _AdoptedTournamentEvidence(FrozenInput):
    """One immutable tournament entry inside adopted week authority."""

    event_id: str = Field(min_length=1)
    package: SeasonEventMatchPackage | None = None
    calendar_event: CalendarEvent | None = None
    point_award_authority: FrozenPointAwardAuthority | None = None
    draw_authority_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )


class AuthoritativeSeasonTransitionPreflight(FrozenInput):
    schema_version: Literal["authoritative_season_transition_preflight.v1"] = (
        "authoritative_season_transition_preflight.v1"
    )
    run_id: str
    branch_id: str
    completed_week: RankingWeek
    target_week: RankingWeek | None
    final_season: bool
    saved_revision_id: str | None
    draft_version: int | None = None
    default_closing_ranking_fingerprint: str | None = None
    default_configuration_fingerprint: str | None = None
    default_sporting_fingerprint: str | None = None
    default_lifecycle_fingerprint: str | None = None
    default_ranking_fingerprint: str | None = None
    position_fingerprint: str
    state_blockers: tuple[str, ...] = ()
    implementation_gaps: tuple[str, ...] = ()
    ready_for_execution: bool = False
    preflight_fingerprint: str


class AuthoritativeSimulationPosition(FrozenInput):
    run_id: str
    branch_id: str
    current_week: RankingWeek
    current_slot_kind: Literal["entry", "match"] | None = None
    current_slot_id: str | None
    slot_ordinal: int | None
    unresolved_group_ids: tuple[str, ...]
    eligible_match_ids: tuple[str, ...]
    blocked_match_ids: tuple[str, ...]
    current_slot_complete: bool
    supported_tournament_complete: bool
    week_ready_for_transition: bool
    transition_blockers: tuple[str, ...] = ()
    terminal_sporting_fingerprint: str | None
    position_fingerprint: str


@dataclass(slots=True)
class AuthoritativeRunSimulationDriver:
    factory: sessionmaker[Session]
    match_service: SeasonMatchService
    awards_service: SeasonPointAwardsService

    def position(
        self, *, run_id: str, branch_id: str
    ) -> AuthoritativeSimulationPosition:
        with self.factory() as session:
            return self._position(session, run_id, branch_id)

    def complete_empty_week(
        self, command: AuthoritativeEmptyWeekCompletionCommand
    ) -> dict:
        """Persist explicit zero-match evidence only for a provably empty week."""

        request_fp = fingerprint(
            {
                "mode": "authoritative_empty_week_completion.v1",
                "command": command.model_dump(mode="json"),
            }
        )
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            key = (command.run_id, command.branch_id, command.command_id)
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt is not None:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError(
                        "empty-week command ID already has a different request"
                    )
                if receipt.status != "complete":
                    raise ValueError("empty-week command receipt is incomplete")
                return json.loads(receipt.result_json)

            before = self._position(
                session,
                command.run_id,
                command.branch_id,
                allow_missing_schedule=True,
            )
            self._validate_expected(session, command, before)

            calendar, calendar_evidence = self._empty_week_calendar_evidence(
                command.expected_week
            )
            covering_events = tuple(
                event.event_id
                for event in calendar.events
                if (event.start_season_week or event.season_week)
                <= command.expected_week.week
                <= (
                    event.end_season_week
                    or event.start_season_week
                    or event.season_week
                )
            )
            if covering_events:
                raise ValueError(
                    "empty-week completion is blocked by Calendar events: "
                    + ", ".join(sorted(covering_events))
                )

            packages = self._packages(
                command.expected_week,
                required=False,
                session=session,
                run_id=command.run_id,
                branch_id=command.branch_id,
            )
            if packages:
                raise ValueError(
                    "empty-week completion is blocked by executable tournament packages"
                )
            if session.get(
                AdoptedTournamentAuthorityModel,
                (command.run_id, command.branch_id, command.expected_week.ordinal),
            ) is not None:
                raise ValueError(
                    "empty-week completion is blocked by adopted tournament authority"
                )
            if self._schedule(
                session,
                command.run_id,
                command.branch_id,
                command.expected_week,
            ) is not None:
                raise ValueError(
                    "empty-week completion is blocked by an adopted Week Schedule"
                )
            if self._entry_slot_ordinals(
                session,
                command.run_id,
                command.branch_id,
                command.expected_week,
            ) or self._wc_slot_ordinals(
                session,
                command.run_id,
                command.branch_id,
                command.expected_week,
            ):
                raise ValueError(
                    "empty-week completion is blocked by non-match Simulation Slots"
                )

            slots = session.scalars(
                select(SimulationSlotModel).where(
                    SimulationSlotModel.run_id == command.run_id,
                    SimulationSlotModel.branch_id == command.branch_id,
                    SimulationSlotModel.week_ordinal == command.expected_week.ordinal,
                )
            ).all()
            groups = session.scalars(
                select(SimulationEventGroupModel).where(
                    SimulationEventGroupModel.run_id == command.run_id,
                    SimulationEventGroupModel.branch_id == command.branch_id,
                    SimulationEventGroupModel.week_ordinal
                    == command.expected_week.ordinal,
                )
            ).all()
            if slots or groups:
                raise ValueError(
                    "empty-week completion is blocked by authoritative match history"
                )

            sources = OwnedTournamentRankingSourceStore(session).history(
                run_id=command.run_id,
                branch_id=command.branch_id,
            )
            if any(source is None for source in sources):
                raise ValueError("owned tournament source history is incomplete")
            if any(
                source is not None
                and source.binding.completed_week == command.expected_week
                for source in sources
            ):
                raise ValueError(
                    "empty-week completion is blocked by completed tournament sources"
                )

            lifecycle = get_lifecycle(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=command.expected_week,
            )
            sporting = get_sporting(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=command.expected_week,
            )
            if lifecycle is None or sporting is None:
                raise ValueError(
                    "empty-week completion requires lifecycle and sporting roster"
                )

            try:
                get_completed_context(
                    session,
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    completed_week=command.expected_week,
                )
            except ValueError as exc:
                if "zero matches cannot be inferred" not in str(exc):
                    raise
            else:
                raise ValueError(
                    "completed week already has authoritative sporting evidence"
                )

            context = put_completed_context(
                session,
                CompletedWeekSportingContext(
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    completed_week=command.expected_week,
                    competitive_match_counts=tuple(
                        CompetitiveMatchCount(player_id=player.player_id, count=0)
                        for player in sorted(
                            sporting.players, key=lambda item: item.player_id
                        )
                    ),
                    source_fingerprints=(calendar_evidence,),
                    provenance=AUTHORITATIVE_EMPTY_WEEK_PROVENANCE,
                ),
            )
            after = self._position(
                session,
                command.run_id,
                command.branch_id,
                allow_missing_schedule=True,
            )
            payload = {
                "schema_version": "authoritative_empty_week_completion.v1",
                "run_id": command.run_id,
                "branch_id": command.branch_id,
                "completed_week": command.expected_week.model_dump(mode="json"),
                "completed_context_fingerprint": context.fingerprint,
                "calendar_evidence_fingerprint": calendar_evidence,
                "competitive_match_count": 0,
                "player_count": len(context.competitive_match_counts),
                "operator_label": command.operator_label,
                "audit_reason": command.audit_reason,
                "position": after.model_dump(mode="json"),
            }
            session.add(
                AuthoritativeSimulationCommandModel(
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    command_id=command.command_id,
                    request_fingerprint=request_fp,
                    status="complete",
                    result_json=json.dumps(
                        payload, sort_keys=True, separators=(",", ":")
                    ),
                )
            )
            session.flush()
            return payload

    def _validate_legacy_entry_roster_against_run(
        self,
        session: Session,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
    ) -> None:
        """Fail closed unless compatibility Entry AI sees the owned active sporting roster."""

        lifecycle = get_lifecycle(
            session,
            run_id=run_id,
            branch_id=branch_id,
            week=week,
        )
        sporting = get_sporting(
            session,
            run_id=run_id,
            branch_id=branch_id,
            week=week,
        )
        if lifecycle is None or sporting is None:
            raise ValueError(
                "Authoritative Entry decisions require lifecycle and sporting roster"
            )

        sporting_ids = {player.player_id for player in sporting.players}
        owned_ids = tuple(
            sorted(
                player.player_id
                for player in lifecycle.players
                if player.status == "active" and player.player_id in sporting_ids
            )
        )
        season = f"{2000 + week.season_index}/{2001 + week.season_index}"
        compatibility = (
            self.match_service.draw_service.entry_list_service.active_players_service
            .get_active_players(season=season)
            .players
        )
        compatibility_ids = tuple(
            sorted(player.player_id for player in compatibility)
        )
        if compatibility_ids != owned_ids:
            raise ValueError(
                "Compatibility Entry AI roster differs from authoritative "
                "Run/Branch active sporting roster"
            )

    def preview_entry_decision_slot(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_ids: tuple[str, ...],
        decision_slot_ordinal: int,
        seed: int = 12345,
    ) -> dict:
        """Build complete pre-cut Entry decisions without mutating compatibility state."""

        if not event_ids or event_ids != tuple(sorted(set(event_ids))):
            raise ValueError("Entry decision preview event IDs must be canonical and unique")
        if decision_slot_ordinal < 1:
            raise ValueError("Entry decision slot ordinal must be one-based")

        with self.factory() as session:
            self._require_writable_scope(session, run_id, branch_id)
            week = self._current_week(session, run_id, branch_id)
            branch = session.get(RunBranchModel, branch_id)
            if branch is None or not branch.saved_head_revision_id:
                raise ValueError("Entry decision preview requires a saved Branch head")

            self._validate_legacy_entry_roster_against_run(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=week,
            )
            batch = SeasonEntryBatchService(
                self.match_service.draw_service.entry_list_service
            ).generate_overlapping_entry_lists(
                event_ids=list(event_ids),
                request=EntryBatchGenerateRequest(
                    seed=seed,
                    dry_run=True,
                    overwrite_existing=False,
                    max_alternates=0,
                    include_not_entered=False,
                ),
            )
            authority = freeze_entry_batch_proposal_as_run_slot(
                batch=batch,
                run_id=run_id,
                branch_id=branch_id,
                week=week,
                decision_slot_ordinal=decision_slot_ordinal,
            )

            # Preview must also fail on already-owned global chronology instead of
            # advertising a proposal that commit can never accept.
            store = RunEntryDecisionSlotStore(session)
            existing = store.validate_candidate(authority)

            return {
                "run_id": run_id,
                "branch_id": branch_id,
                "week": week.model_dump(mode="json"),
                "decision_slot_ordinal": decision_slot_ordinal,
                "event_ids": list(event_ids),
                "seed": seed,
                "expected_revision_id": branch.saved_head_revision_id,
                "entry_batch_fingerprint": batch.metadata.build_fingerprint,
                "application_decisions_fingerprint": (
                    batch.metadata.application_decisions_fingerprint
                ),
                "active_players_fingerprint": batch.metadata.active_players_fingerprint,
                "decision_count": len(authority.decisions),
                "slot_fingerprint": authority.fingerprint,
                "authority": authority.model_dump(mode="json"),
                "persisted": existing is not None,
            }

    def commit_entry_decision_slot(
        self,
        command: AuthoritativeEntryDecisionSlotCommand,
    ) -> dict:
        """Rebuild and atomically persist the exact previewed Entry decision slot."""

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            week = self._current_week(session, command.run_id, command.branch_id)
            if week != command.expected_week:
                raise ValueError("Entry decision slot week is stale")

            branch = session.get(RunBranchModel, command.branch_id)
            if (
                branch is None
                or branch.run_id != command.run_id
                or branch.saved_head_revision_id != command.expected_revision_id
            ):
                raise ValueError("Entry decision Branch head is stale")

            self._validate_legacy_entry_roster_against_run(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=week,
            )
            batch = SeasonEntryBatchService(
                self.match_service.draw_service.entry_list_service
            ).generate_overlapping_entry_lists(
                event_ids=list(command.event_ids),
                request=EntryBatchGenerateRequest(
                    seed=command.seed,
                    dry_run=True,
                    overwrite_existing=False,
                    max_alternates=0,
                    include_not_entered=False,
                ),
            )
            if (
                batch.metadata.build_fingerprint
                != command.expected_entry_batch_fingerprint
            ):
                raise ValueError("Entry decision batch proposal is stale")

            authority = freeze_entry_batch_proposal_as_run_slot(
                batch=batch,
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=week,
                decision_slot_ordinal=command.decision_slot_ordinal,
            )
            if authority.fingerprint != command.expected_slot_fingerprint:
                raise ValueError("Entry decision slot proposal is stale")

            store = RunEntryDecisionSlotStore(session)
            existing = store.get(
                run_id=command.run_id,
                branch_id=command.branch_id,
                week_ordinal=week.ordinal,
                decision_slot_ordinal=command.decision_slot_ordinal,
            )
            stored = store.append(authority)
            return {
                "run_id": command.run_id,
                "branch_id": command.branch_id,
                "week": week.model_dump(mode="json"),
                "decision_slot_ordinal": command.decision_slot_ordinal,
                "event_ids": list(command.event_ids),
                "entry_batch_fingerprint": batch.metadata.build_fingerprint,
                "application_decisions_fingerprint": (
                    batch.metadata.application_decisions_fingerprint
                ),
                "active_players_fingerprint": batch.metadata.active_players_fingerprint,
                "decision_count": len(stored.decisions),
                "slot_fingerprint": stored.fingerprint,
                "authority": stored.model_dump(mode="json"),
                "adoption": "exact_retry" if existing == stored else "committed",
            }

    def _validate_application_identity_tokens(
        self,
        session: Session,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
        validations: tuple[TournamentApplicationValidationAuthority, ...],
    ) -> None:
        """Bind application validation identity to canonical lifecycle truth."""

        lifecycle = get_lifecycle(
            session,
            run_id=run_id,
            branch_id=branch_id,
            week=week,
        )
        if lifecycle is None:
            raise ValueError(
                "Application validation requires authoritative lifecycle identity"
            )
        identities = {player.player_id: player for player in lifecycle.players}
        for validation in validations:
            identity = identities.get(validation.player_id)
            if identity is None:
                raise ValueError(
                    "Application validation player is missing from lifecycle identity"
                )
            if (
                validation.nr_tie_break_token is not None
                and validation.nr_tie_break_token != identity.tie_break_token
            ):
                raise ValueError(
                    "Application validation NR tie-break token differs from "
                    "authoritative lifecycle identity"
                )

    def inspect_entry_decision_slot(
        self,
        *,
        run_id: str,
        branch_id: str,
        decision_slot_ordinal: int,
    ) -> dict:
        """Read one persisted Entry slot with canonical lifecycle identity evidence."""

        if decision_slot_ordinal < 1:
            raise ValueError("Entry decision slot ordinal must be one-based")
        with self.factory() as session:
            week = self._current_week(session, run_id, branch_id)
            slot = RunEntryDecisionSlotStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week.ordinal,
                decision_slot_ordinal=decision_slot_ordinal,
            )
            if slot is None:
                raise ValueError("Entry decision slot is missing")

            lifecycle = get_lifecycle(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=week,
            )
            if lifecycle is None:
                raise ValueError(
                    "Entry decision slot inspection requires lifecycle identity"
                )
            identities = {player.player_id: player for player in lifecycle.players}
            decision_players = {decision.player_id for decision in slot.decisions}
            missing = decision_players - set(identities)
            if missing:
                raise ValueError(
                    "Entry decision slot contains player missing from lifecycle identity"
                )

            validation = session.get(
                ResolvedApplicationValidationSlotModel,
                (run_id, branch_id, week.ordinal, decision_slot_ordinal),
            )
            return {
                "run_id": run_id,
                "branch_id": branch_id,
                "week": week.model_dump(mode="json"),
                "decision_slot_ordinal": decision_slot_ordinal,
                "slot_fingerprint": slot.fingerprint,
                "authority": slot.model_dump(mode="json"),
                "identity_tokens": {
                    player_id: identities[player_id].tie_break_token
                    for player_id in sorted(decision_players)
                },
                "validation_resolved": validation is not None,
                "validation_fingerprint": (
                    None if validation is None else validation.fingerprint
                ),
            }

    def commit_application_validation_slot(
        self,
        command: AuthoritativeApplicationValidationCommand,
    ) -> dict:
        """Persist complete explicit validity outcomes for one real Run Entry slot."""

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            week = self._current_week(session, command.run_id, command.branch_id)
            if week != command.expected_week:
                raise ValueError("Application validation week is stale")

            branch = session.get(RunBranchModel, command.branch_id)
            if (
                branch is None
                or branch.run_id != command.run_id
                or branch.saved_head_revision_id != command.expected_revision_id
            ):
                raise ValueError("Application validation Branch head is stale")

            slot = RunEntryDecisionSlotStore(session).get(
                run_id=command.run_id,
                branch_id=command.branch_id,
                week_ordinal=week.ordinal,
                decision_slot_ordinal=command.decision_slot_ordinal,
            )
            if slot is None:
                raise ValueError("Application validation Entry slot is missing")
            if slot.fingerprint != command.expected_entry_slot_fingerprint:
                raise ValueError("Application validation Entry slot is stale")

            self._validate_application_identity_tokens(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=week,
                validations=command.validations,
            )
            resolved = ResolvedApplicationValidationSlot(
                slot=slot,
                validations=command.validations,
            )
            committed = record_resolved_application_validation_slot(
                session,
                resolved,
            )
            submission = committed.submission_commit
            return {
                "run_id": command.run_id,
                "branch_id": command.branch_id,
                "week": week.model_dump(mode="json"),
                "decision_slot_ordinal": command.decision_slot_ordinal,
                "entry_slot_fingerprint": slot.fingerprint,
                "validation_fingerprint": committed.validation_slot.fingerprint,
                "valid_submission_count": (
                    0 if submission is None else len(submission.batch.submissions)
                ),
                "submission_batch_fingerprint": (
                    None if submission is None else submission.batch.fingerprint
                ),
                "first_tour_entry_trigger_fingerprints": (
                    []
                    if submission is None
                    else [
                        item.fingerprint
                        for item in submission.first_tour_entry_triggers
                    ]
                ),
            }

    def commit_explicit_application_validation_slot(
        self,
        command: AuthoritativeExplicitApplicationValidationCommand,
    ) -> dict:
        """Resolve the current Entry slot from minimal explicit Admin verdicts.

        This intentionally does not invent an eligibility/deadline algorithm. The
        persisted Entry decision slot and lifecycle state remain the source of every
        authority field except the Admin-reviewed valid/invalid verdict and rejection
        reason.
        """

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            week = self._current_week(session, command.run_id, command.branch_id)
            if week != command.expected_week:
                raise ValueError("Explicit application validation week is stale")

            branch = session.get(RunBranchModel, command.branch_id)
            if (
                branch is None
                or branch.run_id != command.run_id
                or branch.saved_head_revision_id != command.expected_revision_id
            ):
                raise ValueError("Explicit application validation Branch head is stale")

            slot = RunEntryDecisionSlotStore(session).get(
                run_id=command.run_id,
                branch_id=command.branch_id,
                week_ordinal=week.ordinal,
                decision_slot_ordinal=command.decision_slot_ordinal,
            )
            if slot is None:
                raise ValueError("Explicit application validation Entry slot is missing")
            if slot.fingerprint != command.expected_entry_slot_fingerprint:
                raise ValueError("Explicit application validation Entry slot is stale")

            decisions = {
                (decision.event_id, decision.player_id): decision
                for decision in slot.decisions
            }
            review_keys = tuple(review.key for review in command.reviews)
            if set(review_keys) != set(decisions):
                raise ValueError(
                    "Explicit application validation must review every frozen decision exactly once"
                )

            lifecycle = get_lifecycle(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=week,
            )
            if lifecycle is None:
                raise ValueError(
                    "Explicit application validation requires authoritative lifecycle identity"
                )
            identities = {player.player_id: player for player in lifecycle.players}

            validations: list[TournamentApplicationValidationAuthority] = []
            for review in command.reviews:
                decision = decisions[review.key]
                identity = identities.get(decision.player_id)
                if identity is None:
                    raise ValueError(
                        "Explicit application validation player is missing from lifecycle identity"
                    )
                if review.outcome == "valid" and not identity.tie_break_token:
                    raise ValueError(
                        "Valid explicit application review requires lifecycle NR tie-break token"
                    )

                stable_identity = fingerprint(
                    {
                        "run_id": command.run_id,
                        "branch_id": command.branch_id,
                        "week_ordinal": week.ordinal,
                        "decision_slot_ordinal": command.decision_slot_ordinal,
                        "source_slot_fingerprint": slot.fingerprint,
                        "event_id": decision.event_id,
                        "player_id": decision.player_id,
                        "source_decision_fingerprint": (
                            decision.source_decision_fingerprint
                        ),
                    }
                )
                validations.append(
                    TournamentApplicationValidationAuthority(
                        validation_id=f"explicit-admin:{stable_identity}",
                        application_id=f"application:{stable_identity}",
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        week=week,
                        decision_slot_ordinal=command.decision_slot_ordinal,
                        source_slot_fingerprint=slot.fingerprint,
                        event_id=decision.event_id,
                        player_id=decision.player_id,
                        entry_window=(
                            "main"
                            if decision.target == "MAIN"
                            else "qualification"
                        ),
                        source_decision_fingerprint=(
                            decision.source_decision_fingerprint
                        ),
                        outcome=review.outcome,
                        nr_tie_break_token=(
                            identity.tie_break_token
                            if review.outcome == "valid"
                            else None
                        ),
                        validation_policy_id=(
                            EXPLICIT_ADMIN_APPLICATION_VALIDATION_POLICY_ID
                        ),
                        validation_policy_fingerprint=(
                            EXPLICIT_ADMIN_APPLICATION_VALIDATION_POLICY_FINGERPRINT
                        ),
                        reasons=review.reasons,
                        provenance=(
                            "explicit_admin_application_validation.v1; "
                            f"operator={command.operator_label}; reason={command.reason}"
                        ),
                    )
                )

            validation_tuple = tuple(validations)
            self._validate_application_identity_tokens(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=week,
                validations=validation_tuple,
            )
            resolved = ResolvedApplicationValidationSlot(
                slot=slot,
                validations=validation_tuple,
            )
            existing_validation = ApplicationValidationSlotStore(session).get(
                run_id=command.run_id,
                branch_id=command.branch_id,
                week_ordinal=week.ordinal,
                decision_slot_ordinal=command.decision_slot_ordinal,
            )
            if existing_validation is None:
                position = self._position(session, command.run_id, command.branch_id)
                if (
                    position.position_fingerprint
                    != command.expected_position_fingerprint
                ):
                    raise ValueError("Explicit application validation Position is stale")
                if (
                    position.current_slot_kind != "entry"
                    or position.slot_ordinal != command.decision_slot_ordinal
                ):
                    raise ValueError(
                        "Explicit application validation must resolve the current Entry slot"
                    )
            elif existing_validation != resolved:
                raise ValueError(
                    "Application validation slot already has different resolved authority"
                )

            committed = record_resolved_application_validation_slot(session, resolved)
            submission = committed.submission_commit
            return {
                "run_id": command.run_id,
                "branch_id": command.branch_id,
                "week": week.model_dump(mode="json"),
                "decision_slot_ordinal": command.decision_slot_ordinal,
                "entry_slot_fingerprint": slot.fingerprint,
                "validation_fingerprint": committed.validation_slot.fingerprint,
                "validation_mode": "explicit_admin_review.v1",
                "validation_policy_id": (
                    EXPLICIT_ADMIN_APPLICATION_VALIDATION_POLICY_ID
                ),
                "validation_policy_fingerprint": (
                    EXPLICIT_ADMIN_APPLICATION_VALIDATION_POLICY_FINGERPRINT
                ),
                "valid_submission_count": (
                    0 if submission is None else len(submission.batch.submissions)
                ),
                "submission_batch_fingerprint": (
                    None if submission is None else submission.batch.fingerprint
                ),
                "first_tour_entry_trigger_fingerprints": (
                    []
                    if submission is None
                    else [
                        item.fingerprint
                        for item in submission.first_tour_entry_triggers
                    ]
                ),
            }

    def inspect_week_tournament_lock(
        self, *, run_id: str, branch_id: str
    ) -> dict:
        """Inspect current accepted-field conflicts without inventing a selection."""

        with self.factory() as session:
            self._require_writable_scope(session, run_id, branch_id)
            position = self._position(
                session,
                run_id,
                branch_id,
                allow_missing_schedule=True,
            )
            branch = session.get(RunBranchModel, branch_id)
            if branch is None or not branch.saved_head_revision_id:
                raise ValueError(
                    "Week Tournament Lock requires a saved Branch head"
                )
            event_ids = self._week_tournament_lock_event_ids(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=position.current_week,
            )
            if event_ids:
                evidence, conflicts = resolve_week_tournament_lock_evidence(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    event_ids=event_ids,
                )
            else:
                evidence, conflicts = (), {}
            stored = WeekTournamentLockStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=position.current_week.ordinal,
            )
            return {
                "run_id": run_id,
                "branch_id": branch_id,
                "week": position.current_week.model_dump(mode="json"),
                "expected_revision_id": branch.saved_head_revision_id,
                "position_fingerprint": position.position_fingerprint,
                "event_ids": list(event_ids),
                "event_evidence": [
                    item.model_dump(mode="json") for item in evidence
                ],
                "conflicts": [
                    {
                        "player_id": player_id,
                        "eligible_event_ids": list(conflicts[player_id]),
                    }
                    for player_id in sorted(conflicts)
                ],
                "lock_status": "locked" if stored is not None else (
                    "required" if conflicts else "not_required"
                ),
                "authority": (
                    stored.model_dump(mode="json") if stored is not None else None
                ),
                "authority_fingerprint": (
                    stored.fingerprint if stored is not None else None
                ),
                "selection_policy_id": (
                    "explicit_admin_week_tournament_lock.v1"
                ),
                "final_commitment_deadline_policy": "intentionally_unresolved",
            }

    def preview_week_tournament_lock(
        self, request: AuthoritativeWeekTournamentLockPreviewRequest
    ) -> dict:
        with self.factory() as session:
            self._require_writable_scope(
                session, request.run_id, request.branch_id
            )
            before = self._position(
                session,
                request.run_id,
                request.branch_id,
                allow_missing_schedule=True,
            )
            self._validate_expected(session, request, before)
            if self._schedule(
                session,
                request.run_id,
                request.branch_id,
                request.expected_week,
            ) is not None:
                raise ValueError(
                    "Week Tournament Lock must be resolved before Week Schedule adoption"
                )
            if WeekTournamentLockStore(session).get(
                run_id=request.run_id,
                branch_id=request.branch_id,
                week_ordinal=request.expected_week.ordinal,
            ) is not None:
                raise ValueError(
                    "Week Tournament Lock is already immutable for this week"
                )
            event_ids = self._week_tournament_lock_event_ids(
                session,
                run_id=request.run_id,
                branch_id=request.branch_id,
                week=request.expected_week,
            )
            authority = derive_week_tournament_lock_authority(
                session,
                run_id=request.run_id,
                branch_id=request.branch_id,
                week=request.expected_week,
                event_ids=event_ids,
                selections=request.selections_by_player,
                command_id=request.command_id,
                operator_label=request.operator_label,
                audit_reason=request.audit_reason,
            )
            return {
                "run_id": request.run_id,
                "branch_id": request.branch_id,
                "week": request.expected_week.model_dump(mode="json"),
                "event_ids": list(event_ids),
                "authority": authority.model_dump(mode="json"),
                "authority_fingerprint": authority.fingerprint,
                "position_fingerprint": before.position_fingerprint,
                "persisted": False,
            }

    def commit_week_tournament_lock(
        self, command: AuthoritativeWeekTournamentLockCommitCommand
    ) -> dict:
        request_fp = fingerprint(
            {
                "mode": "week_tournament_lock",
                "command": command.model_dump(mode="json"),
            }
        )
        key = (command.run_id, command.branch_id, command.command_id)
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(
                session, command.run_id, command.branch_id
            )
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt is not None:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError(
                        "Week Tournament Lock command ID already has a different request"
                    )
                if receipt.status != "complete":
                    raise ValueError(
                        "Week Tournament Lock command receipt is incomplete"
                    )
                return json.loads(receipt.result_json)

            before = self._position(
                session,
                command.run_id,
                command.branch_id,
                allow_missing_schedule=True,
            )
            self._validate_expected(session, command, before)
            if self._schedule(
                session,
                command.run_id,
                command.branch_id,
                command.expected_week,
            ) is not None:
                raise ValueError(
                    "Week Tournament Lock must be resolved before Week Schedule adoption"
                )

            event_ids = self._week_tournament_lock_event_ids(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=command.expected_week,
            )
            lock_commit = WeekTournamentLockStore(session).commit(
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=command.expected_week,
                event_ids=event_ids,
                selections=command.selections_by_player,
                command_id=command.command_id,
                operator_label=command.operator_label,
                audit_reason=command.audit_reason,
                expected_authority_fingerprint=(
                    command.expected_authority_fingerprint
                ),
            )
            authority = lock_commit.authority
            repairs = []
            if not lock_commit.exact_retry:
                withdrawn_by_event: dict[str, set[str]] = {}
                for player_lock in authority.player_locks:
                    for event_id in player_lock.eligible_event_ids:
                        if event_id == player_lock.selected_event_id:
                            continue
                        withdrawn_by_event.setdefault(event_id, set()).add(
                            player_lock.player_id
                        )

                evidence_by_event = {
                    item.event_id: item for item in authority.event_evidence
                }
                field_store = TournamentEntryFieldStore(session)
                for event_id in sorted(withdrawn_by_event):
                    expected = evidence_by_event[event_id]
                    withdrawn = tuple(sorted(withdrawn_by_event[event_id]))
                    repaired = field_store.stage_pre_draw_repair_from_frozen_inputs(
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        event_id=event_id,
                        expected_field_fingerprint=(
                            expected.entry_field_fingerprint
                        ),
                        withdrawn_player_ids=withdrawn,
                        command_id=self._week_lock_field_command_id(
                            command.command_id,
                            event_id,
                        ),
                    )
                    repairs.append(
                        {
                            "event_id": event_id,
                            "withdrawn_player_ids": list(withdrawn),
                            "field_fingerprint": repaired.fingerprint,
                        }
                    )

                _, remaining = resolve_week_tournament_lock_evidence(
                    session,
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    event_ids=event_ids,
                )
                if remaining:
                    raise ValueError(
                        "Week Tournament Lock field repair created or retained "
                        "overlapping accepted players; explicit follow-up policy is required"
                    )

            result = {
                "run_id": command.run_id,
                "branch_id": command.branch_id,
                "week": command.expected_week.model_dump(mode="json"),
                "authority": authority.model_dump(mode="json"),
                "authority_fingerprint": authority.fingerprint,
                "field_repairs": repairs,
                "adoption": (
                    "exact_retry"
                    if lock_commit.exact_retry
                    else "committed"
                ),
            }
            session.add(
                AuthoritativeSimulationCommandModel(
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    command_id=command.command_id,
                    request_fingerprint=request_fp,
                    status="complete",
                    result_json=json.dumps(
                        result, sort_keys=True, separators=(",", ":")
                    ),
                )
            )
            session.flush()
            return result

    def season_transition_preflight(
        self, *, run_id: str, branch_id: str
    ) -> AuthoritativeSeasonTransitionPreflight:
        with self.factory() as session:
            return self._season_transition_preflight(session, run_id, branch_id)

    def _season_transition_preflight(
        self, session: Session, run_id: str, branch_id: str
    ) -> AuthoritativeSeasonTransitionPreflight:
        position = self._position(session, run_id, branch_id)
        week = position.current_week
        branch = session.get(RunBranchModel, branch_id)
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == branch_id
            )
        )
        blockers = [
            item
            for item in position.transition_blockers
            if item != "season_transition_required"
        ]
        if week.week != 61:
            blockers.append("not_at_season_boundary")
        if branch is None or draft is None or branch.run_id != run_id:
            blockers.append("run_branch_scope_missing")
        else:
            if branch.read_only or branch.status != "active":
                blockers.append("run_branch_not_writable")
            if draft.status != "clean":
                blockers.append("working_draft_dirty")
            if (
                not branch.saved_head_revision_id
                or draft.base_revision_id != branch.saved_head_revision_id
            ):
                blockers.append("saved_revision_head_mismatch")

        at_boundary = week.week == 61
        final_season = at_boundary and week.season_index == 49
        target_week = (
            RankingWeek(season_index=week.season_index + 1, week=1)
            if at_boundary and not final_season
            else None
        )
        default_closing = None
        if at_boundary:
            try:
                default_closing = resolve_canonical_season_closing_ranking(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    completed_week=week,
                )
            except ValueError:
                blockers.append("season_closing_ranking_unavailable")
        default_configuration = None
        default_sporting = None
        default_lifecycle = None
        default_ranking = None
        if target_week is not None:
            try:
                default_configuration = resolve_season_transition_configuration(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                )
            except ValueError:
                blockers.append("season_transition_configuration_unavailable")
            if default_configuration is not None:
                try:
                    default_sporting = resolve_season_transition_sporting(
                        session,
                        default_configuration,
                    )
                except ValueError:
                    blockers.append("season_transition_sporting_unavailable")
                try:
                    default_lifecycle = resolve_season_transition_lifecycle(
                        session,
                        default_configuration,
                    )
                except ValueError:
                    blockers.append("season_transition_lifecycle_unavailable")
                if default_lifecycle is not None:
                    try:
                        default_ranking = resolve_season_transition_ranking(
                            session,
                            default_configuration,
                        )
                    except ValueError:
                        blockers.append("season_transition_ranking_unavailable")
        implementation_gaps = ()
        state_blockers = tuple(dict.fromkeys(blockers))
        body = {
            "scope": [run_id, branch_id],
            "completed_week": week.model_dump(mode="json"),
            "target_week": target_week.model_dump(mode="json")
            if target_week
            else None,
            "final_season": final_season,
            "saved_revision_id": branch.saved_head_revision_id
            if branch
            else None,
            "draft_version": draft.draft_version if draft else None,
            "default_closing_ranking_fingerprint": (
                default_closing.fingerprint if default_closing else None
            ),
            "default_configuration_fingerprint": (
                default_configuration.fingerprint if default_configuration else None
            ),
            "default_sporting_fingerprint": (
                default_sporting.target_state.fingerprint if default_sporting else None
            ),
            "default_lifecycle_fingerprint": (
                default_lifecycle.target_state.fingerprint if default_lifecycle else None
            ),
            "default_ranking_fingerprint": (
                default_ranking.target_snapshot.fingerprint if default_ranking else None
            ),
            "position_fingerprint": position.position_fingerprint,
            "state_blockers": state_blockers,
            "implementation_gaps": implementation_gaps,
        }
        ready = not state_blockers and not implementation_gaps
        return AuthoritativeSeasonTransitionPreflight(
            run_id=run_id,
            branch_id=branch_id,
            completed_week=week,
            target_week=target_week,
            final_season=final_season,
            saved_revision_id=branch.saved_head_revision_id
            if branch
            else None,
            draft_version=draft.draft_version if draft else None,
            default_closing_ranking_fingerprint=(
                default_closing.fingerprint if default_closing else None
            ),
            default_configuration_fingerprint=(
                default_configuration.fingerprint if default_configuration else None
            ),
            default_sporting_fingerprint=(
                default_sporting.target_state.fingerprint if default_sporting else None
            ),
            default_lifecycle_fingerprint=(
                default_lifecycle.target_state.fingerprint if default_lifecycle else None
            ),
            default_ranking_fingerprint=(
                default_ranking.target_snapshot.fingerprint if default_ranking else None
            ),
            position_fingerprint=position.position_fingerprint,
            state_blockers=state_blockers,
            implementation_gaps=implementation_gaps,
            ready_for_execution=ready,
            preflight_fingerprint=fingerprint(body),
        )

    def advance_season(
        self, command: OrdinarySeasonTransitionCommand
    ) -> OrdinarySeasonTransitionResult:
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            existing = session.get(
                BranchSavedRevisionModel,
                command.season_saved_revision_id,
            )
            if existing is not None:
                return commit_ordinary_season_transition(session, command)

            preflight = self._season_transition_preflight(
                session, command.run_id, command.branch_id
            )
            if preflight.preflight_fingerprint != command.expected_preflight_fingerprint:
                raise ValueError("season transition preflight is stale")
            if preflight.final_season or preflight.target_week is None:
                raise ValueError(
                    "ordinary Season Transition requires a non-final Week 61 boundary"
                )
            if not preflight.ready_for_execution:
                raise ValueError(
                    "ordinary Season Transition preflight is not ready: "
                    + ", ".join(
                        (*preflight.state_blockers, *preflight.implementation_gaps)
                    )
                )
            if preflight.saved_revision_id != command.expected_saved_revision_id:
                raise ValueError("Season Transition Saved Revision head is stale")
            if preflight.draft_version != command.expected_draft_version:
                raise ValueError("Season Transition Working Draft version is stale")
            if (
                command.configuration.completed_week != preflight.completed_week
                or command.configuration.target_week != preflight.target_week
            ):
                raise ValueError("Season Transition configuration boundary is stale")
            return commit_ordinary_season_transition(session, command)

    def finalize_final_season(
        self, command: FinalSeasonTransitionCommand
    ) -> FinalSeasonTransitionResult:
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            existing = session.get(
                BranchSavedRevisionModel,
                command.final_saved_revision_id,
            )
            if existing is not None:
                return commit_final_season_transition(session, command)

            preflight = self._season_transition_preflight(
                session, command.run_id, command.branch_id
            )
            if preflight.preflight_fingerprint != command.expected_preflight_fingerprint:
                raise ValueError("season transition preflight is stale")
            if not preflight.final_season:
                raise ValueError("final season closure requires 2049/50 Week 61")
            if not preflight.ready_for_execution:
                raise ValueError(
                    "final season closure preflight is not ready: "
                    + ", ".join(
                        (*preflight.state_blockers, *preflight.implementation_gaps)
                    )
                )
            if preflight.saved_revision_id != command.expected_saved_revision_id:
                raise ValueError("final season closure Saved Revision head is stale")
            if preflight.draft_version != command.expected_draft_version:
                raise ValueError("final season closure Working Draft version is stale")
            return commit_final_season_transition(session, command)

    @staticmethod
    def _reconstruction_game_scores(result) -> tuple[tuple[int, int], ...]:
        scores: list[tuple[int, int]] = []
        for set_result in result.sets:
            if set_result.winner_player_id == result.player_a_id:
                scores.append((set_result.winner_games, set_result.loser_games))
            else:
                scores.append((set_result.loser_games, set_result.winner_games))
        return tuple(scores)

    @classmethod
    def _reconstruction_matches_constraints(
        cls, result, constraints: MatchReconstructionConstraints
    ) -> bool:
        # The minimum V1 catalog reconstructs completed competitive matches only.
        if result.retired_player_id is not None:
            return False
        if (
            constraints.winner_player_id is not None
            and result.winner_player_id != constraints.winner_player_id
        ):
            return False
        if constraints.player_a_sets_won is not None:
            if result.sets_won.get(result.player_a_id, 0) != constraints.player_a_sets_won:
                return False
            if result.sets_won.get(result.player_b_id, 0) != constraints.player_b_sets_won:
                return False
        if constraints.exact_game_scores:
            expected = tuple(
                (score.player_a_points, score.player_b_points)
                for score in constraints.exact_game_scores
            )
            if cls._reconstruction_game_scores(result) != expected:
                return False
        return True

    @staticmethod
    def _reconstruction_candidate_fingerprint(
        *,
        request: AuthoritativeMatchReconstructionPreviewRequest,
        slot_start_fingerprint: str,
        seed: int,
        attempt_ordinal: int,
        result_fingerprint: str,
    ) -> str:
        return fingerprint(
            {
                "schema": "match_reconstruction_candidate.v1",
                "scope": [
                    request.run_id,
                    request.branch_id,
                    request.expected_week.ordinal,
                    request.group_id,
                ],
                "position": request.expected_position_fingerprint,
                "slot_start": slot_start_fingerprint,
                "constraints": request.constraints.model_dump(mode="json"),
                "seed": seed,
                "attempt_ordinal": attempt_ordinal,
                "result_fingerprint": result_fingerprint,
            }
        )

    def _build_match_reconstruction_preview(
        self,
        session,
        request: AuthoritativeMatchReconstructionPreviewRequest,
        packages,
    ) -> dict[str, Any]:
        current = self._position(session, request.run_id, request.branch_id)
        eligible_groups = self._eligible_groups(session, current, packages)
        if request.group_id not in eligible_groups:
            raise ValueError(
                "reconstruction target is completed, blocked, or outside the current slot"
            )
        slot, plan, event, package, players = self._group_execution_context(
            session, request, packages, request.group_id
        )
        if (
            request.constraints.winner_player_id is not None
            and request.constraints.winner_player_id not in players
        ):
            raise ValueError(
                "reconstruction winner constraint is not one of the frozen match participants"
            )

        max_sets = 5
        needed_sets = max_sets // 2 + 1
        if request.constraints.player_a_sets_won is not None:
            a_sets = request.constraints.player_a_sets_won
            b_sets = request.constraints.player_b_sets_won or 0
            if (
                max(a_sets, b_sets) != needed_sets
                or min(a_sets, b_sets) >= needed_sets
                or a_sets + b_sets > max_sets
            ):
                raise ValueError(
                    "reconstruction exact match score is not a completed best-of-five result"
                )

        attempt_budget = min(400, max(40, request.candidate_count * 20))
        seed_anchor = (
            f"match-reconstruction-v1|{request.run_id}|{request.branch_id}|"
            f"{request.expected_week.ordinal}|{plan.slot_start_fingerprint}|"
            f"{request.group_id}"
        )
        candidates: list[dict[str, Any]] = []
        attempted = 0
        for attempt_ordinal in range(1, attempt_budget + 1):
            attempted = attempt_ordinal
            seed = int(
                hashlib.sha256(
                    f"{seed_anchor}|{attempt_ordinal}".encode()
                ).hexdigest()[:15],
                16,
            )
            savepoint = session.begin_nested()
            try:
                staged = self._execute_group(
                    session,
                    request,
                    packages,
                    request.group_id,
                    seed_override=seed,
                )
                result_payload = staged.result.model_dump(mode="json")
                result_fingerprint = staged.result_fingerprint
                authoritative_input_fingerprint = staged.authoritative_input.fingerprint
            finally:
                savepoint.rollback()

            if not self._reconstruction_matches_constraints(
                staged.result, request.constraints
            ):
                continue
            candidate_fingerprint = self._reconstruction_candidate_fingerprint(
                request=request,
                slot_start_fingerprint=plan.slot_start_fingerprint,
                seed=seed,
                attempt_ordinal=attempt_ordinal,
                result_fingerprint=result_fingerprint,
            )
            candidates.append(
                {
                    "candidate_fingerprint": candidate_fingerprint,
                    "attempt_ordinal": attempt_ordinal,
                    "seed": seed,
                    "result_fingerprint": result_fingerprint,
                    "authoritative_input_fingerprint": authoritative_input_fingerprint,
                    "winner_player_id": result_payload["winner_player_id"],
                    "player_a_id": result_payload["player_a_id"],
                    "player_b_id": result_payload["player_b_id"],
                    "sets_won": result_payload["sets_won"],
                    "game_scores": [
                        {"player_a_points": a, "player_b_points": b}
                        for a, b in self._reconstruction_game_scores(staged.result)
                    ],
                    "match_elapsed_seconds": (
                        result_payload.get("timeline_log", {}) or {}
                    ).get("total_elapsed_seconds"),
                    "detail": result_payload,
                }
            )
            if len(candidates) >= request.candidate_count:
                break

        preview_fingerprint = fingerprint(
            {
                "schema": "authoritative_match_reconstruction_preview.v1",
                "request": request.model_dump(mode="json"),
                "slot_start_fingerprint": plan.slot_start_fingerprint,
                "event_id": event.event_id,
                "match_id": event.match_id,
                "players": list(players),
                "attempted": attempted,
                "candidate_fingerprints": [
                    item["candidate_fingerprint"] for item in candidates
                ],
            }
        )
        return {
            "schema_version": "authoritative_match_reconstruction_preview.v1",
            "run_id": request.run_id,
            "branch_id": request.branch_id,
            "week": request.expected_week.model_dump(mode="json"),
            "slot_id": slot.slot_id,
            "slot_start_fingerprint": plan.slot_start_fingerprint,
            "group_id": request.group_id,
            "event_id": package.event_id,
            "match_id": event.match_id,
            "player_a_id": players[0],
            "player_b_id": players[1],
            "candidate_count_requested": request.candidate_count,
            "candidate_count_found": len(candidates),
            "attempted_scenarios": attempted,
            "search_complete": len(candidates) == request.candidate_count,
            "constraints": request.constraints.model_dump(mode="json"),
            "candidates": candidates,
            "warnings": (
                []
                if len(candidates) == request.candidate_count
                else [
                    "Natural deterministic search did not fill the requested candidate count "
                    "within the bounded pre-alpha attempt budget. Forcing, nearest-match "
                    "search and probability estimates remain intentionally unsupported."
                ]
            ),
            "preview_fingerprint": preview_fingerprint,
        }

    def inspect_match_reconstruction(
        self, *, run_id: str, branch_id: str, group_id: str
    ) -> dict[str, Any]:
        """Read the current frozen match identity without persisting preview staging."""

        with self.factory() as session:
            self._require_writable_scope(session, run_id, branch_id)
            position = self._position(session, run_id, branch_id)
            branch = session.get(RunBranchModel, branch_id)
            if branch is None or not branch.saved_head_revision_id:
                raise ValueError("Match Reconstruction requires a saved Branch head")
            command = AuthoritativeSimulationCommand(
                command_id="match-reconstruction-inspection",
                run_id=run_id,
                branch_id=branch_id,
                expected_week=position.current_week,
                expected_position_fingerprint=position.position_fingerprint,
                expected_revision_id=branch.saved_head_revision_id,
                group_id=group_id,
            )
            packages, _ = self._authority_package(
                session, run_id, branch_id, position.current_week, adopt=True
            )
            self._ensure_current_slot(session, command, packages)
            current = self._position(session, run_id, branch_id)
            if group_id not in self._eligible_groups(session, current, packages):
                raise ValueError(
                    "reconstruction target is completed, blocked, or outside the current slot"
                )
            slot, plan, event, package, players = self._group_execution_context(
                session, command, packages, group_id
            )
            payload = {
                "run_id": run_id,
                "branch_id": branch_id,
                "week": position.current_week.model_dump(mode="json"),
                "expected_revision_id": branch.saved_head_revision_id,
                "position_fingerprint": position.position_fingerprint,
                "slot_id": slot.slot_id,
                "slot_start_fingerprint": plan.slot_start_fingerprint,
                "group_id": group_id,
                "event_id": package.event_id,
                "match_id": event.match_id,
                "player_a_id": players[0],
                "player_b_id": players[1],
            }
            session.rollback()
            return payload

    def preview_match_reconstruction(
        self, request: AuthoritativeMatchReconstructionPreviewRequest
    ) -> dict[str, Any]:
        """Generate deterministic matching candidates in a transaction that is rolled back."""

        with self.factory() as session:
            self._require_writable_scope(session, request.run_id, request.branch_id)
            before = self._position(session, request.run_id, request.branch_id)
            self._validate_expected(session, request, before)
            packages, _ = self._authority_package(
                session,
                request.run_id,
                request.branch_id,
                request.expected_week,
                adopt=True,
            )
            self._ensure_current_slot(session, request, packages)
            preview = self._build_match_reconstruction_preview(
                session, request, packages
            )
            session.rollback()
            return preview

    def commit_match_reconstruction(
        self, command: AuthoritativeMatchReconstructionCommitCommand
    ) -> dict[str, Any]:
        """Re-derive reviewed candidates and atomically commit only the explicit selection."""

        request_fp = fingerprint(
            {"mode": "match_reconstruction", "command": command.model_dump(mode="json")}
        )
        key = (command.run_id, command.branch_id, command.command_id)
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt is not None:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError(
                        "reconstruction command ID already has a different request"
                    )
                if receipt.status != "complete":
                    raise ValueError("reconstruction command receipt is incomplete")
                return json.loads(receipt.result_json)

            before = self._position(session, command.run_id, command.branch_id)
            self._validate_expected(session, command, before)
            packages, authority_fp = self._authority_package(
                session,
                command.run_id,
                command.branch_id,
                command.expected_week,
                adopt=True,
            )
            self._ensure_current_slot(session, command, packages)
            preview = self._build_match_reconstruction_preview(
                session, command.preview_request(), packages
            )
            if preview["preview_fingerprint"] != command.expected_preview_fingerprint:
                raise ValueError("Match Reconstruction preview is stale")
            selected = next(
                (
                    item
                    for item in preview["candidates"]
                    if item["candidate_fingerprint"]
                    == command.selected_candidate_fingerprint
                ),
                None,
            )
            if selected is None:
                raise ValueError(
                    "selected Match Reconstruction candidate is absent from reviewed preview"
                )

            staged = self._execute_group(
                session,
                command,
                packages,
                command.group_id,
                seed_override=selected["seed"],
            )
            if staged.result_fingerprint != selected["result_fingerprint"]:
                raise ValueError("selected reconstruction candidate did not replay exactly")

            group_row = session.get(
                SimulationEventGroupModel,
                (
                    command.run_id,
                    command.branch_id,
                    command.expected_week.ordinal,
                    preview["slot_id"],
                    command.group_id,
                ),
            )
            if group_row is None:
                raise ValueError("committed reconstruction group receipt is missing")
            group_payload = json.loads(group_row.payload_json)
            group_payload["match_reconstruction"] = {
                "schema_version": "match_reconstruction_commit_audit.v1",
                "preview_fingerprint": preview["preview_fingerprint"],
                "candidate_fingerprint": selected["candidate_fingerprint"],
                "constraints": command.constraints.model_dump(mode="json"),
                "operator_label": command.operator_label,
                "audit_reason": command.audit_reason,
            }
            group_row.payload_json = json.dumps(
                group_payload, sort_keys=True, separators=(",", ":")
            )

            self._advance_or_close(session, command, packages)
            after = self._position(session, command.run_id, command.branch_id)
            payload = {
                "schema_version": "authoritative_match_reconstruction_commit.v1",
                "run_id": command.run_id,
                "branch_id": command.branch_id,
                "group_id": command.group_id,
                "match_id": preview["match_id"],
                "candidate_fingerprint": selected["candidate_fingerprint"],
                "result_fingerprint": staged.result_fingerprint,
                "preview_fingerprint": preview["preview_fingerprint"],
                "operator_label": command.operator_label,
                "audit_reason": command.audit_reason,
                "authority_fingerprint": authority_fp,
                "position": after.model_dump(mode="json"),
                "adoption": "committed",
            }
            session.add(
                AuthoritativeSimulationCommandModel(
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    command_id=command.command_id,
                    request_fingerprint=request_fp,
                    status="complete",
                    result_json=json.dumps(
                        payload, sort_keys=True, separators=(",", ":")
                    ),
                )
            )
            session.flush()
            return payload

    def simulate_next_match(self, command: AuthoritativeSimulationCommand):
        return self._mutate(command, mode="match")

    def simulate_next_slot(
        self, command: AuthoritativeSimulationCommand, *, fault_at: str | None = None
    ):
        return self._mutate(command, mode="slot", fault_at=fault_at)

    def preview_next_match_day(self, *, run_id: str, branch_id: str) -> dict:
        """Freeze the exact remaining global slots of the current canonical Match Day."""

        with self.factory() as session:
            return self._next_match_day_plan(
                session,
                run_id=run_id,
                branch_id=branch_id,
            )

    @staticmethod
    def _match_day_child_command_id(parent_command_id: str, slot_ordinal: int) -> str:
        digest = hashlib.sha256(
            f"{parent_command_id}|match-day-slot|{slot_ordinal}".encode()
        ).hexdigest()[:24]
        return f"match-day-slot:{digest}"

    def simulate_next_match_day(self, command: AuthoritativeMatchDayCommand) -> dict:
        """Execute one frozen Match Day as resumable authoritative Next Slot children.

        Match Day orchestration deliberately reuses the existing authoritative slot
        command instead of inventing a second execution path. The parent receipt
        persists every child command payload before that child starts, so an
        interruption can resume the exact same command while external chronology
        drift fails closed.
        """

        request_fp = fingerprint(
            {"mode": "match_day", "command": command.model_dump(mode="json")}
        )
        key = (command.run_id, command.branch_id, command.command_id)

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt is not None:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError(
                        "Match Day command ID already has a different request"
                    )
                if receipt.status == "complete":
                    return json.loads(receipt.result_json)
                if receipt.status != "pending":
                    raise ValueError("Match Day command receipt has an invalid status")
                frozen = json.loads(receipt.result_json)
            else:
                before = self._position(session, command.run_id, command.branch_id)
                self._validate_expected(session, command, before)
                plan = self._next_match_day_plan(
                    session,
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                )
                child_commands = {
                    str(slot_ordinal): None
                    for slot_ordinal in plan["target_slot_ordinals"]
                }
                frozen = {
                    "schema_version": "authoritative_match_day_operation.v1",
                    "run_id": command.run_id,
                    "branch_id": command.branch_id,
                    "week": command.expected_week.model_dump(mode="json"),
                    "match_day_ordinal": plan["match_day_ordinal"],
                    "schedule_fingerprint": plan["schedule_fingerprint"],
                    "target_slot_ordinals": plan["target_slot_ordinals"],
                    "target_group_ids": plan["target_group_ids"],
                    "child_commands": child_commands,
                }
                session.add(
                    AuthoritativeSimulationCommandModel(
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        command_id=command.command_id,
                        request_fingerprint=request_fp,
                        status="pending",
                        result_json=json.dumps(
                            frozen, sort_keys=True, separators=(",", ":")
                        ),
                    )
                )

        target_ordinals = tuple(int(x) for x in frozen["target_slot_ordinals"])
        for slot_ordinal in target_ordinals:
            with self.factory.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                self._require_writable_scope(
                    session, command.run_id, command.branch_id
                )
                parent = session.get(AuthoritativeSimulationCommandModel, key)
                if parent is None or parent.request_fingerprint != request_fp:
                    raise ValueError("Match Day parent receipt disappeared")
                if parent.status == "complete":
                    return json.loads(parent.result_json)

                current_frozen = json.loads(parent.result_json)
                schedule = self._schedule(
                    session,
                    command.run_id,
                    command.branch_id,
                    command.expected_week,
                )
                if (
                    schedule is None
                    or schedule.fingerprint
                    != current_frozen["schedule_fingerprint"]
                ):
                    raise ValueError("Match Day schedule changed during orchestration")
                branch = session.get(RunBranchModel, command.branch_id)
                if (
                    branch is None
                    or branch.run_id != command.run_id
                    or branch.saved_head_revision_id != command.expected_revision_id
                ):
                    raise ValueError("expected Branch head is stale")

                stored_child = current_frozen["child_commands"].get(
                    str(slot_ordinal)
                )
                if stored_child is None:
                    position = self._position(
                        session, command.run_id, command.branch_id
                    )
                    if position.current_week != command.expected_week:
                        raise ValueError("Match Day orchestration crossed a week boundary")
                    if (
                        position.current_slot_kind != "match"
                        or position.slot_ordinal != slot_ordinal
                    ):
                        raise ValueError(
                            "Match Day chronology drifted before the next frozen slot"
                        )
                    child = AuthoritativeSimulationCommand(
                        command_id=self._match_day_child_command_id(
                            command.command_id, slot_ordinal
                        ),
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        expected_week=command.expected_week,
                        expected_position_fingerprint=position.position_fingerprint,
                        expected_revision_id=command.expected_revision_id,
                    )
                    current_frozen["child_commands"][str(slot_ordinal)] = (
                        child.model_dump(mode="json")
                    )
                    parent.result_json = json.dumps(
                        current_frozen, sort_keys=True, separators=(",", ":")
                    )
                else:
                    child = AuthoritativeSimulationCommand.model_validate(
                        stored_child
                    )

            self.simulate_next_slot(child)

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            parent = session.get(AuthoritativeSimulationCommandModel, key)
            if parent is None or parent.request_fingerprint != request_fp:
                raise ValueError("Match Day parent receipt disappeared")
            if parent.status == "complete":
                return json.loads(parent.result_json)
            frozen = json.loads(parent.result_json)

            schedule = self._schedule(
                session,
                command.run_id,
                command.branch_id,
                command.expected_week,
            )
            if schedule is None or schedule.fingerprint != frozen["schedule_fingerprint"]:
                raise ValueError("Match Day schedule changed during orchestration")
            branch = session.get(RunBranchModel, command.branch_id)
            if (
                branch is None
                or branch.run_id != command.run_id
                or branch.saved_head_revision_id != command.expected_revision_id
            ):
                raise ValueError("expected Branch head is stale")

            for slot_ordinal in target_ordinals:
                child_payload = frozen["child_commands"].get(str(slot_ordinal))
                if child_payload is None:
                    raise ValueError("Match Day child command was not frozen")
                child_id = child_payload["command_id"]
                child_receipt = session.get(
                    AuthoritativeSimulationCommandModel,
                    (command.run_id, command.branch_id, child_id),
                )
                if child_receipt is None or child_receipt.status != "complete":
                    raise ValueError("Match Day child command is incomplete")

            after = self._position(session, command.run_id, command.branch_id)
            if after.current_slot_kind == "match" and after.slot_ordinal is not None:
                remaining_spec = next(
                    (
                        slot
                        for slot in schedule.slots
                        if slot.ordinal == after.slot_ordinal
                    ),
                    None,
                )
                if (
                    remaining_spec is not None
                    and remaining_spec.match_day_ordinal
                    == frozen["match_day_ordinal"]
                ):
                    raise ValueError(
                        "Match Day orchestration left a frozen same-day slot unresolved"
                    )

            payload = {
                "schema_version": "authoritative_match_day_result.v1",
                "run_id": command.run_id,
                "branch_id": command.branch_id,
                "week": command.expected_week.model_dump(mode="json"),
                "match_day_ordinal": frozen["match_day_ordinal"],
                "schedule_fingerprint": frozen["schedule_fingerprint"],
                "target_slot_ordinals": list(target_ordinals),
                "target_group_ids": list(frozen["target_group_ids"]),
                "child_command_ids": [
                    frozen["child_commands"][str(slot_ordinal)]["command_id"]
                    for slot_ordinal in target_ordinals
                ],
                "completed_slot_count": len(target_ordinals),
                "position": after.model_dump(mode="json"),
                "adoption": "committed",
            }
            parent.status = "complete"
            parent.result_json = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            )
            session.flush()
            return payload

    def preview_next_round(self, *, run_id: str, branch_id: str) -> dict:
        """Freeze the current round identity and the chronology required to finish it."""

        with self.factory() as session:
            return self._next_round_plan(
                session,
                run_id=run_id,
                branch_id=branch_id,
            )

    @staticmethod
    def _round_child_command_id(parent_command_id: str, slot_ordinal: int) -> str:
        digest = hashlib.sha256(
            f"{parent_command_id}|round-slot|{slot_ordinal}".encode()
        ).hexdigest()[:24]
        return f"round-slot:{digest}"

    def simulate_next_round(self, command: AuthoritativeRoundCommand) -> dict:
        """Finish the nearest unfinished canonical round without skipping chronology.

        The round target is the current V2 schedule identity
        (event_id, draw_phase, round_number). Every global match slot from the
        current position through the last remaining slot of that round is frozen in
        one durable parent operation. Interleaved matches from other tournament
        identities are transit slots: they execute only because global Simulation
        Slot chronology cannot be skipped.
        """

        request_fp = fingerprint(
            {"mode": "round", "command": command.model_dump(mode="json")}
        )
        key = (command.run_id, command.branch_id, command.command_id)

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt is not None:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError("Round command ID already has a different request")
                if receipt.status == "complete":
                    return json.loads(receipt.result_json)
                if receipt.status != "pending":
                    raise ValueError("Round command receipt has an invalid status")
                frozen = json.loads(receipt.result_json)
            else:
                before = self._position(session, command.run_id, command.branch_id)
                self._validate_expected(session, command, before)
                plan = self._next_round_plan(
                    session,
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                )
                child_commands = {
                    str(slot_ordinal): None
                    for slot_ordinal in plan["horizon_slot_ordinals"]
                }
                frozen = {
                    "schema_version": "authoritative_round_operation.v1",
                    "run_id": command.run_id,
                    "branch_id": command.branch_id,
                    "week": command.expected_week.model_dump(mode="json"),
                    "round_identity": plan["round_identity"],
                    "schedule_fingerprint": plan["schedule_fingerprint"],
                    "target_slot_ordinals": plan["target_slot_ordinals"],
                    "target_group_ids": plan["target_group_ids"],
                    "horizon_slot_ordinals": plan["horizon_slot_ordinals"],
                    "transit_slot_ordinals": plan["transit_slot_ordinals"],
                    "transit_group_ids": plan["transit_group_ids"],
                    "child_commands": child_commands,
                }
                session.add(
                    AuthoritativeSimulationCommandModel(
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        command_id=command.command_id,
                        request_fingerprint=request_fp,
                        status="pending",
                        result_json=json.dumps(
                            frozen, sort_keys=True, separators=(",", ":")
                        ),
                    )
                )

        horizon_ordinals = tuple(
            int(x) for x in frozen["horizon_slot_ordinals"]
        )
        for slot_ordinal in horizon_ordinals:
            with self.factory.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                self._require_writable_scope(
                    session, command.run_id, command.branch_id
                )
                parent = session.get(AuthoritativeSimulationCommandModel, key)
                if parent is None or parent.request_fingerprint != request_fp:
                    raise ValueError("Round parent receipt disappeared")
                if parent.status == "complete":
                    return json.loads(parent.result_json)

                current_frozen = json.loads(parent.result_json)
                schedule = self._schedule(
                    session,
                    command.run_id,
                    command.branch_id,
                    command.expected_week,
                )
                if (
                    schedule is None
                    or schedule.fingerprint
                    != current_frozen["schedule_fingerprint"]
                ):
                    raise ValueError("Round schedule changed during orchestration")
                branch = session.get(RunBranchModel, command.branch_id)
                if (
                    branch is None
                    or branch.run_id != command.run_id
                    or branch.saved_head_revision_id != command.expected_revision_id
                ):
                    raise ValueError("expected Branch head is stale")

                stored_child = current_frozen["child_commands"].get(
                    str(slot_ordinal)
                )
                if stored_child is None:
                    position = self._position(
                        session, command.run_id, command.branch_id
                    )
                    if position.current_week != command.expected_week:
                        raise ValueError("Round orchestration crossed a week boundary")
                    if (
                        position.current_slot_kind != "match"
                        or position.slot_ordinal != slot_ordinal
                    ):
                        raise ValueError(
                            "Round chronology drifted before the next frozen slot"
                        )
                    child = AuthoritativeSimulationCommand(
                        command_id=self._round_child_command_id(
                            command.command_id, slot_ordinal
                        ),
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        expected_week=command.expected_week,
                        expected_position_fingerprint=position.position_fingerprint,
                        expected_revision_id=command.expected_revision_id,
                    )
                    current_frozen["child_commands"][str(slot_ordinal)] = (
                        child.model_dump(mode="json")
                    )
                    parent.result_json = json.dumps(
                        current_frozen, sort_keys=True, separators=(",", ":")
                    )
                else:
                    child = AuthoritativeSimulationCommand.model_validate(
                        stored_child
                    )

            self.simulate_next_slot(child)

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            parent = session.get(AuthoritativeSimulationCommandModel, key)
            if parent is None or parent.request_fingerprint != request_fp:
                raise ValueError("Round parent receipt disappeared")
            if parent.status == "complete":
                return json.loads(parent.result_json)
            frozen = json.loads(parent.result_json)

            schedule = self._schedule(
                session,
                command.run_id,
                command.branch_id,
                command.expected_week,
            )
            if schedule is None or schedule.fingerprint != frozen["schedule_fingerprint"]:
                raise ValueError("Round schedule changed during orchestration")
            branch = session.get(RunBranchModel, command.branch_id)
            if (
                branch is None
                or branch.run_id != command.run_id
                or branch.saved_head_revision_id != command.expected_revision_id
            ):
                raise ValueError("expected Branch head is stale")

            for slot_ordinal in horizon_ordinals:
                child_payload = frozen["child_commands"].get(str(slot_ordinal))
                if child_payload is None:
                    raise ValueError("Round child command was not frozen")
                child_id = child_payload["command_id"]
                child_receipt = session.get(
                    AuthoritativeSimulationCommandModel,
                    (command.run_id, command.branch_id, child_id),
                )
                if child_receipt is None or child_receipt.status != "complete":
                    raise ValueError("Round child command is incomplete")

            after = self._position(session, command.run_id, command.branch_id)
            last_horizon_ordinal = horizon_ordinals[-1]
            if (
                after.current_slot_kind == "match"
                and after.slot_ordinal is not None
                and after.slot_ordinal <= last_horizon_ordinal
            ):
                raise ValueError(
                    "Round orchestration left its frozen chronology horizon unresolved"
                )

            payload = {
                "schema_version": "authoritative_round_result.v1",
                "run_id": command.run_id,
                "branch_id": command.branch_id,
                "week": command.expected_week.model_dump(mode="json"),
                "round_identity": frozen["round_identity"],
                "schedule_fingerprint": frozen["schedule_fingerprint"],
                "target_slot_ordinals": list(frozen["target_slot_ordinals"]),
                "target_group_ids": list(frozen["target_group_ids"]),
                "horizon_slot_ordinals": list(horizon_ordinals),
                "transit_slot_ordinals": list(frozen["transit_slot_ordinals"]),
                "transit_group_ids": list(frozen["transit_group_ids"]),
                "child_command_ids": [
                    frozen["child_commands"][str(slot_ordinal)]["command_id"]
                    for slot_ordinal in horizon_ordinals
                ],
                "completed_slot_count": len(horizon_ordinals),
                "position": after.model_dump(mode="json"),
                "adoption": "committed",
            }
            parent.status = "complete"
            parent.result_json = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            )
            session.flush()
            return payload

    def preview_next_tournament(self, *, run_id: str, branch_id: str) -> dict:
        """Freeze the current tournament and chronology required to finish it."""

        with self.factory() as session:
            return self._next_tournament_plan(
                session,
                run_id=run_id,
                branch_id=branch_id,
            )

    @staticmethod
    def _tournament_child_command_id(
        parent_command_id: str, slot_ordinal: int
    ) -> str:
        digest = hashlib.sha256(
            f"{parent_command_id}|tournament-slot|{slot_ordinal}".encode()
        ).hexdigest()[:24]
        return f"tournament-slot:{digest}"

    def simulate_next_tournament(
        self, command: AuthoritativeTournamentCommand
    ) -> dict:
        """Finish the current canonical tournament without skipping global chronology."""

        request_fp = fingerprint(
            {"mode": "tournament", "command": command.model_dump(mode="json")}
        )
        key = (command.run_id, command.branch_id, command.command_id)

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt is not None:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError(
                        "Tournament command ID already has a different request"
                    )
                if receipt.status == "complete":
                    return json.loads(receipt.result_json)
                if receipt.status != "pending":
                    raise ValueError(
                        "Tournament command receipt has an invalid status"
                    )
                frozen = json.loads(receipt.result_json)
            else:
                before = self._position(session, command.run_id, command.branch_id)
                self._validate_expected(session, command, before)
                plan = self._next_tournament_plan(
                    session,
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                )
                frozen = {
                    "schema_version": "authoritative_tournament_operation.v1",
                    "run_id": command.run_id,
                    "branch_id": command.branch_id,
                    "week": command.expected_week.model_dump(mode="json"),
                    "event_id": plan["event_id"],
                    "schedule_fingerprint": plan["schedule_fingerprint"],
                    "target_slot_ordinals": plan["target_slot_ordinals"],
                    "target_group_ids": plan["target_group_ids"],
                    "horizon_slot_ordinals": plan["horizon_slot_ordinals"],
                    "transit_slot_ordinals": plan["transit_slot_ordinals"],
                    "transit_group_ids": plan["transit_group_ids"],
                    "child_commands": {
                        str(slot_ordinal): None
                        for slot_ordinal in plan["horizon_slot_ordinals"]
                    },
                }
                session.add(
                    AuthoritativeSimulationCommandModel(
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        command_id=command.command_id,
                        request_fingerprint=request_fp,
                        status="pending",
                        result_json=json.dumps(
                            frozen, sort_keys=True, separators=(",", ":")
                        ),
                    )
                )

        horizon_ordinals = tuple(
            int(value) for value in frozen["horizon_slot_ordinals"]
        )
        for slot_ordinal in horizon_ordinals:
            with self.factory.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                self._require_writable_scope(
                    session, command.run_id, command.branch_id
                )
                parent = session.get(AuthoritativeSimulationCommandModel, key)
                if parent is None or parent.request_fingerprint != request_fp:
                    raise ValueError("Tournament parent receipt disappeared")
                if parent.status == "complete":
                    return json.loads(parent.result_json)

                current_frozen = json.loads(parent.result_json)
                schedule = self._schedule(
                    session,
                    command.run_id,
                    command.branch_id,
                    command.expected_week,
                )
                if (
                    schedule is None
                    or schedule.fingerprint
                    != current_frozen["schedule_fingerprint"]
                ):
                    raise ValueError(
                        "Tournament schedule changed during orchestration"
                    )
                branch = session.get(RunBranchModel, command.branch_id)
                if (
                    branch is None
                    or branch.run_id != command.run_id
                    or branch.saved_head_revision_id != command.expected_revision_id
                ):
                    raise ValueError("expected Branch head is stale")

                stored_child = current_frozen["child_commands"].get(
                    str(slot_ordinal)
                )
                if stored_child is None:
                    position = self._position(
                        session, command.run_id, command.branch_id
                    )
                    if position.current_week != command.expected_week:
                        raise ValueError(
                            "Tournament orchestration crossed a week boundary"
                        )
                    if (
                        position.current_slot_kind != "match"
                        or position.slot_ordinal != slot_ordinal
                    ):
                        raise ValueError(
                            "Tournament chronology drifted before the next frozen slot"
                        )
                    child = AuthoritativeSimulationCommand(
                        command_id=self._tournament_child_command_id(
                            command.command_id, slot_ordinal
                        ),
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        expected_week=command.expected_week,
                        expected_position_fingerprint=position.position_fingerprint,
                        expected_revision_id=command.expected_revision_id,
                    )
                    current_frozen["child_commands"][str(slot_ordinal)] = (
                        child.model_dump(mode="json")
                    )
                    parent.result_json = json.dumps(
                        current_frozen, sort_keys=True, separators=(",", ":")
                    )
                else:
                    child = AuthoritativeSimulationCommand.model_validate(
                        stored_child
                    )

            self.simulate_next_slot(child)

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            parent = session.get(AuthoritativeSimulationCommandModel, key)
            if parent is None or parent.request_fingerprint != request_fp:
                raise ValueError("Tournament parent receipt disappeared")
            if parent.status == "complete":
                return json.loads(parent.result_json)
            frozen = json.loads(parent.result_json)

            schedule = self._schedule(
                session,
                command.run_id,
                command.branch_id,
                command.expected_week,
            )
            if schedule is None or schedule.fingerprint != frozen["schedule_fingerprint"]:
                raise ValueError(
                    "Tournament schedule changed during orchestration"
                )
            branch = session.get(RunBranchModel, command.branch_id)
            if (
                branch is None
                or branch.run_id != command.run_id
                or branch.saved_head_revision_id != command.expected_revision_id
            ):
                raise ValueError("expected Branch head is stale")

            for slot_ordinal in horizon_ordinals:
                child_payload = frozen["child_commands"].get(str(slot_ordinal))
                if child_payload is None:
                    raise ValueError("Tournament child command was not frozen")
                child_receipt = session.get(
                    AuthoritativeSimulationCommandModel,
                    (
                        command.run_id,
                        command.branch_id,
                        child_payload["command_id"],
                    ),
                )
                if child_receipt is None or child_receipt.status != "complete":
                    raise ValueError("Tournament child command is incomplete")

            after = self._position(session, command.run_id, command.branch_id)
            if (
                after.current_slot_kind == "match"
                and after.slot_ordinal is not None
                and after.slot_ordinal <= horizon_ordinals[-1]
            ):
                raise ValueError(
                    "Tournament orchestration left its frozen chronology horizon unresolved"
                )

            sources = OwnedTournamentRankingSourceStore(session).history(
                run_id=command.run_id,
                branch_id=command.branch_id,
            )
            target_sources = tuple(
                source
                for source in sources
                if source.binding.event_id == frozen["event_id"]
            )
            if len(target_sources) != 1:
                raise ValueError(
                    "Tournament orchestration did not close exactly one target "
                    "Owned Tournament Ranking Source"
                )
            source = target_sources[0]
            payload = {
                "schema_version": "authoritative_tournament_result.v1",
                "run_id": command.run_id,
                "branch_id": command.branch_id,
                "week": command.expected_week.model_dump(mode="json"),
                "event_id": frozen["event_id"],
                "schedule_fingerprint": frozen["schedule_fingerprint"],
                "target_slot_ordinals": list(frozen["target_slot_ordinals"]),
                "target_group_ids": list(frozen["target_group_ids"]),
                "horizon_slot_ordinals": list(horizon_ordinals),
                "transit_slot_ordinals": list(frozen["transit_slot_ordinals"]),
                "transit_group_ids": list(frozen["transit_group_ids"]),
                "child_command_ids": [
                    frozen["child_commands"][str(slot_ordinal)]["command_id"]
                    for slot_ordinal in horizon_ordinals
                ],
                "completed_slot_count": len(horizon_ordinals),
                "owned_tournament_source_fingerprint": source.fingerprint,
                "position": after.model_dump(mode="json"),
                "adoption": "committed",
            }
            parent.status = "complete"
            parent.result_json = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            )
            session.flush()
            return payload

    def preview_next_week(self, request: AuthoritativeWeekPreviewRequest) -> dict:
        """Freeze the current week and its canonical transition prerequisites."""

        with self.factory() as session:
            return self._next_week_plan(session, request=request)

    @staticmethod
    def _week_slot_child_command_id(
        parent_command_id: str, slot_ordinal: int
    ) -> str:
        digest = hashlib.sha256(
            f"{parent_command_id}|week-slot|{slot_ordinal}".encode()
        ).hexdigest()[:24]
        return f"week-slot:{digest}"

    @staticmethod
    def _week_authority_child_command_id(parent_command_id: str) -> str:
        digest = hashlib.sha256(
            f"{parent_command_id}|week-ranking-authority".encode()
        ).hexdigest()[:24]
        return f"week-authority:{digest}"

    @staticmethod
    def _week_transition_child_command_id(parent_command_id: str) -> str:
        digest = hashlib.sha256(
            f"{parent_command_id}|week-transition".encode()
        ).hexdigest()[:24]
        return f"week-transition:{digest}"

    def simulate_next_week(self, command: AuthoritativeWeekCommand) -> dict:
        """Finish current-week sport and publish the canonical Week Transition."""

        request_fp = fingerprint(
            {"mode": "week", "command": command.model_dump(mode="json")}
        )
        key = (command.run_id, command.branch_id, command.command_id)

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt is not None:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError("Week command ID already has a different request")
                if receipt.status == "complete":
                    return json.loads(receipt.result_json)
                if receipt.status != "pending":
                    raise ValueError("Week command receipt has an invalid status")
                frozen = json.loads(receipt.result_json)
            else:
                before = self._position(session, command.run_id, command.branch_id)
                self._validate_expected(session, command, before)
                preview_request = AuthoritativeWeekPreviewRequest(
                    command_id=command.command_id,
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    operator_label=command.operator_label,
                    audit_reason=command.audit_reason,
                )
                plan = self._next_week_plan(session, request=preview_request)
                if plan["preview_fingerprint"] != command.expected_preview_fingerprint:
                    raise ValueError("Next Week preview changed before commit")
                if plan["week"] != command.expected_week.model_dump(mode="json"):
                    raise ValueError("Next Week reviewed Ranking Week is stale")
                if plan["expected_revision_id"] != command.expected_revision_id:
                    raise ValueError("Next Week reviewed Saved Revision is stale")

                target_week = RankingWeek.model_validate(plan["target_week"])
                authority_store = RankingTransitionAuthorityStore(session)
                authority = authority_store.get(
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    target_ordinal=target_week.ordinal,
                )
                if authority is None:
                    authority = derive_ranking_transition_authority(
                        session,
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        command_id=plan["ranking_authority_command_id"],
                        audit=command.audit,
                    )
                    if (
                        authority.fingerprint
                        != plan["ranking_authority_fingerprint"]
                    ):
                        raise ValueError(
                            "Next Week Ranking Transition Authority changed "
                            "since preview"
                        )
                    authority = authority_store.append(authority)
                elif authority.fingerprint != plan["ranking_authority_fingerprint"]:
                    raise ValueError(
                        "Next Week existing Ranking Transition Authority changed"
                    )

                frozen = {
                    "schema_version": "authoritative_week_operation.v1",
                    "run_id": command.run_id,
                    "branch_id": command.branch_id,
                    "week": plan["week"],
                    "target_week": plan["target_week"],
                    "schedule_fingerprint": plan["schedule_fingerprint"],
                    "target_slot_ordinals": plan["target_slot_ordinals"],
                    "target_group_ids": plan["target_group_ids"],
                    "ranking_authority_mode": plan["ranking_authority_mode"],
                    "ranking_authority_command_id": plan[
                        "ranking_authority_command_id"
                    ],
                    "ranking_authority_fingerprint": authority.fingerprint,
                    "child_commands": {
                        str(slot_ordinal): None
                        for slot_ordinal in plan["target_slot_ordinals"]
                    },
                    "week_transition": None,
                }
                session.add(
                    AuthoritativeSimulationCommandModel(
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        command_id=command.command_id,
                        request_fingerprint=request_fp,
                        status="pending",
                        result_json=json.dumps(
                            frozen, sort_keys=True, separators=(",", ":")
                        ),
                    )
                )

        target_ordinals = tuple(int(x) for x in frozen["target_slot_ordinals"])
        for slot_ordinal in target_ordinals:
            with self.factory.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                self._require_writable_scope(
                    session, command.run_id, command.branch_id
                )
                parent = session.get(AuthoritativeSimulationCommandModel, key)
                if parent is None or parent.request_fingerprint != request_fp:
                    raise ValueError("Week parent receipt disappeared")
                if parent.status == "complete":
                    return json.loads(parent.result_json)

                current_frozen = json.loads(parent.result_json)
                stored_child = current_frozen["child_commands"].get(
                    str(slot_ordinal)
                )
                if stored_child is None:
                    schedule = self._schedule(
                        session,
                        command.run_id,
                        command.branch_id,
                        command.expected_week,
                    )
                    if (
                        schedule is None
                        or schedule.fingerprint
                        != current_frozen["schedule_fingerprint"]
                    ):
                        raise ValueError("Week Schedule changed during Next Week")
                    branch = session.get(RunBranchModel, command.branch_id)
                    if (
                        branch is None
                        or branch.run_id != command.run_id
                        or branch.saved_head_revision_id
                        != command.expected_revision_id
                    ):
                        raise ValueError("expected Branch head is stale")
                    position = self._position(
                        session, command.run_id, command.branch_id
                    )
                    if position.current_week != command.expected_week:
                        raise ValueError(
                            "Next Week crossed Week Transition before its "
                            "sporting children completed"
                        )
                    if (
                        position.current_slot_kind != "match"
                        or position.slot_ordinal != slot_ordinal
                    ):
                        raise ValueError(
                            "Next Week chronology drifted before the next frozen slot"
                        )
                    child = AuthoritativeSimulationCommand(
                        command_id=self._week_slot_child_command_id(
                            command.command_id, slot_ordinal
                        ),
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        expected_week=command.expected_week,
                        expected_position_fingerprint=position.position_fingerprint,
                        expected_revision_id=command.expected_revision_id,
                    )
                    current_frozen["child_commands"][str(slot_ordinal)] = (
                        child.model_dump(mode="json")
                    )
                    parent.result_json = json.dumps(
                        current_frozen, sort_keys=True, separators=(",", ":")
                    )
                else:
                    child = AuthoritativeSimulationCommand.model_validate(
                        stored_child
                    )

            self.simulate_next_slot(child)

        transition_payload = None
        transition_command_payload = None
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            parent = session.get(AuthoritativeSimulationCommandModel, key)
            if parent is None or parent.request_fingerprint != request_fp:
                raise ValueError("Week parent receipt disappeared")
            if parent.status == "complete":
                return json.loads(parent.result_json)
            frozen = json.loads(parent.result_json)
            transition_payload = frozen.get("week_transition")

            if transition_payload is None:
                position = self._position(
                    session, command.run_id, command.branch_id
                )
                if position.current_week != command.expected_week:
                    raise ValueError(
                        "Next Week source week changed before transition was frozen"
                    )
                if not position.week_ready_for_transition:
                    return {
                        "schema_version": "authoritative_week_progress.v1",
                        "status": "blocked",
                        "run_id": command.run_id,
                        "branch_id": command.branch_id,
                        "completed_week": command.expected_week.model_dump(
                            mode="json"
                        ),
                        "target_week": frozen["target_week"],
                        "target_slot_ordinals": list(target_ordinals),
                        "completed_slot_count": len(target_ordinals),
                        "transition_blockers": list(position.transition_blockers),
                        "position": position.model_dump(mode="json"),
                    }

                transition_command = derive_persisted_week_transition_command(
                    session,
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    command_id=self._week_transition_child_command_id(
                        command.command_id
                    ),
                )
                if (
                    transition_command.completed_week != command.expected_week
                    or transition_command.target_week.model_dump(mode="json")
                    != frozen["target_week"]
                    or transition_command.authority_fingerprint
                    != frozen["ranking_authority_fingerprint"]
                ):
                    raise ValueError(
                        "Next Week Week Transition boundary changed before execution"
                    )
                transition_command_payload = transition_command.model_dump(
                    mode="json"
                )

        if transition_payload is None:
            transition_command = AuthoritativeWeekTransitionCommand.model_validate_json(
                json.dumps(transition_command_payload)
            )
            transition_preview = AuthoritativeWeekTransitionRunner(
                self.factory, self.awards_service
            ).preview(transition_command)
            candidate_transition_payload = {
                "command": transition_command.model_dump(mode="json"),
                "request_fingerprint": transition_command.fingerprint,
                "expected_ranking_fingerprint": (
                    transition_preview.official_ranking_fingerprint
                ),
                "expected_lifecycle_fingerprint": (
                    transition_preview.player_lifecycle_fingerprint
                ),
                "expected_sporting_fingerprint": (
                    transition_preview.player_sporting_fingerprint
                ),
            }

            with self.factory.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                self._require_writable_scope(
                    session, command.run_id, command.branch_id
                )
                parent = session.get(AuthoritativeSimulationCommandModel, key)
                if parent is None or parent.request_fingerprint != request_fp:
                    raise ValueError("Week parent receipt disappeared")
                if parent.status == "complete":
                    return json.loads(parent.result_json)
                frozen = json.loads(parent.result_json)
                transition_payload = frozen.get("week_transition")
                if transition_payload is None:
                    position = self._position(
                        session, command.run_id, command.branch_id
                    )
                    if (
                        position.current_week != command.expected_week
                        or not position.week_ready_for_transition
                    ):
                        raise ValueError(
                            "Next Week transition readiness changed during preview"
                        )
                    current_transition = derive_persisted_week_transition_command(
                        session,
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        command_id=self._week_transition_child_command_id(
                            command.command_id
                        ),
                    )
                    if current_transition.fingerprint != transition_command.fingerprint:
                        raise ValueError(
                            "Next Week Week Transition changed during preview"
                        )
                    frozen["week_transition"] = candidate_transition_payload
                    parent.result_json = json.dumps(
                        frozen, sort_keys=True, separators=(",", ":")
                    )
                    transition_payload = candidate_transition_payload

        transition_command = AuthoritativeWeekTransitionCommand.model_validate_json(
            json.dumps(transition_payload["command"])
        )
        transition_result = AuthoritativeWeekTransitionRunner(
            self.factory, self.awards_service
        ).execute(
            transition_command,
            expected_ranking_fingerprint=transition_payload[
                "expected_ranking_fingerprint"
            ],
            expected_lifecycle_fingerprint=transition_payload[
                "expected_lifecycle_fingerprint"
            ],
            expected_sporting_fingerprint=transition_payload[
                "expected_sporting_fingerprint"
            ],
        )

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            parent = session.get(AuthoritativeSimulationCommandModel, key)
            if parent is None or parent.request_fingerprint != request_fp:
                raise ValueError("Week parent receipt disappeared")
            if parent.status == "complete":
                return json.loads(parent.result_json)
            frozen = json.loads(parent.result_json)
            if (
                transition_result.completed_week != command.expected_week
                or transition_result.target_week.model_dump(mode="json")
                != frozen["target_week"]
                or transition_result.official_ranking_fingerprint
                != transition_payload["expected_ranking_fingerprint"]
                or transition_result.player_lifecycle_fingerprint
                != transition_payload["expected_lifecycle_fingerprint"]
                or transition_result.player_sporting_fingerprint
                != transition_payload["expected_sporting_fingerprint"]
            ):
                raise ValueError(
                    "Next Week transition result differs from frozen preview"
                )

            payload = {
                "schema_version": "authoritative_week_result.v1",
                "status": "complete",
                "run_id": command.run_id,
                "branch_id": command.branch_id,
                "completed_week": command.expected_week.model_dump(mode="json"),
                "target_week": frozen["target_week"],
                "schedule_fingerprint": frozen["schedule_fingerprint"],
                "target_slot_ordinals": list(target_ordinals),
                "target_group_ids": list(frozen["target_group_ids"]),
                "child_command_ids": [
                    frozen["child_commands"][str(slot_ordinal)]["command_id"]
                    for slot_ordinal in target_ordinals
                ],
                "completed_slot_count": len(target_ordinals),
                "ranking_authority_mode": frozen["ranking_authority_mode"],
                "ranking_authority_command_id": frozen[
                    "ranking_authority_command_id"
                ],
                "ranking_authority_fingerprint": frozen[
                    "ranking_authority_fingerprint"
                ],
                "week_transition_command_id": transition_result.command_id,
                "week_transition_request_fingerprint": transition_payload[
                    "request_fingerprint"
                ],
                "official_ranking_fingerprint": (
                    transition_result.official_ranking_fingerprint
                ),
                "player_lifecycle_fingerprint": (
                    transition_result.player_lifecycle_fingerprint
                ),
                "player_sporting_fingerprint": (
                    transition_result.player_sporting_fingerprint
                ),
                "world_event_kind": transition_result.world_event_kind,
                "adoption": "committed",
            }
            parent.status = "complete"
            parent.result_json = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            )
            session.flush()
            return payload

    def preview_next_season(
        self, request: AuthoritativeSeasonPreviewRequest
    ) -> dict:
        """Review one progressive season range without mutating future weeks."""

        with self.factory() as session:
            return self._next_season_plan(session, request=request)

    @staticmethod
    def _season_week_child_command_id(
        parent_command_id: str, week: RankingWeek
    ) -> str:
        digest = hashlib.sha256(
            f"{parent_command_id}|season-week|{week.ordinal}".encode()
        ).hexdigest()[:24]
        return f"season-week:{digest}"

    @staticmethod
    def _season_empty_week_child_command_id(
        parent_command_id: str, week: RankingWeek
    ) -> str:
        digest = hashlib.sha256(
            f"{parent_command_id}|season-empty-week|{week.ordinal}".encode()
        ).hexdigest()[:24]
        return f"season-empty:{digest}"

    @staticmethod
    def _season_week61_slot_child_command_id(
        parent_command_id: str, slot_ordinal: int
    ) -> str:
        digest = hashlib.sha256(
            f"{parent_command_id}|season-week61-slot|{slot_ordinal}".encode()
        ).hexdigest()[:24]
        return f"season-w61-slot:{digest}"

    @staticmethod
    def _season_progress_payload(
        *,
        command: AuthoritativeSeasonCommand,
        frozen: dict,
        position: AuthoritativeSimulationPosition,
        checkpoint: str,
        blockers: tuple[str, ...] = (),
        detail: str | None = None,
        season_transition_preflight: dict | None = None,
    ) -> dict:
        payload = {
            "schema_version": "authoritative_season_progress.v1",
            "status": "blocked",
            "run_id": command.run_id,
            "branch_id": command.branch_id,
            "start_week": frozen["start_week"],
            "current_week": position.current_week.model_dump(mode="json"),
            "target_week": frozen["target_week"],
            "completed_weeks": list(frozen["completed_weeks"]),
            "completed_week_count": len(frozen["completed_weeks"]),
            "checkpoint": checkpoint,
            "blockers": list(blockers),
            "detail": detail,
            "position": position.model_dump(mode="json"),
        }
        if season_transition_preflight is not None:
            payload["season_transition_preflight"] = season_transition_preflight
        return payload

    def simulate_next_season(self, command: AuthoritativeSeasonCommand) -> dict:
        """Progress through one season and stop only at explicit canonical boundaries.

        Ordinary weeks are delegated to Next Week. Calendar-proven empty weeks use
        the existing audited empty-week authority. Week 61 finishes competitive
        slots but deliberately requires an explicit Saved Revision and the existing
        reviewed Season Transition surface before this parent can complete.
        """

        request_fp = fingerprint(
            {"mode": "season", "command": command.model_dump(mode="json")}
        )
        key = (command.run_id, command.branch_id, command.command_id)

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt is not None:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError(
                        "Season command ID already has a different request"
                    )
                if receipt.status == "complete":
                    return json.loads(receipt.result_json)
                if receipt.status != "pending":
                    raise ValueError("Season command receipt has an invalid status")
                frozen = json.loads(receipt.result_json)
            else:
                before = self._position(
                    session,
                    command.run_id,
                    command.branch_id,
                    allow_missing_schedule=True,
                )
                if before.current_week != command.expected_start_week:
                    raise ValueError("Next Season reviewed start week is stale")
                if (
                    before.position_fingerprint
                    != command.expected_position_fingerprint
                ):
                    raise ValueError("Next Season reviewed Position is stale")
                branch = session.get(RunBranchModel, command.branch_id)
                if (
                    branch is None
                    or branch.run_id != command.run_id
                    or branch.saved_head_revision_id
                    != command.expected_revision_id
                ):
                    raise ValueError("Next Season reviewed Saved Revision is stale")
                plan = self._next_season_plan(
                    session,
                    request=AuthoritativeSeasonPreviewRequest(
                        command_id=command.command_id,
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        operator_label=command.operator_label,
                        audit_reason=command.audit_reason,
                    ),
                )
                if plan["preview_fingerprint"] != command.expected_preview_fingerprint:
                    raise ValueError("Next Season preview changed before commit")
                frozen = {
                    "schema_version": "authoritative_season_operation.v1",
                    "run_id": command.run_id,
                    "branch_id": command.branch_id,
                    "start_week": plan["start_week"],
                    "target_week": plan["target_week"],
                    "initial_saved_revision_id": command.expected_revision_id,
                    "completed_weeks": [],
                    "week_children": {},
                    "empty_week_children": {},
                    "week61_slot_children": {},
                    "boundary_saved_revision_id": None,
                    "boundary_position_fingerprint": None,
                }
                session.add(
                    AuthoritativeSimulationCommandModel(
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        command_id=command.command_id,
                        request_fingerprint=request_fp,
                        status="pending",
                        result_json=json.dumps(
                            frozen, sort_keys=True, separators=(",", ":")
                        ),
                    )
                )

        start_week = RankingWeek.model_validate(frozen["start_week"])
        target_week = RankingWeek.model_validate(frozen["target_week"])

        for _ in range(512):
            with self.factory() as session:
                parent = session.get(AuthoritativeSimulationCommandModel, key)
                if parent is None or parent.request_fingerprint != request_fp:
                    raise ValueError("Season parent receipt disappeared")
                if parent.status == "complete":
                    return json.loads(parent.result_json)
                frozen = json.loads(parent.result_json)
                position = self._position(
                    session,
                    command.run_id,
                    command.branch_id,
                    allow_missing_schedule=True,
                )
                branch = session.get(RunBranchModel, command.branch_id)
                if (
                    branch is None
                    or branch.run_id != command.run_id
                    or branch.saved_head_revision_id is None
                ):
                    raise ValueError("Next Season lost its Saved Revision-backed Branch")
                current_saved_revision_id = branch.saved_head_revision_id

            if position.current_week == target_week:
                with self.factory.begin() as session:
                    session.execute(text("BEGIN IMMEDIATE"))
                    parent = session.get(AuthoritativeSimulationCommandModel, key)
                    if parent is None or parent.request_fingerprint != request_fp:
                        raise ValueError("Season parent receipt disappeared")
                    if parent.status == "complete":
                        return json.loads(parent.result_json)
                    frozen = json.loads(parent.result_json)
                    payload = {
                        "schema_version": "authoritative_season_result.v1",
                        "status": "complete",
                        "run_id": command.run_id,
                        "branch_id": command.branch_id,
                        "start_week": frozen["start_week"],
                        "target_week": frozen["target_week"],
                        "completed_weeks": list(frozen["completed_weeks"]),
                        "completed_week_count": len(frozen["completed_weeks"]),
                        "week_child_command_ids": [
                            item["command"]["command_id"]
                            for _, item in sorted(
                                frozen["week_children"].items(),
                                key=lambda pair: int(pair[0]),
                            )
                        ],
                        "empty_week_child_command_ids": [
                            command_id
                            for _, command_id in sorted(
                                frozen["empty_week_children"].items(),
                                key=lambda pair: int(pair[0]),
                            )
                        ],
                        "week61_slot_child_command_ids": [
                            item["command_id"]
                            for _, item in sorted(
                                frozen["week61_slot_children"].items(),
                                key=lambda pair: int(pair[0]),
                            )
                        ],
                        "season_transition_observed": True,
                        "saved_revision_id": current_saved_revision_id,
                        "position": position.model_dump(mode="json"),
                        "adoption": "committed",
                    }
                    parent.status = "complete"
                    parent.result_json = json.dumps(
                        payload, sort_keys=True, separators=(",", ":")
                    )
                    session.flush()
                    return payload

            if position.current_week.season_index != start_week.season_index:
                raise ValueError(
                    "Next Season chronology crossed an unexpected Season boundary"
                )

            week = position.current_week
            if position.current_slot_kind == "entry":
                return self._season_progress_payload(
                    command=command,
                    frozen=frozen,
                    position=position,
                    checkpoint="entry_process_required",
                    blockers=("entry_process_required",),
                    detail=(
                        "Resolve the current Entry/application decision surface, "
                        "then retry this exact Next Season command."
                    ),
                )

            if week.week < 61:
                if (
                    position.current_slot_kind == "match"
                    or position.terminal_sporting_fingerprint is not None
                ):
                    week_key = str(week.ordinal)
                    stored = frozen["week_children"].get(week_key)
                    if stored is None:
                        child_id = self._season_week_child_command_id(
                            command.command_id, week
                        )
                        preview_request = AuthoritativeWeekPreviewRequest(
                            command_id=child_id,
                            run_id=command.run_id,
                            branch_id=command.branch_id,
                            operator_label=command.operator_label,
                            audit_reason=command.audit_reason,
                        )
                        try:
                            child_preview = self.preview_next_week(preview_request)
                        except ValueError as exc:
                            return self._season_progress_payload(
                                command=command,
                                frozen=frozen,
                                position=position,
                                checkpoint="week_preparation_required",
                                blockers=tuple(position.transition_blockers),
                                detail=str(exc),
                            )
                        child = AuthoritativeWeekCommand(
                            **preview_request.model_dump(mode="json"),
                            expected_week=week,
                            expected_position_fingerprint=child_preview[
                                "expected_position_fingerprint"
                            ],
                            expected_revision_id=child_preview[
                                "expected_revision_id"
                            ],
                            expected_preview_fingerprint=child_preview[
                                "preview_fingerprint"
                            ],
                        )
                        with self.factory.begin() as session:
                            session.execute(text("BEGIN IMMEDIATE"))
                            parent = session.get(
                                AuthoritativeSimulationCommandModel, key
                            )
                            if (
                                parent is None
                                or parent.request_fingerprint != request_fp
                            ):
                                raise ValueError("Season parent receipt disappeared")
                            frozen_now = json.loads(parent.result_json)
                            existing = frozen_now["week_children"].get(week_key)
                            if existing is None:
                                current = self._position(
                                    session,
                                    command.run_id,
                                    command.branch_id,
                                    allow_missing_schedule=True,
                                )
                                branch_now = session.get(
                                    RunBranchModel, command.branch_id
                                )
                                if (
                                    current.current_week != week
                                    or current.position_fingerprint
                                    != child.expected_position_fingerprint
                                    or branch_now is None
                                    or branch_now.saved_head_revision_id
                                    != child.expected_revision_id
                                ):
                                    raise ValueError(
                                        "Next Season Week child changed before freeze"
                                    )
                                frozen_now["week_children"][week_key] = {
                                    "command": child.model_dump(mode="json"),
                                    "preview_fingerprint": child_preview[
                                        "preview_fingerprint"
                                    ],
                                }
                                parent.result_json = json.dumps(
                                    frozen_now,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                )
                                frozen = frozen_now
                                stored = frozen_now["week_children"][week_key]
                            else:
                                stored = existing
                    child = AuthoritativeWeekCommand.model_validate_json(
                        json.dumps(stored["command"])
                    )
                    child_result = self.simulate_next_week(child)
                    if (
                        child_result.get("schema_version")
                        == "authoritative_week_progress.v1"
                    ):
                        with self.factory() as session:
                            current = self._position(
                                session,
                                command.run_id,
                                command.branch_id,
                                allow_missing_schedule=True,
                            )
                        return self._season_progress_payload(
                            command=command,
                            frozen=frozen,
                            position=current,
                            checkpoint="week_transition_prerequisite",
                            blockers=tuple(
                                child_result.get("transition_blockers", ())
                            ),
                            detail=(
                                "The current canonical Next Week child paused. "
                                "Resolve its explicit prerequisite and retry the "
                                "same Next Season command."
                            ),
                        )

                    completed = child_result["completed_week"]
                    with self.factory.begin() as session:
                        session.execute(text("BEGIN IMMEDIATE"))
                        parent = session.get(
                            AuthoritativeSimulationCommandModel, key
                        )
                        if (
                            parent is None
                            or parent.request_fingerprint != request_fp
                        ):
                            raise ValueError("Season parent receipt disappeared")
                        frozen_now = json.loads(parent.result_json)
                        if completed not in frozen_now["completed_weeks"]:
                            frozen_now["completed_weeks"].append(completed)
                        parent.result_json = json.dumps(
                            frozen_now,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                    continue

                child_id = self._season_empty_week_child_command_id(
                    command.command_id, week
                )
                with self.factory() as session:
                    existing_child = session.get(
                        AuthoritativeSimulationCommandModel,
                        (command.run_id, command.branch_id, child_id),
                    )
                if existing_child is not None:
                    if existing_child.status != "complete":
                        raise ValueError(
                            "Next Season empty-week child receipt is incomplete"
                        )
                    empty_result = json.loads(existing_child.result_json)
                else:
                    empty_command = AuthoritativeEmptyWeekCompletionCommand(
                        command_id=child_id,
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        expected_week=week,
                        expected_position_fingerprint=position.position_fingerprint,
                        expected_revision_id=current_saved_revision_id,
                        operator_label=command.operator_label,
                        audit_reason=command.audit_reason,
                    )
                    try:
                        empty_result = self.complete_empty_week(empty_command)
                    except ValueError as exc:
                        return self._season_progress_payload(
                            command=command,
                            frozen=frozen,
                            position=position,
                            checkpoint="week_preparation_required",
                            blockers=tuple(position.transition_blockers),
                            detail=str(exc),
                        )

                with self.factory.begin() as session:
                    session.execute(text("BEGIN IMMEDIATE"))
                    parent = session.get(AuthoritativeSimulationCommandModel, key)
                    if parent is None or parent.request_fingerprint != request_fp:
                        raise ValueError("Season parent receipt disappeared")
                    frozen_now = json.loads(parent.result_json)
                    frozen_now["empty_week_children"][str(week.ordinal)] = child_id
                    parent.result_json = json.dumps(
                        frozen_now, sort_keys=True, separators=(",", ":")
                    )
                continue

            # Week 61 never uses ordinary Next Week. Finish its sporting proof,
            # then require the explicit Save + reviewed Season Transition surface.
            if position.current_slot_kind == "match":
                if position.slot_ordinal is None:
                    raise ValueError("Week 61 current match slot has no ordinal")
                slot_key = str(position.slot_ordinal)
                stored_slot = frozen["week61_slot_children"].get(slot_key)
                if stored_slot is None:
                    child = AuthoritativeSimulationCommand(
                        command_id=self._season_week61_slot_child_command_id(
                            command.command_id, position.slot_ordinal
                        ),
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        expected_week=week,
                        expected_position_fingerprint=position.position_fingerprint,
                        expected_revision_id=current_saved_revision_id,
                    )
                    with self.factory.begin() as session:
                        session.execute(text("BEGIN IMMEDIATE"))
                        parent = session.get(
                            AuthoritativeSimulationCommandModel, key
                        )
                        if (
                            parent is None
                            or parent.request_fingerprint != request_fp
                        ):
                            raise ValueError("Season parent receipt disappeared")
                        frozen_now = json.loads(parent.result_json)
                        current = self._position(
                            session,
                            command.run_id,
                            command.branch_id,
                            allow_missing_schedule=True,
                        )
                        branch_now = session.get(RunBranchModel, command.branch_id)
                        if (
                            current.current_week != week
                            or current.slot_ordinal != position.slot_ordinal
                            or current.position_fingerprint
                            != child.expected_position_fingerprint
                            or branch_now is None
                            or branch_now.saved_head_revision_id
                            != child.expected_revision_id
                        ):
                            raise ValueError(
                                "Next Season Week 61 slot changed before freeze"
                            )
                        frozen_now["week61_slot_children"][slot_key] = (
                            child.model_dump(mode="json")
                        )
                        parent.result_json = json.dumps(
                            frozen_now,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        frozen = frozen_now
                        stored_slot = frozen_now["week61_slot_children"][
                            slot_key
                        ]
                child = AuthoritativeSimulationCommand.model_validate_json(
                    json.dumps(stored_slot)
                )
                self.simulate_next_slot(child)
                continue

            if position.terminal_sporting_fingerprint is None:
                child_id = self._season_empty_week_child_command_id(
                    command.command_id, week
                )
                with self.factory() as session:
                    existing_child = session.get(
                        AuthoritativeSimulationCommandModel,
                        (command.run_id, command.branch_id, child_id),
                    )
                if existing_child is not None:
                    if existing_child.status != "complete":
                        raise ValueError(
                            "Next Season Week 61 empty-week receipt is incomplete"
                        )
                else:
                    empty_command = AuthoritativeEmptyWeekCompletionCommand(
                        command_id=child_id,
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        expected_week=week,
                        expected_position_fingerprint=position.position_fingerprint,
                        expected_revision_id=current_saved_revision_id,
                        operator_label=command.operator_label,
                        audit_reason=command.audit_reason,
                    )
                    try:
                        self.complete_empty_week(empty_command)
                    except ValueError as exc:
                        return self._season_progress_payload(
                            command=command,
                            frozen=frozen,
                            position=position,
                            checkpoint="week61_preparation_required",
                            blockers=tuple(position.transition_blockers),
                            detail=str(exc),
                        )
                with self.factory.begin() as session:
                    session.execute(text("BEGIN IMMEDIATE"))
                    parent = session.get(AuthoritativeSimulationCommandModel, key)
                    if parent is None or parent.request_fingerprint != request_fp:
                        raise ValueError("Season parent receipt disappeared")
                    frozen_now = json.loads(parent.result_json)
                    frozen_now["empty_week_children"][str(week.ordinal)] = child_id
                    parent.result_json = json.dumps(
                        frozen_now, sort_keys=True, separators=(",", ":")
                    )
                continue

            # Week 61 sporting is complete.
            with self.factory.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                parent = session.get(AuthoritativeSimulationCommandModel, key)
                if parent is None or parent.request_fingerprint != request_fp:
                    raise ValueError("Season parent receipt disappeared")
                frozen_now = json.loads(parent.result_json)
                week_payload = week.model_dump(mode="json")
                if week_payload not in frozen_now["completed_weeks"]:
                    frozen_now["completed_weeks"].append(week_payload)
                mutated_by_parent = bool(
                    frozen_now["week_children"]
                    or frozen_now["empty_week_children"]
                    or frozen_now["week61_slot_children"]
                )
                boundary_head = frozen_now.get("boundary_saved_revision_id")
                if mutated_by_parent and boundary_head is None:
                    frozen_now["boundary_saved_revision_id"] = (
                        current_saved_revision_id
                    )
                    frozen_now["boundary_position_fingerprint"] = (
                        position.position_fingerprint
                    )
                    parent.result_json = json.dumps(
                        frozen_now, sort_keys=True, separators=(",", ":")
                    )
                    frozen = frozen_now
                    return self._season_progress_payload(
                        command=command,
                        frozen=frozen_now,
                        position=position,
                        checkpoint="season_transition_save_required",
                        blockers=("season_transition_save_required",),
                        detail=(
                            "Week 61 sporting evidence was produced during this "
                            "Next Season operation. Save the current canonical "
                            "world explicitly, then retry the same command."
                        ),
                    )
                frozen = frozen_now

            if (
                frozen.get("boundary_saved_revision_id") is not None
                and current_saved_revision_id
                == frozen["boundary_saved_revision_id"]
            ):
                return self._season_progress_payload(
                    command=command,
                    frozen=frozen,
                    position=position,
                    checkpoint="season_transition_save_required",
                    blockers=("season_transition_save_required",),
                    detail=(
                        "The Week 61 boundary has not been saved since this "
                        "Next Season operation reached it."
                    ),
                )

            preflight = self.season_transition_preflight(
                run_id=command.run_id,
                branch_id=command.branch_id,
            )
            if not preflight.ready_for_execution:
                return self._season_progress_payload(
                    command=command,
                    frozen=frozen,
                    position=position,
                    checkpoint="season_transition_prerequisite",
                    blockers=tuple(
                        (*preflight.state_blockers, *preflight.implementation_gaps)
                    ),
                    detail=(
                        "Canonical Season Transition is not ready. Resolve the "
                        "listed boundary prerequisite and retry this exact command."
                    ),
                    season_transition_preflight=preflight.model_dump(mode="json"),
                )

            return self._season_progress_payload(
                command=command,
                frozen=frozen,
                position=position,
                checkpoint="season_transition_review_required",
                blockers=("season_transition_review_required",),
                detail=(
                    "Week 61 is saved and canonical Season Transition preflight "
                    "is ready. Review/commit the existing Season Transition, then "
                    "retry this exact Next Season command to finalize the parent."
                ),
                season_transition_preflight=preflight.model_dump(mode="json"),
            )

        raise ValueError("Next Season exceeded the bounded orchestration step budget")

    def commit_post_cutoff_walkover(self, command: AuthoritativeWalkoverCommand):
        """Commit one Master §15.9 W/O without simulating a competitive match.

        W/O remains noncompetitive sporting evidence, but if it resolves the final
        outstanding tournament node the normal canonical close now freezes result
        and point authorities from the reached-stage progression.
        """

        request_fp = fingerprint(
            {"mode": "walkover", "command": command.model_dump(mode="json")}
        )
        key = (command.run_id, command.branch_id, command.command_id)
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt is not None:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError(
                        "simulation command ID already has a different request"
                    )
                if receipt.status != "complete":
                    raise ValueError("walkover command receipt is incomplete")
                return json.loads(receipt.result_json)

            before = self._position(session, command.run_id, command.branch_id)
            self._validate_expected(session, command, before)
            packages, authority_fp = self._authority_package(
                session,
                command.run_id,
                command.branch_id,
                before.current_week,
                adopt=True,
            )
            self._ensure_current_slot(session, command, packages)
            current = self._position(session, command.run_id, command.branch_id)
            if current.current_slot_id is None:
                raise ValueError("walkover target has no current Simulation Slot")
            eligible_groups = self._eligible_groups(
                session, current, packages
            )
            if command.group_id not in eligible_groups:
                raise ValueError(
                    "walkover target is completed, blocked, or outside the current slot"
                )

            slot = session.get(
                SimulationSlotModel,
                (
                    command.run_id,
                    command.branch_id,
                    command.expected_week.ordinal,
                    current.current_slot_id,
                ),
            )
            if slot is None:
                raise ValueError("walkover current Simulation Slot disappeared")
            plan = AuthoritativeSlotMatchExecutor._load_plan(slot)
            try:
                event_plan = next(
                    item
                    for item in plan.match_events
                    if item.group_id == command.group_id
                )
            except StopIteration as exc:
                raise ValueError("walkover target group is not planned") from exc

            result = TournamentWalkoverAuthorityStore(session).commit(
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=command.expected_week,
                event_id=event_plan.event_id,
                command_id=command.command_id,
                withdrawn_player_id=command.withdrawn_player_id,
                slot_id=slot.slot_id,
                group_id=command.group_id,
            )
            self._advance_or_close(session, command, packages)
            after = self._position(session, command.run_id, command.branch_id)
            payload = {
                "walkover": {
                    "authority_fingerprint": result.authoritative_input.fingerprint,
                    "result_fingerprint": result.result_fingerprint,
                    "event_id": result.authoritative_input.event_id,
                    "match_id": result.result.match_id,
                    "winner_player_id": result.result.winner_player_id,
                    "withdrawn_player_id": result.result.loser_player_id,
                    "scoreline": result.result.scoreline,
                },
                "position": after.model_dump(mode="json"),
                "authority_fingerprint": authority_fp,
            }
            session.add(
                AuthoritativeSimulationCommandModel(
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    command_id=command.command_id,
                    request_fingerprint=request_fp,
                    status="complete",
                    result_json=json.dumps(
                        payload, sort_keys=True, separators=(",", ":")
                    ),
                )
            )
            session.flush()
            return payload

    def _mutate(self, command, *, mode: Literal["match", "slot"], fault_at=None):
        request_fp = fingerprint(
            {"mode": mode, "command": command.model_dump(mode="json")}
        )
        # Establish one durable operation receipt and materialize the frozen slot
        # before executing groups. Each independent group then owns its transaction.
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            key = (command.run_id, command.branch_id, command.command_id)
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError(
                        "simulation command ID already has a different request"
                    )
                if receipt.status == "complete":
                    return json.loads(receipt.result_json)
                operation_targets = tuple(
                    json.loads(receipt.result_json)["target_group_ids"]
                )
            else:
                before = self._position(session, command.run_id, command.branch_id)
                self._validate_expected(session, command, before)
                packages, authority_fp = self._authority_package(
                    session,
                    command.run_id,
                    command.branch_id,
                    before.current_week,
                    adopt=True,
                )
                self._ensure_current_slot(session, command, packages)
                position = self._position(session, command.run_id, command.branch_id)
                targets = self._targets(session, command, mode, position, packages)
                operation_targets = targets
                session.add(
                    AuthoritativeSimulationCommandModel(
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        command_id=command.command_id,
                        request_fingerprint=request_fp,
                        status="pending",
                        result_json=json.dumps(
                            {
                                "target_group_ids": targets,
                                "authority_fingerprint": authority_fp,
                            }
                        ),
                    )
                )

        for index, group_id in enumerate(operation_targets):
            if fault_at == "before_second_group" and index == 1:
                raise RuntimeError("fault before second group")
            with self.factory.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                self._require_writable_scope(session, command.run_id, command.branch_id)
                packages = self._pending_package(session, command, request_fp)
                current = self._position(session, command.run_id, command.branch_id)
                if group_id in current.unresolved_group_ids:
                    self._execute_group(session, command, packages, group_id)
            if fault_at == "after_first_group" and index == 0:
                raise RuntimeError("fault after first committed group")

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            packages = self._pending_package(session, command, request_fp)
            self._advance_or_close(session, command, packages, fault_at=fault_at)
            after = self._position(session, command.run_id, command.branch_id)
            payload = after.model_dump(mode="json")
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt is None:
                raise ValueError("pending simulation command receipt disappeared")
            receipt.status = "complete"
            receipt.result_json = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            )
            if fault_at == "after_source_staging_before_receipt":
                raise RuntimeError(
                    "fault after ranking source staging before command receipt"
                )
            return payload

    def _pending_package(self, session, command, request_fp):
        receipt = session.get(
            AuthoritativeSimulationCommandModel,
            (command.run_id, command.branch_id, command.command_id),
        )
        if (
            receipt is None
            or receipt.request_fingerprint != request_fp
            or receipt.status != "pending"
        ):
            raise ValueError("pending simulation command receipt is invalid")
        evidence = json.loads(receipt.result_json)
        packages, authority_fp = self._authority_package(
            session,
            command.run_id,
            command.branch_id,
            command.expected_week,
            adopt=False,
        )
        if evidence.get("authority_fingerprint") != authority_fp:
            raise ValueError("pending command tournament authority changed")
        slot = session.scalar(
            select(SimulationSlotModel).where(
                SimulationSlotModel.run_id == command.run_id,
                SimulationSlotModel.branch_id == command.branch_id,
                SimulationSlotModel.week_ordinal == command.expected_week.ordinal,
                SimulationSlotModel.status != "complete",
            )
        )
        if (
            slot is not None
            and authority_fp
            not in AuthoritativeSlotMatchExecutor._load_plan(slot).provenance
        ):
            raise ValueError("pending command slot authority is incoherent")
        return packages

    @staticmethod
    def _require_writable_scope(session, run_id, branch_id):
        run = session.get(RunContainerModel, run_id)
        branch = session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("authoritative simulation Run/Branch scope does not exist")
        if run.read_only or branch.read_only or branch.status != "active":
            raise ValueError("authoritative simulation Run/Branch is not writable")

    @staticmethod
    def _validate_expected(session, command, before):
        if before.current_week != command.expected_week:
            raise ValueError("expected current week is stale")
        if before.position_fingerprint != command.expected_position_fingerprint:
            raise ValueError("simulation position is stale")
        branch = session.get(RunBranchModel, command.branch_id)
        if (
            branch is None
            or branch.run_id != command.run_id
            or branch.saved_head_revision_id != command.expected_revision_id
        ):
            raise ValueError("expected Branch head is stale")

    def _targets(self, session, command, mode, position, package):
        eligible_groups = self._eligible_groups(session, position, package)
        if mode == "match":
            if command.group_id is None:
                if len(eligible_groups) != 1:
                    raise ValueError("an explicit current-slot group_id is required")
                return eligible_groups
            if command.group_id not in eligible_groups:
                raise ValueError(
                    "target is completed, blocked, or outside the current slot"
                )
            return (command.group_id,)
        if command.group_id is not None:
            raise ValueError("Simulate Next Slot does not accept group_id")
        if not eligible_groups:
            raise ValueError("current slot has no unresolved eligible match")
        return eligible_groups

    def _week_tournament_lock_event_ids(
        self,
        session: Session,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
    ) -> tuple[str, ...]:
        has_fields = session.scalar(
            select(TournamentEntryFieldVersionModel.event_id)
            .where(
                TournamentEntryFieldVersionModel.run_id == run_id,
                TournamentEntryFieldVersionModel.branch_id == branch_id,
            )
            .limit(1)
        )
        if has_fields is None:
            return ()

        season = f"{2000 + week.season_index}/{2001 + week.season_index}"
        calendar = self.awards_service.calendar_service.get_calendar(
            season=season
        ).calendar
        if calendar is None:
            raise ValueError(
                "Week Tournament Lock requires the season Calendar authority"
            )
        field_store = TournamentEntryFieldStore(session)
        event_ids = []
        for event in calendar.events:
            start = event.start_season_week or event.season_week
            end = event.end_season_week or start
            if not start <= week.week <= end:
                continue
            if field_store.latest(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event.event_id,
            ) is not None:
                event_ids.append(event.event_id)
        return tuple(sorted(event_ids))

    @staticmethod
    def _week_lock_field_command_id(command_id: str, event_id: str) -> str:
        digest = hashlib.sha256(
            f"{command_id}|{event_id}".encode()
        ).hexdigest()[:24]
        return f"week-lock-field:{digest}"

    def _empty_week_calendar_evidence(self, week: RankingWeek):
        season = f"{2000 + week.season_index}/{2001 + week.season_index}"
        resolved = self.awards_service.calendar_service.get_calendar(season=season)
        calendar = resolved.calendar
        if calendar is None:
            raise ValueError(
                "empty-week completion requires explicit season Calendar authority"
            )
        evidence = fingerprint(
            {
                "schema_version": "empty_week_calendar_evidence.v1",
                "season": season,
                "week": week.model_dump(mode="json"),
                "calendar": calendar.model_dump(mode="json"),
            }
        )
        return calendar, evidence

    @staticmethod
    def _explicit_empty_week_context(
        session,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
        sporting,
    ):
        try:
            context = get_completed_context(
                session,
                run_id=run_id,
                branch_id=branch_id,
                completed_week=week,
            )
        except ValueError as exc:
            if "zero matches cannot be inferred" in str(exc):
                return None
            raise
        if context.provenance != AUTHORITATIVE_EMPTY_WEEK_PROVENANCE:
            return None
        expected_ids = (
            tuple(sorted(player.player_id for player in sporting.players))
            if sporting is not None
            else ()
        )
        observed_ids = tuple(
            item.player_id for item in context.competitive_match_counts
        )
        if (
            sporting is None
            or observed_ids != expected_ids
            or any(item.count != 0 for item in context.competitive_match_counts)
            or len(context.source_fingerprints) != 1
            or context.terminal_sporting_fingerprint is not None
            or context.match_effect_fingerprints
        ):
            raise ValueError("explicit empty-week sporting evidence is corrupt")
        return context

    def _current_week(self, session, run_id, branch_id):
        world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
        if world:
            return RankingWeek(
                season_index=world.current_ordinal // 61,
                week=world.current_ordinal % 61 + 1,
            )
        rows = session.execute(
            select(PlayerSportingWeekStateModel.week_ordinal)
            .where(
                PlayerSportingWeekStateModel.run_id == run_id,
                PlayerSportingWeekStateModel.branch_id == branch_id,
            )
            .order_by(PlayerSportingWeekStateModel.week_ordinal.desc())
        ).first()
        if not rows:
            raise ValueError("authoritative sporting week state is missing")
        ordinal = rows[0]
        return RankingWeek(season_index=ordinal // 61, week=ordinal % 61 + 1)

    def _canonical_draw_binding(
        self,
        session,
        *,
        run_id,
        branch_id,
        week,
        event_id,
    ):
        """Resolve Draw ownership as frozen by adopted tournament authority."""

        adopted = session.get(
            AdoptedTournamentAuthorityModel,
            (run_id, branch_id, week.ordinal),
        )
        expected_fp = None
        binding_frozen = False
        if adopted is not None:
            items = self._decode_adopted_authority(adopted.package_json)
            matches = [
                item.draw_authority_fingerprint
                for item in items
                if item.event_id == event_id
            ]
            if len(matches) != 1:
                raise ValueError(
                    "frozen tournament authority lacks unique event Draw binding"
                )
            expected_fp = matches[0]
            binding_frozen = True

        draw = TournamentDrawAuthorityStore(session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if binding_frozen:
            if expected_fp is None:
                return None
            if draw is None or draw.fingerprint != expected_fp:
                raise ValueError(
                    "frozen tournament authority canonical Draw binding changed"
                )
            return draw
        return draw

    def _replay_adopted_authority(
        self,
        session,
        *,
        run_id,
        branch_id,
        week,
        row,
    ):
        items = self._decode_adopted_authority(row.package_json)
        packages = []
        draw_store = TournamentDrawAuthorityStore(session)
        for item in items:
            if item.package is not None:
                package = item.package
                if package.event_id != item.event_id:
                    raise ValueError(
                        "historical frozen tournament authority event identity changed"
                    )
                if item.draw_authority_fingerprint is not None:
                    draw = draw_store.get(
                        run_id=run_id,
                        branch_id=branch_id,
                        event_id=item.event_id,
                    )
                    if (
                        draw is None
                        or draw.fingerprint != item.draw_authority_fingerprint
                    ):
                        raise ValueError(
                            "frozen tournament authority canonical Draw binding changed"
                        )
                packages.append(package)
                continue

            if (
                item.calendar_event is None
                or item.point_award_authority is None
                or item.draw_authority_fingerprint is None
            ):
                raise ValueError(
                    "canonical frozen tournament authority is incomplete"
                )
            event = item.calendar_event
            if event.event_id != item.event_id or event.season_week != week.week:
                raise ValueError(
                    "canonical frozen tournament Calendar Event scope changed"
                )
            expected_start = 2000 + week.season_index
            expected_season = f"{expected_start}/{expected_start + 1}"
            event_season_matches = (
                event.season == expected_start
                if isinstance(event.season, int)
                else str(event.season) == expected_season
            )
            if not event_season_matches:
                raise ValueError(
                    "canonical frozen tournament Calendar Event season changed"
                )
            draw = draw_store.get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=item.event_id,
            )
            if draw is None or draw.fingerprint != item.draw_authority_fingerprint:
                raise ValueError(
                    "frozen tournament authority canonical Draw binding changed"
                )
            package = build_run_owned_match_package(
                draw=draw,
                event=event,
                week=week,
            )
            packages.append(
                self._bind_owned_draw_evidence(
                    package=package,
                    draw=draw,
                    week=week,
                )
            )

        authority_fp = self._tournament_authority_fingerprint(
            run_id,
            branch_id,
            week,
            items,
        )
        if authority_fp != row.authority_fingerprint:
            raise ValueError("frozen tournament authority is corrupt")
        return tuple(sorted(packages, key=lambda package: package.event_id)), authority_fp

    def _packages(
        self,
        week,
        *,
        required=True,
        session=None,
        run_id=None,
        branch_id=None,
    ):
        season = f"{2000 + week.season_index}/{2001 + week.season_index}"

        if session is not None and run_id is not None and branch_id is not None:
            adopted = session.get(
                AdoptedTournamentAuthorityModel,
                (run_id, branch_id, week.ordinal),
            )
            if adopted is not None:
                packages, _ = self._replay_adopted_authority(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    week=week,
                    row=adopted,
                )
                if not packages and required:
                    raise ValueError("supported tournament authority is missing")
                return packages

        canonical_packages = {}
        canonical_event_ids = set()
        if session is not None and run_id is not None and branch_id is not None:
            draw_event_ids = tuple(
                session.scalars(
                    select(TournamentDrawAuthorityModel.event_id)
                    .where(
                        TournamentDrawAuthorityModel.run_id == run_id,
                        TournamentDrawAuthorityModel.branch_id == branch_id,
                    )
                    .order_by(TournamentDrawAuthorityModel.event_id)
                ).all()
            )
            if draw_event_ids:
                calendar = self.awards_service.calendar_service.get_calendar(
                    season=season
                ).calendar
                if calendar is None:
                    raise ValueError(
                        "canonical Draw execution requires the season Calendar authority"
                    )
                events = {event.event_id: event for event in calendar.events}
                for event_id in draw_event_ids:
                    event = events.get(event_id)
                    if event is None or event.season_week != week.week:
                        continue
                    draw = self._canonical_draw_binding(
                        session,
                        run_id=run_id,
                        branch_id=branch_id,
                        week=week,
                        event_id=event_id,
                    )
                    if draw is None:
                        continue
                    package = build_run_owned_match_package(
                        draw=draw,
                        event=event,
                        week=week,
                    )
                    canonical_packages[event_id] = self._bind_owned_draw_evidence(
                        package=package,
                        draw=draw,
                        week=week,
                    )
                    canonical_event_ids.add(event_id)

        legacy_packages = tuple(
            sorted(
                (
                    p
                    for p in self.match_service._load_registry().matches_by_event_id.values()
                    if p.season == season
                    and p.season_week == week.week
                    and p.event_id not in canonical_event_ids
                ),
                key=lambda package: package.event_id,
            )
        )
        bound_legacy = []
        for package in legacy_packages:
            canonical = None
            if session is not None and run_id is not None and branch_id is not None:
                canonical = self._canonical_draw_binding(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    week=week,
                    event_id=package.event_id,
                )
            if canonical is not None:
                if package.event_id not in canonical_packages:
                    raise ValueError(
                        "canonical Draw event could not build Run-owned MatchPackage"
                    )
                continue
            bound_legacy.append(self._bind_current_draw_evidence(package, week))

        packages = tuple(
            sorted(
                (*canonical_packages.values(), *bound_legacy),
                key=lambda package: package.event_id,
            )
        )
        if not packages and required:
            raise ValueError("supported tournament authority is missing")
        if session is None:
            for package in packages:
                self._topology((package,))
        return packages

    def _bind_owned_draw_evidence(self, *, package, draw, week):
        """Bind MatchPackage execution payload to canonical Run-owned Draw authority."""
        expected_season = f"{2000 + week.season_index}/{2001 + week.season_index}"
        if (
            package.event_id != draw.event_id
            or package.season != expected_season
            or package.season_week != week.week
        ):
            raise ValueError("canonical Draw/MatchPackage event or week identity conflicts")
        projected = package.model_copy(deep=True)
        topology = project_canonical_draw_to_match_topology(
            draw=draw,
            package=projected,
        )
        bye_winners = dict(topology.bye_winners)
        for match in projected.qualification_matches + projected.main_draw_matches:
            winner = bye_winners.get(match.match_id)
            if winner is None:
                continue
            match.winner_player_id = winner
            match.loser_player_id = None
            match.scoreline = "BYE"
            match.status = "completed"
            match.result_notes = "automatic BYE advance from canonical Draw authority"
            match.result_fingerprint = fingerprint(
                {
                    "action": "canonical_draw_bye_advance.v1",
                    "draw_authority_fingerprint": draw.fingerprint,
                    "event_id": projected.event_id,
                    "match_id": match.match_id,
                    "winner_player_id": winner,
                }
            )
        return projected.model_copy(
            update={
                "frozen_qualifier_promotions": list(topology.qualifier_promotions),
                "frozen_bye_match_ids": list(topology.bye_match_ids),
            }
        )

    def _bind_current_draw_evidence(self, package, week):
        """Validate producer lineage and freeze qualification side mappings."""
        package = package.model_copy(deep=True)
        legacy_completed = bool(package.main_draw_matches) and all(
            item.status == "completed"
            for item in package.qualification_matches + package.main_draw_matches
        )
        draw = self.match_service.draw_service.get_draw_package(
            event_id=package.event_id
        ).draw_package
        if draw is None:
            if legacy_completed:
                return package
            raise ValueError("persisted DrawPackage authority is missing")
        entry = self.match_service.draw_service.entry_list_service.get_entry_list(
            event_id=package.event_id
        ).entry_list
        if entry is None:
            if legacy_completed:
                return package
            raise ValueError("persisted EntryList authority is missing")
        expected_season = f"{2000 + week.season_index}/{2001 + week.season_index}"
        if not legacy_completed and (
            package.event_id != draw.event_id
            or package.season != draw.season
            or package.season != expected_season
            or package.season_week != draw.season_week
            or package.season_week != week.week
        ):
            raise ValueError("persisted Match/Draw event or week identity conflicts")
        if package.metadata.draw_package_fingerprint != draw.metadata.build_fingerprint:
            raise ValueError("persisted MatchPackage DrawPackage fingerprint conflicts")
        if draw.metadata.entry_list_fingerprint != entry.metadata.build_fingerprint:
            raise ValueError("persisted DrawPackage EntryList fingerprint conflicts")
        bracket_fingerprints = {
            "main": draw.main_draw.generated_fingerprint,
            "qualification": (
                draw.qualification_draw.generated_fingerprint
                if draw.qualification_draw
                else None
            ),
        }
        for match in package.qualification_matches + package.main_draw_matches:
            if match.source_draw_fingerprint != bracket_fingerprints[
                match.draw_type
            ] and not legacy_completed:
                raise ValueError("persisted match source Draw fingerprint conflicts")

        if not legacy_completed:
            frozen_late = sorted(
                package.frozen_late_replacements,
                key=lambda item: item.target_slot_id,
            )
            expected_late_fp = (
                fingerprint(
                    [item.model_dump(mode="json") for item in frozen_late]
                )
                if frozen_late
                else None
            )
            if package.metadata.late_replacements_fingerprint != expected_late_fp:
                raise ValueError(
                    "persisted MatchPackage late-replacement fingerprint conflicts"
                )
            draw_slots = {
                slot.slot_id: slot for slot in draw.main_draw.slots
            }
            observed_fingerprints: list[str] = []
            for replacement in frozen_late:
                if (
                    replacement.draw_package_fingerprint
                    != draw.metadata.build_fingerprint
                    or replacement.entry_list_fingerprint
                    != entry.metadata.build_fingerprint
                ):
                    raise ValueError(
                        "persisted late-replacement producer lineage conflicts"
                    )
                slot = draw_slots.get(replacement.target_slot_id)
                if (
                    slot is None
                    or slot.player_id != replacement.withdrawn_player_id
                    or slot.bracket_position
                    != replacement.target_bracket_position
                ):
                    raise ValueError(
                        "persisted late-replacement target conflicts with Draw authority"
                    )
                targets = [
                    (match, side)
                    for match in package.main_draw_matches
                    for side in ("top", "bottom")
                    if getattr(match, f"{side}_slot_id")
                    == replacement.target_slot_id
                ]
                if len(targets) != 1:
                    raise ValueError(
                        "persisted late-replacement Match side is ambiguous"
                    )
                target, side = targets[0]
                if (
                    getattr(target, f"{side}_player_id")
                    != replacement.replacement_player_id
                    or getattr(
                        target,
                        f"{side}_late_replacement_fingerprint",
                    )
                    != replacement.authority_fingerprint
                ):
                    raise ValueError(
                        "persisted late-replacement Match evidence conflicts"
                    )
                observed_fingerprints.append(replacement.authority_fingerprint)

            all_side_fingerprints = sorted(
                fingerprint_value
                for match in package.main_draw_matches
                for fingerprint_value in (
                    match.top_late_replacement_fingerprint,
                    match.bottom_late_replacement_fingerprint,
                )
                if fingerprint_value is not None
            )
            if all_side_fingerprints != sorted(observed_fingerprints):
                raise ValueError(
                    "persisted MatchPackage has orphan late-replacement evidence"
                )

        promotions = []
        if package.qualification_matches:
            final_round = max(m.round_number for m in package.qualification_matches)
            finals = sorted(
                (
                    m
                    for m in package.qualification_matches
                    if m.round_number == final_round
                ),
                key=lambda m: (m.bracket_position, m.match_id),
            )
            placeholders = sorted(
                draw.main_draw.qualifier_placeholders,
                key=lambda p: (p.qualifier_index, p.bracket_position, p.slot_id),
            )
            if len(finals) != len(placeholders):
                raise ValueError("qualification final/placeholder mapping is ambiguous")
            for source, placeholder in zip(finals, placeholders, strict=True):
                targets = [
                    (m, side)
                    for m in package.main_draw_matches
                    for side in ("top", "bottom")
                    if getattr(m, f"{side}_slot_id") == placeholder.slot_id
                ]
                if len(targets) != 1:
                    raise ValueError(
                        "qualification placeholder target side is ambiguous"
                    )
                target, side = targets[0]
                promotions.append(
                    FrozenQualifierPromotion(
                        qualifier_index=placeholder.qualifier_index,
                        source_match_id=source.match_id,
                        target_match_id=target.match_id,
                        target_side=side,
                        target_slot_id=placeholder.slot_id,
                    )
                )
        bye_ids = []
        for match in package.qualification_matches + package.main_draw_matches:
            if match.status != "bye_auto_advance_pending":
                continue
            known = [p for p in (match.top_player_id, match.bottom_player_id) if p]
            if len(known) != 1 or not match.winner_to_match_id:
                raise ValueError("persisted BYE advancement is ambiguous")
            match.winner_player_id = known[0]
            match.loser_player_id = None
            match.scoreline = "BYE"
            match.status = "completed"
            match.result_notes = "automatic BYE advance"
            match.result_fingerprint = fingerprint(
                {
                    "action": "authoritative_bye_advance.v1",
                    "event_id": package.event_id,
                    "match_id": match.match_id,
                    "winner_player_id": known[0],
                }
            )
            self.match_service._propagate_winner(package, completed=match)
            bye_ids.append(match.match_id)
        return package.model_copy(
            update={
                "frozen_qualifier_promotions": promotions,
                "frozen_bye_match_ids": bye_ids,
            }
        )

    def _package(self, week, *, required=True):
        """Legacy single-event discovery retained for reviewed compatibility."""
        packages = self._packages(week, required=required)
        if len(packages) > 1:
            raise ValueError(
                "multiple supported tournaments lack authoritative cross-event "
                "Simulation Slot chronology"
            )
        return packages[0] if packages else None

    @staticmethod
    def _decode_adopted_authority(payload_json):
        payload = json.loads(payload_json)
        version = payload.get("schema_version")

        if version == "adopted_tournament_authority.v6":
            items = []
            for item in payload["tournaments"]:
                event = CalendarEvent.model_validate(item["calendar_event"])
                evidence = _AdoptedTournamentEvidence(
                    event_id=item["event_id"],
                    calendar_event=event,
                    point_award_authority=FrozenPointAwardAuthority.model_validate(
                        item["point_award_authority"]
                    ),
                    draw_authority_fingerprint=item["draw_authority_fingerprint"],
                )
                if evidence.event_id != event.event_id:
                    raise ValueError(
                        "canonical adopted tournament event identity mismatch"
                    )
                items.append(evidence)
            return tuple(sorted(items, key=lambda item: item.event_id))

        if version == "adopted_tournament_authority.v5":
            return tuple(
                sorted(
                    (
                        _AdoptedTournamentEvidence(
                            event_id=package.event_id,
                            package=package,
                            point_award_authority=FrozenPointAwardAuthority.model_validate(
                                item["point_award_authority"]
                            ),
                            draw_authority_fingerprint=item.get(
                                "draw_authority_fingerprint"
                            ),
                        )
                        for item in payload["tournaments"]
                        for package in (
                            SeasonEventMatchPackage.model_validate(item["package"]),
                        )
                    ),
                    key=lambda item: item.event_id,
                )
            )

        if version in {
            "adopted_tournament_authority.v3",
            "adopted_tournament_authority.v4",
        }:
            return tuple(
                sorted(
                    (
                        _AdoptedTournamentEvidence(
                            event_id=package.event_id,
                            package=package,
                            point_award_authority=FrozenPointAwardAuthority.model_validate(
                                item["point_award_authority"]
                            ),
                        )
                        for item in payload["tournaments"]
                        for package in (
                            SeasonEventMatchPackage.model_validate(item["package"]),
                        )
                    ),
                    key=lambda item: item.event_id,
                )
            )

        if version == "adopted_tournament_authority.v2":
            package = SeasonEventMatchPackage.model_validate(payload["package"])
            return (
                _AdoptedTournamentEvidence(
                    event_id=package.event_id,
                    package=package,
                    point_award_authority=FrozenPointAwardAuthority.model_validate(
                        payload["point_award_authority"]
                    ),
                ),
            )

        package = SeasonEventMatchPackage.model_validate(payload)
        return (
            _AdoptedTournamentEvidence(
                event_id=package.event_id,
                package=package,
            ),
        )

    @staticmethod
    def _encode_adopted_authority(items):
        items = tuple(sorted(items, key=lambda item: item.event_id))
        canonical = all(
            item.package is None
            and item.calendar_event is not None
            and item.point_award_authority is not None
            and item.draw_authority_fingerprint is not None
            for item in items
        )
        if canonical:
            return json.dumps(
                {
                    "schema_version": "adopted_tournament_authority.v6",
                    "tournaments": [
                        {
                            "event_id": item.event_id,
                            "calendar_event": item.calendar_event.model_dump(
                                mode="json",
                                exclude_computed_fields=True,
                            ),
                            "point_award_authority": (
                                item.point_award_authority.model_dump(mode="json")
                            ),
                            "draw_authority_fingerprint": (
                                item.draw_authority_fingerprint
                            ),
                        }
                        for item in items
                    ],
                },
                sort_keys=True,
                separators=(",", ":"),
            )

        if any(item.package is None for item in items):
            raise ValueError(
                "adopted tournament week cannot mix canonical-only and legacy evidence"
            )
        return json.dumps(
            {
                "schema_version": "adopted_tournament_authority.v5",
                "tournaments": [
                    {
                        "package": item.package.model_dump(mode="json"),
                        "point_award_authority": (
                            item.point_award_authority.model_dump(mode="json")
                            if item.point_award_authority is not None
                            else None
                        ),
                        "draw_authority_fingerprint": (
                            item.draw_authority_fingerprint
                        ),
                    }
                    for item in items
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def _freeze_calendar_event_snapshot(self, *, package, week):
        calendar = self.awards_service.calendar_service.get_calendar(
            season=package.season
        ).calendar
        if calendar is None:
            raise ValueError(
                "canonical tournament adoption requires Calendar authority"
            )
        matches = [
            event for event in calendar.events if event.event_id == package.event_id
        ]
        if len(matches) != 1:
            raise ValueError(
                "canonical tournament adoption requires unique Calendar Event"
            )
        event = matches[0]
        if event.season_week != week.week:
            raise ValueError(
                "canonical tournament Calendar Event belongs to a different week"
            )
        return CalendarEvent.model_validate(
            event.model_dump(mode="json", exclude_computed_fields=True)
        )

    def _authority_package(self, session, run_id, branch_id, week, *, adopt):
        row = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        if row is not None:
            return self._replay_adopted_authority(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=week,
                row=row,
            )
        if not adopt:
            raise ValueError("frozen tournament authority is missing")

        packages = self._packages(
            week,
            session=session,
            run_id=run_id,
            branch_id=branch_id,
        )
        if (
            len(packages) > 1
            or len(
                self._topology_for_session(
                    session, run_id, branch_id, packages, week=week
                )
            )
            != 3
        ) and self._schedule(
            session, run_id, branch_id, week
        ) is None:
            raise ValueError(
                "tournaments lack authoritative explicit Simulation Slot chronology"
            )

        draw_store = TournamentDrawAuthorityStore(session)
        items = []
        for package in packages:
            point_authority = self.awards_service.freeze_point_award_authority(package)
            draw = draw_store.get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=package.event_id,
            )
            if draw is None:
                items.append(
                    _AdoptedTournamentEvidence(
                        event_id=package.event_id,
                        package=package,
                        point_award_authority=point_authority,
                    )
                )
                continue

            event = self._freeze_calendar_event_snapshot(
                package=package,
                week=week,
            )
            rebuilt = self._bind_owned_draw_evidence(
                package=build_run_owned_match_package(
                    draw=draw,
                    event=event,
                    week=week,
                ),
                draw=draw,
                week=week,
            )
            if rebuilt != package:
                raise ValueError(
                    "canonical tournament package cannot replay from Draw + Calendar evidence"
                )
            items.append(
                _AdoptedTournamentEvidence(
                    event_id=package.event_id,
                    calendar_event=event,
                    point_award_authority=point_authority,
                    draw_authority_fingerprint=draw.fingerprint,
                )
            )
        items = tuple(items)

        authority_fp = self._tournament_authority_fingerprint(
            run_id, branch_id, week, items
        )
        session.add(
            AdoptedTournamentAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week.ordinal,
                event_id=(
                    packages[0].event_id
                    if len(packages) == 1
                    else "__week_tournament_authority_bundle_v1__"
                ),
                authority_fingerprint=authority_fp,
                package_json=self._encode_adopted_authority(items),
            )
        )
        session.flush()
        return packages, authority_fp

    @staticmethod
    def _tournament_authority_fingerprint(run_id, branch_id, week, items):
        normalized = []
        for raw in items:
            if isinstance(raw, _AdoptedTournamentEvidence):
                normalized.append(raw)
                continue
            package, point_authority, draw_fp = raw
            normalized.append(
                _AdoptedTournamentEvidence(
                    event_id=package.event_id,
                    package=package,
                    point_award_authority=point_authority,
                    draw_authority_fingerprint=draw_fp,
                )
            )
        bodies = []
        for item in sorted(normalized, key=lambda item: item.event_id):
            if item.package is not None:
                payload = item.package.model_dump(mode="json")
                payload["metadata"].pop("persistence_path", None)
                body = {
                    "package": payload,
                    "point_award_authority": (
                        item.point_award_authority.model_dump(mode="json")
                        if item.point_award_authority
                        else None
                    ),
                }
                # Preserve historical v1-v4/v5 authority fingerprints exactly.
                if item.draw_authority_fingerprint is not None:
                    body["draw_authority_fingerprint"] = (
                        item.draw_authority_fingerprint
                    )
            else:
                if (
                    item.calendar_event is None
                    or item.point_award_authority is None
                    or item.draw_authority_fingerprint is None
                ):
                    raise ValueError(
                        "canonical adopted tournament evidence is incomplete"
                    )
                body = {
                    "event_id": item.event_id,
                    "calendar_event": item.calendar_event.model_dump(
                        mode="json",
                        exclude_computed_fields=True,
                    ),
                    "point_award_authority": (
                        item.point_award_authority.model_dump(mode="json")
                    ),
                    "draw_authority_fingerprint": (
                        item.draw_authority_fingerprint
                    ),
                }
            bodies.append(body)
        return fingerprint(
            {"scope": [run_id, branch_id, week.ordinal], "tournaments": bodies}
        )

    def _schedule(self, session, run_id, branch_id, week):
        row = session.get(
            WeekSimulationScheduleModel, (run_id, branch_id, week.ordinal)
        )
        if row is None:
            return None
        value = WeekSimulationSchedule.model_validate_json(row.payload_json)
        if value.fingerprint != row.schedule_fingerprint or (
            value.run_id,
            value.branch_id,
            value.week,
        ) != (run_id, branch_id, week):
            raise ValueError("adopted week schedule is corrupt")
        return value

    @staticmethod
    def _entry_slot_ordinals(session, run_id, branch_id, week):
        return tuple(
            session.scalars(
                select(RunEntryDecisionSlotAuthorityModel.decision_slot_ordinal)
                .where(
                    RunEntryDecisionSlotAuthorityModel.run_id == run_id,
                    RunEntryDecisionSlotAuthorityModel.branch_id == branch_id,
                    RunEntryDecisionSlotAuthorityModel.week_ordinal == week.ordinal,
                )
                .order_by(
                    RunEntryDecisionSlotAuthorityModel.decision_slot_ordinal
                )
            ).all()
        )

    @staticmethod
    def _wc_slot_ordinals(session, run_id, branch_id, week):
        from beta_engine.infrastructure.db.tournament_wild_card_authority import (
            wild_card_decision_slot_ordinals,
        )

        return tuple(
            sorted(
                wild_card_decision_slot_ordinals(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    week_ordinal=week.ordinal,
                )
            )
        )

    def _next_match_day_plan(
        self,
        session: Session,
        *,
        run_id: str,
        branch_id: str,
    ) -> dict:
        position = self._position(session, run_id, branch_id)
        if position.current_slot_kind != "match" or position.slot_ordinal is None:
            raise ValueError("Next Match Day requires a current competitive match slot")

        schedule = self._schedule(session, run_id, branch_id, position.current_week)
        if schedule is None or schedule.schema_version != "week_simulation_schedule.v2":
            raise ValueError(
                "Next Match Day requires an adopted Week Simulation Schedule v2"
            )
        current_spec = next(
            (
                slot
                for slot in schedule.slots
                if slot.ordinal == position.slot_ordinal
            ),
            None,
        )
        if current_spec is None or current_spec.match_day_ordinal is None:
            raise ValueError("current Simulation Slot has no canonical Match Day")
        match_day_ordinal = current_spec.match_day_ordinal
        targets = tuple(
            slot
            for slot in schedule.slots
            if slot.match_day_ordinal == match_day_ordinal
            and slot.ordinal >= position.slot_ordinal
        )
        if not targets or targets[0].ordinal != position.slot_ordinal:
            raise ValueError("current Match Day schedule cannot be resolved")

        target_ordinals = tuple(slot.ordinal for slot in targets)
        first_ordinal, last_ordinal = target_ordinals[0], target_ordinals[-1]
        contiguous = tuple(range(first_ordinal, last_ordinal + 1))
        if target_ordinals != contiguous:
            missing = sorted(set(contiguous) - set(target_ordinals))
            reserved = set(
                self._entry_slot_ordinals(
                    session, run_id, branch_id, position.current_week
                )
            ) | set(
                self._wc_slot_ordinals(
                    session, run_id, branch_id, position.current_week
                )
            )
            if reserved.intersection(missing):
                raise ValueError(
                    "Next Match Day cannot cross a non-match process slot"
                )
            raise ValueError(
                "Next Match Day requires consecutive global Simulation Slots"
            )

        branch = session.get(RunBranchModel, branch_id)
        if (
            branch is None
            or branch.run_id != run_id
            or branch.saved_head_revision_id is None
        ):
            raise ValueError("Next Match Day requires a Saved Revision head")

        body = {
            "schema_version": "authoritative_match_day_preview.v1",
            "run_id": run_id,
            "branch_id": branch_id,
            "week": position.current_week.model_dump(mode="json"),
            "match_day_ordinal": match_day_ordinal,
            "schedule_fingerprint": schedule.fingerprint,
            "target_slot_ordinals": list(target_ordinals),
            "target_group_ids": [
                group_id
                for slot in targets
                for group_id in slot.group_ids
            ],
            "expected_position_fingerprint": position.position_fingerprint,
            "expected_revision_id": branch.saved_head_revision_id,
        }
        return {
            **body,
            "preview_fingerprint": fingerprint(body),
        }

    def _next_round_plan(
        self,
        session: Session,
        *,
        run_id: str,
        branch_id: str,
    ) -> dict:
        position = self._position(session, run_id, branch_id)
        if position.current_slot_kind != "match" or position.slot_ordinal is None:
            raise ValueError("Next Round requires a current competitive match slot")

        schedule = self._schedule(session, run_id, branch_id, position.current_week)
        if schedule is None or schedule.schema_version != "week_simulation_schedule.v2":
            raise ValueError(
                "Next Round requires an adopted Week Simulation Schedule v2"
            )
        current_spec = next(
            (
                slot
                for slot in schedule.slots
                if slot.ordinal == position.slot_ordinal
            ),
            None,
        )
        if current_spec is None:
            raise ValueError("current Simulation Slot is absent from the Week Schedule")
        if (
            current_spec.event_id is None
            or current_spec.draw_phase is None
            or current_spec.round_number is None
        ):
            raise ValueError("current Simulation Slot has no canonical round identity")

        round_identity = {
            "event_id": current_spec.event_id,
            "draw_phase": current_spec.draw_phase,
            "round_number": current_spec.round_number,
        }

        def same_round(slot) -> bool:
            return (
                slot.event_id == round_identity["event_id"]
                and slot.draw_phase == round_identity["draw_phase"]
                and slot.round_number == round_identity["round_number"]
            )

        remaining = tuple(
            slot
            for slot in schedule.slots
            if slot.ordinal >= position.slot_ordinal
        )
        targets = tuple(slot for slot in remaining if same_round(slot))
        if not targets or not same_round(current_spec):
            raise ValueError("current canonical Round cannot be resolved")

        first_ordinal = position.slot_ordinal
        last_ordinal = max(slot.ordinal for slot in targets)
        horizon = tuple(
            slot
            for slot in schedule.slots
            if first_ordinal <= slot.ordinal <= last_ordinal
        )
        horizon_ordinals = tuple(slot.ordinal for slot in horizon)
        contiguous = tuple(range(first_ordinal, last_ordinal + 1))
        if horizon_ordinals != contiguous:
            missing = sorted(set(contiguous) - set(horizon_ordinals))
            reserved = set(
                self._entry_slot_ordinals(
                    session, run_id, branch_id, position.current_week
                )
            ) | set(
                self._wc_slot_ordinals(
                    session, run_id, branch_id, position.current_week
                )
            )
            if reserved.intersection(missing):
                raise ValueError(
                    "Next Round cannot cross a non-match process slot"
                )
            raise ValueError(
                "Next Round requires consecutive global Simulation Slots "
                "through the round horizon"
            )

        target_ordinals = tuple(slot.ordinal for slot in targets)
        target_ordinal_set = set(target_ordinals)
        transit = tuple(
            slot for slot in horizon if slot.ordinal not in target_ordinal_set
        )
        branch = session.get(RunBranchModel, branch_id)
        if (
            branch is None
            or branch.run_id != run_id
            or branch.saved_head_revision_id is None
        ):
            raise ValueError("Next Round requires a Saved Revision head")

        body = {
            "schema_version": "authoritative_round_preview.v1",
            "run_id": run_id,
            "branch_id": branch_id,
            "week": position.current_week.model_dump(mode="json"),
            "round_identity": round_identity,
            "schedule_fingerprint": schedule.fingerprint,
            "target_slot_ordinals": list(target_ordinals),
            "target_group_ids": [
                group_id
                for slot in targets
                for group_id in slot.group_ids
            ],
            "horizon_slot_ordinals": list(horizon_ordinals),
            "transit_slot_ordinals": [slot.ordinal for slot in transit],
            "transit_group_ids": [
                group_id
                for slot in transit
                for group_id in slot.group_ids
            ],
            "expected_position_fingerprint": position.position_fingerprint,
            "expected_revision_id": branch.saved_head_revision_id,
        }
        return {
            **body,
            "preview_fingerprint": fingerprint(body),
        }

    def _next_tournament_plan(
        self,
        session: Session,
        *,
        run_id: str,
        branch_id: str,
    ) -> dict:
        position = self._position(session, run_id, branch_id)
        if position.current_slot_kind != "match" or position.slot_ordinal is None:
            raise ValueError(
                "Next Tournament requires a current competitive match slot"
            )

        schedule = self._schedule(session, run_id, branch_id, position.current_week)
        if schedule is None or schedule.schema_version != "week_simulation_schedule.v2":
            raise ValueError(
                "Next Tournament requires an adopted Week Simulation Schedule v2"
            )
        current_spec = next(
            (
                slot
                for slot in schedule.slots
                if slot.ordinal == position.slot_ordinal
            ),
            None,
        )
        if current_spec is None:
            raise ValueError(
                "current Simulation Slot is absent from the Week Schedule"
            )
        if current_spec.event_id is None:
            raise ValueError(
                "current Simulation Slot has no canonical tournament identity"
            )
        event_id = current_spec.event_id

        remaining = tuple(
            slot
            for slot in schedule.slots
            if slot.ordinal >= position.slot_ordinal
        )
        targets = tuple(slot for slot in remaining if slot.event_id == event_id)
        if not targets or current_spec.event_id != event_id:
            raise ValueError("current canonical Tournament cannot be resolved")

        first_ordinal = position.slot_ordinal
        last_ordinal = max(slot.ordinal for slot in targets)
        horizon = tuple(
            slot
            for slot in schedule.slots
            if first_ordinal <= slot.ordinal <= last_ordinal
        )
        horizon_ordinals = tuple(slot.ordinal for slot in horizon)
        contiguous = tuple(range(first_ordinal, last_ordinal + 1))
        if horizon_ordinals != contiguous:
            missing = sorted(set(contiguous) - set(horizon_ordinals))
            reserved = set(
                self._entry_slot_ordinals(
                    session, run_id, branch_id, position.current_week
                )
            ) | set(
                self._wc_slot_ordinals(
                    session, run_id, branch_id, position.current_week
                )
            )
            if reserved.intersection(missing):
                raise ValueError(
                    "Next Tournament cannot cross a non-match process slot"
                )
            raise ValueError(
                "Next Tournament requires consecutive global Simulation Slots "
                "through the tournament horizon"
            )

        target_ordinals = tuple(slot.ordinal for slot in targets)
        target_set = set(target_ordinals)
        transit = tuple(
            slot for slot in horizon if slot.ordinal not in target_set
        )
        branch = session.get(RunBranchModel, branch_id)
        if (
            branch is None
            or branch.run_id != run_id
            or branch.saved_head_revision_id is None
        ):
            raise ValueError("Next Tournament requires a Saved Revision head")

        body = {
            "schema_version": "authoritative_tournament_preview.v1",
            "run_id": run_id,
            "branch_id": branch_id,
            "week": position.current_week.model_dump(mode="json"),
            "event_id": event_id,
            "schedule_fingerprint": schedule.fingerprint,
            "target_slot_ordinals": list(target_ordinals),
            "target_group_ids": [
                group_id
                for slot in targets
                for group_id in slot.group_ids
            ],
            "horizon_slot_ordinals": list(horizon_ordinals),
            "transit_slot_ordinals": [slot.ordinal for slot in transit],
            "transit_group_ids": [
                group_id
                for slot in transit
                for group_id in slot.group_ids
            ],
            "expected_position_fingerprint": position.position_fingerprint,
            "expected_revision_id": branch.saved_head_revision_id,
        }
        return {
            **body,
            "preview_fingerprint": fingerprint(body),
        }

    def _next_week_plan(
        self,
        session: Session,
        *,
        request: AuthoritativeWeekPreviewRequest,
    ) -> dict:
        position = self._position(session, request.run_id, request.branch_id)
        week = position.current_week
        if week.week == 61:
            raise ValueError(
                "Next Week stops at Week 61; canonical Season Transition is required"
            )
        if position.current_slot_kind == "entry":
            raise ValueError(
                "Next Week cannot cross unresolved Entry application validation"
            )

        branch = session.get(RunBranchModel, request.branch_id)
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == request.branch_id
            )
        )
        if (
            branch is None
            or branch.run_id != request.run_id
            or draft is None
            or branch.saved_head_revision_id is None
        ):
            raise ValueError("Next Week requires a Saved Revision-backed Run/Branch")
        if draft.status != "clean":
            raise ValueError(
                "Next Week requires a clean Working Draft before the wider operation"
            )
        if draft.base_revision_id != branch.saved_head_revision_id:
            raise ValueError("Next Week Working Draft base is not the Saved head")

        schedule = self._schedule(
            session, request.run_id, request.branch_id, week
        )
        targets = ()
        if position.current_slot_kind == "match":
            if (
                schedule is None
                or schedule.schema_version != "week_simulation_schedule.v2"
            ):
                raise ValueError(
                    "Next Week requires an adopted Week Simulation Schedule v2"
                )
            if position.slot_ordinal is None:
                raise ValueError("Next Week current match slot has no ordinal")
            targets = tuple(
                slot
                for slot in schedule.slots
                if slot.ordinal >= position.slot_ordinal
            )
            if not targets or targets[0].ordinal != position.slot_ordinal:
                raise ValueError(
                    "Next Week current match slot is absent from the Week Schedule"
                )
            ordinals = tuple(slot.ordinal for slot in targets)
            expected = tuple(range(ordinals[0], ordinals[-1] + 1))
            if ordinals != expected:
                missing = sorted(set(expected) - set(ordinals))
                reserved = set(
                    self._entry_slot_ordinals(
                        session, request.run_id, request.branch_id, week
                    )
                ) | set(
                    self._wc_slot_ordinals(
                        session, request.run_id, request.branch_id, week
                    )
                )
                if reserved.intersection(missing):
                    raise ValueError(
                        "Next Week cannot cross a non-match Entry/WC process slot"
                    )
                raise ValueError(
                    "Next Week requires consecutive global Simulation Slots"
                )
        elif (
            schedule is not None
            and schedule.schema_version != "week_simulation_schedule.v2"
        ):
            raise ValueError(
                "Next Week requires Week Simulation Schedule v2 when one exists"
            )

        allowed_in_progress = {
            "pending_authoritative_groups",
            "tournament_source_missing",
            "terminal_sporting_checkpoint_missing",
            "week_transition_sporting_preflight_failed",
            "ranking_transition_authority_missing",
        }
        hard_blockers = tuple(
            blocker
            for blocker in position.transition_blockers
            if blocker not in allowed_in_progress
        )
        if hard_blockers:
            raise ValueError(
                "Next Week preflight is blocked: " + ", ".join(hard_blockers)
            )

        target_week = RankingWeek(
            season_index=week.season_index,
            week=week.week + 1,
        )
        authority_store = RankingTransitionAuthorityStore(session)
        authority = authority_store.get(
            run_id=request.run_id,
            branch_id=request.branch_id,
            target_ordinal=target_week.ordinal,
        )
        authority_command_id = self._week_authority_child_command_id(
            request.command_id
        )
        if authority is None:
            authority = derive_ranking_transition_authority(
                session,
                run_id=request.run_id,
                branch_id=request.branch_id,
                command_id=authority_command_id,
                audit=request.audit,
            )
            authority_mode = "derived"
        else:
            authority_mode = "existing"

        target_ordinals = tuple(slot.ordinal for slot in targets)
        body = {
            "schema_version": "authoritative_week_preview.v1",
            "run_id": request.run_id,
            "branch_id": request.branch_id,
            "week": week.model_dump(mode="json"),
            "target_week": target_week.model_dump(mode="json"),
            "schedule_fingerprint": schedule.fingerprint if schedule else None,
            "target_slot_ordinals": list(target_ordinals),
            "target_group_ids": [
                group_id
                for slot in targets
                for group_id in slot.group_ids
            ],
            "ranking_authority_mode": authority_mode,
            "ranking_authority_command_id": (
                authority_command_id
                if authority_mode == "derived"
                else authority.adopted_by_command_id
            ),
            "ranking_authority_fingerprint": authority.fingerprint,
            "expected_position_fingerprint": position.position_fingerprint,
            "expected_revision_id": branch.saved_head_revision_id,
            "initial_transition_blockers": list(position.transition_blockers),
        }
        return {
            **body,
            "preview_fingerprint": fingerprint(body),
        }

    def _next_season_plan(
        self,
        session: Session,
        *,
        request: AuthoritativeSeasonPreviewRequest,
    ) -> dict:
        position = self._position(
            session,
            request.run_id,
            request.branch_id,
            allow_missing_schedule=True,
        )
        start_week = position.current_week
        if start_week.season_index >= 49:
            raise ValueError(
                "Next Season does not own final 2049/50 closure; use canonical final Season Transition"
            )

        branch = session.get(RunBranchModel, request.branch_id)
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == request.branch_id
            )
        )
        if (
            branch is None
            or branch.run_id != request.run_id
            or draft is None
            or branch.saved_head_revision_id is None
        ):
            raise ValueError("Next Season requires a Saved Revision-backed Run/Branch")
        if branch.read_only or branch.status != "active":
            raise ValueError("Next Season requires a writable active Branch")
        if draft.status != "clean":
            raise ValueError("Next Season requires a clean Working Draft at review")
        if draft.base_revision_id != branch.saved_head_revision_id:
            raise ValueError("Next Season Working Draft base is not the Saved head")

        if position.current_slot_kind == "entry":
            initial_action = "blocked_entry_process"
        elif start_week.week == 61:
            initial_action = (
                "finish_week_61_matches"
                if position.current_slot_kind == "match"
                else (
                    "season_transition_boundary"
                    if position.terminal_sporting_fingerprint is not None
                    else "prove_or_prepare_week_61"
                )
            )
        elif position.current_slot_kind == "match":
            initial_action = "next_week"
        elif position.terminal_sporting_fingerprint is not None:
            initial_action = "next_week_transition"
        else:
            initial_action = "prove_empty_or_prepare_week"

        target_week = RankingWeek(
            season_index=start_week.season_index + 1,
            week=1,
        )
        body = {
            "schema_version": "authoritative_season_preview.v1",
            "run_id": request.run_id,
            "branch_id": request.branch_id,
            "start_week": start_week.model_dump(mode="json"),
            "target_week": target_week.model_dump(mode="json"),
            "weeks_including_current": 62 - start_week.week,
            "initial_action": initial_action,
            "initial_transition_blockers": list(position.transition_blockers),
            "auto_empty_week_policy": "calendar_proven_audited_child_only",
            "season_transition_mode": "explicit_save_and_review_checkpoint",
            "expected_position_fingerprint": position.position_fingerprint,
            "expected_revision_id": branch.saved_head_revision_id,
        }
        return {
            **body,
            "preview_fingerprint": fingerprint(body),
        }

    def inspect_schedule(self, *, run_id, branch_id):
        with self.factory() as session:
            week = self._current_week(session, run_id, branch_id)
            packages = self._packages(
                week,
                required=False,
                session=session,
                run_id=run_id,
                branch_id=branch_id,
            )
            schedule = self._schedule(session, run_id, branch_id, week)
            plans = self._topology_for_session(
                session, run_id, branch_id, packages, week=week
            ) if packages else {}
            entry_slot_ordinals = self._entry_slot_ordinals(
                session, run_id, branch_id, week
            )
            wc_slot_ordinals = self._wc_slot_ordinals(
                session, run_id, branch_id, week
            )
            requirement_position = self._position(
                session, run_id, branch_id, allow_missing_schedule=True
            )
            return {
                "run_id": run_id,
                "branch_id": branch_id,
                "week": week.model_dump(mode="json"),
                "required": (
                    bool(entry_slot_ordinals)
                    or bool(wc_slot_ordinals)
                    or len(packages) > 1
                    or len(plans) != 3
                    or any(
                        self._canonical_draw_binding(
                            session,
                            run_id=run_id,
                            branch_id=branch_id,
                            week=week,
                            event_id=package.event_id,
                        )
                        is not None
                        for package in packages
                    )
                ),
                "reserved_entry_slot_ordinals": list(entry_slot_ordinals),
                "reserved_wc_slot_ordinals": list(wc_slot_ordinals),
                "event_ids": [p.event_id for p in packages],
                "group_ids": list(plans),
                "schedule": schedule.canonical_payload() if schedule else None,
                "schedule_fingerprint": schedule.fingerprint if schedule else None,
                "expected_position_fingerprint": requirement_position.position_fingerprint,
            }

    def _build_topological_schedule_proposal(
        self,
        session,
        *,
        run_id: str,
        branch_id: str,
    ) -> tuple[WeekSimulationSchedule, str]:
        """Build the first-version Match Day schedule from canonical topology."""

        week = self._current_week(session, run_id, branch_id)
        if self._schedule(session, run_id, branch_id, week) is not None:
            raise ValueError("week schedule is already adopted and immutable")

        current = self._position(
            session, run_id, branch_id, allow_missing_schedule=True
        )
        if "week_tournament_lock_missing" in current.transition_blockers:
            raise ValueError(
                "Week Tournament Lock must resolve overlapping accepted players "
                "before Week Schedule proposal"
            )
        if "week_tournament_lock_conflict_after_lock" in current.transition_blockers:
            raise ValueError(
                "Week Tournament Lock state is inconsistent with current Entry Fields"
            )

        packages = self._packages(
            week,
            session=session,
            run_id=run_id,
            branch_id=branch_id,
        )
        plans = self._topology_for_session(
            session, run_id, branch_id, packages, week=week
        )
        if not plans:
            raise ValueError(
                "week has no authoritative tournament groups to schedule"
            )

        match_meta: dict[str, tuple[str, str, int, int]] = {}
        qualification_rounds_by_event: dict[str, int] = {}
        for package in packages:
            for match in package.qualification_matches + package.main_draw_matches:
                if match.match_id not in plans:
                    continue
                draw_phase = (
                    "qualification"
                    if match.draw_type == "qualification"
                    else "main"
                )
                if draw_phase == "qualification":
                    qualification_rounds_by_event[package.event_id] = max(
                        qualification_rounds_by_event.get(package.event_id, 0),
                        match.round_number,
                    )
                if match.match_id in match_meta:
                    raise ValueError(
                        "Match Day schedule contains duplicate canonical match identity"
                    )
                match_meta[match.match_id] = (
                    package.event_id,
                    draw_phase,
                    match.round_number,
                    match.bracket_position,
                )
        if set(match_meta) != set(plans):
            missing = sorted(set(plans) - set(match_meta))
            raise ValueError(
                "Match Day schedule cannot resolve canonical match metadata: "
                + ", ".join(missing)
            )

        day_by_group: dict[str, int] = {}
        for group_id in sorted(plans):
            event_id, draw_phase, round_number, _ = match_meta[group_id]
            qualification_rounds = qualification_rounds_by_event.get(event_id, 0)
            day_by_group[group_id] = (
                round_number
                if draw_phase == "qualification"
                else qualification_rounds + round_number
            )

        for group_id, plan in plans.items():
            for feeder in self._plan_feeders(plan):
                if feeder not in plans:
                    raise ValueError(
                        "week topology references a feeder outside the authoritative graph"
                    )
                if day_by_group[feeder] >= day_by_group[group_id]:
                    raise ValueError(
                        "Match Day schedule requires every feeder match on an earlier day"
                    )

        by_day: dict[int, list[str]] = {}
        for group_id, day in day_by_group.items():
            by_day.setdefault(day, []).append(group_id)

        reserved_nonmatch_ordinals = set(
            self._entry_slot_ordinals(session, run_id, branch_id, week)
        ) | set(self._wc_slot_ordinals(session, run_id, branch_id, week))

        slots: list[WeekSimulationScheduleSlot] = []
        scheduled_position_by_group: dict[str, tuple[int, int]] = {}
        next_global_ordinal = 1
        for match_day_ordinal in sorted(by_day):
            ordered_groups = sorted(
                by_day[match_day_ordinal],
                key=lambda group_id: (
                    *self._fair_rest_feeder_position(
                        self._plan_feeders(plans[group_id]),
                        scheduled_position_by_group,
                    ),
                    self._deterministic_schedule_tiebreak(
                        run_id=run_id,
                        branch_id=branch_id,
                        week=week,
                        group_id=group_id,
                    ),
                    group_id,
                ),
            )

            known_player_owner: dict[str, str] = {}
            for group_id in ordered_groups:
                plan = plans[group_id]
                direct_ids = (
                    tuple(plan.direct_player_ids or ())
                    if plan.participant_sources is None
                    else tuple(
                        source.removeprefix("player:")
                        for source in plan.participant_sources
                        if source.startswith("player:")
                    )
                )
                for player_id in direct_ids:
                    prior = known_player_owner.get(player_id)
                    if prior is not None:
                        raise ValueError(
                            "Match Day schedule found one directly known player in "
                            "multiple matches on the same day; Week Tournament Lock "
                            "or tournament chronology must resolve the conflict "
                            f"({player_id}: {prior}, {group_id})"
                        )
                    known_player_owner[player_id] = group_id

            for match_order, group_id in enumerate(ordered_groups, start=1):
                while next_global_ordinal in reserved_nonmatch_ordinals:
                    next_global_ordinal += 1
                event_id, draw_phase, round_number, _ = match_meta[group_id]
                slots.append(
                    WeekSimulationScheduleSlot(
                        ordinal=next_global_ordinal,
                        group_ids=(group_id,),
                        match_day_ordinal=match_day_ordinal,
                        match_order=match_order,
                        event_id=event_id,
                        draw_phase=draw_phase,
                        round_number=round_number,
                    )
                )
                scheduled_position_by_group[group_id] = (
                    match_day_ordinal,
                    match_order,
                )
                next_global_ordinal += 1

        schedule = WeekSimulationSchedule(
            schema_version="week_simulation_schedule.v2",
            run_id=run_id,
            branch_id=branch_id,
            week=week,
            slots=tuple(slots),
        )
        self._validate_schedule(session, schedule, packages)
        position_fingerprint = fingerprint(
            {
                "position": current.position_fingerprint,
                "schedule": schedule.fingerprint,
            }
        )
        return schedule, position_fingerprint

    @staticmethod
    def _fair_rest_feeder_position(
        feeder_ids: tuple[str, ...],
        scheduled_position_by_group: dict[str, tuple[int, int]],
    ) -> tuple[int, int]:
        """Order dependent matches after opponents whose feeder finished later.

        Master §13.4 priority 3 says the scheduler must consider who played the
        previous match later. Match Day has no exact clock time in pre-alpha, so
        the authoritative approximation is the stored (day, within-day order)
        position of the latest feeder. First-round/direct-only matches retain the
        existing deterministic tie-break order.
        """

        if not feeder_ids:
            return (0, 0)
        missing = tuple(
            feeder_id
            for feeder_id in feeder_ids
            if feeder_id not in scheduled_position_by_group
        )
        if missing:
            raise ValueError(
                "fair-rest scheduling requires every feeder position before "
                "ordering its dependent match: " + ", ".join(sorted(missing))
            )
        return max(scheduled_position_by_group[feeder_id] for feeder_id in feeder_ids)

    @staticmethod
    def _deterministic_schedule_tiebreak(
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
        group_id: str,
    ) -> str:
        """Stable pseudo-random tie-break for otherwise equally fair matches.

        Master §13.4 forbids ranking/seed/bracket position from creating a rest
        advantage and reserves deterministic randomness for equal valid variants.
        The final order is persisted in WeekSimulationSchedule; this token only
        makes proposal rebuilding reproducible before adoption.
        """

        payload = (
            "match_day_schedule_tiebreak.v1|"
            f"{run_id}|{branch_id}|{week.ordinal}|{group_id}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _topological_schedule_proposal_payload(
        schedule: WeekSimulationSchedule,
        *,
        position_fingerprint: str,
    ) -> dict:
        return {
            "schedule": schedule.canonical_payload(),
            "schedule_fingerprint": schedule.fingerprint,
            "position_fingerprint": position_fingerprint,
            "provenance": (
                "match_day_schedule_fair_rest.v2; "
                "one competitive match per global Simulation Slot; "
                "Qualification before Main; feeder next-day minimum; "
                "fair-rest feeder chronology; deterministic hash tie-break for "
                "otherwise equal valid variants; "
                "carryover/minimal-reflow/travel optimization remains follow-up"
            ),
            "persisted": False,
        }

    def propose_topological_schedule(self, *, run_id: str, branch_id: str):
        """Propose hard-constraint Match Day chronology from canonical topology."""
        with self.factory() as session:
            self._require_writable_scope(session, run_id, branch_id)
            schedule, position_fingerprint = (
                self._build_topological_schedule_proposal(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                )
            )
            return self._topological_schedule_proposal_payload(
                schedule,
                position_fingerprint=position_fingerprint,
            )

    def adopt_topological_schedule_proposal(
        self,
        *,
        run_id: str,
        branch_id: str,
        request_id: str,
        expected_week: RankingWeek,
        expected_schedule_fingerprint: str,
        expected_position_fingerprint: str,
    ):
        """Atomically rebuild and adopt the exact current Match Day proposal."""
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, run_id, branch_id)
            current_week = self._current_week(session, run_id, branch_id)
            row = session.get(
                WeekSimulationScheduleModel,
                (run_id, branch_id, expected_week.ordinal),
            )
            if row is not None:
                stored = self._schedule(
                    session, run_id, branch_id, expected_week
                )
                assert stored is not None
                request_fp = fingerprint(
                    {
                        "request_id": request_id,
                        "schedule": stored.canonical_payload(),
                    }
                )
                if (
                    row.request_id == request_id
                    and row.request_fingerprint == request_fp
                    and stored.fingerprint == expected_schedule_fingerprint
                ):
                    return {
                        "schedule": stored.canonical_payload(),
                        "schedule_fingerprint": stored.fingerprint,
                        "adoption": "exact_retry",
                    }
                raise ValueError("week schedule is already adopted and immutable")

            if current_week != expected_week:
                raise ValueError("schedule week is stale")
            schedule, position_fingerprint = (
                self._build_topological_schedule_proposal(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                )
            )
            if schedule.fingerprint != expected_schedule_fingerprint:
                raise ValueError("Match Day schedule proposal is stale")
            if position_fingerprint != expected_position_fingerprint:
                raise ValueError("simulation position is stale")

            request_fp = fingerprint(
                {
                    "request_id": request_id,
                    "schedule": schedule.canonical_payload(),
                }
            )
            session.add(
                WeekSimulationScheduleModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    week_ordinal=expected_week.ordinal,
                    request_id=request_id,
                    request_fingerprint=request_fp,
                    schedule_fingerprint=schedule.fingerprint,
                    payload_json=schedule.model_dump_json(),
                )
            )

        inspected = self.inspect_schedule(run_id=run_id, branch_id=branch_id)
        inspected["adoption"] = "adopted_topological_proposal"
        return inspected

    def adopt_schedule(
        self,
        schedule: WeekSimulationSchedule,
        *,
        request_id: str,
        expected_position_fingerprint: str,
    ):
        request_fp = fingerprint(
            {"request_id": request_id, "schedule": schedule.canonical_payload()}
        )
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, schedule.run_id, schedule.branch_id)
            current = self._position(
                session,
                schedule.run_id,
                schedule.branch_id,
                allow_missing_schedule=True,
            )
            row = session.get(
                WeekSimulationScheduleModel,
                (schedule.run_id, schedule.branch_id, schedule.week.ordinal),
            )
            if row:
                if (
                    row.request_id == request_id
                    and row.request_fingerprint == request_fp
                ):
                    return {
                        "schedule": schedule.canonical_payload(),
                        "schedule_fingerprint": schedule.fingerprint,
                        "adoption": "exact_retry",
                    }
                raise ValueError("week schedule is already adopted and immutable")
            proposal_position = fingerprint(
                {
                    "position": current.position_fingerprint,
                    "schedule": schedule.fingerprint,
                }
            )
            if proposal_position != expected_position_fingerprint:
                raise ValueError("simulation position is stale")
            if current.current_week != schedule.week:
                raise ValueError("schedule week is stale")
            packages = self._packages(
                schedule.week,
                session=session,
                run_id=schedule.run_id,
                branch_id=schedule.branch_id,
            )
            self._validate_schedule(
                session,
                schedule,
                packages,
            )
            session.add(
                WeekSimulationScheduleModel(
                    run_id=schedule.run_id,
                    branch_id=schedule.branch_id,
                    week_ordinal=schedule.week.ordinal,
                    request_id=request_id,
                    request_fingerprint=request_fp,
                    schedule_fingerprint=schedule.fingerprint,
                    payload_json=schedule.model_dump_json(),
                )
            )
        return self.inspect_schedule(
            run_id=schedule.run_id, branch_id=schedule.branch_id
        )

    def preview_schedule(self, schedule: WeekSimulationSchedule):
        with self.factory() as session:
            self._require_writable_scope(session, schedule.run_id, schedule.branch_id)
            if self._schedule(
                session, schedule.run_id, schedule.branch_id, schedule.week
            ):
                raise ValueError("week schedule is already adopted and immutable")
            current = self._position(
                session,
                schedule.run_id,
                schedule.branch_id,
                allow_missing_schedule=True,
            )
            if current.current_week != schedule.week:
                raise ValueError("schedule week is stale")
            self._validate_schedule(
                session,
                schedule,
                self._packages(
                    schedule.week,
                    session=session,
                    run_id=schedule.run_id,
                    branch_id=schedule.branch_id,
                ),
            )
            return {
                "schedule": schedule.canonical_payload(),
                "schedule_fingerprint": schedule.fingerprint,
                "position_fingerprint": fingerprint(
                    {
                        "position": current.position_fingerprint,
                        "schedule": schedule.fingerprint,
                    }
                ),
            }

    @staticmethod
    def _topology(packages):
        """Build the canonical executable DAG exclusively from persisted sources."""
        plans = {}
        for package in packages:
            if package.validation_errors:
                raise ValueError("persisted tournament topology has validation errors")
            matches = tuple(package.qualification_matches + package.main_draw_matches)
            by_id = {match.match_id: match for match in matches}
            if len(by_id) != len(matches):
                raise ValueError("persisted topology contains duplicate match identity")
            incoming = {match_id: [] for match_id in by_id}
            # Historical v1-v3 authority could omit feeder links for the reviewed
            # three-match compatibility shape. Keep that reader; new/general
            # topology never receives this inference.
            legacy_four = False
            if len(matches) == 3 and not any(m.winner_to_match_id for m in matches):
                _, ordered = validate_adopted_four_player_match_package(package)
                incoming[ordered[2].match_id] = [
                    ordered[0].match_id,
                    ordered[1].match_id,
                ]
                terminals = [ordered[2].match_id]
                legacy_four = True
            for match in matches:
                if match.event_id != package.event_id:
                    raise ValueError(
                        "tournaments lack authoritative cross-event identity: "
                        "persisted topology contains a foreign event match"
                    )
                if match.winner_to_match_id:
                    if match.winner_to_match_id not in by_id:
                        raise ValueError(
                            "persisted topology feeder target does not exist"
                        )
                    incoming[match.winner_to_match_id].append(match.match_id)
            promotion_by_target = {
                (item.target_match_id, item.target_side): item.source_match_id
                for item in package.frozen_qualifier_promotions
            }
            for item in package.frozen_qualifier_promotions:
                if (
                    item.source_match_id not in by_id
                    or item.target_match_id not in by_id
                ):
                    raise ValueError(
                        "frozen qualifier promotion references a missing match"
                    )
                incoming[item.target_match_id].append(item.source_match_id)
            visiting, visited = set(), set()

            def validate_acyclic(node):
                if node in visiting:
                    raise ValueError("persisted topology contains a feeder cycle")
                if node in visited:
                    return
                visiting.add(node)
                target = by_id[node].winner_to_match_id
                if target:
                    validate_acyclic(target)
                visiting.remove(node)
                visited.add(node)

            for node in by_id:
                validate_acyclic(node)
            bye_winners = {}
            for match in matches:
                if match.match_id in package.frozen_bye_match_ids:
                    known = [
                        p for p in (match.top_player_id, match.bottom_player_id) if p
                    ]
                    winner = match.winner_player_id or (
                        known[0] if len(known) == 1 else None
                    )
                    if winner is None or not match.winner_to_match_id:
                        raise ValueError("persisted BYE advancement is ambiguous")
                    bye_winners[match.match_id] = winner

            def node_ref(match_id):
                parts = match_id.split(":")
                rounds = [p for p in parts if p.startswith("R") and p[1:].isdigit()]
                numbers = [p for p in parts if p.startswith("M") and p[1:].isdigit()]
                return (
                    f"{rounds[0]}-N{numbers[0][1:]}" if rounds and numbers else match_id
                )

            for match in matches:
                if match.match_id in bye_winners:
                    continue
                sources = []
                for side_index, side in enumerate(("top", "bottom")):
                    promoted = promotion_by_target.get((match.match_id, side))
                    candidates = [
                        feeder
                        for feeder in incoming[match.match_id]
                        if getattr(match, f"{side}_source") == node_ref(feeder)
                        or getattr(match, f"{side}_slot_id") == feeder
                    ]
                    feeder = promoted or (
                        candidates[0] if len(candidates) == 1 else None
                    )
                    if (
                        feeder is None
                        and legacy_four
                        and len(incoming[match.match_id]) == 2
                    ):
                        feeder = incoming[match.match_id][side_index]
                    if feeder in bye_winners:
                        sources.append(f"player:{bye_winners[feeder]}")
                    elif feeder:
                        sources.append(f"winner:{feeder}")
                    else:
                        player_id = getattr(match, f"{side}_player_id")
                        if not player_id:
                            raise ValueError(
                                "persisted topology has an unresolved participant source"
                            )
                        sources.append(f"player:{player_id}")
                plan = SimulationMatchEventPlan(
                    group_id=match.match_id,
                    event_id=package.event_id,
                    match_id=match.match_id,
                    participant_sources=tuple(sources),
                )
                if match.match_id in plans:
                    raise ValueError("week topology contains duplicate group identity")
                plans[match.match_id] = plan

            # Acyclicity and reachability are validated independently of authored
            # round names/numbers. Every node must drain into the sole terminal.
            terminals = (
                terminals
                if legacy_four
                else [
                    m.match_id
                    for m in package.main_draw_matches
                    if not m.winner_to_match_id
                ]
            )
            if len(terminals) != 1:
                raise ValueError(
                    "persisted topology must identify exactly one terminal match"
                )
        return plans

    def _topology_for_session(
        self, session, run_id, branch_id, packages, *, week
    ):
        """Prefer the Draw source frozen for this tournament authority generation."""
        if not packages:
            return {}
        canonical = []
        for package in packages:
            draw = self._canonical_draw_binding(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=week,
                event_id=package.event_id,
            )
            canonical.append((package, draw))
        if all(draw is None for _, draw in canonical):
            return self._topology(packages)
        if any(draw is None for _, draw in canonical):
            raise ValueError(
                "week mixes canonical Draw authority with legacy-only tournament topology"
            )
        plans = {}
        for package, draw in canonical:
            projection = project_canonical_draw_to_match_topology(
                draw=draw,
                package=package,
            )
            for plan in projection.plans:
                if plan.group_id in plans:
                    raise ValueError("week topology contains duplicate group identity")
                plans[plan.group_id] = plan
        return plans

    def _validate_schedule(self, session, schedule, packages):
        plans = self._topology_for_session(
            session,
            schedule.run_id,
            schedule.branch_id,
            packages,
            week=schedule.week,
        )
        reserved_entry_ordinals = set(
            self._entry_slot_ordinals(
                session,
                schedule.run_id,
                schedule.branch_id,
                schedule.week,
            )
        )
        reserved_wc_ordinals = set(
            self._wc_slot_ordinals(
                session,
                schedule.run_id,
                schedule.branch_id,
                schedule.week,
            )
        )
        reserved_nonmatch_ordinals = reserved_entry_ordinals | reserved_wc_ordinals
        overlap = reserved_nonmatch_ordinals & {
            slot.ordinal for slot in schedule.slots
        }
        if overlap:
            raise ValueError(
                "match schedule collides with persisted non-match global slot"
            )
        match_ordinals = {slot.ordinal for slot in schedule.slots}
        required_prefix = set(range(1, max(match_ordinals) + 1))
        unexplained_gaps = required_prefix - match_ordinals - reserved_nonmatch_ordinals
        if unexplained_gaps:
            raise ValueError(
                "match schedule contains a global-slot gap not owned by an "
                "entry-decision slot or WC-decision slot"
            )
        authored_sequence = tuple(g for slot in schedule.slots for g in slot.group_ids)
        if len(authored_sequence) != len(set(authored_sequence)) or set(
            authored_sequence
        ) != set(plans):
            raise ValueError("schedule must cover every supported group exactly once")
        ordinal = {g: slot.ordinal for slot in schedule.slots for g in slot.group_ids}
        for group_id, plan in plans.items():
            for feeder in self._plan_feeders(plan):
                if ordinal[feeder] >= ordinal[group_id]:
                    raise ValueError(
                        "dependent groups require a strictly later slot than feeders"
                    )

        if schedule.schema_version == "week_simulation_schedule.v2":
            match_meta: dict[str, tuple[str, str, int]] = {}
            known_players: dict[str, tuple[str, ...]] = {}
            qualification_groups_by_event: dict[str, list[str]] = {}
            main_groups_by_event: dict[str, list[str]] = {}
            for package in packages:
                for match in package.qualification_matches + package.main_draw_matches:
                    if match.match_id not in plans:
                        continue
                    draw_phase = (
                        "qualification"
                        if match.draw_type == "qualification"
                        else "main"
                    )
                    match_meta[match.match_id] = (
                        package.event_id,
                        draw_phase,
                        match.round_number,
                    )
                    plan = plans[match.match_id]
                    direct_ids = (
                        tuple(plan.direct_player_ids or ())
                        if plan.participant_sources is None
                        else tuple(
                            source.removeprefix("player:")
                            for source in plan.participant_sources
                            if source.startswith("player:")
                        )
                    )
                    known_players[match.match_id] = direct_ids
                    target = (
                        qualification_groups_by_event
                        if draw_phase == "qualification"
                        else main_groups_by_event
                    )
                    target.setdefault(package.event_id, []).append(match.match_id)

            if set(match_meta) != set(plans):
                raise ValueError(
                    "Match Day schedule metadata does not cover canonical match topology"
                )

            day_of: dict[str, int] = {}
            order_by_day: dict[int, list[tuple[int, int, str]]] = {}
            player_by_day: dict[int, dict[str, str]] = {}
            for slot in schedule.slots:
                group_id = slot.group_ids[0]
                expected_event, expected_phase, expected_round = match_meta[group_id]
                if (
                    slot.event_id,
                    slot.draw_phase,
                    slot.round_number,
                ) != (
                    expected_event,
                    expected_phase,
                    expected_round,
                ):
                    raise ValueError(
                        "Match Day schedule metadata differs from canonical match evidence"
                    )
                assert slot.match_day_ordinal is not None
                assert slot.match_order is not None
                day_of[group_id] = slot.match_day_ordinal
                order_by_day.setdefault(slot.match_day_ordinal, []).append(
                    (slot.match_order, slot.ordinal, group_id)
                )
                owners = player_by_day.setdefault(slot.match_day_ordinal, {})
                for player_id in known_players[group_id]:
                    prior = owners.get(player_id)
                    if prior is not None:
                        raise ValueError(
                            "Match Day schedule assigns one directly known player "
                            "to multiple matches on the same day "
                            f"({player_id}: {prior}, {group_id})"
                        )
                    owners[player_id] = group_id

            for day, values in order_by_day.items():
                ordered = sorted(values)
                if [order for order, _, _ in ordered] != list(
                    range(1, len(ordered) + 1)
                ):
                    raise ValueError(
                        f"Match Day {day} match order is not contiguous"
                    )
                ordinals = [global_ordinal for _, global_ordinal, _ in ordered]
                if ordinals != sorted(ordinals):
                    raise ValueError(
                        "Match Day match order must follow global Simulation Slot order"
                    )

            chronological = [
                (
                    slot.match_day_ordinal,
                    slot.match_order,
                    slot.ordinal,
                )
                for slot in schedule.slots
            ]
            if chronological != sorted(chronological):
                raise ValueError(
                    "global Simulation Slot order must follow Match Day chronology"
                )

            for group_id, plan in plans.items():
                for feeder in self._plan_feeders(plan):
                    if day_of[feeder] >= day_of[group_id]:
                        raise ValueError(
                            "dependent match must start on a later Match Day than its feeder"
                        )

            for event_id, q_groups in qualification_groups_by_event.items():
                main_groups = main_groups_by_event.get(event_id, [])
                if not main_groups:
                    continue
                if max(day_of[group] for group in q_groups) >= min(
                    day_of[group] for group in main_groups
                ):
                    raise ValueError(
                        "Qualification must finish before Main Draw starts"
                    )

    @staticmethod
    def _plan_feeders(plan):
        if plan.participant_sources:
            return tuple(
                source.removeprefix("winner:")
                for source in plan.participant_sources
                if source.startswith("winner:")
            )
        return tuple(plan.feeder_group_ids or ())

    def _position(self, session, run_id, branch_id, *, allow_missing_schedule=False):
        week = self._current_week(session, run_id, branch_id)
        frozen = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        packages = (
            self._authority_package(session, run_id, branch_id, week, adopt=False)[0]
            if frozen
            else self._packages(
                week,
                required=False,
                session=session,
                run_id=run_id,
                branch_id=branch_id,
            )
        )
        schedule = self._schedule(session, run_id, branch_id, week)
        entry_slot_ordinals = self._entry_slot_ordinals(
            session, run_id, branch_id, week
        )
        wc_slot_ordinals = self._wc_slot_ordinals(
            session, run_id, branch_id, week
        )
        lock_event_ids = self._week_tournament_lock_event_ids(
            session,
            run_id=run_id,
            branch_id=branch_id,
            week=week,
        )
        if lock_event_ids:
            _, current_lock_conflicts = resolve_week_tournament_lock_evidence(
                session,
                run_id=run_id,
                branch_id=branch_id,
                event_ids=lock_event_ids,
            )
        else:
            current_lock_conflicts = {}
        week_tournament_lock = WeekTournamentLockStore(session).get(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week.ordinal,
        )
        entry_validation_rows = tuple(
            session.scalars(
                select(ResolvedApplicationValidationSlotModel)
                .where(
                    ResolvedApplicationValidationSlotModel.run_id == run_id,
                    ResolvedApplicationValidationSlotModel.branch_id == branch_id,
                    ResolvedApplicationValidationSlotModel.week_ordinal == week.ordinal,
                )
                .order_by(
                    ResolvedApplicationValidationSlotModel.decision_slot_ordinal
                )
            ).all()
        )
        resolved_entry_ordinals = {
            row.decision_slot_ordinal for row in entry_validation_rows
        }
        unresolved_entry_ordinals = tuple(
            ordinal
            for ordinal in entry_slot_ordinals
            if ordinal not in resolved_entry_ordinals
        )
        if (
            schedule is None
            and packages
            and (
                bool(entry_slot_ordinals)
                or bool(wc_slot_ordinals)
                or len(packages) > 1
                or len(
                    self._topology_for_session(
                        session, run_id, branch_id, packages, week=week
                    )
                )
                != 3
                or any(
                    self._canonical_draw_binding(
                        session,
                        run_id=run_id,
                        branch_id=branch_id,
                        week=week,
                        event_id=package.event_id,
                    )
                    is not None
                    for package in packages
                )
            )
            and not allow_missing_schedule
        ):
            raise ValueError(
                "tournaments lack authoritative cross-event or general-draw "
                "Simulation Slot chronology"
            )
        slots = session.scalars(
            select(SimulationSlotModel)
            .where(
                SimulationSlotModel.run_id == run_id,
                SimulationSlotModel.branch_id == branch_id,
                SimulationSlotModel.week_ordinal == week.ordinal,
            )
            .order_by(SimulationSlotModel.slot_ordinal)
        ).all()
        groups = session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
                SimulationEventGroupModel.week_ordinal == week.ordinal,
            )
        ).all()
        done = {g.group_id for g in groups}
        plans = (
            self._topology_for_session(
                session, run_id, branch_id, packages, week=week
            )
            if packages
            else {}
        )
        current = next((s for s in slots if s.status != "complete"), None)
        authored_slots = schedule.slots if schedule else ()
        if (
            not authored_slots
            and not entry_slot_ordinals
            and not wc_slot_ordinals
            and len(packages) == 1
            and len(plans) == 3
        ):
            matches = sorted(
                packages[0].main_draw_matches,
                key=lambda m: (m.round_number, m.bracket_position),
            )
            authored_slots = (
                type(
                    "S",
                    (),
                    {"ordinal": 1, "group_ids": tuple(m.match_id for m in matches[:2])},
                )(),
                type("S", (), {"ordinal": 2, "group_ids": (matches[2].match_id,)})(),
            )
        next_spec = next(
            (x for x in authored_slots if any(g not in done for g in x.group_ids)), None
        )
        current_ids = tuple(
            current
            and AuthoritativeSlotMatchExecutor._load_plan(current).group_ids
            or (next_spec.group_ids if next_spec else ())
        )
        unresolved = tuple(g for g in current_ids if g not in done)
        target_match_ordinal = (
            current.slot_ordinal
            if current is not None
            else (next_spec.ordinal if next_spec is not None else None)
        )
        pending_entry_ordinal = (
            min(unresolved_entry_ordinals) if unresolved_entry_ordinals else None
        )
        entry_is_current = (
            pending_entry_ordinal is not None
            and (
                target_match_ordinal is None
                or pending_entry_ordinal < target_match_ordinal
            )
        )
        eligible_groups = (
            ()
            if entry_is_current
            else tuple(
                g for g in unresolved if set(self._plan_feeders(plans[g])) <= done
            )
        )
        blocked_groups = tuple(
            g for g in plans if g not in done and g not in eligible_groups
        )
        owned_store = OwnedTournamentRankingSourceStore(session)
        owned = {
            p.event_id: owned_store.get(
                run_id=run_id, branch_id=branch_id, edition_id=p.event_id
            )
            for p in packages
        }
        executor = AuthoritativeSlotMatchExecutor(session)
        terminal = (
            executor.terminal_checkpoint(run_id=run_id, branch_id=branch_id, week=week)
            if slots and all(s.status == "complete" for s in slots)
            else None
        )
        lifecycle = get_lifecycle(
            session, run_id=run_id, branch_id=branch_id, week=week
        )
        sporting = get_sporting(
            session, run_id=run_id, branch_id=branch_id, week=week
        )
        explicit_empty_context = (
            self._explicit_empty_week_context(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=week,
                sporting=sporting,
            )
            if (
                not packages
                and schedule is None
                and not slots
                and not groups
                and not entry_slot_ordinals
                and not wc_slot_ordinals
            )
            else None
        )
        blockers = []
        if unresolved_entry_ordinals:
            blockers.append("entry_validation_pending")
        if current_lock_conflicts and week_tournament_lock is None:
            blockers.append("week_tournament_lock_missing")
        elif current_lock_conflicts and week_tournament_lock is not None:
            blockers.append("week_tournament_lock_conflict_after_lock")
        if explicit_empty_context is None and schedule is None and (
            bool(entry_slot_ordinals)
            or bool(wc_slot_ordinals)
            or len(packages) > 1
            or len(plans) != 3
            or any(
                self._canonical_draw_binding(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    week=week,
                    event_id=package.event_id,
                )
                is not None
                for package in packages
            )
        ):
            blockers.append("week_schedule_missing")
        if set(done) != set(plans):
            blockers.append("pending_authoritative_groups")
        if any(v is None for v in owned.values()):
            blockers.append("tournament_source_missing")
        if terminal is None and explicit_empty_context is None:
            blockers.append("terminal_sporting_checkpoint_missing")
        if lifecycle is None:
            blockers.append("lifecycle_roster_missing")
        if sporting is None:
            blockers.append("sporting_roster_missing")
        if not blockers and explicit_empty_context is None:
            try:
                preflight_completed_context_from_authoritative_matches(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    completed_week=week,
                    player_ids=tuple(p.player_id for p in sporting.players),
                )
                if any(x.binding.completed_week != week for x in owned.values()):
                    raise ValueError()
            except ValueError:
                blockers.append("week_transition_sporting_preflight_failed")
        if not (week.season_index == 49 and week.week == 61):
            blockers.extend(
                x
                for x in preview_persisted_week_transition(
                    session,
                    self.awards_service,
                    run_id=run_id,
                    branch_id=branch_id,
                    completed_week=week,
                )
                if x not in blockers
            )
        branch = session.get(RunBranchModel, branch_id)
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == branch_id
            )
        )
        transition_authority = session.get(
            RankingTransitionAuthorityModel, (run_id, branch_id, week.ordinal + 1)
        )
        world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
        body = {
            "scope": [run_id, branch_id, week.ordinal],
            "schedule": schedule.fingerprint if schedule else None,
            "entry_slot_ordinals": list(entry_slot_ordinals),
            "wc_slot_ordinals": list(wc_slot_ordinals),
            "week_tournament_lock": (
                week_tournament_lock.fingerprint
                if week_tournament_lock is not None
                else None
            ),
            "week_tournament_lock_conflicts": [
                [player_id, list(current_lock_conflicts[player_id])]
                for player_id in sorted(current_lock_conflicts)
            ],
            "entry_validation_slots": [
                (row.decision_slot_ordinal, row.fingerprint)
                for row in entry_validation_rows
            ],
            "current_slot_kind": "entry" if entry_is_current else (
                "match" if target_match_ordinal is not None else None
            ),
            "current_slot_ordinal": (
                pending_entry_ordinal if entry_is_current else target_match_ordinal
            ),
            "proposed_schedule_requirement": [p.event_id for p in packages],
            "slots": [
                (s.slot_id, s.status, s.plan_fingerprint, s.terminal_checkpoint_json)
                for s in slots
            ],
            "groups": [
                (g.group_id, g.command_fingerprint, g.result_fingerprint)
                for g in sorted(groups, key=lambda x: x.group_id)
            ],
            "owned": sorted(
                (k, v.fingerprint if v else None) for k, v in owned.items()
            ),
            "tournament_authority": frozen.authority_fingerprint
            if frozen
            else (
                self._tournament_authority_fingerprint(
                    run_id,
                    branch_id,
                    week,
                    tuple(
                        (
                            p,
                            self.awards_service.freeze_point_award_authority(p),
                            (
                                draw.fingerprint
                                if (
                                    draw := TournamentDrawAuthorityStore(session).get(
                                        run_id=run_id,
                                        branch_id=branch_id,
                                        event_id=p.event_id,
                                    )
                                )
                                is not None
                                else None
                            ),
                        )
                        for p in packages
                    ),
                )
                if packages
                else None
            ),
            "sporting": sporting.fingerprint if sporting else None,
            "lifecycle": lifecycle.fingerprint if lifecycle else None,
            "branch_head": branch.saved_head_revision_id if branch else None,
            "draft": [draft.base_revision_id, draft.status, draft.draft_version]
            if draft
            else None,
            "transition_authority": (
                transition_authority.fingerprint if transition_authority else None
            ),
            "world": (
                [world.current_ordinal, world.ranking_fingerprint] if world else None
            ),
            "terminal": terminal.fingerprint if terminal else None,
            "empty_week_context": (
                explicit_empty_context.fingerprint
                if explicit_empty_context is not None
                else None
            ),
        }
        ready = not blockers
        return AuthoritativeSimulationPosition(
            run_id=run_id,
            branch_id=branch_id,
            current_week=week,
            current_slot_kind=(
                "entry"
                if entry_is_current
                else ("match" if target_match_ordinal is not None else None)
            ),
            current_slot_id=(
                f"week-{week.ordinal}:entry-slot:{pending_entry_ordinal}"
                if entry_is_current
                else (
                    current.slot_id
                    if current
                    else (
                        (
                            f"week-{week.ordinal}:slot:{next_spec.ordinal}"
                            if schedule
                            else f"{packages[0].event_id}:slot:{next_spec.ordinal}"
                        )
                        if next_spec
                        else None
                    )
                )
            ),
            slot_ordinal=(
                pending_entry_ordinal if entry_is_current else target_match_ordinal
            ),
            unresolved_group_ids=(() if entry_is_current else unresolved),
            eligible_match_ids=tuple(plans[g].match_id for g in eligible_groups),
            blocked_match_ids=tuple(plans[g].match_id for g in blocked_groups),
            current_slot_complete=(False if entry_is_current else not unresolved),
            supported_tournament_complete=bool(packages) and all(owned.values()),
            week_ready_for_transition=ready,
            transition_blockers=tuple(blockers),
            terminal_sporting_fingerprint=terminal.fingerprint if terminal else None,
            position_fingerprint=fingerprint(body),
        )

    def _ensure_current_slot(self, session, command, packages):
        pos = self._position(session, command.run_id, command.branch_id)
        if pos.current_slot_kind == "entry":
            raise ValueError(
                "nearest unresolved global Simulation Slot is an Entry decision slot "
                "awaiting complete application validation"
            )
        if any(
            s.status != "complete"
            for s in session.scalars(
                select(SimulationSlotModel).where(
                    SimulationSlotModel.run_id == command.run_id,
                    SimulationSlotModel.branch_id == command.branch_id,
                    SimulationSlotModel.week_ordinal == command.expected_week.ordinal,
                )
            ).all()
        ):
            return
        schedule = self._schedule(
            session, command.run_id, command.branch_id, command.expected_week
        )
        plans = self._topology_for_session(
            session,
            command.run_id,
            command.branch_id,
            packages,
            week=command.expected_week,
        )
        if schedule:
            spec = next(x for x in schedule.slots if x.ordinal == pos.slot_ordinal)
        else:
            ids = tuple(plans)
            spec = type(
                "S",
                (),
                {
                    "ordinal": pos.slot_ordinal,
                    "group_ids": ids[:2] if pos.slot_ordinal == 1 else ids[2:],
                },
            )()
        selected = tuple(plans[g] for g in spec.group_ids)
        authority_fp = self._authority_package(
            session,
            command.run_id,
            command.branch_id,
            command.expected_week,
            adopt=False,
        )[1]
        AuthoritativeSlotMatchExecutor(session).create_slot(
            run_id=command.run_id,
            branch_id=command.branch_id,
            week=command.expected_week,
            slot_id=pos.current_slot_id,
            ordinal=spec.ordinal,
            group_ids=spec.group_ids,
            match_events=selected,
            dependency_ids=tuple(f for p in selected for f in self._plan_feeders(p)),
            provenance=(
                f"adopted-authority:{authority_fp};"
                f"week-schedule:{schedule.fingerprint if schedule else 'single-event-compat'};"
                f"match-day:{getattr(spec, 'match_day_ordinal', None) or 'legacy'};"
                f"match-order:{getattr(spec, 'match_order', None) or 'legacy'}"
            ),
        )

    def _eligible_groups(self, session, position, packages):
        slot = session.get(
            SimulationSlotModel,
            (
                position.run_id,
                position.branch_id,
                position.current_week.ordinal,
                position.current_slot_id,
            ),
        )
        plan = AuthoritativeSlotMatchExecutor._load_plan(slot)
        return tuple(
            e.group_id
            for e in plan.match_events
            if e.match_id in position.eligible_match_ids
        )

    def _group_execution_context(self, session, command, packages, group_id):
        pos = self._position(session, command.run_id, command.branch_id)
        if pos.current_slot_id is None:
            raise ValueError("current authoritative match slot is missing")
        slot = session.get(
            SimulationSlotModel,
            (
                command.run_id,
                command.branch_id,
                command.expected_week.ordinal,
                pos.current_slot_id,
            ),
        )
        if slot is None:
            raise ValueError("current authoritative Simulation Slot disappeared")
        plan = AuthoritativeSlotMatchExecutor._load_plan(slot)
        try:
            event = next(e for e in plan.match_events if e.group_id == group_id)
        except StopIteration as exc:
            raise ValueError("target match group is not planned in the current slot") from exc
        package = next(p for p in packages if p.event_id == event.event_id)
        if event.participant_sources:
            players = tuple(
                source.removeprefix("player:")
                if source.startswith("player:")
                else AuthoritativeSlotMatchExecutor._load_group(
                    session.scalar(
                        select(SimulationEventGroupModel).where(
                            SimulationEventGroupModel.run_id == command.run_id,
                            SimulationEventGroupModel.branch_id == command.branch_id,
                            SimulationEventGroupModel.week_ordinal
                            == command.expected_week.ordinal,
                            SimulationEventGroupModel.group_id
                            == source.removeprefix("winner:"),
                        )
                    )
                ).result.winner_player_id
                for source in event.participant_sources
            )
        elif event.direct_player_ids:
            players = event.direct_player_ids
        else:
            players = tuple(
                AuthoritativeSlotMatchExecutor._load_group(
                    session.scalar(
                        select(SimulationEventGroupModel).where(
                            SimulationEventGroupModel.run_id == command.run_id,
                            SimulationEventGroupModel.branch_id == command.branch_id,
                            SimulationEventGroupModel.week_ordinal
                            == command.expected_week.ordinal,
                            SimulationEventGroupModel.group_id == f,
                        )
                    )
                ).result.winner_player_id
                for f in event.feeder_group_ids
            )
        if len(players) != 2:
            raise ValueError("supported reconstruction requires exactly two participants")
        return slot, plan, event, package, players

    def _execute_group(
        self, session, command, packages, group_id, *, seed_override: int | None = None
    ):
        slot, plan, event, package, players = self._group_execution_context(
            session, command, packages, group_id
        )
        authority_fp = self._authority_package(
            session,
            command.run_id,
            command.branch_id,
            command.expected_week,
            adopt=False,
        )[1]
        seed = (
            seed_override
            if seed_override is not None
            else int(
                hashlib.sha256(
                    f"{command.run_id}|{command.branch_id}|{command.expected_week.ordinal}|{authority_fp}|{group_id}".encode()
                ).hexdigest()[:15],
                16,
            )
        )
        return AuthoritativeSlotMatchExecutor(session).execute_match_group(
            run_id=command.run_id,
            branch_id=command.branch_id,
            week=command.expected_week,
            slot_id=slot.slot_id,
            group_id=group_id,
            event_id=package.event_id,
            match_id=event.match_id,
            player_a_id=players[0],
            player_b_id=players[1],
            seed=seed,
            expected_slot_start_fingerprint=plan.slot_start_fingerprint,
        )

    def _advance_or_close(self, session, command, packages, *, fault_at=None):
        # Tournament close is distinct from Week/Season Transition. Week 61 must
        # still freeze completed tournament sources before the season boundary can
        # consume them; _position() separately exposes season_transition_required.
        executor = AuthoritativeSlotMatchExecutor(session)
        loaded = {
            g.group_id: executor._load_group(g)
            for g in session.scalars(
                select(SimulationEventGroupModel).where(
                    SimulationEventGroupModel.run_id == command.run_id,
                    SimulationEventGroupModel.branch_id == command.branch_id,
                    SimulationEventGroupModel.week_ordinal
                    == command.expected_week.ordinal,
                )
            ).all()
        }
        items = self._decode_adopted_authority(
            session.get(
                AdoptedTournamentAuthorityModel,
                (command.run_id, command.branch_id, command.expected_week.ordinal),
            ).package_json
        )
        evidence_by_event = {item.event_id: item for item in items}
        if set(evidence_by_event) != {package.event_id for package in packages}:
            raise ValueError(
                "frozen tournament authority package universe changed"
            )
        for package in packages:
            evidence = evidence_by_event[package.event_id]
            point_authority = evidence.point_award_authority
            draw_fp = evidence.draw_authority_fingerprint
            matches = tuple(
                m
                for m in package.qualification_matches + package.main_draw_matches
                if m.match_id not in package.frozen_bye_match_ids
            )
            if not all(m.match_id in loaded for m in matches):
                continue
            if draw_fp is not None:
                draw = TournamentDrawAuthorityStore(session).get(
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    event_id=package.event_id,
                )
                if draw is None or draw.fingerprint != draw_fp:
                    raise ValueError(
                        "frozen tournament canonical Draw binding changed"
                    )
                projection = project_canonical_draw_to_match_topology(
                    draw=draw,
                    package=package,
                )
                terminal_match_id = projection.terminal_group_id
            else:
                terminals = tuple(
                    m
                    for m in package.main_draw_matches
                    if m.match_id not in package.frozen_bye_match_ids
                    and not m.winner_to_match_id
                )
                if len(matches) == 3 and len(terminals) == 3:
                    _, ordered = validate_adopted_four_player_match_package(package)
                    terminals = (ordered[2],)
                if len(terminals) != 1:
                    raise ValueError(
                        "frozen tournament topology has ambiguous terminal"
                    )
                terminal_match_id = terminals[0].match_id
            auth = AuthoritativeTournamentResult(
                event_id=package.event_id,
                groups=tuple(loaded[m.match_id] for m in matches),
                terminal_group_ids=(terminal_match_id,),
                champion_player_id=loaded[
                    terminal_match_id
                ].result.winner_player_id,
                match_result_fingerprints=tuple(
                    loaded[m.match_id].result_fingerprint for m in matches
                ),
            )
            if fault_at == "after_final_before_source":
                raise RuntimeError(
                    "fault after tournament final before ranking source persistence"
                )
            store = OwnedTournamentRankingSourceStore(session)
            existing = store.get(
                run_id=command.run_id,
                branch_id=command.branch_id,
                edition_id=package.event_id,
            )
            if existing:
                self._validate_existing_owned_source(existing, command, package, auth)
                continue
            canonical_result = None
            canonical_awards = None
            canonical_prize_awards = None
            result = None
            awards = None
            if draw_fp is not None:
                (
                    _,
                    canonical_result,
                    canonical_awards,
                    canonical_prize_awards,
                ) = build_run_owned_tournament_authorities(
                    package=package,
                    authoritative=auth,
                    draw=draw,
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    week=command.expected_week,
                    calendar_event=evidence.calendar_event,
                    award_seed=self._stable_seed(package, "awards"),
                    frozen_point_authority=point_authority,
                )
            else:
                _, result, awards = build_authoritative_tournament_ranking_packages(
                    self.awards_service,
                    package=package,
                    authoritative=auth,
                    result_seed=self._stable_seed(package, "result"),
                    award_seed=self._stable_seed(package, "awards"),
                    frozen_point_authority=point_authority,
                )
            first_publication_week, closing_eligibility_ordinal = (
                self._ranking_source_boundary(command.expected_week)
            )
            binding = TournamentRankingBinding(
                run_id=command.run_id,
                branch_id=command.branch_id,
                edition_id=package.event_id,
                event_id=package.event_id,
                completed_week=command.expected_week,
                first_publication_week=first_publication_week,
                closing_eligibility_ordinal=closing_eligibility_ordinal,
                validity_weeks=61,
                ranking_status="ranked",
                expected_result_fingerprint=(
                    canonical_result.fingerprint
                    if canonical_result is not None
                    else result.metadata.build_fingerprint
                ),
                expected_award_fingerprint=(
                    canonical_awards.fingerprint
                    if canonical_awards is not None
                    else awards.metadata.build_fingerprint
                ),
            )
            if canonical_result is not None and canonical_awards is not None:
                if binding.closing_only:
                    prepare_final_season_closing_ranking_results(
                        binding,
                        canonical_result,
                        canonical_awards,
                    )
                    source = OwnedTournamentRankingSource(
                        schema_version="owned_tournament_ranking_source.v6",
                        binding=binding,
                        canonical_result=canonical_result,
                        canonical_awards=canonical_awards,
                        canonical_prize_awards=canonical_prize_awards,
                        adopted_by_command_id=command.command_id,
                        provenance_kind=(
                            "canonical_run_owned_tournament_authorities_and_prize_money_final_closing"
                            if canonical_prize_awards is not None
                            else "canonical_run_owned_tournament_authorities_final_closing"
                        ),
                    )
                else:
                    prepare_canonical_tournament_ranking_sources(
                        binding,
                        canonical_result,
                        canonical_awards,
                    )
                    if canonical_prize_awards is not None:
                        source = OwnedTournamentRankingSource(
                            schema_version="owned_tournament_ranking_source.v5",
                            binding=binding,
                            canonical_result=canonical_result,
                            canonical_awards=canonical_awards,
                            canonical_prize_awards=canonical_prize_awards,
                            adopted_by_command_id=command.command_id,
                            provenance_kind=(
                                "canonical_run_owned_tournament_authorities_and_prize_money"
                            ),
                        )
                    else:
                        # Historical adopted authorities before Calendar Event snapshot
                        # freezing cannot reconstruct prize configuration safely.
                        source = OwnedTournamentRankingSource(
                            schema_version="owned_tournament_ranking_source.v4",
                            binding=binding,
                            canonical_result=canonical_result,
                            canonical_awards=canonical_awards,
                            adopted_by_command_id=command.command_id,
                            provenance_kind="canonical_run_owned_tournament_authorities",
                        )
            else:
                if result is None or awards is None:
                    raise ValueError("Legacy tournament close produced no packages")
                if binding.closing_only:
                    raise ValueError(
                        "Final Season Closing Ranking requires canonical tournament source"
                    )
                prepare_tournament_ranking_sources(binding, result, awards)
                source = OwnedTournamentRankingSource(
                    schema_version="owned_tournament_ranking_source.v1",
                    binding=binding,
                    result=result,
                    awards=awards,
                    adopted_by_command_id=command.command_id,
                    provenance_kind="explicit_legacy_tournament_adoption",
                )
            store.append(source)

    @staticmethod
    def _ranking_source_boundary(
        completed_week: RankingWeek,
    ) -> tuple[RankingWeek | None, int | None]:
        """Return Official publication or final Closing-only eligibility boundary."""

        if completed_week.week < 61:
            return (
                RankingWeek(
                    season_index=completed_week.season_index,
                    week=completed_week.week + 1,
                ),
                None,
            )
        if completed_week.season_index < 49:
            return (
                RankingWeek(
                    season_index=completed_week.season_index + 1,
                    week=1,
                ),
                None,
            )
        return None, completed_week.ordinal + 1

    @staticmethod
    def _validate_existing_owned_source(existing, command, package, authoritative):
        binding = existing.binding
        if (
            binding.run_id,
            binding.branch_id,
            binding.edition_id,
            binding.event_id,
            binding.completed_week,
        ) != (
            command.run_id,
            command.branch_id,
            package.event_id,
            package.event_id,
            command.expected_week,
        ):
            raise ValueError("Conflicting owned tournament source")
        expected = {
            g.authoritative_input.match_id: g.result_fingerprint
            for g in authoritative.groups
        }
        if existing.canonical_result is not None:
            stored_results = {
                r.match_id: r.result_fingerprint
                for r in existing.canonical_result.matches
            }
        else:
            if existing.result is None:
                raise ValueError("Historical owned tournament source is incomplete")
            stored_results = {
                r.match_id: r.result_fingerprint
                for r in existing.result.match_result_refs
            }
        if stored_results != expected:
            raise ValueError("Conflicting owned tournament source")
        if existing.schema_version == "owned_tournament_ranking_source.v6":
            if existing.canonical_result is None or existing.canonical_awards is None:
                raise ValueError("Final Closing tournament source is incomplete")
            prepare_final_season_closing_ranking_results(
                existing.binding,
                existing.canonical_result,
                existing.canonical_awards,
            )
        elif existing.schema_version in {
            "owned_tournament_ranking_source.v3",
            "owned_tournament_ranking_source.v4",
            "owned_tournament_ranking_source.v5",
        }:
            if existing.canonical_result is None or existing.canonical_awards is None:
                raise ValueError("Canonical owned tournament source is incomplete")
            prepare_canonical_tournament_ranking_sources(
                existing.binding,
                existing.canonical_result,
                existing.canonical_awards,
            )
        else:
            if existing.result is None or existing.awards is None:
                raise ValueError("Historical owned tournament source is incomplete")
            prepare_tournament_ranking_sources(
                existing.binding, existing.result, existing.awards
            )

    @staticmethod
    def _stable_seed(package, suffix):
        return int(
            hashlib.sha256(
                f"{package.metadata.build_fingerprint}|{suffix}".encode()
            ).hexdigest()[:15],
            16,
        )

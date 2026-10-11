"""Canonical transaction-owning Admin WC/RWC review workflow.

Exact WC eligibility and construction/order of the RWC list remain open in the
Master. This pre-alpha boundary therefore accepts only an explicit Admin-reviewed
nomination/order, while the server owns chronology, frozen field evidence,
Direct->RWC resolution, definitive assignments and Tour-entry effects.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import select, text

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.simulation_slots import WeekSimulationSchedule
from beta_engine.domain.tournaments.definitive_wild_card_assignment import (
    DefinitiveWildCardAssignmentAuthority,
)
from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthority,
    TournamentWildCardAuthorityBuilder,
)
from beta_engine.infrastructure.db.definitive_wild_card_assignments import (
    DefinitiveWildCardAssignmentStore,
    record_definitive_wild_card_assignment,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    PlayerSportingWeekStateModel,
    ResolvedApplicationValidationSlotModel,
    RunBranchModel,
    RunContainerModel,
    RunEntryDecisionSlotAuthorityModel,
    SimulationSlotModel,
    TournamentDrawInputAuthorityModel,
    WeekSimulationScheduleModel,
)
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PlayerTourEntryTriggerStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_wild_card_authority import (
    TournamentWildCardAuthorityConflict,
    TournamentWildCardAuthorityStore,
    wild_card_decision_slot_ordinals,
)


EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_ID = (
    "explicit_admin_wild_card_selection.v1"
)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_FINGERPRINT = _fingerprint(
    {
        "policy_id": EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_ID,
        "selection_mode": "explicit_admin_review",
        "automatic_wc_eligibility": False,
        "automatic_rwc_ordering": False,
        "server_owned_global_chronology": True,
        "server_owned_direct_acceptance_release": True,
    }
)


class AuthoritativeWildCardReviewRequest(FrozenInput):
    """Explicit reviewed WC nominations without inventing open selection policy."""

    command_id: str = Field(min_length=1, max_length=128)
    original_wild_card_player_ids: tuple[str | None, ...]
    reserve_wild_card_player_ids: tuple[str, ...] = ()
    unavailable_player_ids: tuple[str, ...] = ()
    operator_label: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def validate_review(self):
        if self.command_id != self.command_id.strip():
            raise ValueError("WC review command ID must be trimmed")
        if self.operator_label != self.operator_label.strip():
            raise ValueError("WC review operator label must be trimmed")
        if self.reason != self.reason.strip():
            raise ValueError("WC review audit reason must be trimmed")

        originals = tuple(
            player_id
            for player_id in self.original_wild_card_player_ids
            if player_id is not None
        )
        for player_id in (*originals, *self.reserve_wild_card_player_ids, *self.unavailable_player_ids):
            if not player_id.strip() or player_id != player_id.strip():
                raise ValueError("WC review player IDs must be trimmed and non-blank")
        if len(originals) != len(set(originals)):
            raise ValueError("WC review cannot nominate one original player twice")
        if len(self.reserve_wild_card_player_ids) != len(
            set(self.reserve_wild_card_player_ids)
        ):
            raise ValueError("WC review RWC ordering cannot contain duplicates")
        if self.unavailable_player_ids != tuple(
            sorted(set(self.unavailable_player_ids))
        ):
            raise ValueError(
                "WC review unavailable player IDs must be unique and canonical"
            )
        return self


class AuthoritativeWildCardCommitCommand(AuthoritativeWildCardReviewRequest):
    expected_week: RankingWeek
    expected_revision_id: str = Field(min_length=1)
    expected_decision_slot_ordinal: int = Field(ge=1)
    expected_proposal_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class AuthoritativeWildCardAssignmentPreview(FrozenInput):
    schema_version: Literal["authoritative_wild_card_assignment_preview.v1"] = (
        "authoritative_wild_card_assignment_preview.v1"
    )
    run_id: str
    branch_id: str
    event_id: str
    week: RankingWeek
    decision_slot_ordinal: int = Field(ge=1)
    expected_revision_id: str
    selection_policy_id: str = EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_ID
    selection_policy_fingerprint: str = (
        EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_FINGERPRINT
    )
    entry_field_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    field_sequence: int = Field(ge=1)
    authority: TournamentWildCardAuthority
    definitive_assignments: tuple[DefinitiveWildCardAssignmentAuthority, ...]
    first_tour_entry_source_player_ids: tuple[str, ...]
    persisted: bool = False
    proposal_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class AuthoritativeWildCardCommitItem(FrozenInput):
    assignment: DefinitiveWildCardAssignmentAuthority
    first_tour_entry_trigger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    assignment_is_first_tour_entry_source: bool


class AuthoritativeWildCardAssignmentCommitResult(FrozenInput):
    schema_version: Literal["authoritative_wild_card_assignment_commit.v1"] = (
        "authoritative_wild_card_assignment_commit.v1"
    )
    run_id: str
    branch_id: str
    event_id: str
    week: RankingWeek
    decision_slot_ordinal: int
    proposal_fingerprint: str
    authority: TournamentWildCardAuthority
    assignment_results: tuple[AuthoritativeWildCardCommitItem, ...]
    adoption: Literal["committed", "exact_retry"]


class AuthoritativeWildCardAssignmentState(FrozenInput):
    schema_version: Literal["authoritative_wild_card_assignment_state.v1"] = (
        "authoritative_wild_card_assignment_state.v1"
    )
    run_id: str
    branch_id: str
    event_id: str
    authority: TournamentWildCardAuthority | None = None
    definitive_assignments: tuple[DefinitiveWildCardAssignmentAuthority, ...] = ()


class AuthoritativeWildCardAssignmentService:
    def __init__(self, factory):
        self.factory = factory

    @staticmethod
    def _require_writable_scope(session, run_id: str, branch_id: str) -> RunBranchModel:
        run = session.get(RunContainerModel, run_id)
        branch = session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Canonical WC Run/Branch scope does not exist")
        if run.read_only or branch.read_only or branch.status != "active":
            raise ValueError("Canonical WC Run/Branch scope is not writable")
        if not branch.saved_head_revision_id:
            raise ValueError("Canonical WC review requires a saved Branch head")
        return branch

    @staticmethod
    def _current_week(session, run_id: str, branch_id: str) -> RankingWeek:
        world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
        if world is not None:
            return RankingWeek(
                season_index=world.current_ordinal // 61,
                week=world.current_ordinal % 61 + 1,
            )
        ordinal = session.scalar(
            select(PlayerSportingWeekStateModel.week_ordinal)
            .where(
                PlayerSportingWeekStateModel.run_id == run_id,
                PlayerSportingWeekStateModel.branch_id == branch_id,
            )
            .order_by(PlayerSportingWeekStateModel.week_ordinal.desc())
            .limit(1)
        )
        if ordinal is None:
            raise ValueError("Canonical WC review requires authoritative current week")
        return RankingWeek(season_index=ordinal // 61, week=ordinal % 61 + 1)

    @staticmethod
    def _next_global_slot_ordinal(
        session,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
    ) -> int:
        entry_ordinals = set(
            session.scalars(
                select(RunEntryDecisionSlotAuthorityModel.decision_slot_ordinal).where(
                    RunEntryDecisionSlotAuthorityModel.run_id == run_id,
                    RunEntryDecisionSlotAuthorityModel.branch_id == branch_id,
                    RunEntryDecisionSlotAuthorityModel.week_ordinal == week.ordinal,
                )
            ).all()
        )
        completed_entries = set(
            session.scalars(
                select(ResolvedApplicationValidationSlotModel.decision_slot_ordinal).where(
                    ResolvedApplicationValidationSlotModel.run_id == run_id,
                    ResolvedApplicationValidationSlotModel.branch_id == branch_id,
                    ResolvedApplicationValidationSlotModel.week_ordinal == week.ordinal,
                )
            ).all()
        )
        match_rows = session.scalars(
            select(SimulationSlotModel).where(
                SimulationSlotModel.run_id == run_id,
                SimulationSlotModel.branch_id == branch_id,
                SimulationSlotModel.week_ordinal == week.ordinal,
            )
        ).all()
        match_ordinals = {row.slot_ordinal for row in match_rows}
        completed_matches = {
            row.slot_ordinal for row in match_rows if row.status == "complete"
        }
        wc_ordinals = wild_card_decision_slot_ordinals(
            session,
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week.ordinal,
        )
        completed = completed_entries | completed_matches | wc_ordinals

        ordinal = 1
        while ordinal in completed:
            ordinal += 1

        if ordinal in entry_ordinals:
            raise TournamentWildCardAuthorityConflict(
                "Current global Simulation Slot is an unresolved Entry decision slot"
            )
        if ordinal in match_ordinals:
            raise TournamentWildCardAuthorityConflict(
                "Current global Simulation Slot is an incomplete match slot"
            )

        schedule_row = session.get(
            WeekSimulationScheduleModel,
            (run_id, branch_id, week.ordinal),
        )
        if schedule_row is not None:
            schedule = WeekSimulationSchedule.model_validate_json(
                schedule_row.payload_json
            )
            if schedule.fingerprint != schedule_row.schedule_fingerprint:
                raise ValueError("Persisted match schedule is corrupt")
            if any(slot.ordinal == ordinal for slot in schedule.slots):
                raise TournamentWildCardAuthorityConflict(
                    "Current global Simulation Slot is reserved by the adopted match schedule"
                )
        return ordinal

    @staticmethod
    def _validate_player_identities(
        session,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
        request: AuthoritativeWildCardReviewRequest,
    ) -> None:
        lifecycle = get_lifecycle(
            session,
            run_id=run_id,
            branch_id=branch_id,
            week=week,
        )
        if lifecycle is None:
            raise ValueError("Canonical WC review requires lifecycle identity authority")
        known = {player.player_id for player in lifecycle.players}
        referenced = {
            player_id
            for player_id in (
                *request.original_wild_card_player_ids,
                *request.reserve_wild_card_player_ids,
                *request.unavailable_player_ids,
            )
            if player_id is not None
        }
        missing = sorted(referenced - known)
        if missing:
            raise ValueError(
                "WC review references players missing from lifecycle identity: "
                + ", ".join(missing)
            )

    @staticmethod
    def _assignments(
        authority: TournamentWildCardAuthority,
    ) -> tuple[DefinitiveWildCardAssignmentAuthority, ...]:
        if authority.decision_week is None or authority.decision_slot_ordinal is None:
            raise ValueError("Canonical WC Admin authority lacks exact chronology")
        assignments = []
        for slot in authority.slots:
            if slot.active_player_id is None or slot.source == "unfilled":
                continue
            assignments.append(
                DefinitiveWildCardAssignmentAuthority.from_resolution(
                    authority=authority,
                    wildcard_index=slot.wildcard_index,
                    assignment_week=authority.decision_week,
                    decision_slot_ordinal=authority.decision_slot_ordinal,
                    provenance=(
                        "canonical explicit Admin WC/RWC review; "
                        f"policy={EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_ID}"
                    ),
                )
            )
        return tuple(assignments)

    @staticmethod
    def _proposal_fingerprint(
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        expected_revision_id: str,
        authority: TournamentWildCardAuthority,
        assignments: tuple[DefinitiveWildCardAssignmentAuthority, ...],
    ) -> str:
        return _fingerprint(
            {
                "scope": [run_id, branch_id, event_id],
                "expected_revision_id": expected_revision_id,
                "selection_policy_id": EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_ID,
                "selection_policy_fingerprint": (
                    EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_FINGERPRINT
                ),
                "authority_fingerprint": authority.fingerprint,
                "assignment_fingerprints": [
                    assignment.fingerprint for assignment in assignments
                ],
            }
        )

    @staticmethod
    def _request_matches_existing(
        authority: TournamentWildCardAuthority,
        request: AuthoritativeWildCardReviewRequest,
    ) -> bool:
        return (
            authority.schema_version == "tournament_wild_card_authority.v3"
            and authority.resolved_by_command_id == request.command_id
            and authority.original_wild_card_player_ids
            == request.original_wild_card_player_ids
            and authority.reserve_wild_card_player_ids
            == request.reserve_wild_card_player_ids
            and authority.unavailable_player_ids
            == request.unavailable_player_ids
            and authority.selection_policy_id
            == EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_ID
            and authority.operator_label == request.operator_label
            and authority.audit_reason == request.reason
        )

    def _preview_in_session(
        self,
        session,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        request: AuthoritativeWildCardReviewRequest,
    ) -> AuthoritativeWildCardAssignmentPreview:
        branch = self._require_writable_scope(session, run_id, branch_id)
        week = self._current_week(session, run_id, branch_id)
        self._validate_player_identities(
            session,
            run_id=run_id,
            branch_id=branch_id,
            week=week,
            request=request,
        )

        wc_store = TournamentWildCardAuthorityStore(session)
        existing = wc_store.get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if existing is not None:
            if not self._request_matches_existing(existing, request):
                raise TournamentWildCardAuthorityConflict(
                    "Tournament event already has a different canonical WC authority"
                )
            if existing.decision_week is None or existing.decision_slot_ordinal is None:
                raise TournamentWildCardAuthorityConflict(
                    "Existing historical WC authority has no canonical global chronology"
                )
            assignments = self._assignments(existing)
            proposal_fp = self._proposal_fingerprint(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                expected_revision_id=branch.saved_head_revision_id,
                authority=existing,
                assignments=assignments,
            )
            triggers = PlayerTourEntryTriggerStore(session)
            first_sources = tuple(
                sorted(
                    assignment.player_id
                    for assignment in assignments
                    if (
                        (trigger := triggers.get(
                            run_id=run_id,
                            branch_id=branch_id,
                            player_id=assignment.player_id,
                        ))
                        is not None
                        and trigger.source_evidence_id == assignment.source_evidence_id
                    )
                )
            )
            return AuthoritativeWildCardAssignmentPreview(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                week=existing.decision_week,
                decision_slot_ordinal=existing.decision_slot_ordinal,
                expected_revision_id=branch.saved_head_revision_id,
                entry_field_fingerprint=existing.entry_field_fingerprint,
                field_sequence=existing.field_sequence,
                authority=existing,
                definitive_assignments=assignments,
                first_tour_entry_source_player_ids=first_sources,
                persisted=True,
                proposal_fingerprint=proposal_fp,
            )

        if session.get(
            TournamentDrawInputAuthorityModel,
            (run_id, branch_id, event_id),
        ) is not None:
            raise TournamentWildCardAuthorityConflict(
                "Canonical WC review is locked after Draw Input commitment"
            )

        history = TournamentEntryFieldStore(session).history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not history:
            raise ValueError("Canonical WC review requires Tournament Entry Field")
        field = history[-1]
        field_sequence = len(history)
        decision_slot_ordinal = self._next_global_slot_ordinal(
            session,
            run_id=run_id,
            branch_id=branch_id,
            week=week,
        )
        wc_store.validate_global_slot(
            run_id=run_id,
            branch_id=branch_id,
            decision_week=week,
            decision_slot_ordinal=decision_slot_ordinal,
        )

        authority = TournamentWildCardAuthorityBuilder.build(
            field=field,
            field_sequence=field_sequence,
            command_id=request.command_id,
            original_wild_card_player_ids=request.original_wild_card_player_ids,
            reserve_wild_card_player_ids=request.reserve_wild_card_player_ids,
            unavailable_player_ids=request.unavailable_player_ids,
            decision_week=week,
            decision_slot_ordinal=decision_slot_ordinal,
            selection_policy_id=EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_ID,
            operator_label=request.operator_label,
            audit_reason=request.reason,
        )
        assignments = self._assignments(authority)

        trigger_store = PlayerTourEntryTriggerStore(session)
        first_sources: list[str] = []
        for assignment in assignments:
            existing_trigger = trigger_store.get(
                run_id=run_id,
                branch_id=branch_id,
                player_id=assignment.player_id,
            )
            proposed = assignment.to_tour_entry_trigger()
            if existing_trigger is None:
                first_sources.append(assignment.player_id)
                continue
            if existing_trigger == proposed:
                first_sources.append(assignment.player_id)
                continue
            if existing_trigger.decision_position > proposed.decision_position:
                raise TournamentWildCardAuthorityConflict(
                    "Definitive WC would predate persisted first Tour-entry trigger"
                )
            if existing_trigger.decision_position == proposed.decision_position:
                raise TournamentWildCardAuthorityConflict(
                    "Distinct simultaneous first-entry authorities require slot arbitration"
                )

        proposal_fp = self._proposal_fingerprint(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            expected_revision_id=branch.saved_head_revision_id,
            authority=authority,
            assignments=assignments,
        )
        return AuthoritativeWildCardAssignmentPreview(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            week=week,
            decision_slot_ordinal=decision_slot_ordinal,
            expected_revision_id=branch.saved_head_revision_id,
            entry_field_fingerprint=field.fingerprint,
            field_sequence=field_sequence,
            authority=authority,
            definitive_assignments=assignments,
            first_tour_entry_source_player_ids=tuple(sorted(first_sources)),
            persisted=False,
            proposal_fingerprint=proposal_fp,
        )

    def inspect(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
    ) -> AuthoritativeWildCardAssignmentState:
        with self.factory() as session:
            run = session.get(RunContainerModel, run_id)
            branch = session.get(RunBranchModel, branch_id)
            if run is None or branch is None or branch.run_id != run_id:
                raise ValueError("Canonical WC Run/Branch scope does not exist")
            authority = TournamentWildCardAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            assignments = tuple(
                item
                for item in DefinitiveWildCardAssignmentStore(session).list(
                    run_id=run_id,
                    branch_id=branch_id,
                )
                if item.event_id == event_id
            )
            return AuthoritativeWildCardAssignmentState(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                authority=authority,
                definitive_assignments=assignments,
            )

    def preview(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        request: AuthoritativeWildCardReviewRequest,
    ) -> AuthoritativeWildCardAssignmentPreview:
        with self.factory() as session:
            return self._preview_in_session(
                session,
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                request=request,
            )

    def commit(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command: AuthoritativeWildCardCommitCommand,
    ) -> AuthoritativeWildCardAssignmentCommitResult:
        request = AuthoritativeWildCardReviewRequest(
            command_id=command.command_id,
            original_wild_card_player_ids=command.original_wild_card_player_ids,
            reserve_wild_card_player_ids=command.reserve_wild_card_player_ids,
            unavailable_player_ids=command.unavailable_player_ids,
            operator_label=command.operator_label,
            reason=command.reason,
        )
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            branch = self._require_writable_scope(session, run_id, branch_id)
            store = TournamentWildCardAuthorityStore(session)
            existing = store.get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )

            if existing is not None:
                if not self._request_matches_existing(existing, request):
                    raise TournamentWildCardAuthorityConflict(
                        "Tournament event already has a different canonical WC authority"
                    )
                if (
                    existing.decision_week != command.expected_week
                    or existing.decision_slot_ordinal
                    != command.expected_decision_slot_ordinal
                ):
                    raise TournamentWildCardAuthorityConflict(
                        "Exact WC retry chronology differs from committed authority"
                    )
                assignments = self._assignments(existing)
                expected_fp = self._proposal_fingerprint(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                    expected_revision_id=command.expected_revision_id,
                    authority=existing,
                    assignments=assignments,
                )
                if expected_fp != command.expected_proposal_fingerprint:
                    raise TournamentWildCardAuthorityConflict(
                        "Exact WC retry proposal fingerprint differs from committed authority"
                    )
                authority = store.resolve(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                    command_id=request.command_id,
                    original_wild_card_player_ids=request.original_wild_card_player_ids,
                    reserve_wild_card_player_ids=request.reserve_wild_card_player_ids,
                    unavailable_player_ids=request.unavailable_player_ids,
                    decision_week=existing.decision_week,
                    decision_slot_ordinal=existing.decision_slot_ordinal,
                    selection_policy_id=EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_ID,
                    operator_label=request.operator_label,
                    audit_reason=request.reason,
                )
                adoption = "exact_retry"
            else:
                preview = self._preview_in_session(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                    request=request,
                )
                if branch.saved_head_revision_id != command.expected_revision_id:
                    raise TournamentWildCardAuthorityConflict(
                        "Canonical WC Branch head is stale"
                    )
                if (
                    preview.week != command.expected_week
                    or preview.decision_slot_ordinal
                    != command.expected_decision_slot_ordinal
                ):
                    raise TournamentWildCardAuthorityConflict(
                        "Canonical WC global position is stale"
                    )
                if preview.proposal_fingerprint != command.expected_proposal_fingerprint:
                    raise TournamentWildCardAuthorityConflict(
                        "Canonical WC reviewed proposal is stale"
                    )
                authority = store.resolve(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                    command_id=request.command_id,
                    original_wild_card_player_ids=request.original_wild_card_player_ids,
                    reserve_wild_card_player_ids=request.reserve_wild_card_player_ids,
                    unavailable_player_ids=request.unavailable_player_ids,
                    decision_week=preview.week,
                    decision_slot_ordinal=preview.decision_slot_ordinal,
                    selection_policy_id=EXPLICIT_ADMIN_WILD_CARD_SELECTION_POLICY_ID,
                    operator_label=request.operator_label,
                    audit_reason=request.reason,
                )
                assignments = self._assignments(authority)
                adoption = "committed"

            items: list[AuthoritativeWildCardCommitItem] = []
            for assignment in assignments:
                committed = record_definitive_wild_card_assignment(
                    session,
                    assignment,
                )
                items.append(
                    AuthoritativeWildCardCommitItem(
                        assignment=committed.assignment,
                        first_tour_entry_trigger_fingerprint=(
                            committed.first_tour_entry_trigger.fingerprint
                        ),
                        assignment_is_first_tour_entry_source=(
                            committed.first_tour_entry_trigger.source_evidence_id
                            == committed.assignment.source_evidence_id
                        ),
                    )
                )

            proposal_fp = self._proposal_fingerprint(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                expected_revision_id=command.expected_revision_id,
                authority=authority,
                assignments=assignments,
            )
            return AuthoritativeWildCardAssignmentCommitResult(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                week=authority.decision_week,
                decision_slot_ordinal=authority.decision_slot_ordinal,
                proposal_fingerprint=proposal_fp,
                authority=authority,
                assignment_results=tuple(items),
                adoption=adoption,
            )

"""Persistence for canonical Run/Branch Wild Card / Reserve Wild Card authority."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import WeekSimulationSchedule
from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthority,
    TournamentWildCardAuthorityBuilder,
)
from beta_engine.infrastructure.db.models import (
    ResolvedApplicationValidationSlotModel,
    RunBranchModel,
    RunContainerModel,
    RunEntryDecisionSlotAuthorityModel,
    SimulationSlotModel,
    TournamentDrawInputAuthorityModel,
    TournamentWildCardAuthorityModel,
    WeekSimulationScheduleModel,
)
from beta_engine.infrastructure.db.tournament_entry_field import TournamentEntryFieldStore


class TournamentWildCardAuthorityConflict(ValueError):
    """A WC/RWC command or event authority conflicts with persisted state."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def wild_card_decision_slot_ordinals(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    week_ordinal: int,
) -> set[int]:
    """Return completed canonical WC-decision ordinals for one FAX week."""

    rows = session.scalars(
        select(TournamentWildCardAuthorityModel).where(
            TournamentWildCardAuthorityModel.run_id == run_id,
            TournamentWildCardAuthorityModel.branch_id == branch_id,
        )
    ).all()
    ordinals: set[int] = set()
    for row in rows:
        authority = TournamentWildCardAuthority.model_validate_json(row.payload_json)
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.resolved_by_command_id,
            authority.entry_field_fingerprint,
            authority.field_sequence,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.entry_field_fingerprint,
            row.field_sequence,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Tournament WC authority chronology is corrupt")
        if authority.schema_version != "tournament_wild_card_authority.v2":
            continue
        if authority.decision_week is None or authority.decision_slot_ordinal is None:
            raise ValueError("Canonical WC authority v2 is missing global-slot chronology")
        if authority.decision_week.ordinal != week_ordinal:
            continue
        if authority.decision_slot_ordinal in ordinals:
            raise ValueError("Multiple WC authorities claim the same global Simulation Slot")
        ordinals.add(authority.decision_slot_ordinal)
    return ordinals


class TournamentWildCardAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Tournament WC Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Tournament WC scope is not writable")

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentWildCardAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentWildCardAuthorityModel,
            (run_id, branch_id, event_id),
        )
        return None if row is None else self._load(row)

    def _load(
        self, row: TournamentWildCardAuthorityModel
    ) -> TournamentWildCardAuthority:
        history = TournamentEntryFieldStore(self.session).history(
            run_id=row.run_id,
            branch_id=row.branch_id,
            event_id=row.event_id,
        )
        if not history:
            raise ValueError("Tournament WC authority references missing Entry Field")
        if len(history) != row.field_sequence:
            raise ValueError("Tournament WC authority no longer references terminal Entry Field")
        field = history[-1]
        authority = TournamentWildCardAuthority.model_validate_json(row.payload_json)
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.resolved_by_command_id,
            authority.entry_field_fingerprint,
            authority.field_sequence,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.entry_field_fingerprint,
            row.field_sequence,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Tournament WC authority is corrupt")
        if field.fingerprint != row.entry_field_fingerprint:
            raise ValueError("Tournament WC authority Entry Field fingerprint is stale")
        rebuilt = TournamentWildCardAuthorityBuilder.build(
            field=field,
            field_sequence=row.field_sequence,
            command_id=row.command_id,
            original_wild_card_player_ids=authority.original_wild_card_player_ids,
            reserve_wild_card_player_ids=authority.reserve_wild_card_player_ids,
            unavailable_player_ids=authority.unavailable_player_ids,
            decision_week=authority.decision_week,
            decision_slot_ordinal=authority.decision_slot_ordinal,
        )
        if rebuilt != authority:
            raise ValueError("Tournament WC authority does not replay from frozen field")
        return authority

    def _validate_global_slot(
        self,
        *,
        run_id: str,
        branch_id: str,
        decision_week: RankingWeek,
        decision_slot_ordinal: int,
    ) -> None:
        week_ordinal = decision_week.ordinal
        existing_wc = wild_card_decision_slot_ordinals(
            self.session,
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week_ordinal,
        )
        if decision_slot_ordinal in existing_wc:
            raise TournamentWildCardAuthorityConflict(
                "Global Simulation Slot ordinal already belongs to a WC-decision slot"
            )
        if self.session.get(
            RunEntryDecisionSlotAuthorityModel,
            (run_id, branch_id, week_ordinal, decision_slot_ordinal),
        ) is not None:
            raise TournamentWildCardAuthorityConflict(
                "Global Simulation Slot ordinal already belongs to an entry-decision slot"
            )
        match_slot = self.session.scalar(
            select(SimulationSlotModel).where(
                SimulationSlotModel.run_id == run_id,
                SimulationSlotModel.branch_id == branch_id,
                SimulationSlotModel.week_ordinal == week_ordinal,
                SimulationSlotModel.slot_ordinal == decision_slot_ordinal,
            )
        )
        if match_slot is not None:
            raise TournamentWildCardAuthorityConflict(
                "Global Simulation Slot ordinal already belongs to a match slot"
            )

        schedule_row = self.session.get(
            WeekSimulationScheduleModel,
            (run_id, branch_id, week_ordinal),
        )
        if schedule_row is not None:
            schedule = WeekSimulationSchedule.model_validate_json(schedule_row.payload_json)
            if schedule.fingerprint != schedule_row.schedule_fingerprint:
                raise ValueError("Persisted match schedule is corrupt")
            if any(slot.ordinal == decision_slot_ordinal for slot in schedule.slots):
                raise TournamentWildCardAuthorityConflict(
                    "Global Simulation Slot ordinal is reserved by the adopted match schedule"
                )

        required_prior = set(range(1, decision_slot_ordinal))
        if not required_prior:
            return
        completed_entries = set(
            self.session.scalars(
                select(ResolvedApplicationValidationSlotModel.decision_slot_ordinal).where(
                    ResolvedApplicationValidationSlotModel.run_id == run_id,
                    ResolvedApplicationValidationSlotModel.branch_id == branch_id,
                    ResolvedApplicationValidationSlotModel.week_ordinal == week_ordinal,
                    ResolvedApplicationValidationSlotModel.decision_slot_ordinal
                    < decision_slot_ordinal,
                )
            ).all()
        )
        completed_matches = set(
            self.session.scalars(
                select(SimulationSlotModel.slot_ordinal).where(
                    SimulationSlotModel.run_id == run_id,
                    SimulationSlotModel.branch_id == branch_id,
                    SimulationSlotModel.week_ordinal == week_ordinal,
                    SimulationSlotModel.slot_ordinal < decision_slot_ordinal,
                    SimulationSlotModel.status == "complete",
                )
            ).all()
        )
        completed_prior = completed_entries | completed_matches | {
            ordinal for ordinal in existing_wc if ordinal < decision_slot_ordinal
        }
        if completed_prior != required_prior:
            missing = sorted(required_prior - completed_prior)
            raise TournamentWildCardAuthorityConflict(
                "WC decision slot cannot skip or overtake incomplete global "
                f"Simulation Slots: missing completed ordinals {missing}"
            )

    def resolve(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        original_wild_card_player_ids: tuple[str | None, ...],
        reserve_wild_card_player_ids: tuple[str, ...] = (),
        unavailable_player_ids: tuple[str, ...] = (),
        decision_week: RankingWeek | None = None,
        decision_slot_ordinal: int | None = None,
    ) -> TournamentWildCardAuthority:
        if (decision_week is None) != (decision_slot_ordinal is None):
            raise ValueError("WC decision chronology requires week and slot ordinal together")
        self._scope(run_id, branch_id, writing=True)
        if self.session.get(
            TournamentDrawInputAuthorityModel,
            (run_id, branch_id, event_id),
        ) is not None:
            raise TournamentWildCardAuthorityConflict(
                "Tournament WC authority is locked after Draw Input commitment"
            )

        history = TournamentEntryFieldStore(self.session).history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not history:
            raise ValueError("Tournament WC authority requires Tournament Entry Field")
        field = history[-1]
        field_sequence = len(history)

        request = {
            "entry_field_fingerprint": field.fingerprint,
            "field_sequence": field_sequence,
            "original_wild_card_player_ids": list(original_wild_card_player_ids),
            "reserve_wild_card_player_ids": list(reserve_wild_card_player_ids),
            "unavailable_player_ids": sorted(set(unavailable_player_ids)),
        }
        if decision_week is not None:
            request["decision_week"] = decision_week.model_dump(mode="json")
            request["decision_slot_ordinal"] = decision_slot_ordinal
        request_fp = _fingerprint(request)

        retry = self.session.scalar(
            select(TournamentWildCardAuthorityModel).where(
                TournamentWildCardAuthorityModel.run_id == run_id,
                TournamentWildCardAuthorityModel.branch_id == branch_id,
                TournamentWildCardAuthorityModel.command_id == command_id,
            )
        )
        if retry is not None:
            if retry.event_id != event_id or retry.request_fingerprint != request_fp:
                raise TournamentWildCardAuthorityConflict(
                    "Tournament WC command ID already has a different request"
                )
            return self._load(retry)

        if self.session.get(
            TournamentWildCardAuthorityModel,
            (run_id, branch_id, event_id),
        ) is not None:
            raise TournamentWildCardAuthorityConflict(
                "Tournament event already has WC authority"
            )

        if decision_week is not None and decision_slot_ordinal is not None:
            self._validate_global_slot(
                run_id=run_id,
                branch_id=branch_id,
                decision_week=decision_week,
                decision_slot_ordinal=decision_slot_ordinal,
            )

        authority = TournamentWildCardAuthorityBuilder.build(
            field=field,
            field_sequence=field_sequence,
            command_id=command_id,
            original_wild_card_player_ids=original_wild_card_player_ids,
            reserve_wild_card_player_ids=reserve_wild_card_player_ids,
            unavailable_player_ids=unavailable_player_ids,
            decision_week=decision_week,
            decision_slot_ordinal=decision_slot_ordinal,
        )
        self.session.add(
            TournamentWildCardAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=authority.fingerprint,
                entry_field_fingerprint=field.fingerprint,
                field_sequence=field_sequence,
                payload_json=authority.model_dump_json(),
            )
        )
        self.session.flush()
        return authority

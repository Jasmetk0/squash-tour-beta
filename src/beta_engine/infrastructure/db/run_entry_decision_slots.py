"""Persistence for Run/Branch-owned entry-decision Simulation Slots."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from beta_engine.domain.simulation_slots import WeekSimulationSchedule
from beta_engine.domain.tournaments.run_entry_decision_slot import (
    RunEntryDecisionSlotAuthority,
)
from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthority,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    ResolvedApplicationValidationSlotModel,
    RunEntryDecisionSlotAuthorityModel,
    SimulationSlotModel,
    WeekSimulationScheduleModel,
)


RUN_ENTRY_DECISION_SLOT_COMPONENT_KEY = "run_entry_decision_slots"
SIMULATION_SLOT_COMPONENT_KEY = "simulation_slot_match_state"


class RunEntryDecisionSlotConflict(ValueError):
    """Entry-decision slot conflicts with existing global-slot authority."""


def _canonical(
    slots: tuple[RunEntryDecisionSlotAuthority, ...]
    | list[RunEntryDecisionSlotAuthority],
) -> tuple[RunEntryDecisionSlotAuthority, ...]:
    return tuple(
        sorted(
            slots,
            key=lambda item: (item.week.ordinal, item.decision_slot_ordinal),
        )
    )


def _component_fingerprint(
    slots: tuple[RunEntryDecisionSlotAuthority, ...],
) -> str:
    body = [item.model_dump(mode="json") for item in slots]
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _load(
    row: RunEntryDecisionSlotAuthorityModel,
) -> RunEntryDecisionSlotAuthority:
    authority = RunEntryDecisionSlotAuthority.model_validate_json(row.payload_json)
    if (
        authority.run_id,
        authority.branch_id,
        authority.week.ordinal,
        authority.decision_slot_ordinal,
        authority.fingerprint,
    ) != (
        row.run_id,
        row.branch_id,
        row.week_ordinal,
        row.decision_slot_ordinal,
        row.fingerprint,
    ):
        raise ValueError("Stored Run entry decision slot is corrupt")
    return authority


def _insert(session: Session, authority: RunEntryDecisionSlotAuthority) -> None:
    session.add(
        RunEntryDecisionSlotAuthorityModel(
            run_id=authority.run_id,
            branch_id=authority.branch_id,
            week_ordinal=authority.week.ordinal,
            decision_slot_ordinal=authority.decision_slot_ordinal,
            fingerprint=authority.fingerprint,
            payload_json=authority.model_dump_json(),
        )
    )
    session.flush()


class RunEntryDecisionSlotStore:
    """Append-only entry-decision authority over the product-level global slot ordinal."""

    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Run entry decision slot scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status != "active"):
            raise ValueError("Run entry decision slot scope is not writable")

    def get(
        self,
        *,
        run_id: str,
        branch_id: str,
        week_ordinal: int,
        decision_slot_ordinal: int,
    ) -> RunEntryDecisionSlotAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            RunEntryDecisionSlotAuthorityModel,
            (run_id, branch_id, week_ordinal, decision_slot_ordinal),
        )
        return None if row is None else _load(row)

    def list(
        self,
        *,
        run_id: str,
        branch_id: str,
    ) -> tuple[RunEntryDecisionSlotAuthority, ...]:
        self._scope(run_id, branch_id)
        rows = self.session.scalars(
            select(RunEntryDecisionSlotAuthorityModel)
            .where(
                RunEntryDecisionSlotAuthorityModel.run_id == run_id,
                RunEntryDecisionSlotAuthorityModel.branch_id == branch_id,
            )
            .order_by(
                RunEntryDecisionSlotAuthorityModel.week_ordinal,
                RunEntryDecisionSlotAuthorityModel.decision_slot_ordinal,
            )
        ).all()
        return tuple(_load(row) for row in rows)

    def validate_candidate(
        self,
        authority: RunEntryDecisionSlotAuthority,
    ) -> RunEntryDecisionSlotAuthority | None:
        """Validate exact retry/collision/chronology without mutating persistence."""

        self._scope(authority.run_id, authority.branch_id, writing=True)
        existing = self.get(
            run_id=authority.run_id,
            branch_id=authority.branch_id,
            week_ordinal=authority.week.ordinal,
            decision_slot_ordinal=authority.decision_slot_ordinal,
        )
        if existing is not None:
            if existing == authority:
                return existing
            raise RunEntryDecisionSlotConflict(
                "Global entry-decision slot already has different authority"
            )

        match_slot = self.session.scalar(
            select(SimulationSlotModel).where(
                SimulationSlotModel.run_id == authority.run_id,
                SimulationSlotModel.branch_id == authority.branch_id,
                SimulationSlotModel.week_ordinal == authority.week.ordinal,
                SimulationSlotModel.slot_ordinal == authority.decision_slot_ordinal,
            )
        )
        if match_slot is not None:
            raise RunEntryDecisionSlotConflict(
                "Global Simulation Slot ordinal already belongs to a match slot"
            )

        from beta_engine.infrastructure.db.tournament_wild_card_authority import (
            wild_card_decision_slot_ordinals,
        )
        wc_ordinals = wild_card_decision_slot_ordinals(
            self.session,
            run_id=authority.run_id,
            branch_id=authority.branch_id,
            week_ordinal=authority.week.ordinal,
        )
        if authority.decision_slot_ordinal in wc_ordinals:
            raise RunEntryDecisionSlotConflict(
                "Global Simulation Slot ordinal already belongs to a WC-decision slot"
            )

        schedule_row = self.session.get(
            WeekSimulationScheduleModel,
            (authority.run_id, authority.branch_id, authority.week.ordinal),
        )
        if schedule_row is not None:
            schedule = WeekSimulationSchedule.model_validate_json(
                schedule_row.payload_json
            )
            if schedule.fingerprint != schedule_row.schedule_fingerprint:
                raise ValueError("Persisted match schedule is corrupt")
            if any(
                slot.ordinal == authority.decision_slot_ordinal
                for slot in schedule.slots
            ):
                raise RunEntryDecisionSlotConflict(
                    "Global Simulation Slot ordinal is reserved by the adopted match schedule"
                )

        required_prior = set(range(1, authority.decision_slot_ordinal))
        if required_prior:
            completed_entry_ordinals = set(
                self.session.scalars(
                    select(
                        ResolvedApplicationValidationSlotModel.decision_slot_ordinal
                    ).where(
                        ResolvedApplicationValidationSlotModel.run_id
                        == authority.run_id,
                        ResolvedApplicationValidationSlotModel.branch_id
                        == authority.branch_id,
                        ResolvedApplicationValidationSlotModel.week_ordinal
                        == authority.week.ordinal,
                        ResolvedApplicationValidationSlotModel.decision_slot_ordinal
                        < authority.decision_slot_ordinal,
                    )
                ).all()
            )
            completed_match_ordinals = set(
                self.session.scalars(
                    select(SimulationSlotModel.slot_ordinal).where(
                        SimulationSlotModel.run_id == authority.run_id,
                        SimulationSlotModel.branch_id == authority.branch_id,
                        SimulationSlotModel.week_ordinal == authority.week.ordinal,
                        SimulationSlotModel.slot_ordinal
                        < authority.decision_slot_ordinal,
                        SimulationSlotModel.status == "complete",
                    )
                ).all()
            )
            completed_wc_ordinals = {
                ordinal
                for ordinal in wc_ordinals
                if ordinal < authority.decision_slot_ordinal
            }
            completed_prior = (
                completed_entry_ordinals
                | completed_match_ordinals
                | completed_wc_ordinals
            )
            if completed_prior != required_prior:
                missing = sorted(required_prior - completed_prior)
                raise RunEntryDecisionSlotConflict(
                    "Entry decision slot cannot skip or overtake incomplete global "
                    f"Simulation Slots: missing completed ordinals {missing}"
                )

        return None

    def append(
        self,
        authority: RunEntryDecisionSlotAuthority,
    ) -> RunEntryDecisionSlotAuthority:
        existing = self.validate_candidate(authority)
        if existing is not None:
            return existing
        _insert(self.session, authority)
        return authority


def capture_saved_run_entry_decision_slots(
    session: Session,
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> None:
    slots = RunEntryDecisionSlotStore(session).list(
        run_id=run_id,
        branch_id=branch_id,
    )
    payload["content"][RUN_ENTRY_DECISION_SLOT_COMPONENT_KEY] = {
        "fingerprint": _component_fingerprint(slots),
        "slots": [item.model_dump(mode="json") for item in slots],
    }


def load_saved_run_entry_decision_slots(
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> tuple[RunEntryDecisionSlotAuthority, ...] | None:
    component = payload.get("content", {}).get(RUN_ENTRY_DECISION_SLOT_COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "slots"}:
        raise ValueError("Invalid Saved Revision Run entry-slot component")
    raw = component["slots"]
    if not isinstance(raw, list):
        raise ValueError("Saved Run entry-decision slots must be a list")
    slots = tuple(
        RunEntryDecisionSlotAuthority.model_validate_json(json.dumps(item))
        for item in raw
    )
    if slots != _canonical(slots):
        raise ValueError("Saved Run entry-decision slots are not ordered")
    keys = [(item.week.ordinal, item.decision_slot_ordinal) for item in slots]
    if len(set(keys)) != len(keys):
        raise ValueError("Saved Run entry-decision slots contain duplicate positions")
    if any((item.run_id, item.branch_id) != (run_id, branch_id) for item in slots):
        raise ValueError("Saved Run entry-decision slot scope mismatch")
    if _component_fingerprint(slots) != component["fingerprint"]:
        raise ValueError("Saved Run entry-decision slot fingerprint mismatch")
    return slots


def _saved_wild_card_decision_positions(
    simulation: dict | None,
    *,
    run_id: str,
    branch_id: str,
) -> set[tuple[int, int]]:
    raw = [] if simulation is None else simulation.get("wild_card_authorities", [])
    if not isinstance(raw, list):
        raise ValueError("Saved Simulation Slot component has invalid WC authority rows")
    positions: set[tuple[int, int]] = set()
    for row in raw:
        if not isinstance(row, dict):
            raise ValueError("Saved Tournament WC authority row is invalid")
        payload_json = row.get("payload_json")
        if not isinstance(payload_json, str):
            raise ValueError("Saved Tournament WC authority payload is invalid")
        authority = TournamentWildCardAuthority.model_validate_json(payload_json)
        if (
            row.get("run_id"),
            row.get("branch_id"),
            row.get("event_id"),
            row.get("authority_fingerprint"),
        ) != (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.fingerprint,
        ):
            raise ValueError("Saved Tournament WC authority chronology is corrupt")
        if (authority.run_id, authority.branch_id) != (run_id, branch_id):
            raise ValueError("Saved Tournament WC authority has mismatched Run/Branch scope")
        if authority.schema_version != "tournament_wild_card_authority.v2":
            continue
        if authority.decision_week is None or authority.decision_slot_ordinal is None:
            raise ValueError("Saved canonical WC authority is missing global-slot chronology")
        position = (authority.decision_week.ordinal, authority.decision_slot_ordinal)
        if position in positions:
            raise ValueError("Saved WC decisions contain duplicate global positions")
        positions.add(position)
    return positions


def validate_saved_entry_match_slot_collisions(
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> None:
    entry_slots = load_saved_run_entry_decision_slots(
        payload,
        run_id=run_id,
        branch_id=branch_id,
    ) or ()
    simulation = payload.get("content", {}).get(SIMULATION_SLOT_COMPONENT_KEY)
    raw_match_slots = [] if simulation is None else simulation.get("slots", [])
    wc_positions = _saved_wild_card_decision_positions(
        simulation,
        run_id=run_id,
        branch_id=branch_id,
    )
    if not isinstance(raw_match_slots, list):
        raise ValueError("Saved Simulation Slot component has invalid slot rows")
    match_positions: set[tuple[int, int]] = set()
    for row in raw_match_slots:
        if not isinstance(row, dict):
            raise ValueError("Saved Simulation Slot row is invalid")
        if (row.get("run_id"), row.get("branch_id")) != (run_id, branch_id):
            raise ValueError("Saved Simulation Slot row has mismatched Run/Branch scope")
        try:
            position = (int(row["week_ordinal"]), int(row["slot_ordinal"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Saved Simulation Slot row has invalid global position") from exc
        match_positions.add(position)
    entry_positions = {
        (item.week.ordinal, item.decision_slot_ordinal) for item in entry_slots
    }
    overlap = match_positions & entry_positions
    if overlap:
        week_ordinal, slot_ordinal = sorted(overlap)[0]
        raise ValueError(
            "Saved entry and match slots claim the same global position "
            f"({week_ordinal}, {slot_ordinal})"
        )
    wc_overlap = wc_positions & (match_positions | entry_positions)
    if wc_overlap:
        week_ordinal, slot_ordinal = sorted(wc_overlap)[0]
        raise ValueError(
            "Saved WC decision and another slot claim the same global position "
            f"({week_ordinal}, {slot_ordinal})"
        )

    match_weeks = {week for week, _ in match_positions}
    for week_ordinal in sorted(match_weeks):
        match_ordinals = {
            ordinal for week, ordinal in match_positions if week == week_ordinal
        }
        entry_ordinals = {
            ordinal for week, ordinal in entry_positions if week == week_ordinal
        }
        max_match = max(match_ordinals)
        wc_ordinals = {
            ordinal for week, ordinal in wc_positions if week == week_ordinal
        }
        missing = (
            set(range(1, max_match + 1))
            - match_ordinals
            - entry_ordinals
            - wc_ordinals
        )
        if missing:
            raise ValueError(
                "Saved match chronology contains a global-slot gap not owned "
                "by an entry-decision slot or WC-decision slot"
            )

    all_positions = match_positions | entry_positions | wc_positions
    all_weeks = {week for week, _ in all_positions}
    for week_ordinal in sorted(all_weeks):
        global_ordinals = {
            ordinal
            for week, ordinal in all_positions
            if week == week_ordinal
        }
        if global_ordinals != set(range(1, max(global_ordinals) + 1)):
            raise ValueError(
                "Saved global Simulation Slot chronology is not contiguous"
            )


def restore_saved_run_entry_decision_slots(
    session: Session,
    *,
    current_payload: dict,
    target_payload: dict,
    run_id: str,
    branch_id: str,
) -> None:
    expected = load_saved_run_entry_decision_slots(
        current_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    target = load_saved_run_entry_decision_slots(
        target_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    live = RunEntryDecisionSlotStore(session).list(
        run_id=run_id,
        branch_id=branch_id,
    )
    if tuple(item.fingerprint for item in live) != tuple(
        item.fingerprint for item in (expected or ())
    ):
        raise ValueError("Live Run entry-decision slots differ from saved head")

    session.execute(
        delete(RunEntryDecisionSlotAuthorityModel).where(
            RunEntryDecisionSlotAuthorityModel.run_id == run_id,
            RunEntryDecisionSlotAuthorityModel.branch_id == branch_id,
        )
    )
    for authority in target or ():
        _insert(session, authority)

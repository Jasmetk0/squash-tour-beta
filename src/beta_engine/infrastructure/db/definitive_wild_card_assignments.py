"""Persistence and Saved Revision support for definitive WC assignments."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.domain.tournaments.definitive_wild_card_assignment import (
    DefinitiveWildCardAssignmentAuthority,
)
from beta_engine.infrastructure.db.models import (
    DefinitiveWildCardAssignmentAuthorityModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PlayerTourEntryTriggerStore,
)


DEFINITIVE_WILD_CARD_ASSIGNMENT_COMPONENT_KEY = (
    "definitive_wild_card_assignments"
)


class DefinitiveWildCardAssignmentConflict(ValueError):
    """Persisted definitive WC truth conflicts with existing authority."""


@dataclass(frozen=True)
class DefinitiveWildCardAssignmentCommit:
    """Stable result of persisting one definitive WC and first-entry truth."""

    assignment: DefinitiveWildCardAssignmentAuthority
    first_tour_entry_trigger: PlayerTourEntryTrigger


def _component_fingerprint(
    assignments: tuple[DefinitiveWildCardAssignmentAuthority, ...],
) -> str:
    body = [item.model_dump(mode="json") for item in assignments]
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _canonical(
    assignments: tuple[DefinitiveWildCardAssignmentAuthority, ...]
    | list[DefinitiveWildCardAssignmentAuthority],
) -> tuple[DefinitiveWildCardAssignmentAuthority, ...]:
    return tuple(
        sorted(
            assignments,
            key=lambda item: (
                item.assignment_week.ordinal,
                item.decision_slot_ordinal,
                item.source_evidence_id,
            ),
        )
    )


def _load(
    row: DefinitiveWildCardAssignmentAuthorityModel,
) -> DefinitiveWildCardAssignmentAuthority:
    assignment = DefinitiveWildCardAssignmentAuthority.model_validate_json(
        row.payload_json
    )
    if (
        assignment.run_id,
        assignment.branch_id,
        assignment.source_evidence_id,
        assignment.event_id,
        assignment.player_id,
        assignment.wildcard_index,
        assignment.assignment_week.ordinal,
        assignment.decision_slot_ordinal,
        assignment.fingerprint,
    ) != (
        row.run_id,
        row.branch_id,
        row.assignment_id,
        row.event_id,
        row.player_id,
        row.wildcard_index,
        row.assignment_week_ordinal,
        row.decision_slot_ordinal,
        row.fingerprint,
    ):
        raise ValueError("Stored definitive Wild Card assignment is corrupt")
    return assignment


def _insert(
    session: Session,
    assignment: DefinitiveWildCardAssignmentAuthority,
) -> None:
    session.add(
        DefinitiveWildCardAssignmentAuthorityModel(
            run_id=assignment.run_id,
            branch_id=assignment.branch_id,
            assignment_id=assignment.source_evidence_id,
            event_id=assignment.event_id,
            player_id=assignment.player_id,
            wildcard_index=assignment.wildcard_index,
            assignment_week_ordinal=assignment.assignment_week.ordinal,
            decision_slot_ordinal=assignment.decision_slot_ordinal,
            fingerprint=assignment.fingerprint,
            payload_json=assignment.model_dump_json(),
        )
    )
    session.flush()


class DefinitiveWildCardAssignmentStore:
    """Append-only Branch-owned authority for definitive WC/RWC assignments."""

    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Definitive WC Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status != "active"):
            raise ValueError("Definitive WC Run/Branch scope is not writable")

    def get(
        self,
        *,
        run_id: str,
        branch_id: str,
        assignment_id: str,
    ) -> DefinitiveWildCardAssignmentAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            DefinitiveWildCardAssignmentAuthorityModel,
            (run_id, branch_id, assignment_id),
        )
        return None if row is None else _load(row)

    def list(
        self,
        *,
        run_id: str,
        branch_id: str,
    ) -> tuple[DefinitiveWildCardAssignmentAuthority, ...]:
        self._scope(run_id, branch_id)
        rows = self.session.scalars(
            select(DefinitiveWildCardAssignmentAuthorityModel)
            .where(
                DefinitiveWildCardAssignmentAuthorityModel.run_id == run_id,
                DefinitiveWildCardAssignmentAuthorityModel.branch_id == branch_id,
            )
            .order_by(
                DefinitiveWildCardAssignmentAuthorityModel.assignment_week_ordinal,
                DefinitiveWildCardAssignmentAuthorityModel.decision_slot_ordinal,
                DefinitiveWildCardAssignmentAuthorityModel.assignment_id,
            )
        ).all()
        return tuple(_load(row) for row in rows)

    def append(
        self,
        assignment: DefinitiveWildCardAssignmentAuthority,
    ) -> DefinitiveWildCardAssignmentAuthority:
        self._scope(assignment.run_id, assignment.branch_id, writing=True)
        existing = self.session.get(
            DefinitiveWildCardAssignmentAuthorityModel,
            (assignment.run_id, assignment.branch_id, assignment.source_evidence_id),
        )
        if existing is not None:
            loaded = _load(existing)
            if loaded == assignment:
                return loaded
            raise DefinitiveWildCardAssignmentConflict(
                "WC assignment ID already has different definitive authority"
            )
        _insert(self.session, assignment)
        return assignment


def record_definitive_wild_card_assignment(
    session: Session,
    assignment: DefinitiveWildCardAssignmentAuthority,
) -> DefinitiveWildCardAssignmentCommit:
    """Persist definitive WC truth and establish first Tour entry atomically."""

    assignment_store = DefinitiveWildCardAssignmentStore(session)
    existing_assignment = assignment_store.get(
        run_id=assignment.run_id,
        branch_id=assignment.branch_id,
        assignment_id=assignment.source_evidence_id,
    )
    if existing_assignment is not None and existing_assignment != assignment:
        raise DefinitiveWildCardAssignmentConflict(
            "WC assignment ID already has different definitive authority"
        )

    trigger_store = PlayerTourEntryTriggerStore(session)
    proposed_trigger = assignment.to_tour_entry_trigger()
    existing_trigger = trigger_store.get(
        run_id=assignment.run_id,
        branch_id=assignment.branch_id,
        player_id=assignment.player_id,
    )

    if existing_trigger is not None:
        if existing_trigger == proposed_trigger:
            first_trigger = existing_trigger
        elif existing_trigger.decision_position > proposed_trigger.decision_position:
            raise DefinitiveWildCardAssignmentConflict(
                "Definitive WC predates persisted first Tour-entry trigger"
            )
        elif existing_trigger.decision_position == proposed_trigger.decision_position:
            raise DefinitiveWildCardAssignmentConflict(
                "Distinct simultaneous first-entry authorities require slot arbitration"
            )
        else:
            first_trigger = existing_trigger
    else:
        first_trigger = proposed_trigger

    stored = assignment_store.append(assignment)
    if existing_trigger is None:
        first_trigger = trigger_store.append(proposed_trigger)

    return DefinitiveWildCardAssignmentCommit(
        assignment=stored,
        first_tour_entry_trigger=first_trigger,
    )


def capture_saved_definitive_wild_card_assignments(
    session: Session,
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> None:
    assignments = DefinitiveWildCardAssignmentStore(session).list(
        run_id=run_id,
        branch_id=branch_id,
    )
    payload["content"][DEFINITIVE_WILD_CARD_ASSIGNMENT_COMPONENT_KEY] = {
        "fingerprint": _component_fingerprint(assignments),
        "assignments": [item.model_dump(mode="json") for item in assignments],
    }


def load_saved_definitive_wild_card_assignments(
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> tuple[DefinitiveWildCardAssignmentAuthority, ...] | None:
    component = payload.get("content", {}).get(
        DEFINITIVE_WILD_CARD_ASSIGNMENT_COMPONENT_KEY
    )
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {
        "fingerprint",
        "assignments",
    }:
        raise ValueError("Invalid Saved Revision definitive WC component")
    raw = component["assignments"]
    if not isinstance(raw, list):
        raise ValueError("Saved definitive WC assignments must be a list")
    assignments = tuple(
        DefinitiveWildCardAssignmentAuthority.model_validate_json(json.dumps(item))
        for item in raw
    )
    if assignments != _canonical(assignments):
        raise ValueError("Saved definitive WC assignments are not ordered")
    if len({item.source_evidence_id for item in assignments}) != len(assignments):
        raise ValueError("Saved definitive WC assignments contain duplicate IDs")
    if any(
        (item.run_id, item.branch_id) != (run_id, branch_id) for item in assignments
    ):
        raise ValueError("Saved definitive WC assignment scope mismatch")
    if _component_fingerprint(assignments) != component["fingerprint"]:
        raise ValueError("Saved definitive WC assignment fingerprint mismatch")
    return assignments


def remap_saved_definitive_wild_card_assignments_component(
    payload: dict,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    frozen_fingerprint_map: dict[str, str],
) -> tuple[dict | None, dict[str, tuple[str, str]]]:
    """Retarget definitive WC assignments through mapped WC + Entry Field identity."""

    source = load_saved_definitive_wild_card_assignments(
        payload,
        run_id=run_id,
        branch_id=source_branch_id,
    )
    if source is None:
        return None, {}

    target = []
    identity_map: dict[str, tuple[str, str]] = {}
    for assignment in source:
        try:
            target_wc_fingerprint = frozen_fingerprint_map[
                assignment.source_wild_card_authority_fingerprint
            ]
        except KeyError as exc:
            raise ValueError(
                "Definitive Wild Card assignment references WC authority without a target mapping"
            ) from exc
        try:
            target_entry_field_fingerprint = frozen_fingerprint_map[
                assignment.source_entry_field_fingerprint
            ]
        except KeyError as exc:
            raise ValueError(
                "Definitive Wild Card assignment references Entry Field without a target mapping"
            ) from exc

        mapped = assignment.model_copy(
            update={
                "branch_id": target_branch_id,
                "source_wild_card_authority_fingerprint": target_wc_fingerprint,
                "source_entry_field_fingerprint": target_entry_field_fingerprint,
            }
        )
        target.append(mapped)
        identity_map[assignment.fingerprint] = (
            mapped.source_evidence_id,
            mapped.fingerprint,
        )

    target_tuple = tuple(target)
    return (
        {
            "fingerprint": _component_fingerprint(target_tuple),
            "assignments": [item.model_dump(mode="json") for item in target_tuple],
        },
        identity_map,
    )


def restore_saved_definitive_wild_card_assignments(
    session: Session,
    *,
    current_payload: dict,
    target_payload: dict,
    run_id: str,
    branch_id: str,
) -> None:
    expected = load_saved_definitive_wild_card_assignments(
        current_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    target = load_saved_definitive_wild_card_assignments(
        target_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    live = DefinitiveWildCardAssignmentStore(session).list(
        run_id=run_id,
        branch_id=branch_id,
    )
    if tuple(item.fingerprint for item in live) != tuple(
        item.fingerprint for item in (expected or ())
    ):
        raise ValueError("Live definitive WC assignments differ from saved head")

    session.execute(
        delete(DefinitiveWildCardAssignmentAuthorityModel).where(
            DefinitiveWildCardAssignmentAuthorityModel.run_id == run_id,
            DefinitiveWildCardAssignmentAuthorityModel.branch_id == branch_id,
        )
    )
    for assignment in target or ():
        _insert(session, assignment)

"""Persistence and Saved Revision support for resolved application validation slots."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.application_validation_authority import (
    ResolvedApplicationValidationSlot,
)
from beta_engine.infrastructure.db.models import (
    ResolvedApplicationValidationSlotModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.run_entry_decision_slots import (
    RunEntryDecisionSlotStore,
)
from beta_engine.infrastructure.db.tournament_application_submissions import (
    ValidApplicationSubmissionBatchCommit,
    record_valid_application_submission_batch,
)


APPLICATION_VALIDATION_SLOT_COMPONENT_KEY = "application_validation_slots"


class ApplicationValidationSlotConflict(ValueError):
    """Persisted validation-slot truth conflicts with existing authority."""


@dataclass(frozen=True)
class ResolvedApplicationValidationCommit:
    """Atomic resolved-validation commit and optional valid-submission result."""

    validation_slot: ResolvedApplicationValidationSlot
    submission_commit: ValidApplicationSubmissionBatchCommit | None


def _canonical(
    slots: tuple[ResolvedApplicationValidationSlot, ...]
    | list[ResolvedApplicationValidationSlot],
) -> tuple[ResolvedApplicationValidationSlot, ...]:
    return tuple(
        sorted(
            slots,
            key=lambda item: (
                item.slot.week.ordinal,
                item.slot.decision_slot_ordinal,
            ),
        )
    )


def _component_fingerprint(
    slots: tuple[ResolvedApplicationValidationSlot, ...],
) -> str:
    body = [item.model_dump(mode="json") for item in slots]
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _load(
    row: ResolvedApplicationValidationSlotModel,
) -> ResolvedApplicationValidationSlot:
    resolved = ResolvedApplicationValidationSlot.model_validate_json(row.payload_json)
    if (
        resolved.slot.run_id,
        resolved.slot.branch_id,
        resolved.slot.week.ordinal,
        resolved.slot.decision_slot_ordinal,
        resolved.slot.fingerprint,
        resolved.fingerprint,
    ) != (
        row.run_id,
        row.branch_id,
        row.week_ordinal,
        row.decision_slot_ordinal,
        row.source_slot_fingerprint,
        row.fingerprint,
    ):
        raise ValueError("Stored application validation slot is corrupt")
    return resolved


def _insert(
    session: Session,
    resolved: ResolvedApplicationValidationSlot,
) -> None:
    session.add(
        ResolvedApplicationValidationSlotModel(
            run_id=resolved.slot.run_id,
            branch_id=resolved.slot.branch_id,
            week_ordinal=resolved.slot.week.ordinal,
            decision_slot_ordinal=resolved.slot.decision_slot_ordinal,
            source_slot_fingerprint=resolved.slot.fingerprint,
            fingerprint=resolved.fingerprint,
            payload_json=resolved.model_dump_json(),
        )
    )
    session.flush()


class ApplicationValidationSlotStore:
    """Append-only Branch-owned resolved validation-slot authority."""

    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Application validation Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status != "active"):
            raise ValueError("Application validation Run/Branch scope is not writable")

    def get(
        self,
        *,
        run_id: str,
        branch_id: str,
        week_ordinal: int,
        decision_slot_ordinal: int,
    ) -> ResolvedApplicationValidationSlot | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            ResolvedApplicationValidationSlotModel,
            (run_id, branch_id, week_ordinal, decision_slot_ordinal),
        )
        return None if row is None else _load(row)

    def list(
        self,
        *,
        run_id: str,
        branch_id: str,
    ) -> tuple[ResolvedApplicationValidationSlot, ...]:
        self._scope(run_id, branch_id)
        rows = self.session.scalars(
            select(ResolvedApplicationValidationSlotModel)
            .where(
                ResolvedApplicationValidationSlotModel.run_id == run_id,
                ResolvedApplicationValidationSlotModel.branch_id == branch_id,
            )
            .order_by(
                ResolvedApplicationValidationSlotModel.week_ordinal,
                ResolvedApplicationValidationSlotModel.decision_slot_ordinal,
            )
        ).all()
        return tuple(_load(row) for row in rows)

    def append(
        self,
        resolved: ResolvedApplicationValidationSlot,
    ) -> ResolvedApplicationValidationSlot:
        self._scope(resolved.slot.run_id, resolved.slot.branch_id, writing=True)
        key = (
            resolved.slot.run_id,
            resolved.slot.branch_id,
            resolved.slot.week.ordinal,
            resolved.slot.decision_slot_ordinal,
        )
        existing = self.session.get(ResolvedApplicationValidationSlotModel, key)
        if existing is not None:
            loaded = _load(existing)
            if loaded == resolved:
                return loaded
            raise ApplicationValidationSlotConflict(
                "Application validation slot already has different resolved authority"
            )
        _insert(self.session, resolved)
        return resolved


def record_resolved_application_validation_slot(
    session: Session,
    resolved: ResolvedApplicationValidationSlot,
) -> ResolvedApplicationValidationCommit:
    """Persist complete validation truth and downstream valid submissions atomically."""

    source_slot = RunEntryDecisionSlotStore(session).get(
        run_id=resolved.slot.run_id,
        branch_id=resolved.slot.branch_id,
        week_ordinal=resolved.slot.week.ordinal,
        decision_slot_ordinal=resolved.slot.decision_slot_ordinal,
    )
    if source_slot is None:
        raise ApplicationValidationSlotConflict(
            "Application validation requires a persisted Run entry-decision slot"
        )
    if source_slot != resolved.slot:
        raise ApplicationValidationSlotConflict(
            "Application validation source slot differs from persisted Run authority"
        )

    store = ApplicationValidationSlotStore(session)
    existing = store.get(
        run_id=resolved.slot.run_id,
        branch_id=resolved.slot.branch_id,
        week_ordinal=resolved.slot.week.ordinal,
        decision_slot_ordinal=resolved.slot.decision_slot_ordinal,
    )
    if existing is not None and existing != resolved:
        raise ApplicationValidationSlotConflict(
            "Application validation slot already has different resolved authority"
        )

    submission_batch = resolved.to_validated_entry_slot().to_submission_batch()
    submission_commit = (
        None
        if submission_batch is None
        else record_valid_application_submission_batch(session, submission_batch)
    )
    stored = store.append(resolved)
    return ResolvedApplicationValidationCommit(
        validation_slot=stored,
        submission_commit=submission_commit,
    )


def capture_saved_application_validation_slots(
    session: Session,
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> None:
    slots = ApplicationValidationSlotStore(session).list(
        run_id=run_id,
        branch_id=branch_id,
    )
    payload["content"][APPLICATION_VALIDATION_SLOT_COMPONENT_KEY] = {
        "fingerprint": _component_fingerprint(slots),
        "slots": [item.model_dump(mode="json") for item in slots],
    }


def load_saved_application_validation_slots(
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> tuple[ResolvedApplicationValidationSlot, ...] | None:
    component = payload.get("content", {}).get(APPLICATION_VALIDATION_SLOT_COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "slots"}:
        raise ValueError("Invalid Saved Revision application validation component")
    raw = component["slots"]
    if not isinstance(raw, list):
        raise ValueError("Saved application validation slots must be a list")
    slots = tuple(
        ResolvedApplicationValidationSlot.model_validate_json(json.dumps(item))
        for item in raw
    )
    if slots != _canonical(slots):
        raise ValueError("Saved application validation slots are not ordered")
    keys = [
        (item.slot.week.ordinal, item.slot.decision_slot_ordinal) for item in slots
    ]
    if len(set(keys)) != len(keys):
        raise ValueError("Saved application validation slots contain duplicate positions")
    if any(
        (item.slot.run_id, item.slot.branch_id) != (run_id, branch_id)
        for item in slots
    ):
        raise ValueError("Saved application validation slot scope mismatch")
    if _component_fingerprint(slots) != component["fingerprint"]:
        raise ValueError("Saved application validation slot fingerprint mismatch")
    return slots


def restore_saved_application_validation_slots(
    session: Session,
    *,
    current_payload: dict,
    target_payload: dict,
    run_id: str,
    branch_id: str,
) -> None:
    expected = load_saved_application_validation_slots(
        current_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    target = load_saved_application_validation_slots(
        target_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    live = ApplicationValidationSlotStore(session).list(
        run_id=run_id,
        branch_id=branch_id,
    )
    if tuple(item.fingerprint for item in live) != tuple(
        item.fingerprint for item in (expected or ())
    ):
        raise ValueError("Live application validation slots differ from saved head")

    session.execute(
        delete(ResolvedApplicationValidationSlotModel).where(
            ResolvedApplicationValidationSlotModel.run_id == run_id,
            ResolvedApplicationValidationSlotModel.branch_id == branch_id,
        )
    )
    for resolved in target or ():
        _insert(session, resolved)

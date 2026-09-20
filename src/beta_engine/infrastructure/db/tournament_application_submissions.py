"""Persistence and Saved Revision support for valid tournament submissions."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentApplicationSubmissionAuthorityModel,
)
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PlayerTourEntryTriggerStore,
)


TOURNAMENT_APPLICATION_SUBMISSION_COMPONENT_KEY = (
    "tournament_application_submissions"
)


class TournamentApplicationSubmissionConflict(ValueError):
    """Persisted valid-application truth conflicts with existing authority."""


@dataclass(frozen=True)
class ValidApplicationSubmissionCommit:
    """Stable result of persisting one valid submission and first-entry truth."""

    submission: TournamentApplicationSubmissionAuthority
    first_tour_entry_trigger: PlayerTourEntryTrigger


def _component_fingerprint(
    submissions: tuple[TournamentApplicationSubmissionAuthority, ...],
) -> str:
    body = [item.model_dump(mode="json") for item in submissions]
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _canonical(
    submissions: tuple[TournamentApplicationSubmissionAuthority, ...]
    | list[TournamentApplicationSubmissionAuthority],
) -> tuple[TournamentApplicationSubmissionAuthority, ...]:
    return tuple(
        sorted(
            submissions,
            key=lambda item: (
                item.submission_week.ordinal,
                item.decision_slot_ordinal,
                item.application_id,
            ),
        )
    )


def _load(
    row: TournamentApplicationSubmissionAuthorityModel,
) -> TournamentApplicationSubmissionAuthority:
    submission = TournamentApplicationSubmissionAuthority.model_validate_json(
        row.payload_json
    )
    if (
        submission.run_id,
        submission.branch_id,
        submission.application_id,
        submission.event_id,
        submission.player_id,
        submission.submission_week.ordinal,
        submission.decision_slot_ordinal,
        submission.fingerprint,
    ) != (
        row.run_id,
        row.branch_id,
        row.application_id,
        row.event_id,
        row.player_id,
        row.submission_week_ordinal,
        row.decision_slot_ordinal,
        row.fingerprint,
    ):
        raise ValueError("Stored tournament application submission is corrupt")
    return submission


def _insert(
    session: Session,
    submission: TournamentApplicationSubmissionAuthority,
) -> None:
    session.add(
        TournamentApplicationSubmissionAuthorityModel(
            run_id=submission.run_id,
            branch_id=submission.branch_id,
            application_id=submission.application_id,
            event_id=submission.event_id,
            player_id=submission.player_id,
            submission_week_ordinal=submission.submission_week.ordinal,
            decision_slot_ordinal=submission.decision_slot_ordinal,
            fingerprint=submission.fingerprint,
            payload_json=submission.model_dump_json(),
        )
    )
    session.flush()


class TournamentApplicationSubmissionStore:
    """Append-only Branch-owned authority for already-valid submissions."""

    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Tournament application Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status != "active"):
            raise ValueError("Tournament application Run/Branch scope is not writable")

    def get(
        self,
        *,
        run_id: str,
        branch_id: str,
        application_id: str,
    ) -> TournamentApplicationSubmissionAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentApplicationSubmissionAuthorityModel,
            (run_id, branch_id, application_id),
        )
        return None if row is None else _load(row)

    def list(
        self,
        *,
        run_id: str,
        branch_id: str,
    ) -> tuple[TournamentApplicationSubmissionAuthority, ...]:
        self._scope(run_id, branch_id)
        rows = self.session.scalars(
            select(TournamentApplicationSubmissionAuthorityModel)
            .where(
                TournamentApplicationSubmissionAuthorityModel.run_id == run_id,
                TournamentApplicationSubmissionAuthorityModel.branch_id == branch_id,
            )
            .order_by(
                TournamentApplicationSubmissionAuthorityModel.submission_week_ordinal,
                TournamentApplicationSubmissionAuthorityModel.decision_slot_ordinal,
                TournamentApplicationSubmissionAuthorityModel.application_id,
            )
        ).all()
        return tuple(_load(row) for row in rows)

    def append(
        self,
        submission: TournamentApplicationSubmissionAuthority,
    ) -> TournamentApplicationSubmissionAuthority:
        self._scope(submission.run_id, submission.branch_id, writing=True)
        existing = self.session.get(
            TournamentApplicationSubmissionAuthorityModel,
            (submission.run_id, submission.branch_id, submission.application_id),
        )
        if existing is not None:
            loaded = _load(existing)
            if loaded == submission:
                return loaded
            raise TournamentApplicationSubmissionConflict(
                "Application ID already has different submission authority"
            )
        _insert(self.session, submission)
        return submission


def record_valid_application_submission(
    session: Session,
    submission: TournamentApplicationSubmissionAuthority,
) -> ValidApplicationSubmissionCommit:
    """Persist a valid submission and establish first Tour entry in one transaction.

    Validation of the submission is upstream. This boundary only coordinates canonical
    persistence. A later valid application remains historical evidence but never
    replaces an earlier first Tour-entry trigger.
    """

    trigger_store = PlayerTourEntryTriggerStore(session)
    proposed_trigger = submission.to_tour_entry_trigger()
    existing_trigger = trigger_store.get(
        run_id=submission.run_id,
        branch_id=submission.branch_id,
        player_id=submission.player_id,
    )

    if existing_trigger is not None:
        if existing_trigger == proposed_trigger:
            first_trigger = existing_trigger
        elif existing_trigger.decision_position > proposed_trigger.decision_position:
            raise TournamentApplicationSubmissionConflict(
                "Valid submission predates persisted first Tour-entry trigger"
            )
        elif existing_trigger.decision_position == proposed_trigger.decision_position:
            raise TournamentApplicationSubmissionConflict(
                "Distinct simultaneous first-entry authorities require slot arbitration"
            )
        else:
            first_trigger = existing_trigger
    else:
        first_trigger = proposed_trigger

    stored = TournamentApplicationSubmissionStore(session).append(submission)
    if existing_trigger is None:
        first_trigger = trigger_store.append(proposed_trigger)

    return ValidApplicationSubmissionCommit(
        submission=stored,
        first_tour_entry_trigger=first_trigger,
    )


def capture_saved_application_submissions(
    session: Session,
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> None:
    submissions = TournamentApplicationSubmissionStore(session).list(
        run_id=run_id,
        branch_id=branch_id,
    )
    payload["content"][TOURNAMENT_APPLICATION_SUBMISSION_COMPONENT_KEY] = {
        "fingerprint": _component_fingerprint(submissions),
        "submissions": [item.model_dump(mode="json") for item in submissions],
    }


def load_saved_application_submissions(
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> tuple[TournamentApplicationSubmissionAuthority, ...] | None:
    component = payload.get("content", {}).get(
        TOURNAMENT_APPLICATION_SUBMISSION_COMPONENT_KEY
    )
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {
        "fingerprint",
        "submissions",
    }:
        raise ValueError("Invalid Saved Revision tournament application component")
    raw = component["submissions"]
    if not isinstance(raw, list):
        raise ValueError("Saved tournament application submissions must be a list")
    submissions = tuple(
        TournamentApplicationSubmissionAuthority.model_validate_json(json.dumps(item))
        for item in raw
    )
    if submissions != _canonical(submissions):
        raise ValueError("Saved tournament application submissions are not ordered")
    if len({item.application_id for item in submissions}) != len(submissions):
        raise ValueError("Saved tournament application submissions contain duplicate IDs")
    if any(
        (item.run_id, item.branch_id) != (run_id, branch_id) for item in submissions
    ):
        raise ValueError("Saved tournament application submission scope mismatch")
    if _component_fingerprint(submissions) != component["fingerprint"]:
        raise ValueError("Saved tournament application submission fingerprint mismatch")
    return submissions


def restore_saved_application_submissions(
    session: Session,
    *,
    current_payload: dict,
    target_payload: dict,
    run_id: str,
    branch_id: str,
) -> None:
    expected = load_saved_application_submissions(
        current_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    target = load_saved_application_submissions(
        target_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    live = TournamentApplicationSubmissionStore(session).list(
        run_id=run_id,
        branch_id=branch_id,
    )
    if tuple(item.fingerprint for item in live) != tuple(
        item.fingerprint for item in (expected or ())
    ):
        raise ValueError("Live tournament application submissions differ from saved head")

    session.execute(
        delete(TournamentApplicationSubmissionAuthorityModel).where(
            TournamentApplicationSubmissionAuthorityModel.run_id == run_id,
            TournamentApplicationSubmissionAuthorityModel.branch_id == branch_id,
        )
    )
    for submission in target or ():
        _insert(session, submission)

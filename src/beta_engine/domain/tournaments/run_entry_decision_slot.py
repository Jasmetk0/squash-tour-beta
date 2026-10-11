"""Run/Branch authority over one simultaneous entry-decision Simulation Slot."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
    TournamentApplicationSubmissionBatchAuthority,
)
from beta_engine.domain.tournaments.entry_field import EntryWindow


EntryDecisionTarget = Literal["MAIN", "QUALIFICATION"]


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class EntryDecisionEvidence(FrozenInput):
    """Immutable reference to one preserved pre-cut application decision."""

    event_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    target: EntryDecisionTarget
    source_decision_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class RunEntryDecisionSlotAuthority(FrozenInput):
    """Freeze one global entry-decision slot without deciding eligibility."""

    schema_version: Literal["run_entry_decision_slot_authority.v1"] = (
        "run_entry_decision_slot_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RankingWeek
    decision_slot_ordinal: int = Field(ge=1)
    source_entry_batch_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_application_decisions_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_active_players_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    decisions: tuple[EntryDecisionEvidence, ...]

    @model_validator(mode="after")
    def validate_canonical_decisions(self):
        keys = tuple((d.event_id, d.player_id, d.target) for d in self.decisions)
        if keys != tuple(sorted(keys)):
            raise ValueError("Entry decision slot evidence must use canonical order")
        if len(set(keys)) != len(keys):
            raise ValueError("Entry decision slot contains duplicate decision evidence")
        return self

    @property
    def decision_position(self) -> tuple[int, int]:
        return (self.week.ordinal, self.decision_slot_ordinal)

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class ValidatedApplicationDecision(FrozenInput):
    """Upstream proof that one preserved decision is a valid MSA Tour application."""

    application_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    entry_window: EntryWindow
    source_decision_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    nr_tie_break_token: str = Field(min_length=1)
    validation_authority_id: str = Field(min_length=1, max_length=256)
    validation_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance: str = Field(min_length=1)

    @property
    def key(self) -> tuple[str, str]:
        return (self.event_id, self.player_id)


class ValidatedEntryDecisionSlot(FrozenInput):
    """Validated subset of one entry-decision slot, ready for submission authority."""

    slot: RunEntryDecisionSlotAuthority
    valid_applications: tuple[ValidatedApplicationDecision, ...]

    @model_validator(mode="after")
    def validate_subset(self):
        applications = self.valid_applications
        ids = tuple(item.application_id for item in applications)
        if len(set(ids)) != len(ids):
            raise ValueError("Validated entry slot contains duplicate application IDs")
        if ids != tuple(sorted(ids)):
            raise ValueError("Validated applications must use canonical application-ID order")

        evidence_by_key = {
            (item.event_id, item.player_id): item for item in self.slot.decisions
        }
        seen_keys: set[tuple[str, str]] = set()
        for item in applications:
            if item.key in seen_keys:
                raise ValueError(
                    "Validated entry slot contains duplicate event/player application"
                )
            seen_keys.add(item.key)
            evidence = evidence_by_key.get(item.key)
            if evidence is None:
                raise ValueError(
                    "Validated application does not exist in preserved pre-cut decisions"
                )
            expected_window = (
                "main" if evidence.target == "MAIN" else "qualification"
            )
            if item.entry_window != expected_window:
                raise ValueError(
                    "Validated application window differs from preserved decision target"
                )
            if item.source_decision_fingerprint != evidence.source_decision_fingerprint:
                raise ValueError(
                    "Validated application decision fingerprint does not match source"
                )
        return self

    def to_submission_batch(
        self,
    ) -> TournamentApplicationSubmissionBatchAuthority | None:
        if not self.valid_applications:
            return None
        submissions = tuple(
            TournamentApplicationSubmissionAuthority(
                application_id=item.application_id,
                run_id=self.slot.run_id,
                branch_id=self.slot.branch_id,
                event_id=item.event_id,
                player_id=item.player_id,
                entry_window=item.entry_window,
                submission_week=self.slot.week,
                decision_slot_ordinal=self.slot.decision_slot_ordinal,
                nr_tie_break_token=item.nr_tie_break_token,
                validation_authority_id=item.validation_authority_id,
                validation_authority_fingerprint=item.validation_authority_fingerprint,
                provenance=item.provenance,
            )
            for item in self.valid_applications
        )
        return TournamentApplicationSubmissionBatchAuthority.from_submissions(
            submissions
        )

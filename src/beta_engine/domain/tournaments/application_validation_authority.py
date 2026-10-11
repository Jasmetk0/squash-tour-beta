"""Versioned outcome authority for MSA Tour application validity."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.tournaments.entry_field import EntryWindow
from beta_engine.domain.tournaments.run_entry_decision_slot import (
    RunEntryDecisionSlotAuthority,
    ValidatedApplicationDecision,
    ValidatedEntryDecisionSlot,
)


ApplicationValidationOutcome = Literal["valid", "invalid"]


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentApplicationValidationAuthority(FrozenInput):
    """Resolved validity for one preserved pre-cut application decision.

    This contract does not implement eligibility/deadline rules. It freezes the
    result of whichever versioned validator or explicit Admin authority resolved
    those still-separate rules.
    """

    schema_version: Literal["tournament_application_validation_authority.v1"] = (
        "tournament_application_validation_authority.v1"
    )
    validation_id: str = Field(min_length=1, max_length=256)
    application_id: str = Field(min_length=1, max_length=256)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RankingWeek
    decision_slot_ordinal: int = Field(ge=1)
    source_slot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    entry_window: EntryWindow
    source_decision_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: ApplicationValidationOutcome
    nr_tie_break_token: str | None = None
    validation_policy_id: str = Field(min_length=1, max_length=256)
    validation_policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    reasons: tuple[str, ...] = ()
    provenance: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_outcome(self):
        if self.outcome == "valid" and not self.nr_tie_break_token:
            raise ValueError("Valid application requires NR tie-break token")
        if self.outcome == "invalid" and not self.reasons:
            raise ValueError("Invalid application requires at least one reason")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("Application validation reasons must not be blank")
        if self.reasons != tuple(sorted(set(self.reasons))):
            raise ValueError("Application validation reasons must be unique and canonical")
        return self

    @property
    def key(self) -> tuple[str, str]:
        return (self.event_id, self.player_id)

    @property
    def decision_position(self) -> tuple[int, int]:
        return (self.week.ordinal, self.decision_slot_ordinal)

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))

    def to_validated_application_decision(
        self,
    ) -> ValidatedApplicationDecision | None:
        if self.outcome != "valid":
            return None
        assert self.nr_tie_break_token is not None
        return ValidatedApplicationDecision(
            application_id=self.application_id,
            event_id=self.event_id,
            player_id=self.player_id,
            entry_window=self.entry_window,
            source_decision_fingerprint=self.source_decision_fingerprint,
            nr_tie_break_token=self.nr_tie_break_token,
            validation_authority_id=self.validation_id,
            validation_authority_fingerprint=self.fingerprint,
            provenance=self.provenance,
        )


class ResolvedApplicationValidationSlot(FrozenInput):
    """Complete valid/invalid resolution for every application in one entry slot."""

    schema_version: Literal["resolved_application_validation_slot.v1"] = (
        "resolved_application_validation_slot.v1"
    )
    slot: RunEntryDecisionSlotAuthority
    validations: tuple[TournamentApplicationValidationAuthority, ...]

    @model_validator(mode="after")
    def validate_complete_coverage(self):
        ordered = tuple(
            sorted(self.validations, key=lambda item: (item.event_id, item.player_id))
        )
        if self.validations != ordered:
            raise ValueError("Application validations must use canonical event/player order")

        validation_keys = tuple(item.key for item in self.validations)
        if len(set(validation_keys)) != len(validation_keys):
            raise ValueError("Application validation slot contains duplicate decisions")

        decision_by_key = {
            (item.event_id, item.player_id): item for item in self.slot.decisions
        }
        if set(validation_keys) != set(decision_by_key):
            raise ValueError(
                "Application validation slot must resolve every preserved decision exactly once"
            )

        application_ids = tuple(item.application_id for item in self.validations)
        if len(set(application_ids)) != len(application_ids):
            raise ValueError("Application validation slot has duplicate application IDs")

        for validation in self.validations:
            evidence = decision_by_key[validation.key]
            if (
                validation.run_id,
                validation.branch_id,
                validation.week,
                validation.decision_slot_ordinal,
                validation.source_slot_fingerprint,
            ) != (
                self.slot.run_id,
                self.slot.branch_id,
                self.slot.week,
                self.slot.decision_slot_ordinal,
                self.slot.fingerprint,
            ):
                raise ValueError("Application validation scope or slot evidence mismatch")
            expected_window = "main" if evidence.target == "MAIN" else "qualification"
            if validation.entry_window != expected_window:
                raise ValueError(
                    "Application validation window differs from preserved decision target"
                )
            if (
                validation.source_decision_fingerprint
                != evidence.source_decision_fingerprint
            ):
                raise ValueError(
                    "Application validation decision fingerprint mismatch"
                )
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))

    def to_validated_entry_slot(self) -> ValidatedEntryDecisionSlot:
        valid = tuple(
            item.to_validated_application_decision()
            for item in self.validations
            if item.outcome == "valid"
        )
        return ValidatedEntryDecisionSlot(
            slot=self.slot,
            valid_applications=tuple(
                sorted(
                    (item for item in valid if item is not None),
                    key=lambda item: item.application_id,
                )
            ),
        )

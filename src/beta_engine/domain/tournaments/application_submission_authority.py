"""Canonical evidence for one valid MSA Tour tournament application submission."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.tournaments.entry_field import (
    EntryWindow,
    TournamentEntryApplication,
)


class TournamentApplicationSubmissionAuthority(FrozenInput):
    """Freeze a valid application at the moment it is submitted.

    Validation policy is upstream. This object exists only after that policy has
    established that the submission is valid. Field acceptance/capacity is downstream
    and cannot revoke the fact that a valid Tour application was submitted.
    """

    schema_version: Literal["tournament_application_submission_authority.v1"] = (
        "tournament_application_submission_authority.v1"
    )
    application_id: str = Field(min_length=1, max_length=256)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    entry_window: EntryWindow
    submission_week: RankingWeek
    decision_slot_ordinal: int = Field(ge=0)
    nr_tie_break_token: str = Field(min_length=1)
    validation_authority_id: str = Field(min_length=1, max_length=256)
    validation_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance: str = Field(min_length=1)

    @property
    def decision_position(self) -> tuple[int, int]:
        return (self.submission_week.ordinal, self.decision_slot_ordinal)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

    def to_tour_entry_trigger(self) -> PlayerTourEntryTrigger:
        """Project this valid submission into the canonical first-entry contract."""

        return PlayerTourEntryTrigger(
            run_id=self.run_id,
            branch_id=self.branch_id,
            player_id=self.player_id,
            event_id=self.event_id,
            trigger_kind="valid_tournament_application",
            trigger_week=self.submission_week,
            decision_slot_ordinal=self.decision_slot_ordinal,
            source_evidence_id=self.application_id,
            source_evidence_fingerprint=self.fingerprint,
            provenance=self.provenance,
        )

    def to_entry_field_application(self) -> TournamentEntryApplication:
        """Project submission truth into the existing downstream field-cut payload."""

        return TournamentEntryApplication(
            application_id=self.application_id,
            run_id=self.run_id,
            branch_id=self.branch_id,
            event_id=self.event_id,
            player_id=self.player_id,
            entry_window=self.entry_window,
            decision_slot_ordinal=self.decision_slot_ordinal,
            nr_tie_break_token=self.nr_tie_break_token,
            eligible=True,
        )

class TournamentApplicationSubmissionBatchAuthority(FrozenInput):
    """One simultaneous entry-decision-slot batch of already-valid submissions.

    The Master requires all decisions in one entry slot to read the same pre-slot
    snapshot and become visible together. Canonical ordering is technical provenance
    only; it never creates sporting priority between simultaneous applications.
    """

    schema_version: Literal["tournament_application_submission_batch.v1"] = (
        "tournament_application_submission_batch.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    submission_week: RankingWeek
    decision_slot_ordinal: int = Field(ge=0)
    submissions: tuple[TournamentApplicationSubmissionAuthority, ...] = Field(
        min_length=1
    )

    @model_validator(mode="after")
    def validate_batch(self):
        if any(
            (item.run_id, item.branch_id)
            != (self.run_id, self.branch_id)
            for item in self.submissions
        ):
            raise ValueError("Application batch contains a different Run/Branch scope")
        if any(
            item.decision_position
            != (self.submission_week.ordinal, self.decision_slot_ordinal)
            for item in self.submissions
        ):
            raise ValueError("Application batch contains a different decision slot")
        ids = tuple(item.application_id for item in self.submissions)
        if len(set(ids)) != len(ids):
            raise ValueError("Application batch contains duplicate application IDs")
        if ids != tuple(sorted(ids)):
            raise ValueError("Application batch must use canonical application-ID order")
        return self

    @classmethod
    def from_submissions(
        cls,
        submissions: tuple[TournamentApplicationSubmissionAuthority, ...],
    ) -> "TournamentApplicationSubmissionBatchAuthority":
        if not submissions:
            raise ValueError("Application batch cannot be empty")
        canonical = tuple(sorted(submissions, key=lambda item: item.application_id))
        first = canonical[0]
        return cls(
            run_id=first.run_id,
            branch_id=first.branch_id,
            submission_week=first.submission_week,
            decision_slot_ordinal=first.decision_slot_ordinal,
            submissions=canonical,
        )

    @property
    def decision_position(self) -> tuple[int, int]:
        return (self.submission_week.ordinal, self.decision_slot_ordinal)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

    def representative_first_applications(
        self,
    ) -> tuple[TournamentApplicationSubmissionAuthority, ...]:
        """Choose deterministic provenance only, never a causal within-slot order."""

        by_player: dict[str, TournamentApplicationSubmissionAuthority] = {}
        for submission in self.submissions:
            by_player.setdefault(submission.player_id, submission)
        return tuple(by_player[player_id] for player_id in sorted(by_player))


"""Canonical evidence for one valid MSA Tour tournament application submission."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field

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

"""Audited Admin authority for one exact unresolved group-standings tie."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsTieCase,
    TournamentGroupTieResolutionDecision,
)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentGroupTieResolutionAuthority(FrozenInput):
    """One immutable, explicit Admin ordering for an unresolved tie case."""

    schema_version: Literal["tournament_group_tie_resolution_authority.v1"] = (
        "tournament_group_tie_resolution_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    resolved_by_command_id: str = Field(min_length=1, max_length=128)
    group_match_schedule_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: TournamentGroupTieResolutionDecision

    @model_validator(mode="after")
    def validate_authority(self) -> "TournamentGroupTieResolutionAuthority":
        if not self.decision.admin_reason.strip():
            raise ValueError("Admin tie resolution requires an audit reason")
        return self

    @property
    def case(self) -> TournamentGroupStandingsTieCase:
        return self.decision.case

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))

"""Immutable resolved ranking sources, versioned by effective publication week."""

import hashlib
import json

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import (
    FrozenInput,
    OfficialRankingResult,
    RankingWeek,
)


class RankingResultVersion(FrozenInput):
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    effective_week: RankingWeek
    result: OfficialRankingResult
    previous_fingerprint: str | None = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_effective_week(self):
        if self.effective_week.ordinal < self.result.first_publication_week.ordinal:
            raise ValueError("Result cannot be effective before first publication")
        if (
            self.previous_fingerprint is None
            and self.effective_week != self.result.first_publication_week
        ):
            raise ValueError("Initial result must start at its first publication week")
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()


def validate_result_successor(
    previous: RankingResultVersion, current: RankingResultVersion
) -> None:
    """Corrections replace awards, never silently restart their original lifetime."""
    if (
        current.run_id,
        current.branch_id,
        current.result.edition_id,
        current.result.player_id,
    ) != (
        previous.run_id,
        previous.branch_id,
        previous.result.edition_id,
        previous.result.player_id,
    ):
        raise ValueError("Result correction scope mismatch")
    if (
        current.previous_fingerprint != previous.fingerprint
        or current.effective_week.ordinal <= previous.effective_week.ordinal
    ):
        raise ValueError("Result correction must extend its source lineage")
    for field in ("completed_week", "first_publication_week", "validity_weeks"):
        if getattr(current.result, field) != getattr(previous.result, field):
            raise ValueError(
                "Result correction cannot change original timing or validity"
            )

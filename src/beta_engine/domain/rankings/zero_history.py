"""Immutable versions of explicit zero decisions; no sanction tariffs inferred."""

import hashlib
import json

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import DisciplinaryZero, FrozenInput, RankingWeek


class RankingZeroVersion(FrozenInput):
    effective_week: RankingWeek
    zero: DisciplinaryZero
    previous_fingerprint: str | None = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_effective_week(self):
        if self.effective_week.ordinal < self.zero.effective_week.ordinal:
            raise ValueError("Zero version cannot precede original effective week")
        if self.previous_fingerprint is None and self.effective_week != self.zero.effective_week:
            raise ValueError("Initial zero version must start at original effective week")
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()


def validate_zero_successor(previous: RankingZeroVersion, current: RankingZeroVersion) -> None:
    for field in ("run_id", "branch_id", "zero_id", "player_id", "effective_week"):
        if getattr(previous.zero, field) != getattr(current.zero, field):
            raise ValueError("Zero correction cannot change identity or original effective week")
    if (current.previous_fingerprint != previous.fingerprint
            or current.effective_week.ordinal <= previous.effective_week.ordinal):
        raise ValueError("Zero correction must extend its source lineage")


def resolve_zero_versions(versions, week: RankingWeek) -> tuple[DisciplinaryZero, ...]:
    """Retain expired decisions too; calculation determines their active slots."""
    latest = {}
    for version in versions:
        if version.effective_week.ordinal <= week.ordinal:
            latest[version.zero.zero_id] = version.zero
    return tuple(latest[key] for key in sorted(latest))

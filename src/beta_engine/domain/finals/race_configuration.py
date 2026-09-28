"""Season-scoped configuration authority for the canonical World Tour Finals Race."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class WorldTourFinalsRaceConfiguration(FrozenInput):
    """Immutable upstream choices required before a Finals Race may be built.

    The Race calculation itself lives in finals.race. This object freezes only
    the season-specific product choices and canonical source identities that the
    kernel must not guess: eligible tournament categories, Best-N, the selected
    published Official Ranking cutoff, the Run-owned Calendar and the configured
    Finals Edition.
    """

    schema_version: Literal["world_tour_finals_race_configuration.v1"] = (
        "world_tour_finals_race_configuration.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_season_index: int = Field(ge=0, le=49)
    finals_event_id: str = Field(min_length=1)
    eligible_categories: tuple[str, ...]
    best_n: int = Field(ge=1)
    cutoff_week: RankingWeek
    cutoff_official_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    cutoff_transition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calendar_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_id: Literal["world_tour_finals_race.v1"] = "world_tour_finals_race.v1"
    adopted_by_command_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_configuration(self) -> "WorldTourFinalsRaceConfiguration":
        if self.cutoff_week.season_index != self.target_season_index:
            raise ValueError("Finals Race cutoff must belong to the configured season")
        normalized = tuple(value.strip() for value in self.eligible_categories)
        if (
            not normalized
            or any(not value for value in normalized)
            or normalized != tuple(sorted(set(normalized)))
        ):
            raise ValueError(
                "Finals Race eligible categories must be unique, sorted and non-empty"
            )
        if normalized != self.eligible_categories:
            raise ValueError("Finals Race eligible categories must be normalized")
        return self

    @property
    def eligibility_fingerprint(self) -> str:
        """Identity of the frozen tournament-scope selection consumed by the kernel."""

        return _hash(
            {
                "run_id": self.run_id,
                "branch_id": self.branch_id,
                "target_season_index": self.target_season_index,
                "finals_event_id": self.finals_event_id,
                "eligible_categories": self.eligible_categories,
                "calendar_content_fingerprint": self.calendar_content_fingerprint,
            }
        )

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))

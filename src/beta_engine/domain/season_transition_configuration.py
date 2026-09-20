"""Season Transition policy/reset configuration for ordinary Week 61 -> Week 1.

This is a configuration candidate, not the transition commit itself.  It freezes the
supported incoming policy set against exact outgoing Week-61 authorities and carries
the explicit season-scoped reset registry used by the later atomic rollover writer.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.players.sporting import PlayerDevelopmentPolicy
from beta_engine.domain.rankings.official import (
    FrozenInput,
    OfficialRankingPolicy,
    RankingWeek,
)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class SeasonScopedResetCatalog(FrozenInput):
    """Explicit registry of authoritative season-scoped stores reset at rollover.

    The current canonical registry is empty because no resettable season-stat store is
    authoritative yet.  An empty registry means "reset nothing", never "invent zeros".
    """

    schema_version: Literal["season_scoped_reset_catalog.v1"] = (
        "season_scoped_reset_catalog.v1"
    )
    registry_version: Literal["season_scoped_reset_registry.v1"] = (
        "season_scoped_reset_registry.v1"
    )
    component_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_catalog(self):
        if list(self.component_ids) != sorted(set(self.component_ids)):
            raise ValueError(
                "Season-scoped reset catalog components must be canonical and unique"
            )
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class SeasonTransitionConfiguration(FrozenInput):
    """Immutable target-season configuration candidate bound to the current W61."""

    schema_version: Literal["season_transition_configuration.v1"] = (
        "season_transition_configuration.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    base_revision_id: str = Field(min_length=1)
    completed_week: RankingWeek
    target_week: RankingWeek
    predecessor_official_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_sporting_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    outgoing_ranking_policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_ranking_policy: OfficialRankingPolicy
    outgoing_development_policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_development_policy: PlayerDevelopmentPolicy
    reset_catalog: SeasonScopedResetCatalog = SeasonScopedResetCatalog()
    provenance: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_boundary(self):
        if self.completed_week.week != 61:
            raise ValueError("Season Transition configuration requires completed Week 61")
        if self.completed_week.season_index >= 49:
            raise ValueError(
                "Final season has no incoming Season Transition configuration"
            )
        if self.target_week != RankingWeek(
            season_index=self.completed_week.season_index + 1,
            week=1,
        ):
            raise ValueError(
                "Season Transition configuration target must be next season Week 1"
            )
        return self

    @property
    def ranking_policy_inherited(self) -> bool:
        return (
            _fingerprint(self.target_ranking_policy.model_dump(mode="json"))
            == self.outgoing_ranking_policy_fingerprint
        )

    @property
    def development_policy_inherited(self) -> bool:
        return (
            _fingerprint(self.target_development_policy.model_dump(mode="json"))
            == self.outgoing_development_policy_fingerprint
        )

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


def policy_fingerprint(policy: FrozenInput) -> str:
    return _fingerprint(policy.model_dump(mode="json"))

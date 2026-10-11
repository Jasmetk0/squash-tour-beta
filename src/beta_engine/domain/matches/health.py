"""Deterministic Health facts projected into one Match without numeric calibration."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.players.health import PlayerHealthProfile
from beta_engine.domain.rankings.official import FrozenInput


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class MatchHealthRecordProjection(FrozenInput):
    record_id: str = Field(min_length=1, max_length=160)
    kind: Literal["Injury", "Illness"]
    condition_key: str = Field(min_length=1, max_length=160)
    lifecycle: Literal["At Risk", "Active", "Recovering"]
    severity: int = Field(ge=0, le=100)
    affected_domains: tuple[str, ...] = Field(min_length=1)
    provenance: str = Field(min_length=1, max_length=1000)


class MatchPermanentHealthConsequenceProjection(FrozenInput):
    consequence_id: str = Field(min_length=1, max_length=160)
    source_record_id: str = Field(min_length=1, max_length=160)
    affected_domains: tuple[str, ...] = Field(min_length=1)
    limitation_severity: int = Field(ge=1, le=100)
    provenance: str = Field(min_length=1, max_length=1000)


class PlayerMatchHealthProjection(FrozenInput):
    """Current Health facts relevant to Match execution.

    The projection is intentionally descriptive. Master v72 decides that Health is a
    distinct Match input, while the exact limitation profiles/stacking mathematics
    remain calibration work. No numeric sporting penalty is invented here.
    """

    player_id: str = Field(min_length=1, max_length=160)
    current_records: tuple[MatchHealthRecordProjection, ...] = ()
    permanent_consequences: tuple[
        MatchPermanentHealthConsequenceProjection, ...
    ] = ()
    affected_domains: tuple[str, ...] = ()
    highest_current_severity: int = Field(ge=0, le=100)
    highest_permanent_limitation: int = Field(ge=0, le=100)
    numeric_effect_applied: Literal[False] = False
    numeric_calibration_required: bool

    @model_validator(mode="after")
    def canonical_projection(self):
        record_ids = tuple(item.record_id for item in self.current_records)
        if record_ids != tuple(sorted(set(record_ids))):
            raise ValueError("Match Health record projections must be sorted and unique")
        consequence_ids = tuple(
            item.consequence_id for item in self.permanent_consequences
        )
        if consequence_ids != tuple(sorted(set(consequence_ids))):
            raise ValueError(
                "Match Health permanent consequences must be sorted and unique"
            )
        if self.affected_domains != tuple(sorted(set(self.affected_domains))):
            raise ValueError("Match Health affected domains must be sorted and unique")
        expected_domains = tuple(
            sorted(
                {
                    domain
                    for item in (*self.current_records, *self.permanent_consequences)
                    for domain in item.affected_domains
                }
            )
        )
        if self.affected_domains != expected_domains:
            raise ValueError(
                "Match Health affected domains must derive from projected limitations"
            )
        if self.highest_current_severity != max(
            (item.severity for item in self.current_records), default=0
        ):
            raise ValueError("Match Health current Severity summary is inconsistent")
        if self.highest_permanent_limitation != max(
            (
                item.limitation_severity
                for item in self.permanent_consequences
            ),
            default=0,
        ):
            raise ValueError(
                "Match Health permanent limitation summary is inconsistent"
            )
        expected_calibration = bool(
            self.current_records or self.permanent_consequences
        )
        if self.numeric_calibration_required != expected_calibration:
            raise ValueError(
                "Match Health calibration flag must reflect projected limitations"
            )
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class EffectiveMatchHealthSnapshot(FrozenInput):
    """Hash-protected participant-ordered Health projection for one Match."""

    schema_version: Literal["effective_match_health.v1"] = (
        "effective_match_health.v1"
    )
    projection_version: Literal["health_limitation_projection.v1"] = (
        "health_limitation_projection.v1"
    )
    player_profiles: tuple[
        PlayerMatchHealthProjection, PlayerMatchHealthProjection
    ]
    numeric_effect_applied: Literal[False] = False
    unsupported_components: tuple[
        Literal[
            "numeric_limitation_effects",
            "health_check",
            "start_wo_ret_decision",
            "medical_timeout_effect",
        ],
        ...,
    ] = (
        "numeric_limitation_effects",
        "health_check",
        "start_wo_ret_decision",
        "medical_timeout_effect",
    )

    @model_validator(mode="after")
    def unique_players(self):
        ids = tuple(item.player_id for item in self.player_profiles)
        if len(set(ids)) != 2:
            raise ValueError("Match Health snapshot requires two unique participants")
        return self

    @classmethod
    def create_healthy(
        cls, *, player_a_id: str, player_b_id: str
    ) -> "EffectiveMatchHealthSnapshot":
        return cls(
            player_profiles=(
                PlayerMatchHealthProjection(
                    player_id=player_a_id,
                    highest_current_severity=0,
                    highest_permanent_limitation=0,
                    numeric_calibration_required=False,
                ),
                PlayerMatchHealthProjection(
                    player_id=player_b_id,
                    highest_current_severity=0,
                    highest_permanent_limitation=0,
                    numeric_calibration_required=False,
                ),
            )
        )

    @classmethod
    def from_profiles(
        cls,
        *,
        player_a: PlayerHealthProfile,
        player_b: PlayerHealthProfile,
    ) -> "EffectiveMatchHealthSnapshot":
        return cls(
            player_profiles=(
                project_player_health(player_a),
                project_player_health(player_b),
            )
        )

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


def project_player_health(profile: PlayerHealthProfile) -> PlayerMatchHealthProjection:
    current_records = tuple(
        MatchHealthRecordProjection(
            record_id=record.record_id,
            kind=record.kind,
            condition_key=record.condition_key,
            lifecycle=record.lifecycle,
            severity=record.severity,
            affected_domains=record.affected_domains,
            provenance=record.provenance,
        )
        for record in profile.records
        if record.lifecycle != "Recovered"
    )
    permanent = tuple(
        MatchPermanentHealthConsequenceProjection(
            consequence_id=item.consequence_id,
            source_record_id=item.source_record_id,
            affected_domains=item.affected_domains,
            limitation_severity=item.limitation_severity,
            provenance=item.provenance,
        )
        for item in profile.permanent_consequences
    )
    domains = tuple(
        sorted(
            {
                domain
                for item in (*current_records, *permanent)
                for domain in item.affected_domains
            }
        )
    )
    return PlayerMatchHealthProjection(
        player_id=profile.player_id,
        current_records=current_records,
        permanent_consequences=permanent,
        affected_domains=domains,
        highest_current_severity=max(
            (item.severity for item in current_records), default=0
        ),
        highest_permanent_limitation=max(
            (item.limitation_severity for item in permanent), default=0
        ),
        numeric_calibration_required=bool(current_records or permanent),
    )

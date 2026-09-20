"""Deterministic hidden sporting-profile kernel for generated prospects.

This module deliberately does not place a pre-Tour prospect into weekly sporting
state. It only turns already-owned prospect seeds into immutable, simulation-valid
sporting truth that a later explicit competitive/Tour-entry boundary may adopt.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.domain.players.attribute_catalog import (
    ATTRIBUTE_GROUPS,
    CANONICAL_PLAYER_ATTRIBUTES,
)


DevelopmentTiming = Literal["Early Bloomer", "Standard", "Late Bloomer"]


class ProspectSportingProfilePolicy(BaseModel):
    """Versioned pre-alpha calibration for prospect sporting generation."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["prospect_sporting_profile_policy.v1"] = (
        "prospect_sporting_profile_policy.v1"
    )
    policy_id: str = "prospect-sporting-profile.provisional.v1"
    base_ability_min: int = Field(default=55, ge=0, le=200)
    base_ability_max: int = Field(default=105, ge=0, le=200)
    group_jitter: int = Field(default=10, ge=0, le=50)
    attribute_jitter: int = Field(default=18, ge=0, le=50)
    potential_min: int = Field(default=110, ge=0, le=200)
    potential_max: int = Field(default=190, ge=0, le=200)
    provenance: str = (
        "Provisional deterministic pre-alpha calibration; numeric values are "
        "technical calibration, not product canon"
    )

    @model_validator(mode="after")
    def valid_ranges(self):
        if self.base_ability_min > self.base_ability_max:
            raise ValueError("Prospect base ability range is inverted")
        if self.potential_min > self.potential_max:
            raise ValueError("Prospect potential range is inverted")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class ProspectSportingProfile(BaseModel):
    """Immutable canonical 57-attribute profile prepared for one generated prospect."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["prospect_sporting_profile.v1"] = (
        "prospect_sporting_profile.v1"
    )
    player_id: str = Field(min_length=1)
    attributes: tuple[tuple[str, int], ...]
    potential_ovr: int = Field(ge=0, le=200)
    potential_identity: str = Field(min_length=1)
    potential_provenance: str = Field(min_length=1)
    development_timing: DevelopmentTiming
    profile_policy_id: str = Field(min_length=1)
    profile_policy_fingerprint: str = Field(min_length=1)
    source_profile_seed_digest: str = Field(min_length=1)
    source_development_seed_digest: str = Field(min_length=1)
    source_potential_seed_digest: str = Field(min_length=1)

    @model_validator(mode="after")
    def canonical_profile(self):
        names = tuple(name for name, _ in self.attributes)
        if names != CANONICAL_PLAYER_ATTRIBUTES:
            raise ValueError(
                "Prospect sporting profile requires exactly the canonical 57 attributes"
            )
        if any(
            type(value) is not int or not 0 <= value <= 200
            for _, value in self.attributes
        ):
            raise ValueError("Prospect canonical attributes must be integers from 0 through 200")
        if self.potential_ovr < self.ovr:
            raise ValueError("Prospect potential cannot be below generated current OVR")
        return self

    @property
    def ovr(self) -> int:
        return round(sum(value for _, value in self.attributes) / len(self.attributes))

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY = ProspectSportingProfilePolicy()


def materialize_prospect_sporting_profile(
    *,
    player_id: str,
    profile_seed: str,
    development_seed: str,
    potential_seed: str,
    policy: ProspectSportingProfilePolicy = DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY,
) -> ProspectSportingProfile:
    """Derive deterministic hidden profile truth without mutating world state."""

    for label, value in (
        ("player_id", player_id),
        ("profile_seed", profile_seed),
        ("development_seed", development_seed),
        ("potential_seed", potential_seed),
    ):
        if not value:
            raise ValueError(f"{label} must be non-empty")

    base = _roll(
        profile_seed,
        player_id,
        policy.policy_id,
        "base",
        lower=policy.base_ability_min,
        upper=policy.base_ability_max,
    )
    group_offsets = {
        group: _roll(
            profile_seed,
            player_id,
            policy.policy_id,
            "group",
            group,
            lower=-policy.group_jitter,
            upper=policy.group_jitter,
        )
        for group in ATTRIBUTE_GROUPS
    }

    attributes: list[tuple[str, int]] = []
    for group, names in ATTRIBUTE_GROUPS.items():
        for name in names:
            attribute_offset = _roll(
                profile_seed,
                player_id,
                policy.policy_id,
                "attribute",
                name,
                lower=-policy.attribute_jitter,
                upper=policy.attribute_jitter,
            )
            value = min(200, max(0, base + group_offsets[group] + attribute_offset))
            attributes.append((name, value))

    current_ovr = round(sum(value for _, value in attributes) / len(attributes))
    rolled_potential = _roll(
        potential_seed,
        player_id,
        policy.policy_id,
        "potential",
        lower=policy.potential_min,
        upper=policy.potential_max,
    )
    potential_ovr = max(current_ovr, rolled_potential)

    timings: tuple[DevelopmentTiming, ...] = (
        "Early Bloomer",
        "Standard",
        "Late Bloomer",
    )
    timing = timings[
        _roll(
            development_seed,
            player_id,
            policy.policy_id,
            "development-timing",
            lower=0,
            upper=len(timings) - 1,
        )
    ]

    profile_seed_digest = _seed_digest(profile_seed)
    development_seed_digest = _seed_digest(development_seed)
    potential_seed_digest = _seed_digest(potential_seed)
    potential_payload = {
        "schema_version": "prospect_potential_identity.v1",
        "player_id": player_id,
        "policy_id": policy.policy_id,
        "policy_fingerprint": policy.fingerprint,
        "potential_seed_digest": potential_seed_digest,
        "potential_ovr": potential_ovr,
    }
    potential_provenance = json.dumps(
        potential_payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return ProspectSportingProfile(
        player_id=player_id,
        attributes=tuple(attributes),
        potential_ovr=potential_ovr,
        potential_identity=hashlib.sha256(
            potential_provenance.encode("utf-8")
        ).hexdigest(),
        potential_provenance=potential_provenance,
        development_timing=timing,
        profile_policy_id=policy.policy_id,
        profile_policy_fingerprint=policy.fingerprint,
        source_profile_seed_digest=profile_seed_digest,
        source_development_seed_digest=development_seed_digest,
        source_potential_seed_digest=potential_seed_digest,
    )


def _seed_digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _roll(*parts: object, lower: int, upper: int) -> int:
    if lower > upper:
        raise ValueError("Deterministic roll range is inverted")
    payload = "|".join(str(part) for part in parts)
    width = upper - lower + 1
    raw = int.from_bytes(
        hashlib.blake2b(payload.encode("utf-8"), digest_size=8).digest(),
        "big",
    )
    return lower + raw % width


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

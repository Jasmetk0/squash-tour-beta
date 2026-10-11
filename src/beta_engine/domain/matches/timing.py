"""Historically captured match-timing rules and player restart profiles."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RestartIntent(str, Enum):
    """A player's intended tempo before the next serve is struck."""

    ACCELERATE = "ACCELERATE"
    NATURAL = "NATURAL"
    DELAY = "DELAY"


class RestartDecisionFactor(str, Enum):
    """Observable input that influenced a pre-alpha restart decision."""

    NATURAL_TENDENCY = "NATURAL_TENDENCY"
    PREVIOUS_RALLY_LOAD = "PREVIOUS_RALLY_LOAD"
    CLOSE_ENDGAME = "CLOSE_ENDGAME"


class PlayerRestartTimingProfile(BaseModel):
    """Stable match input for one player's serve and return restart tendencies."""

    player_id: str = Field(min_length=1)
    serve_tendency: RestartIntent = RestartIntent.NATURAL
    return_tendency: RestartIntent = RestartIntent.NATURAL


class MatchTimingOverride(BaseModel):
    """Optional Admin-facing timing values resolved before a match starts."""

    nominal_game_break_seconds: float | None = Field(default=None, gt=0)
    player_restart_profiles: tuple[PlayerRestartTimingProfile, ...] = ()

    @model_validator(mode="after")
    def validate_unique_players(self) -> MatchTimingOverride:
        player_ids = [profile.player_id for profile in self.player_restart_profiles]
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("match timing override contains duplicate player profiles")
        return self


class EffectiveMatchTimingSnapshot(BaseModel):
    """Hash-protected timing truth selected before match simulation."""

    schema_version: Literal["effective_match_timing.v1"] = "effective_match_timing.v1"
    nominal_game_break_seconds: float = Field(default=120.0, gt=0)
    player_restart_profiles: tuple[PlayerRestartTimingProfile, ...]
    between_rally_calibration_profile: Literal["pre_alpha_men_v1"] = "pre_alpha_men_v1"
    source_scope: Literal["official_default", "match_simulation_override"] = (
        "official_default"
    )
    source_key: str = Field(default="official:match-timing", min_length=1)
    snapshot_hash_algorithm: Literal["sha256"] = "sha256"
    snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        *,
        player_a_id: str,
        player_b_id: str,
        override: MatchTimingOverride | None = None,
    ) -> EffectiveMatchTimingSnapshot:
        profiles = {
            player_a_id: PlayerRestartTimingProfile(player_id=player_a_id),
            player_b_id: PlayerRestartTimingProfile(player_id=player_b_id),
        }
        if override is not None:
            for profile in override.player_restart_profiles:
                if profile.player_id not in profiles:
                    raise ValueError(
                        "match timing override profile must reference a match participant"
                    )
                profiles[profile.player_id] = profile
        ordered_profiles = (profiles[player_a_id], profiles[player_b_id])
        nominal_break = (
            override.nominal_game_break_seconds
            if override is not None and override.nominal_game_break_seconds is not None
            else 120.0
        )
        source_scope: Literal["official_default", "match_simulation_override"] = (
            "match_simulation_override"
            if override is not None
            and (
                override.nominal_game_break_seconds is not None
                or override.player_restart_profiles
            )
            else "official_default"
        )
        source_key = (
            "request:match-timing"
            if source_scope == "match_simulation_override"
            else "official:match-timing"
        )
        payload = cls._hash_payload(
            nominal_game_break_seconds=nominal_break,
            player_restart_profiles=ordered_profiles,
            between_rally_calibration_profile="pre_alpha_men_v1",
            source_scope=source_scope,
            source_key=source_key,
        )
        return cls(
            nominal_game_break_seconds=nominal_break,
            player_restart_profiles=ordered_profiles,
            source_scope=source_scope,
            source_key=source_key,
            snapshot_hash=cls._content_hash(payload),
        )

    @model_validator(mode="after")
    def validate_snapshot(self) -> EffectiveMatchTimingSnapshot:
        player_ids = [profile.player_id for profile in self.player_restart_profiles]
        if len(player_ids) != 2 or len(set(player_ids)) != 2:
            raise ValueError(
                "effective match timing requires exactly two distinct player profiles"
            )
        expected_hash = self._content_hash(
            self._hash_payload(
                nominal_game_break_seconds=self.nominal_game_break_seconds,
                player_restart_profiles=self.player_restart_profiles,
                between_rally_calibration_profile=(
                    self.between_rally_calibration_profile
                ),
                source_scope=self.source_scope,
                source_key=self.source_key,
            )
        )
        if self.snapshot_hash != expected_hash:
            raise ValueError("effective match timing snapshot hash mismatch")
        return self

    def profile_for(self, player_id: str) -> PlayerRestartTimingProfile:
        for profile in self.player_restart_profiles:
            if profile.player_id == player_id:
                return profile
        raise ValueError(
            f"effective match timing has no profile for participant '{player_id}'"
        )

    @staticmethod
    def _hash_payload(
        *,
        nominal_game_break_seconds: float,
        player_restart_profiles: tuple[PlayerRestartTimingProfile, ...],
        between_rally_calibration_profile: str,
        source_scope: str,
        source_key: str,
    ) -> dict[str, object]:
        return {
            "schema_version": "effective_match_timing.v1",
            "nominal_game_break_seconds": nominal_game_break_seconds,
            "player_restart_profiles": [
                profile.model_dump(mode="json") for profile in player_restart_profiles
            ],
            "between_rally_calibration_profile": (between_rally_calibration_profile),
            "source_scope": source_scope,
            "source_key": source_key,
        }

    @staticmethod
    def _content_hash(payload: dict[str, object]) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

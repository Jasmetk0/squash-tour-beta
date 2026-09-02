"""Hash-protected inputs captured immediately before match simulation."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from beta_engine.domain.matches.formats import EffectiveMatchFormatSnapshot
from beta_engine.domain.matches.models import MatchContext
from beta_engine.domain.matches.stamina import EffectiveMatchStaminaSnapshot
from beta_engine.domain.matches.timing import EffectiveMatchTimingSnapshot


class MatchInputSnapshot(BaseModel):
    """Immutable current-engine truth needed to reproduce one simulated match."""

    schema_version: Literal[
        "match_input_snapshot.v1",
        "match_input_snapshot.v2",
        "match_input_snapshot.v3",
        "match_input_snapshot.v4",
    ] = "match_input_snapshot.v4"
    match_id: str = Field(min_length=1)
    simulation_seed: int
    match_engine_version: str = Field(min_length=1)
    effective_match_format: EffectiveMatchFormatSnapshot
    effective_match_timing: EffectiveMatchTimingSnapshot | None = None
    effective_match_stamina: EffectiveMatchStaminaSnapshot | None = None
    context: MatchContext
    unsupported_future_inputs: tuple[
        Literal[
            "active_gameplans",
            "rally_model_configuration",
            "rally_seed_stream",
        ],
        ...,
    ] = ("active_gameplans",)
    snapshot_hash_algorithm: Literal["sha256"] = "sha256"
    snapshot_hash: str

    @classmethod
    def create(
        cls,
        *,
        context: MatchContext,
        effective_match_format: EffectiveMatchFormatSnapshot,
        simulation_seed: int,
        match_engine_version: str,
        effective_match_timing: EffectiveMatchTimingSnapshot | None = None,
        effective_match_stamina: EffectiveMatchStaminaSnapshot | None = None,
    ) -> MatchInputSnapshot:
        timing = effective_match_timing or EffectiveMatchTimingSnapshot.create(
            player_a_id=context.player_a.player.player_id,
            player_b_id=context.player_b.player.player_id,
        )
        stamina = effective_match_stamina or EffectiveMatchStaminaSnapshot.create(
            context=context
        )
        payload = cls._hash_payload(
            schema_version="match_input_snapshot.v4",
            match_id=context.match_id,
            simulation_seed=simulation_seed,
            match_engine_version=match_engine_version,
            effective_match_format=effective_match_format,
            effective_match_timing=timing,
            effective_match_stamina=stamina,
            context=context,
            unsupported_future_inputs=("active_gameplans",),
        )
        return cls(
            match_id=context.match_id,
            simulation_seed=simulation_seed,
            match_engine_version=match_engine_version,
            effective_match_format=effective_match_format,
            effective_match_timing=timing,
            effective_match_stamina=stamina,
            context=context,
            snapshot_hash=cls._content_hash(payload),
        )

    @model_validator(mode="after")
    def validate_snapshot(self) -> MatchInputSnapshot:
        if self.context.match_id != self.match_id:
            raise ValueError("match input snapshot has mismatched match identity")
        expected_format = self.effective_match_format.format
        if (
            self.context.best_of,
            self.context.games_to,
            self.context.win_by,
        ) != (
            expected_format.best_of,
            expected_format.games_to,
            expected_format.win_by,
        ):
            raise ValueError(
                "match input context does not match effective format snapshot"
            )
        if self.schema_version in {"match_input_snapshot.v3", "match_input_snapshot.v4"}:
            if self.effective_match_timing is None:
                raise ValueError(
                    "v3+ match input snapshot requires effective match timing"
                )
            timing_player_ids = {
                profile.player_id
                for profile in self.effective_match_timing.player_restart_profiles
            }
            context_player_ids = {
                self.context.player_a.player.player_id,
                self.context.player_b.player.player_id,
            }
            if timing_player_ids != context_player_ids:
                raise ValueError(
                    "effective match timing does not match snapshot participants"
                )
        elif self.effective_match_timing is not None:
            raise ValueError(
                "legacy match input snapshot cannot contain unprotected timing data"
            )
        if self.schema_version == "match_input_snapshot.v4":
            if self.effective_match_stamina is None:
                raise ValueError("v4 match input snapshot requires effective stamina")
            stamina_player_ids = tuple(
                profile.player_id
                for profile in self.effective_match_stamina.player_profiles
            )
            context_player_ids = (
                self.context.player_a.player.player_id,
                self.context.player_b.player.player_id,
            )
            if stamina_player_ids != context_player_ids:
                raise ValueError(
                    "effective match stamina does not match snapshot participants"
                )
        elif self.effective_match_stamina is not None:
            raise ValueError(
                "legacy match input snapshot cannot contain unprotected stamina data"
            )
        expected_hash = self._content_hash(
            self._hash_payload(
                schema_version=self.schema_version,
                match_id=self.match_id,
                simulation_seed=self.simulation_seed,
                match_engine_version=self.match_engine_version,
                effective_match_format=self.effective_match_format,
                effective_match_timing=self.effective_match_timing,
                effective_match_stamina=self.effective_match_stamina,
                context=self.context,
                unsupported_future_inputs=self.unsupported_future_inputs,
            )
        )
        if self.snapshot_hash != expected_hash:
            raise ValueError("match input snapshot hash mismatch")
        return self

    @staticmethod
    def _hash_payload(
        *,
        schema_version: str,
        match_id: str,
        simulation_seed: int,
        match_engine_version: str,
        effective_match_format: EffectiveMatchFormatSnapshot,
        effective_match_timing: EffectiveMatchTimingSnapshot | None = None,
        effective_match_stamina: EffectiveMatchStaminaSnapshot | None = None,
        context: MatchContext,
        unsupported_future_inputs: tuple[str, ...],
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": schema_version,
            "match_id": match_id,
            "simulation_seed": simulation_seed,
            "match_engine_version": match_engine_version,
            "effective_match_format": effective_match_format.model_dump(mode="json"),
            "context": context.model_dump(mode="json"),
            "unsupported_future_inputs": unsupported_future_inputs,
        }
        if schema_version in {"match_input_snapshot.v3", "match_input_snapshot.v4"}:
            payload["effective_match_timing"] = (
                effective_match_timing.model_dump(mode="json")
                if effective_match_timing is not None
                else None
            )
        if schema_version == "match_input_snapshot.v4":
            payload["effective_match_stamina"] = (
                effective_match_stamina.model_dump(mode="json")
                if effective_match_stamina is not None
                else None
            )
        return payload

    @staticmethod
    def _content_hash(payload: dict[str, object]) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

"""Canonical Run/Branch-owned player Health V1 state.

This module defines historical health facts and deterministic carry-forward only.
It deliberately does not choose PAQ-155 probabilities, healing curves, detection
rates, or stochastic Health Check calibration.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek

HealthKind = Literal["Injury", "Illness"]
HealthLifecycle = Literal["At Risk", "Active", "Recovering", "Recovered"]


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class PermanentHealthConsequence(FrozenInput):
    """Persistent post-recovery limitation kept separate from the acute record."""

    consequence_id: str = Field(min_length=1, max_length=160)
    source_record_id: str = Field(min_length=1, max_length=160)
    affected_domains: tuple[str, ...] = Field(min_length=1)
    limitation_severity: int = Field(ge=1, le=100)
    provenance: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def canonical_domains(self):
        if self.affected_domains != tuple(sorted(set(self.affected_domains))):
            raise ValueError(
                "Permanent health consequence domains must be sorted and unique"
            )
        return self


class PlayerHealthRecord(FrozenInput):
    """One independent Injury/Illness history item.

    started_before_run permits explicit pre-start history without fabricating a
    simulated pre-Week-1 timeline.
    """

    record_id: str = Field(min_length=1, max_length=160)
    kind: HealthKind
    condition_key: str = Field(min_length=1, max_length=160)
    lifecycle: HealthLifecycle
    severity: int = Field(ge=0, le=100)
    affected_domains: tuple[str, ...] = Field(min_length=1)
    onset_week: RankingWeek | None = None
    recovered_week: RankingWeek | None = None
    started_before_run: bool = False
    recurrence_of_record_id: str | None = Field(default=None, min_length=1, max_length=160)
    recovery_window_min_weeks: int | None = Field(default=None, ge=0, le=520)
    recovery_window_max_weeks: int | None = Field(default=None, ge=0, le=520)
    provenance: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_record(self):
        if self.affected_domains != tuple(sorted(set(self.affected_domains))):
            raise ValueError("Health record domains must be sorted and unique")
        if (self.onset_week is None) != self.started_before_run:
            raise ValueError(
                "Health record without onset_week must be explicitly marked started_before_run"
            )
        if self.lifecycle == "Recovered":
            if not self.started_before_run and self.recovered_week is None:
                raise ValueError("Recovered in-Run health record requires recovered_week")
        elif self.recovered_week is not None:
            raise ValueError("Only Recovered health records may have recovered_week")
        if (
            self.recovery_window_min_weeks is None
        ) != (self.recovery_window_max_weeks is None):
            raise ValueError("Recovery window requires both min and max")
        if (
            self.recovery_window_min_weeks is not None
            and self.recovery_window_max_weeks is not None
            and self.recovery_window_min_weeks > self.recovery_window_max_weeks
        ):
            raise ValueError("Recovery window minimum cannot exceed maximum")
        if (
            self.onset_week is not None
            and self.recovered_week is not None
            and self.recovered_week.ordinal < self.onset_week.ordinal
        ):
            raise ValueError("Recovered week cannot precede onset week")
        return self


class PlayerHealthProfile(FrozenInput):
    """Complete current health truth for one player at one weekly boundary."""

    player_id: str = Field(min_length=1, max_length=160)
    records: tuple[PlayerHealthRecord, ...] = ()
    permanent_consequences: tuple[PermanentHealthConsequence, ...] = ()

    @model_validator(mode="after")
    def validate_history(self):
        record_ids = tuple(record.record_id for record in self.records)
        if record_ids != tuple(sorted(set(record_ids))):
            raise ValueError("Health record IDs must be sorted and unique")

        record_by_id = {record.record_id: record for record in self.records}
        for record in self.records:
            if record.recurrence_of_record_id is None:
                continue
            source = record_by_id.get(record.recurrence_of_record_id)
            if source is None:
                raise ValueError("Health recurrence references unknown source record")
            if source.record_id >= record.record_id:
                raise ValueError(
                    "Health recurrence source must precede the recurrent record in canonical order"
                )
            if source.kind != record.kind:
                raise ValueError("Health recurrence cannot cross Injury/Illness kind")

        consequence_ids = tuple(
            consequence.consequence_id for consequence in self.permanent_consequences
        )
        if consequence_ids != tuple(sorted(set(consequence_ids))):
            raise ValueError("Permanent consequence IDs must be sorted and unique")
        for consequence in self.permanent_consequences:
            source = record_by_id.get(consequence.source_record_id)
            if source is None:
                raise ValueError(
                    "Permanent consequence references unknown health record"
                )
            if source.lifecycle != "Recovered":
                raise ValueError(
                    "Permanent consequence requires a Recovered source health record"
                )
        return self

    @property
    def active_records(self) -> tuple[PlayerHealthRecord, ...]:
        return tuple(
            record
            for record in self.records
            if record.lifecycle in {"At Risk", "Active", "Recovering"}
        )


class PlayerHealthWeekState(FrozenInput):
    """Immutable Run/Branch/week health authority."""

    schema_version: Literal["player_health_week_state.v1"] = (
        "player_health_week_state.v1"
    )
    run_id: str = Field(min_length=1, max_length=128)
    branch_id: str = Field(min_length=1, max_length=128)
    week: RankingWeek
    players: tuple[PlayerHealthProfile, ...]
    source_initial_world_fingerprint: str = Field(min_length=1)
    predecessor_fingerprint: str | None = None
    stage_provenance: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def canonical_players(self):
        player_ids = tuple(player.player_id for player in self.players)
        if player_ids != tuple(sorted(set(player_ids))):
            raise ValueError("Health players require sorted unique identities")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


def bootstrap_health_state(
    *,
    run_id: str,
    branch_id: str,
    source_initial_world_fingerprint: str,
    player_ids: tuple[str, ...],
) -> PlayerHealthWeekState:
    """Create explicit fresh Week-1 health truth without fabricating pre-history."""

    canonical = tuple(sorted(set(player_ids)))
    if len(canonical) != len(player_ids):
        raise ValueError("Health bootstrap player IDs must be unique")
    return PlayerHealthWeekState(
        run_id=run_id,
        branch_id=branch_id,
        week=RankingWeek(season_index=0, week=1),
        players=tuple(PlayerHealthProfile(player_id=player_id) for player_id in canonical),
        source_initial_world_fingerprint=source_initial_world_fingerprint,
        stage_provenance="player_health_bootstrap.v1:fresh-unless-explicit-history",
    )


def carry_health_state_forward(
    predecessor: PlayerHealthWeekState,
    *,
    target: RankingWeek,
    target_player_ids: tuple[str, ...],
) -> PlayerHealthWeekState:
    """Carry health truth across a weekly boundary with no invented Health Check.

    New lifecycle identities receive an empty profile. Existing records and permanent
    consequences remain unchanged. A later calibrated Health Check can replace this
    no-op facts transition while preserving this historical state contract.
    """

    if target.ordinal != predecessor.week.ordinal + 1:
        raise ValueError("Health carry-forward requires consecutive weeks")
    canonical_target = tuple(sorted(set(target_player_ids)))
    if len(canonical_target) != len(target_player_ids):
        raise ValueError("Health target player IDs must be unique")

    previous = {player.player_id: player for player in predecessor.players}
    missing = sorted(set(previous) - set(canonical_target))
    if missing:
        raise ValueError(
            "Health carry-forward cannot silently drop lifecycle identities: "
            + ",".join(missing)
        )
    players = tuple(
        previous.get(player_id, PlayerHealthProfile(player_id=player_id))
        for player_id in canonical_target
    )
    return PlayerHealthWeekState(
        run_id=predecessor.run_id,
        branch_id=predecessor.branch_id,
        week=target,
        players=players,
        source_initial_world_fingerprint=predecessor.source_initial_world_fingerprint,
        predecessor_fingerprint=predecessor.fingerprint,
        stage_provenance=(
            "player_health_carry_forward.v1:no-stochastic-health-check;"
            "new-lifecycle-identities-start-empty"
        ),
    )

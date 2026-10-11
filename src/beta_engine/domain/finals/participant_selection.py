"""Canonical World Tour Finals participant selection and entry seeding."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.finals.race import WorldTourFinalsRaceSnapshot
from beta_engine.domain.rankings.official import FrozenInput


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
    ).hexdigest()


class WorldTourFinalsParticipantSelectionConfiguration(FrozenInput):
    """Immutable Finals Edition choices needed to turn Race into entrants."""

    schema_version: Literal[
        "world_tour_finals_participant_selection_configuration.v1"
    ] = "world_tour_finals_participant_selection_configuration.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_season_index: int = Field(ge=0, le=49)
    finals_event_id: str = Field(min_length=1)
    participant_capacity: int = Field(ge=1, le=128)
    direct_entry_event_ids: tuple[str, ...] = ()
    race_snapshot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calendar_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    adopted_by_command_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_configuration(
        self,
    ) -> "WorldTourFinalsParticipantSelectionConfiguration":
        normalized = tuple(value.strip() for value in self.direct_entry_event_ids)
        if any(not value for value in normalized):
            raise ValueError("Finals direct-entry event IDs cannot be empty")
        if normalized != tuple(sorted(set(normalized))):
            raise ValueError(
                "Finals direct-entry event IDs must be unique, sorted and normalized"
            )
        if normalized != self.direct_entry_event_ids:
            raise ValueError("Finals direct-entry event IDs must be normalized")
        if len(self.direct_entry_event_ids) >= self.participant_capacity:
            raise ValueError(
                "Possible distinct Finals direct entries must be strictly below capacity"
            )
        if self.finals_event_id in self.direct_entry_event_ids:
            raise ValueError("Finals Edition cannot grant its own direct entry")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


class WorldTourFinalsSelectedPlayer(FrozenInput):
    player_id: str = Field(min_length=1)
    race_rank: int = Field(ge=1)
    race_points: int = Field(ge=0)
    seed: int = Field(ge=1)
    qualification_source: Literal["direct_entry", "race"]
    direct_entry_event_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_source(self) -> "WorldTourFinalsSelectedPlayer":
        if self.qualification_source == "direct_entry":
            if not self.direct_entry_event_ids:
                raise ValueError(
                    "Direct-entry Finals participant requires source event evidence"
                )
        elif self.direct_entry_event_ids:
            raise ValueError(
                "Race-qualified Finals participant cannot carry direct-entry events"
            )
        if self.direct_entry_event_ids != tuple(
            sorted(set(self.direct_entry_event_ids))
        ):
            raise ValueError(
                "Finals direct-entry source events must be unique and sorted"
            )
        return self


class WorldTourFinalsParticipantSelectionSnapshot(FrozenInput):
    """Immutable initial Finals field selected from direct entries + frozen Race."""

    schema_version: Literal[
        "world_tour_finals_participant_selection_snapshot.v1"
    ] = "world_tour_finals_participant_selection_snapshot.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_season_index: int = Field(ge=0, le=49)
    finals_event_id: str = Field(min_length=1)
    participant_capacity: int = Field(ge=1, le=128)
    configuration_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    race_snapshot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    direct_entry_winner_event_ids: tuple[str, ...]
    participants: tuple[WorldTourFinalsSelectedPlayer, ...]

    @model_validator(mode="after")
    def validate_snapshot(self) -> "WorldTourFinalsParticipantSelectionSnapshot":
        if len(self.participants) != self.participant_capacity:
            raise ValueError(
                "Finals participant selection must exactly fill configured capacity"
            )
        player_ids = tuple(player.player_id for player in self.participants)
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("Finals participant selection has duplicate players")
        if tuple(player.seed for player in self.participants) != tuple(
            range(1, self.participant_capacity + 1)
        ):
            raise ValueError("Finals participant seeds must be contiguous and ordered")
        if tuple(player.race_rank for player in self.participants) != tuple(
            sorted(player.race_rank for player in self.participants)
        ):
            raise ValueError("Finals participants must be ordered by final Race")
        if self.direct_entry_winner_event_ids != tuple(
            sorted(set(self.direct_entry_winner_event_ids))
        ):
            raise ValueError(
                "Finals resolved direct-entry event IDs must be unique and sorted"
            )
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


def select_world_tour_finals_participants(
    *,
    configuration: WorldTourFinalsParticipantSelectionConfiguration,
    race_snapshot: WorldTourFinalsRaceSnapshot,
    direct_entry_winners: tuple[tuple[str, str], ...],
) -> WorldTourFinalsParticipantSelectionSnapshot:
    """Select and seed the initial Finals field without legacy Race semantics.

    direct_entry_winners contains one (event_id, champion_player_id) pair for every
    configured direct-entry event. Multiple selected events won by one player still
    create exactly one direct entrant. Remaining capacity is filled in frozen Race
    order. All seeds are then assigned solely by Race order among the selected field.
    """

    if (
        race_snapshot.run_id,
        race_snapshot.branch_id,
        race_snapshot.target_season_index,
        race_snapshot.fingerprint,
    ) != (
        configuration.run_id,
        configuration.branch_id,
        configuration.target_season_index,
        configuration.race_snapshot_fingerprint,
    ):
        raise ValueError("Finals participant selection Race snapshot mismatch")

    expected_events = configuration.direct_entry_event_ids
    winner_events = tuple(event_id for event_id, _ in direct_entry_winners)
    if winner_events != tuple(sorted(set(winner_events))):
        raise ValueError(
            "Finals direct-entry winner evidence must be unique and sorted by event"
        )
    if winner_events != expected_events:
        raise ValueError(
            "Finals direct-entry winner evidence does not match configured events"
        )

    race_by_player = {row.player_id: row for row in race_snapshot.rows}
    direct_events_by_player: dict[str, list[str]] = {}
    for event_id, player_id in direct_entry_winners:
        if player_id not in race_by_player:
            raise ValueError(
                "Finals direct-entry winner is absent from frozen Race snapshot"
            )
        direct_events_by_player.setdefault(player_id, []).append(event_id)

    direct_player_ids = set(direct_events_by_player)
    selected_ids: set[str] = set(direct_player_ids)
    for row in race_snapshot.rows:
        if len(selected_ids) >= configuration.participant_capacity:
            break
        selected_ids.add(row.player_id)

    if len(selected_ids) != configuration.participant_capacity:
        raise ValueError(
            "Frozen Finals Race does not contain enough players to fill capacity"
        )

    selected_rows = [
        row for row in race_snapshot.rows if row.player_id in selected_ids
    ]
    if len(selected_rows) != configuration.participant_capacity:
        raise ValueError("Finals participant selection Race evidence is incomplete")

    participants = tuple(
        WorldTourFinalsSelectedPlayer(
            player_id=row.player_id,
            race_rank=row.rank,
            race_points=row.race_points,
            seed=index,
            qualification_source=(
                "direct_entry"
                if row.player_id in direct_player_ids
                else "race"
            ),
            direct_entry_event_ids=tuple(
                sorted(direct_events_by_player.get(row.player_id, ()))
            ),
        )
        for index, row in enumerate(selected_rows, start=1)
    )
    return WorldTourFinalsParticipantSelectionSnapshot(
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        target_season_index=configuration.target_season_index,
        finals_event_id=configuration.finals_event_id,
        participant_capacity=configuration.participant_capacity,
        configuration_fingerprint=configuration.fingerprint,
        race_snapshot_fingerprint=race_snapshot.fingerprint,
        direct_entry_winner_event_ids=winner_events,
        participants=participants,
    )

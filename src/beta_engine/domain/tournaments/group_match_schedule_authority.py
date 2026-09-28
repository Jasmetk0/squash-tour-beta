"""Immutable group Match + Match Day schedule authority.

The topology freezes who is in each group and every round-robin pairing. This layer
materializes those pairings as executable match contracts with effective BO3/BO5
format and deterministic conflict-free Match Day chronology. It deliberately does
not calculate standings or hybrid knockout entrants.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.matches.formats import (
    EffectiveMatchFormatSnapshot,
    MatchFormat,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.format_authority import TournamentFormatAuthority
from beta_engine.domain.tournaments.topology_authority import (
    TournamentGroupTopologyMatch,
    TournamentTopologyAuthority,
)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentGroupScheduledMatch(FrozenInput):
    """One frozen group match with sporting format and Match Day chronology."""

    match_id: str = Field(min_length=1)
    group_index: int = Field(ge=1, le=64)
    topology_match_index: int = Field(ge=1)
    match_day_ordinal: int = Field(ge=1)
    match_order: int = Field(ge=1)
    top_slot_index: int = Field(ge=1)
    bottom_slot_index: int = Field(ge=1)
    top_player_id: str = Field(min_length=1)
    bottom_player_id: str = Field(min_length=1)
    effective_match_format: EffectiveMatchFormatSnapshot

    @model_validator(mode="after")
    def validate_pair(self) -> "TournamentGroupScheduledMatch":
        if self.top_slot_index >= self.bottom_slot_index:
            raise ValueError(
                "Scheduled group match slots must use canonical ascending pair order"
            )
        if self.top_player_id == self.bottom_player_id:
            raise ValueError("Scheduled group match cannot pair one player with itself")
        return self


class TournamentGroupMatchScheduleAuthority(FrozenInput):
    """Immutable executable group-stage match/schedule contract for one Edition."""

    schema_version: Literal["tournament_group_match_schedule_authority.v1"] = (
        "tournament_group_match_schedule_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    generated_by_command_id: str = Field(min_length=1, max_length=128)
    format_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    topology_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    group_rules_policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    schedule_policy_id: Literal["round_robin_circle.v1"] = "round_robin_circle.v1"
    group_count: int = Field(ge=1, le=64)
    group_size: int = Field(ge=2, le=128)
    match_day_count: int = Field(ge=1)
    matches: tuple[TournamentGroupScheduledMatch, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_schedule(self) -> "TournamentGroupMatchScheduleAuthority":
        expected_matches = self.group_count * self.group_size * (self.group_size - 1) // 2
        if len(self.matches) != expected_matches:
            raise ValueError(
                "Group Match Schedule must contain every round-robin pairing exactly once"
            )
        ids = tuple(match.match_id for match in self.matches)
        if len(ids) != len(set(ids)):
            raise ValueError("Group Match Schedule contains duplicate match identity")

        expected_days = self.group_size - 1 if self.group_size % 2 == 0 else self.group_size
        if self.match_day_count != expected_days:
            raise ValueError("Group Match Schedule has non-canonical Match Day count")
        days = tuple(sorted({match.match_day_ordinal for match in self.matches}))
        if days != tuple(range(1, self.match_day_count + 1)):
            raise ValueError("Group Match Day ordinals must be contiguous from one")

        for day in days:
            day_matches = tuple(
                match for match in self.matches if match.match_day_ordinal == day
            )
            orders = tuple(sorted(match.match_order for match in day_matches))
            if orders != tuple(range(1, len(day_matches) + 1)):
                raise ValueError(
                    f"Group Match Day {day} match order must be contiguous from one"
                )
            seen_players: set[str] = set()
            for match in day_matches:
                for player_id in (match.top_player_id, match.bottom_player_id):
                    if player_id in seen_players:
                        raise ValueError(
                            "One player cannot play twice on the same group Match Day"
                        )
                    seen_players.add(player_id)
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TournamentGroupMatchScheduleBuilder:
    """Materialize a canonical minimal-day round robin from frozen topology."""

    @staticmethod
    def build(
        *,
        format_authority: TournamentFormatAuthority,
        topology_authority: TournamentTopologyAuthority,
        command_id: str,
    ) -> TournamentGroupMatchScheduleAuthority:
        if format_authority.format_kind not in {"groups", "groups_knockout"}:
            raise ValueError("Group Match Schedule requires group-based Format authority")
        group = format_authority.group_configuration
        assert group is not None
        if topology_authority.format_kind != format_authority.format_kind:
            raise ValueError("Tournament Topology format kind differs from Format authority")
        if (
            topology_authority.run_id,
            topology_authority.branch_id,
            topology_authority.event_id,
            topology_authority.format_authority_fingerprint,
        ) != (
            format_authority.run_id,
            format_authority.branch_id,
            format_authority.event_id,
            format_authority.fingerprint,
        ):
            raise ValueError("Tournament Topology is stale for Format authority")

        topology_by_pair: dict[
            tuple[int, int, int], TournamentGroupTopologyMatch
        ] = {}
        for match in topology_authority.group_matches:
            key = (
                match.group_index,
                match.top_slot_index,
                match.bottom_slot_index,
            )
            if key in topology_by_pair:
                raise ValueError("Tournament Topology contains duplicate group pairing")
            topology_by_pair[key] = match

        format_snapshot = TournamentGroupMatchScheduleBuilder._match_format(
            format_authority
        )
        scheduled: list[TournamentGroupScheduledMatch] = []
        order_by_day = {
            day: 0
            for day in range(
                1,
                (group.group_size - 1 if group.group_size % 2 == 0 else group.group_size)
                + 1,
            )
        }

        for group_index in range(1, group.group_count + 1):
            slots = tuple(range(1, group.group_size + 1))
            for day, pairs in enumerate(
                TournamentGroupMatchScheduleBuilder._round_robin_rounds(slots),
                start=1,
            ):
                for first_slot, second_slot in pairs:
                    top_slot, bottom_slot = sorted((first_slot, second_slot))
                    topology_match = topology_by_pair.get(
                        (group_index, top_slot, bottom_slot)
                    )
                    if topology_match is None:
                        raise ValueError(
                            "Tournament Topology is missing canonical group pairing"
                        )
                    order_by_day[day] += 1
                    scheduled.append(
                        TournamentGroupScheduledMatch(
                            match_id=topology_match.match_id,
                            group_index=group_index,
                            topology_match_index=topology_match.match_index,
                            match_day_ordinal=day,
                            match_order=order_by_day[day],
                            top_slot_index=topology_match.top_slot_index,
                            bottom_slot_index=topology_match.bottom_slot_index,
                            top_player_id=topology_match.top_player_id,
                            bottom_player_id=topology_match.bottom_player_id,
                            effective_match_format=format_snapshot,
                        )
                    )

        expected_ids = {match.match_id for match in topology_authority.group_matches}
        if {match.match_id for match in scheduled} != expected_ids:
            raise ValueError(
                "Group Match Schedule does not exactly cover Tournament Topology matches"
            )

        return TournamentGroupMatchScheduleAuthority(
            run_id=format_authority.run_id,
            branch_id=format_authority.branch_id,
            event_id=format_authority.event_id,
            generated_by_command_id=command_id,
            format_authority_fingerprint=format_authority.fingerprint,
            topology_authority_fingerprint=topology_authority.fingerprint,
            group_rules_policy_fingerprint=group.group_rules_policy_fingerprint,
            group_count=group.group_count,
            group_size=group.group_size,
            match_day_count=(
                group.group_size - 1
                if group.group_size % 2 == 0
                else group.group_size
            ),
            matches=tuple(
                sorted(
                    scheduled,
                    key=lambda match: (
                        match.match_day_ordinal,
                        match.match_order,
                    ),
                )
            ),
        )

    @staticmethod
    def _match_format(
        format_authority: TournamentFormatAuthority,
    ) -> EffectiveMatchFormatSnapshot:
        group = format_authority.group_configuration
        assert group is not None
        if group.rules_source_kind == "season_policy":
            return EffectiveMatchFormatSnapshot.create(
                format=MatchFormat(
                    best_of=group.match_best_of,
                    games_to=11,
                    win_by=2,
                ),
                source_scope="tournament_group_rules_policy",
                source_key=(
                    "group-rules-policy:"
                    f"{group.group_rules_policy_fingerprint}"
                ),
            )
        return EffectiveMatchFormatSnapshot.create(
            format=MatchFormat(
                best_of=group.match_best_of,
                games_to=11,
                win_by=2,
            ),
            source_scope="tournament_group_edition_override",
            source_key=f"tournament-format:{format_authority.fingerprint}",
        )

    @staticmethod
    def _round_robin_rounds(
        slots: tuple[int, ...],
    ) -> tuple[tuple[tuple[int, int], ...], ...]:
        """Return circle-method rounds with no participant repeated within a round."""

        values: list[int | None] = list(slots)
        if len(values) % 2:
            values.append(None)
        rounds: list[tuple[tuple[int, int], ...]] = []
        for _ in range(len(values) - 1):
            pairs: list[tuple[int, int]] = []
            half = len(values) // 2
            for index in range(half):
                left = values[index]
                right = values[-(index + 1)]
                if left is None or right is None:
                    continue
                pairs.append((left, right))
            rounds.append(tuple(pairs))
            values = [values[0], values[-1], *values[1:-1]]
        return tuple(rounds)

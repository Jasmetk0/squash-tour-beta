"""Season-versioned tournament-format and shared group-rules authorities.

These contracts implement only decisions that are explicit in Master Vision v68.
General group seed placement and hybrid crossing are therefore stored as explicit
configuration; this module does not invent an automatic universal mapping.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput


TournamentFormatKind = Literal["knockout", "groups", "groups_knockout"]
TournamentGroupRulesSourceKind = Literal["season_policy", "edition_override"]
TournamentGroupMatchBestOf = Literal[3, 5]


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentGroupRulesPolicy(FrozenInput):
    """One immutable Run/Branch group-rules version effective from a season."""

    schema_version: Literal["tournament_group_rules_policy.v1"] = (
        "tournament_group_rules_policy.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    effective_from_season_index: int = Field(ge=0, le=49)
    default_match_best_of: TournamentGroupMatchBestOf = 5
    scoring_policy_id: Literal["master_group_table_points.v1"] = (
        "master_group_table_points.v1"
    )
    tie_break_policy_id: Literal[
        "wins_points_h2h_ratios_admin_unresolved.v1"
    ] = "wins_points_h2h_ratios_admin_unresolved.v1"
    walkover_policy_id: Literal[
        "group_wo_win_max_points_no_fabricated_ratios.v1"
    ] = "group_wo_win_max_points_no_fabricated_ratios.v1"
    adopted_by_command_id: str = Field(min_length=1, max_length=128)

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TournamentGroupSeedPlacement(FrozenInput):
    """Explicit placement of one seed into a group slot."""

    seed_number: int = Field(ge=1, le=128)
    group_index: int = Field(ge=1, le=64)
    slot_index: int = Field(ge=1, le=128)


class TournamentGroupCrossingSource(FrozenInput):
    """One post-group source identified only by achieved group position."""

    group_index: int = Field(ge=1, le=64)
    finishing_position: int = Field(ge=1, le=128)


class TournamentGroupCrossingMatch(FrozenInput):
    """Explicit first knockout round crossing for a hybrid format."""

    match_index: int = Field(ge=1, le=64)
    top: TournamentGroupCrossingSource
    bottom: TournamentGroupCrossingSource

    @model_validator(mode="after")
    def validate_distinct_sources(self) -> "TournamentGroupCrossingMatch":
        if self.top == self.bottom:
            raise ValueError("Hybrid crossing cannot pair one group position with itself")
        return self


class TournamentGroupFormatConfiguration(FrozenInput):
    """Edition-effective group topology configuration.

    Seed placement is explicit because Master v68 does not define one universal
    seed-layer algorithm for arbitrary non-Qualification group formats.
    """

    group_count: int = Field(ge=1, le=64)
    group_size: int = Field(ge=2, le=128)
    seeded_slots_per_group: int = Field(default=0, ge=0, le=128)
    group_seed_placements: tuple[TournamentGroupSeedPlacement, ...] = ()
    match_best_of: TournamentGroupMatchBestOf
    rules_source_kind: TournamentGroupRulesSourceKind
    group_rules_policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    group_rules_effective_from_season_index: int = Field(ge=0, le=49)
    advancing_per_group: int = Field(default=0, ge=0, le=128)
    knockout_crossings: tuple[TournamentGroupCrossingMatch, ...] = ()

    @model_validator(mode="after")
    def validate_group_configuration(self) -> "TournamentGroupFormatConfiguration":
        if self.seeded_slots_per_group > self.group_size:
            raise ValueError("Seeded group slots cannot exceed group size")
        expected_seed_count = self.group_count * self.seeded_slots_per_group
        if len(self.group_seed_placements) != expected_seed_count:
            raise ValueError(
                "Group seed placement count must equal group_count * seeded_slots_per_group"
            )
        if expected_seed_count:
            if tuple(
                sorted(item.seed_number for item in self.group_seed_placements)
            ) != tuple(range(1, expected_seed_count + 1)):
                raise ValueError("Group seed numbers must be contiguous from 1")
        seen_slots: set[tuple[int, int]] = set()
        per_group = {index: 0 for index in range(1, self.group_count + 1)}
        for item in self.group_seed_placements:
            if item.group_index > self.group_count:
                raise ValueError("Group seed placement references unknown group")
            if item.slot_index > self.group_size:
                raise ValueError("Group seed placement references unknown group slot")
            key = (item.group_index, item.slot_index)
            if key in seen_slots:
                raise ValueError("Two seeds cannot occupy the same group slot")
            seen_slots.add(key)
            per_group[item.group_index] += 1
        if any(
            count != self.seeded_slots_per_group for count in per_group.values()
        ):
            raise ValueError("Every group must receive the same configured seed count")
        return self

    @property
    def participant_capacity(self) -> int:
        return self.group_count * self.group_size


class TournamentFormatAuthority(FrozenInput):
    """Immutable effective competition format for one Tournament Edition."""

    schema_version: Literal["tournament_format_authority.v1"] = (
        "tournament_format_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    target_season_index: int = Field(ge=0, le=49)
    configured_by_command_id: str = Field(min_length=1, max_length=128)
    entry_field_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    format_kind: TournamentFormatKind
    knockout_policy_id: Literal["master_classic_bracket.v2"] = (
        "master_classic_bracket.v2"
    )
    group_configuration: TournamentGroupFormatConfiguration | None = None

    @model_validator(mode="after")
    def validate_format(self) -> "TournamentFormatAuthority":
        if self.format_kind == "knockout":
            if self.group_configuration is not None:
                raise ValueError("Knockout format cannot carry group configuration")
            return self

        group = self.group_configuration
        if group is None:
            raise ValueError("Group-based format requires group configuration")

        if self.format_kind == "groups":
            if group.advancing_per_group or group.knockout_crossings:
                raise ValueError(
                    "Groups-only format cannot define knockout advancement/crossing"
                )
            return self

        if group.advancing_per_group < 1:
            raise ValueError(
                "Groups + knockout format requires at least one advancer per group"
            )
        if group.advancing_per_group > group.group_size:
            raise ValueError("Advancers per group cannot exceed group size")

        advancing_count = group.group_count * group.advancing_per_group
        if advancing_count < 2 or advancing_count & (advancing_count - 1):
            raise ValueError(
                "Configured hybrid knockout field must be a power of two"
            )
        if len(group.knockout_crossings) != advancing_count // 2:
            raise ValueError(
                "Hybrid crossing count must exactly fill the first knockout round"
            )
        if tuple(
            sorted(item.match_index for item in group.knockout_crossings)
        ) != tuple(range(1, advancing_count // 2 + 1)):
            raise ValueError("Hybrid crossing match indexes must be contiguous from 1")

        expected_sources = {
            (group_index, finishing_position)
            for group_index in range(1, group.group_count + 1)
            for finishing_position in range(1, group.advancing_per_group + 1)
        }
        configured_sources: list[tuple[int, int]] = []
        for match in group.knockout_crossings:
            for source in (match.top, match.bottom):
                if source.group_index > group.group_count:
                    raise ValueError("Hybrid crossing references unknown group")
                if source.finishing_position > group.advancing_per_group:
                    raise ValueError(
                        "Hybrid crossing references non-advancing group position"
                    )
                configured_sources.append(
                    (source.group_index, source.finishing_position)
                )
        if set(configured_sources) != expected_sources:
            raise ValueError(
                "Hybrid crossing must use every advancing group position exactly once"
            )
        if len(configured_sources) != len(set(configured_sources)):
            raise ValueError(
                "Hybrid crossing cannot reuse an advancing group position"
            )
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))

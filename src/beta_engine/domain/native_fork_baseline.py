"""Target-owned current facts over an unchanged native Saved past.

A fork baseline describes a candidate new authority at the selected boundary,
not a rewritten birth/Health/match history. Original events and rankings remain source-owned.
Parsing this model does not authenticate its facts; the persistence adapter must
rebuild them from the real source before installation or continuation.
"""

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.native_fork_source import NativeForkSourceBinding
from beta_engine.domain.players.calendar_health import CalendarHealthProfile
from beta_engine.domain.players.calendar_lifecycle import CalendarTourLifecycleIdentity
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from beta_engine.domain.players.sporting import PlayerSportingRecord
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class NativeForkBaseline(FrozenInput):
    schema_version: Literal["native_fork_baseline.v1"] = "native_fork_baseline.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1, max_length=128)
    selected_source_branch_id: str = Field(min_length=1)
    source_binding: NativeForkSourceBinding
    week: RunWeekPosition

    # These are unchanged original authorities, not target-local rewritten hashes.
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_lifecycle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_health_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_health_week: RunWeekPosition
    source_checkpoint_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_tour_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    lifecycle_policy: PlayerLifecyclePolicy
    lifecycle_players: tuple[CalendarTourLifecycleIdentity, ...] = Field(min_length=1)
    health_players: tuple[CalendarHealthProfile, ...] = Field(min_length=1)
    sporting_players: tuple[PlayerSportingRecord, ...] = Field(min_length=1)
    slot_cursor: int = Field(ge=0)

    @model_validator(mode="after")
    def coherent_target_population(self):
        if (
            self.run_id != self.source_binding.run_id
            or self.branch_id
            in {
                self.selected_source_branch_id,
                self.source_binding.source.branch_id,
            }
            or self.branch_id != self.branch_id.strip()
            or not self.branch_id.strip()
        ):
            raise ValueError(
                "Native fork baseline requires a distinct target owner in the same Run"
            )
        populations = tuple(
            tuple(p.player_id for p in players)
            for players in (
                self.lifecycle_players,
                self.health_players,
                self.sporting_players,
            )
        )
        if (
            any(ids != tuple(sorted(set(ids))) for ids in populations)
            or len(set(populations)) != 1
        ):
            raise ValueError(
                "Native fork baseline requires identical complete canonical populations"
            )
        if self.week.ordinal < 1:
            raise ValueError(
                "Native Tour fork baseline requires its initialized current week"
            )
        a, b = self.source_health_week.calendar, self.week.calendar
        if (
            self.source_health_week.ordinal > self.week.ordinal
            or (a.weeks_per_year, a.season_start_year_week, a.start_year)
            != (b.weeks_per_year, b.season_start_year_week, b.start_year)
            or a.season_count > b.season_count
        ):
            raise ValueError(
                "Native fork baseline has a future or foreign Health source"
            )
        # Historical effective dates retain their original compatible horizon.
        # Validate each identity in that horizon, rather than rewriting the date.
        for player in self.lifecycle_players:
            dates = (player.tour_entry_week, player.retirement_effective_week)
            for date in dates:
                if date is not None:
                    a, b = date.calendar, self.week.calendar
                    if (
                        (a.weeks_per_year, a.season_start_year_week, a.start_year)
                        != (b.weeks_per_year, b.season_start_year_week, b.start_year)
                        or a.season_count > b.season_count
                        or date.ordinal > self.week.ordinal
                    ):
                        raise ValueError(
                            "Native fork baseline contains future or foreign lifecycle dates"
                        )
            position = self.week.calendar_position
            from beta_engine.domain.calendar.season_weeks import (
                age_at_calendar_position,
            )

            if player.age != age_at_calendar_position(
                birth_year=player.birth_year,
                birth_year_week=player.birth_year_week,
                calendar_year=position.calendar_year,
                year_week=position.year_week,
                weeks_per_calendar_year=self.week.calendar.weeks_per_year,
            ) or (player.status == "retired") != (
                player.age >= self.lifecycle_policy.automatic_retirement_age
            ):
                raise ValueError(
                    "Native fork baseline lifecycle age/status differs from its source policy"
                )
            if (player.status == "retired") != (
                player.retirement_effective_week is not None
            ):
                raise ValueError(
                    "Native fork baseline retirement lacks its effective date"
                )
            if (player.tour_entry_week is None) != (player.tie_break_token is None):
                raise ValueError(
                    "Native fork baseline Entry lacks its original stable tie-break token"
                )
        for player in self.health_players:
            for record in player.records:
                for date in (record.onset_week, record.recovered_week):
                    if date is not None:
                        a, b = date.calendar, self.source_health_week.calendar
                        if (
                            (a.weeks_per_year, a.season_start_year_week, a.start_year)
                            != (
                                b.weeks_per_year,
                                b.season_start_year_week,
                                b.start_year,
                            )
                            or a.season_count > b.season_count
                            or date.ordinal > self.source_health_week.ordinal
                        ):
                            raise ValueError(
                                "Native fork baseline contains future or foreign Health dates"
                            )
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def project_native_fork_baseline(
    *,
    binding,
    selected_source_branch_id,
    target_branch_id,
    week,
    world_fingerprint,
    lifecycle,
    health,
    checkpoint,
    tour,
):
    """Copy current facts exactly; do not advance time, recover or replay matches."""
    owner = (binding.run_id, binding.source.branch_id)
    if any(
        (s.run_id, s.branch_id) != owner for s in (lifecycle, health, checkpoint, tour)
    ):
        raise ValueError("Native fork baseline inputs have a foreign original owner")
    if any(s.week.ordinal != week.ordinal for s in (lifecycle, checkpoint, tour)):
        raise ValueError("Native fork baseline inputs have different current weeks")
    if health.week.ordinal > week.ordinal:
        raise ValueError("Native fork baseline cannot consume future Health facts")
    if (
        lifecycle.fingerprint != tour.lifecycle_fingerprint
        or checkpoint.fingerprint != tour.checkpoint_fingerprint
        or lifecycle.source_initial_world_fingerprint != world_fingerprint
        or health.source_initial_world_fingerprint != world_fingerprint
        or checkpoint.source_initial_world_fingerprint != world_fingerprint
    ):
        raise ValueError(
            "Native fork baseline inputs are not the same source authority"
        )
    for state in (lifecycle, health, checkpoint, tour):
        a, b = state.week.calendar, week.calendar
        if (a.weeks_per_year, a.season_start_year_week, a.start_year) != (
            b.weeks_per_year,
            b.season_start_year_week,
            b.start_year,
        ) or a.season_count > b.season_count:
            raise ValueError("Native fork baseline cannot reinterpret its Saved clock")
    return NativeForkBaseline(
        run_id=binding.run_id,
        branch_id=target_branch_id,
        selected_source_branch_id=selected_source_branch_id,
        source_binding=binding,
        week=week,
        source_initial_world_fingerprint=world_fingerprint,
        source_lifecycle_fingerprint=lifecycle.fingerprint,
        source_health_fingerprint=health.fingerprint,
        source_health_week=health.week,
        source_checkpoint_fingerprint=checkpoint.fingerprint,
        source_tour_fingerprint=tour.fingerprint,
        source_ranking_fingerprint=tour.rankings[-1].fingerprint,
        lifecycle_policy=lifecycle.policy,
        lifecycle_players=tuple(lifecycle.players),
        health_players=tuple(
            CalendarHealthProfile.model_validate_json(p.model_dump_json())
            for p in health.players
        ),
        sporting_players=tuple(checkpoint.players),
        slot_cursor=tour.slot_cursor,
    )

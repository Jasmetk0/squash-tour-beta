"""Separate v2 InitialWorld and bootstrap; v1 snapshots keep their exact schema."""

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.application.season_player_bootstrap_service import SeasonActivePlayer
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.calendar.season_weeks import (
    completed_weeks_at_calendar_position,
)
from beta_engine.domain.players.calendar_initial_pool import (
    CalendarInitialPoolPlayer,
    InitialPoolCalendarBasis,
)
from beta_engine.domain.players.calendar_lifecycle import (
    CalendarPlayerLifecycleIdentity,
    CalendarPlayerLifecycleState,
)
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarSeasonActivePlayer(SeasonActivePlayer):
    schema_version: Literal["season_active_player.v2"] = "season_active_player.v2"
    birth_year: int
    birth_year_week: int = Field(ge=1)
    season: str = Field(min_length=1)
    time_basis: InitialPoolCalendarBasis

    @model_validator(mode="after")
    def validate_calendar_age(self):
        basis = self.time_basis
        weeks = completed_weeks_at_calendar_position(
            birth_year=self.birth_year,
            birth_year_week=self.birth_year_week,
            calendar_year=basis.start_year,
            year_week=basis.season_start_year_week,
            weeks_per_calendar_year=basis.weeks_per_year,
        )
        if weeks <= 15 * basis.weeks_per_year:
            raise ValueError("Initial player must be fifteen before opening Week 1")
        if (
            weeks != self.age_weeks_at_season_start
            or weeks // basis.weeks_per_year != self.age_years_at_season_start
        ):
            raise ValueError("Initial player age disagrees with its calendar")
        if self.season != basis.season_label:
            raise ValueError("Initial player season differs from its calendar")
        return self


class CalendarInitialWorldState(FrozenInput):
    schema_version: Literal["initial_world_state.v2"] = "initial_world_state.v2"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    run_calendar: RunCalendar
    season: str = Field(min_length=1)
    players: tuple[CalendarSeasonActivePlayer, ...] = Field(min_length=1)
    source_kind: Literal["run_calendar_generated_pool.v2"] = (
        "run_calendar_generated_pool.v2"
    )
    source_season: str = Field(min_length=1)
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    world_package_id: str = Field(min_length=1)
    world_country_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    world_generation_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    run_world_pool_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    bootstrap_seed: int
    bootstrap_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    adopted_by_command_id: str = Field(min_length=1, max_length=128)
    audit_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)
    adoption_request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle_policy: PlayerLifecyclePolicy

    @model_validator(mode="after")
    def validate_world(self):
        if self.run_calendar.schema_version != "run_calendar.v1":
            raise ValueError(
                "Calendar InitialWorld requires an explicit saved v1 Run clock"
            )
        ids = [p.player_id for p in self.players]
        if ids != sorted(set(ids)):
            raise ValueError(
                "Calendar InitialWorld requires canonical distinct players"
            )
        basis = InitialPoolCalendarBasis.from_run_calendar(self.run_calendar)
        if self.season != basis.season_label or self.source_season != self.season:
            raise ValueError(
                "Calendar InitialWorld season differs from the stored clock"
            )
        if self.source_fingerprint != self.run_world_pool_preview_fingerprint:
            raise ValueError("Calendar InitialWorld source preview differs")
        for player in self.players:
            if (
                player.time_basis != basis
                or player.season != self.season
                or player.active_status != "active"
            ):
                raise ValueError(
                    "Calendar InitialWorld player differs from its stored clock"
                )
            if (
                player.age_years_at_season_start
                >= self.lifecycle_policy.automatic_retirement_age
            ):
                raise ValueError(
                    "Initial player already reached the stored retirement age"
                )
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


def bootstrap_calendar_player(
    player: CalendarInitialPoolPlayer, *, seed: int, bootstrap_fingerprint: str
) -> CalendarSeasonActivePlayer:
    basis = player.time_basis
    weeks = completed_weeks_at_calendar_position(
        birth_year=player.birth_year,
        birth_year_week=player.birth_year_week,
        calendar_year=basis.start_year,
        year_week=basis.season_start_year_week,
        weeks_per_calendar_year=basis.weeks_per_year,
    )
    return CalendarSeasonActivePlayer(
        **{
            name: getattr(player, name)
            for name in (
                "player_id",
                "name",
                "country_code",
                "nationality",
                "birth_year",
                "birth_year_week",
                "current_ability",
                "potential_ability",
                "potential_tier",
                "career_stage",
                "play_style",
                "archetype",
                "attributes",
                "hidden_career_traits",
                "manual_override",
            )
        },
        time_basis=basis,
        age_years_at_season_start=player.current_age_years,
        age_weeks_at_season_start=weeks,
        season=basis.season_label,
        source_pool_player_id=player.player_id,
        source_generation_fingerprint=player.generation_fingerprint,
        source_generation="initial_pool",
        locked_from_initial_pool=False,
        bootstrap_seed=seed,
        bootstrap_fingerprint=bootstrap_fingerprint,
        bootstrap_id="calendar-initial-world.v2:" + bootstrap_fingerprint,
    )


def derive_calendar_bootstrap_lifecycle(
    world: CalendarInitialWorldState,
) -> CalendarPlayerLifecycleState:
    return CalendarPlayerLifecycleState(
        run_id=world.run_id,
        branch_id=world.branch_id,
        week=RunWeekPosition(calendar=world.run_calendar, season_index=0, week=1),
        players=tuple(
            CalendarPlayerLifecycleIdentity(
                player_id=p.player_id,
                birth_year=p.birth_year,
                birth_year_week=p.birth_year_week,
                age=p.age_years_at_season_start,
                source_generation_fingerprint=p.source_generation_fingerprint,
            )
            for p in world.players
        ),
        source_initial_world_fingerprint=world.fingerprint,
        policy=world.lifecycle_policy,
    )

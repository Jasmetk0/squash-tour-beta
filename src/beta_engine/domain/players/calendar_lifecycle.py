"""Calendar-owned population bootstrap, before Tour/sporting initialization."""

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.calendar.season_weeks import age_at_calendar_position
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarPlayerLifecycleIdentity(FrozenInput):
    player_id: str = Field(min_length=1)
    birth_year: int
    birth_year_week: int = Field(ge=1)
    age: int = Field(ge=15, le=120)
    status: Literal["active"] = "active"
    source_generation_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class CalendarPlayerLifecycleState(FrozenInput):
    schema_version: Literal["player_lifecycle_calendar_state.v2"] = (
        "player_lifecycle_calendar_state.v2"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RunWeekPosition
    players: tuple[CalendarPlayerLifecycleIdentity, ...]
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_fingerprint: None = None
    policy: PlayerLifecyclePolicy
    # Population adoption creates no historical Tour entry or retirement event.
    # The future ranking/entry migration must initialize those separately.
    initialization_stage: Literal["population_only"] = "population_only"

    @model_validator(mode="after")
    def validate_initial_population(self):
        if self.week.ordinal != 0:
            raise ValueError("Calendar population bootstrap must be at opening Week 1")
        ids = [p.player_id for p in self.players]
        if not ids or ids != sorted(set(ids)):
            raise ValueError("Calendar lifecycle requires canonical distinct players")
        position = self.week.calendar_position
        for player in self.players:
            age = age_at_calendar_position(
                birth_year=player.birth_year,
                birth_year_week=player.birth_year_week,
                calendar_year=position.calendar_year,
                year_week=position.year_week,
                weeks_per_calendar_year=self.week.calendar.weeks_per_year,
            )
            if player.age != age:
                raise ValueError(
                    "Calendar lifecycle age differs from its birth identity"
                )
            if age >= self.policy.automatic_retirement_age:
                raise ValueError(
                    "Initial player already reached the stored retirement age"
                )
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


class CalendarTourLifecycleIdentity(CalendarPlayerLifecycleIdentity):
    status: Literal["active", "retired"] = "active"
    retirement_effective_week: RunWeekPosition | None = None
    tour_entry_week: RunWeekPosition | None = None
    tie_break_token: str | None = None


class CalendarTourLifecycleState(FrozenInput):
    """Native consecutive lifecycle; v2 population bootstrap bytes stay unchanged."""

    schema_version: Literal["player_lifecycle_calendar_state.v3"] = (
        "player_lifecycle_calendar_state.v3"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RunWeekPosition
    players: tuple[CalendarTourLifecycleIdentity, ...]
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy: PlayerLifecyclePolicy

    @model_validator(mode="after")
    def validate_current_population(self):
        ids = tuple(p.player_id for p in self.players)
        if not ids or ids != tuple(sorted(set(ids))) or self.week.ordinal < 1:
            raise ValueError(
                "Native lifecycle requires its canonical population and target week"
            )
        position = self.week.calendar_position
        for player in self.players:
            age = age_at_calendar_position(
                birth_year=player.birth_year,
                birth_year_week=player.birth_year_week,
                calendar_year=position.calendar_year,
                year_week=position.year_week,
                weeks_per_calendar_year=self.week.calendar.weeks_per_year,
            )
            if player.age != age or (player.status == "retired") != (
                age >= self.policy.automatic_retirement_age
            ):
                raise ValueError(
                    "Native lifecycle age/status differs from birth identity and stored policy"
                )
            if (player.status == "retired") != (
                player.retirement_effective_week is not None
            ):
                raise ValueError("Native retirement requires its effective week")
            if (player.tour_entry_week is None) != (player.tie_break_token is None):
                raise ValueError(
                    "Native Tour entry requires its stable tie-break token"
                )
            for date in (player.retirement_effective_week, player.tour_entry_week):
                if date and (
                    date.calendar != self.week.calendar
                    or date.ordinal > self.week.ordinal
                ):
                    raise ValueError(
                        "Native lifecycle contains a foreign or future effective date"
                    )
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def advance_calendar_lifecycle(predecessor, target, submissions=()):
    """Birthdays/retirement and completed-week first Entry from actual authorities."""
    if target.ordinal != predecessor.week.ordinal + 1:
        raise ValueError("Native lifecycle requires a consecutive Week Transition")
    original = predecessor.week.calendar
    if (
        original.weeks_per_year,
        original.season_start_year_week,
        original.start_year,
    ) != (
        target.calendar.weeks_per_year,
        target.calendar.season_start_year_week,
        target.calendar.start_year,
    ) or original.season_count > target.calendar.season_count:
        raise ValueError("Native lifecycle cannot reinterpret its Run clock")
    first = {}
    for source in submissions:
        if (source.run_id, source.branch_id) != (
            predecessor.run_id,
            predecessor.branch_id,
        ):
            raise ValueError("Foreign native lifecycle Entry authority")
        if source.submission_week.ordinal > predecessor.week.ordinal:
            continue
        prior = first.get(source.player_id)
        if prior is None or source.decision_position < prior.decision_position:
            first[source.player_id] = source
    position = target.calendar_position
    players = []
    for old in predecessor.players:
        age = age_at_calendar_position(
            birth_year=old.birth_year,
            birth_year_week=old.birth_year_week,
            calendar_year=position.calendar_year,
            year_week=position.year_week,
            weeks_per_calendar_year=target.calendar.weeks_per_year,
        )
        retired = age >= predecessor.policy.automatic_retirement_age
        source = first.get(old.player_id)
        entry = getattr(old, "tour_entry_week", None)
        token = getattr(old, "tie_break_token", None)
        if entry is None and source is not None:
            entry = source.submission_week
            token = source.nr_tie_break_token

        # A compatible horizon extension retains the original birthday/entry
        # identity; dates in this newly owned snapshot use the extended horizon.
        def date(value):
            return (
                RunWeekPosition(
                    calendar=target.calendar,
                    season_index=value.season_index,
                    week=value.week,
                )
                if value
                else None
            )

        players.append(
            CalendarTourLifecycleIdentity(
                player_id=old.player_id,
                birth_year=old.birth_year,
                birth_year_week=old.birth_year_week,
                age=age,
                status="retired" if retired else "active",
                source_generation_fingerprint=old.source_generation_fingerprint,
                retirement_effective_week=date(
                    getattr(old, "retirement_effective_week", None)
                )
                or (target if retired else None),
                tour_entry_week=date(entry),
                tie_break_token=token,
            )
        )
    return CalendarTourLifecycleState(
        run_id=predecessor.run_id,
        branch_id=predecessor.branch_id,
        week=target,
        players=tuple(players),
        source_initial_world_fingerprint=predecessor.source_initial_world_fingerprint,
        predecessor_fingerprint=predecessor.fingerprint,
        policy=predecessor.policy,
    )


def calendar_lifecycle_history(
    bootstrap, target, submissions=(), *, effective_calendars=None
):
    states = [bootstrap]
    for ordinal in range(1, target.ordinal + 1):
        calendar = (effective_calendars or {}).get(ordinal, target.calendar)
        position = calendar.position_at_ordinal(ordinal)
        states.append(
            advance_calendar_lifecycle(
                states[-1],
                RunWeekPosition(
                    calendar=calendar,
                    season_index=position.season_index,
                    week=position.season_week,
                ),
                submissions,
            )
        )
    return tuple(states)

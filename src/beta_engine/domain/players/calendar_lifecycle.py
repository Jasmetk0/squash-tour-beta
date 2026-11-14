"""Calendar-owned population bootstrap, before Tour/sporting initialization."""

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.calendar.season_weeks import age_at_calendar_position
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from beta_engine.domain.players.turn_pro import (
    opening_turn_pro_tie_break_token,
    turn_pro_decisions_by_player,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarPlayerLifecycleIdentity(FrozenInput):
    player_id: str = Field(min_length=1)
    birth_year: int
    birth_year_week: int = Field(ge=1)
    age: int = Field(ge=15, le=120)
    status: Literal["active"] = "active"
    source_generation_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class CalendarInitialProfessionalIdentity(CalendarPlayerLifecycleIdentity):
    """Master v87: an opening player who had already turned pro before Run start.

    A separate type keeps every population-only identity's bytes unchanged.
    """

    tour_entry_week: RunWeekPosition
    tie_break_token: str = Field(min_length=1)


class CalendarPlayerLifecycleState(FrozenInput):
    schema_version: Literal["player_lifecycle_calendar_state.v2"] = (
        "player_lifecycle_calendar_state.v2"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RunWeekPosition
    players: tuple[
        CalendarInitialProfessionalIdentity | CalendarPlayerLifecycleIdentity, ...
    ]
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_fingerprint: None = None
    policy: PlayerLifecyclePolicy
    # Population adoption creates no historical Tour entry or retirement event.
    # Exception (Master v87 only): opening players who had turned pro before Run
    # start carry Tour entry at opening Week 1 from the InitialWorld's evidence.
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
            if isinstance(player, CalendarInitialProfessionalIdentity):
                if not self.policy.requires_turn_pro:
                    raise ValueError(
                        "Opening Tour entry requires the v87 Turn Pro lifecycle policy"
                    )
                entry = player.tour_entry_week
                if (entry.calendar, entry.ordinal) != (self.week.calendar, 0):
                    raise ValueError("Opening professional must enter at opening Week 1")
                if player.tie_break_token != opening_turn_pro_tie_break_token(
                    run_id=self.run_id, player_id=player.player_id
                ):
                    raise ValueError("Opening professional has a foreign tie-break token")
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


def advance_calendar_lifecycle(predecessor, target, submissions=(), turn_pro=()):
    """Birthdays/retirement and first Entry from actual authorities.

    Historical policy: first Entry is the earliest valid application of the
    completed week. Master v87 ``turn_pro.v87`` policy: first Entry is only the
    Turn Pro decision effective at ``target``; an application from a player who had
    not already turned pro is rejected, and applications never create Entry.
    """
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
    turn_pro_rule = predecessor.policy.requires_turn_pro
    if turn_pro and not turn_pro_rule:
        raise ValueError("Turn Pro decisions require the v87 lifecycle policy")
    decisions = turn_pro_decisions_by_player(
        turn_pro, run_id=predecessor.run_id, branch_id=predecessor.branch_id
    )
    known_ids = {p.player_id for p in predecessor.players}
    if any(
        d.effective_week.ordinal <= target.ordinal and pid not in known_ids
        for pid, d in decisions.items()
    ):
        raise ValueError("Turn Pro decision references a player absent from lifecycle")
    first = {}
    for source in submissions:
        if (source.run_id, source.branch_id) != (
            predecessor.run_id,
            predecessor.branch_id,
        ):
            raise ValueError("Foreign native lifecycle Entry authority")
        if source.submission_week.ordinal > predecessor.week.ordinal:
            continue
        if turn_pro_rule:
            # v87: the application is a consequence of being a pro, never its cause.
            known = next(
                (p for p in predecessor.players if p.player_id == source.player_id),
                None,
            )
            entered = getattr(known, "tour_entry_week", None)
            if entered is None or entered.ordinal > source.submission_week.ordinal:
                raise ValueError(
                    "Application predates the player's Turn Pro week under policy v87"
                )
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
        decision = decisions.get(old.player_id)
        if decision is not None and decision.effective_week.ordinal <= target.ordinal:
            clock = decision.effective_week.calendar
            if (
                clock.weeks_per_year,
                clock.season_start_year_week,
                clock.start_year,
            ) != (
                target.calendar.weeks_per_year,
                target.calendar.season_start_year_week,
                target.calendar.start_year,
            ) or clock.season_count > target.calendar.season_count:
                raise ValueError("Turn Pro decision uses a foreign Run calendar")
            if entry is not None:
                if entry.ordinal != decision.effective_week.ordinal:
                    raise ValueError("Turn Pro decision conflicts with recorded Tour entry")
            elif decision.effective_week.ordinal != target.ordinal:
                raise ValueError("Turn Pro decision was not applied at its own week")
            elif retired:
                raise ValueError("A retired player cannot turn pro")
            else:
                entry, token = decision.effective_week, decision.tie_break_token

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
    bootstrap, target, submissions=(), *, effective_calendars=None, turn_pro=()
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
                turn_pro,
            )
        )
    return tuple(states)


def bootstrap_calendar_lifecycle(world):
    """Pure opening identities shared by population and recorded pre-Tour weeks."""
    opening = RunWeekPosition(calendar=world.run_calendar, season_index=0, week=1)
    pros = set(
        world.initial_turn_pro.professional_player_ids if world.initial_turn_pro else ()
    )

    def identity(p):
        common = dict(
            player_id=p.player_id,
            birth_year=p.birth_year,
            birth_year_week=p.birth_year_week,
            age=p.age_years_at_season_start,
            source_generation_fingerprint=p.source_generation_fingerprint,
        )
        if p.player_id not in pros:
            return CalendarPlayerLifecycleIdentity(**common)
        return CalendarInitialProfessionalIdentity(
            **common,
            tour_entry_week=opening,
            tie_break_token=opening_turn_pro_tie_break_token(
                run_id=world.run_id, player_id=p.player_id
            ),
        )

    return CalendarPlayerLifecycleState(
        run_id=world.run_id,
        branch_id=world.branch_id,
        week=opening,
        players=tuple(identity(p) for p in world.players),
        source_initial_world_fingerprint=world.fingerprint,
        policy=world.lifecycle_policy,
    )

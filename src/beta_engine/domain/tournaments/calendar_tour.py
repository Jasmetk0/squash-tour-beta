"""Run-calendar adapter joining existing Entry, draw, sporting and ranking rules.

This authority applies only to newly configured Editions. Historical exhibitions
never acquire an Edition or become ranking sources through this adapter.
"""

import itertools
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_sporting_week import (
    CalendarAnnualDevelopmentPolicy,
)
from beta_engine.domain.rankings.calendar_official import (
    CalendarOfficialRankingSnapshot,
    CalendarRankingPlayer,
    CalendarRankingResult,
    CalendarRankingWeek,
    calculate_calendar_official_ranking,
)
from beta_engine.domain.rankings.official import FrozenInput, OfficialRankingPolicy
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
)
from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawAuthority,
    TournamentDrawAuthorityBuilder,
)
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthorityBuilder,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryField,
    TournamentEntryFieldCapacity,
    TournamentEntryFieldResolver,
)
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)


def ranking_week(week):
    return CalendarRankingWeek(season_index=week.season_index, week=week.week)


class CalendarTourEdition(FrozenInput):
    schema_version: Literal["calendar_tournament_edition.v1"] = (
        "calendar_tournament_edition.v1"
    )
    edition_id: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    week: RunWeekPosition
    announcement_week: RunWeekPosition
    # This first executor has explicitly sequential global slots. Simultaneous
    # cross-Edition execution needs the shared-slot owner and is blocked.
    start_slot: int = Field(ge=1)
    main_entrant_count: int = Field(ge=2, le=128)
    ranked: bool = True
    point_table: dict[str, int]
    validity_weeks: int = Field(ge=1)
    best_of: Literal[5] = 5
    games_to: Literal[11] = 11
    win_by: Literal[2] = 2

    @property
    def capacity(self):
        return TournamentEntryFieldCapacity.for_main_entrant_count(
            main_entrant_count=self.main_entrant_count
        )

    @model_validator(mode="after")
    def validate_edition(self):
        if (
            self.week.calendar != self.announcement_week.calendar
            or self.announcement_week.ordinal + 1 > self.week.ordinal
        ):
            raise ValueError(
                "Edition announcement must precede play on the same Run clock"
            )
        stages = required_stages(self.capacity.main_draw_size)
        if self.ranked and (
            set(self.point_table) != set(stages)
            or any(type(v) is not int or v < 0 for v in self.point_table.values())
            or any(
                self.point_table[a] < self.point_table[b]
                for a, b in itertools.pairwise(stages)
            )
        ):
            raise ValueError(
                "Ranked Edition requires its complete descending point table before announcement"
            )
        if not self.ranked and self.point_table:
            raise ValueError("Unranked Edition must have an empty point table")
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def required_stages(size):
    names = {2: "finalist", 4: "semifinal", 8: "quarterfinal"}
    return ("champion",) + tuple(
        names.get(n, f"round{n}") for n in (2**i for i in range(1, size.bit_length()))
    )


class CalendarTourPolicy(FrozenInput):
    effective_week: RunWeekPosition
    ranking: OfficialRankingPolicy
    development: CalendarAnnualDevelopmentPolicy = CalendarAnnualDevelopmentPolicy()


class CalendarEditionAuthority(FrozenInput):
    edition: CalendarTourEdition
    created_command_id: str
    created_saved_head: str
    submissions: tuple[TournamentApplicationSubmissionAuthority, ...] = ()
    ranking_authority: TournamentRankingSnapshotAuthority | None = None
    field: TournamentEntryField | None = None
    draw: TournamentDrawAuthority | None = None
    draw_seed: int | None = None
    draw_command_id: str | None = None
    played_saved_head: str | None = None
    tournament_fingerprint: str | None = None
    result_confirmed: bool = False

    @property
    def execution_fingerprint(self):
        return canonical_hash(
            {
                "edition": self.edition.fingerprint,
                "submissions": [s.fingerprint for s in self.submissions],
                "field": self.field.fingerprint if self.field else None,
                "draw": self.draw.fingerprint if self.draw else None,
                "ranking": self.ranking_authority.fingerprint
                if self.ranking_authority
                else None,
                "created_command_id": self.created_command_id,
                "created_saved_head": self.created_saved_head,
            }
        )

    @model_validator(mode="after")
    def validate_sources(self):
        ids = tuple(s.application_id for s in self.submissions)
        if ids != tuple(sorted(set(ids))) or len(
            {s.player_id for s in self.submissions}
        ) != len(ids):
            raise ValueError("Edition applications must be canonical and player-unique")
        if any(
            s.event_id != self.edition.edition_id
            or not s.schema_version.endswith(".v2")
            or s.submission_week.calendar != self.edition.week.calendar
            or s.submission_week.ordinal < self.edition.announcement_week.ordinal + 1
            or s.submission_week.ordinal > self.edition.week.ordinal
            for s in self.submissions
        ):
            raise ValueError("Edition contains foreign/future application authority")
        if self.field is not None:
            if self.ranking_authority is None:
                raise ValueError("Approved field lacks frozen ranking authority")
            if (
                self.ranking_authority.schema_version
                != "tournament_ranking_snapshot_authority.v2"
                or self.ranking_authority.event_id != self.edition.edition_id
                or self.ranking_authority.ranking_week.ordinal
                != self.edition.week.ordinal
            ):
                raise ValueError("Approved field has a foreign Edition ranking binding")
            expected = TournamentEntryFieldResolver.build_initial(
                authority=self.ranking_authority,
                applications=tuple(
                    s.to_entry_field_application() for s in self.submissions
                ),
                capacity=self.edition.capacity,
            )
            if self.field != expected:
                raise ValueError(
                    "Approved field differs from actual valid applications"
                )
        if self.draw is not None:
            if (
                self.field is None
                or self.draw_seed is None
                or self.draw_command_id is None
            ):
                raise ValueError("Draw lacks approved Entry authority")
            if self.draw != build_draw(self, self.draw_command_id, self.draw_seed):
                raise ValueError("Draw differs from approved field and injected seed")
        if self.tournament_fingerprint and (
            not self.draw or not self.played_saved_head
        ):
            raise ValueError("Played Edition lacks pre-existing Saved draw authority")
        if self.result_confirmed and not self.tournament_fingerprint:
            raise ValueError("Unplayed Edition cannot confirm results")
        return self


def build_draw(authority, command_id, seed):
    inputs = TournamentDrawInputAuthorityBuilder.build(
        authority=authority.ranking_authority,
        field=authority.field,
        field_sequence=1,
        command_id=command_id,
        draw_seed=seed,
        main_seed_count=None,
        qualification_seed_count=None,
        schema_version="tournament_draw_input_authority.v2",
    )
    return TournamentDrawAuthorityBuilder.build(
        draw_input=inputs, command_id=command_id
    )


class CalendarTourReceipt(FrozenInput):
    command_id: str
    request: dict
    result: dict


class CalendarTourTransition(FrozenInput):
    command_id: str
    completed_week: RunWeekPosition
    target_week: RunWeekPosition
    sporting_advance_fingerprint: str
    ranking_fingerprint: str
    health_fingerprint: str
    ages: tuple[tuple[str, int], ...]
    retired_player_ids: tuple[str, ...]
    public_event: dict


class CalendarTourState(FrozenInput):
    schema_version: Literal["calendar_tour_authority.v1"] = "calendar_tour_authority.v1"
    run_id: str
    branch_id: str
    week: RunWeekPosition
    checkpoint_fingerprint: str
    lifecycle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    slot_cursor: int = Field(default=0, ge=0)
    policies: tuple[CalendarTourPolicy, ...]
    editions: tuple[CalendarEditionAuthority, ...] = ()
    rankings: tuple[CalendarOfficialRankingSnapshot, ...]
    transitions: tuple[CalendarTourTransition, ...] = ()
    receipts: tuple[CalendarTourReceipt, ...] = ()

    @model_validator(mode="after")
    def validate_state(self):
        if not self.rankings or not self.policies:
            raise ValueError("Native Tour lacks initial policy/ranking authority")

        def basis(c):
            return (c.weeks_per_year, c.season_start_year_week, c.start_year)

        if any(
            basis(p.effective_week.calendar) != basis(self.week.calendar)
            or p.effective_week.calendar.season_count > self.week.calendar.season_count
            for p in self.policies
        ):
            raise ValueError("Policy has a foreign Run calendar")
        ids = [e.edition.edition_id for e in self.editions]
        if any(
            (a.ranking_authority.run_id, a.ranking_authority.branch_id)
            != (self.run_id, self.branch_id)
            for a in self.editions
            if a.ranking_authority
        ):
            raise ValueError("Edition ranking binding has a foreign Run/Branch")
        if any(
            s.submission_week.ordinal > self.week.ordinal
            for a in self.editions
            for s in a.submissions
        ):
            raise ValueError("Tour authority contains a future application")
        commands = [r.command_id for r in self.receipts]
        if len(ids) != len(set(ids)) or len(commands) != len(set(commands)):
            raise ValueError("Duplicate Edition or command identity")
        accepted = set()
        for authority in self.editions:
            if authority.field:
                for pid in authority.field.direct_main_player_ids:
                    key = (authority.edition.week.ordinal, pid)
                    if key in accepted:
                        raise ValueError(
                            "Week Tournament Lock conflict in approved native fields"
                        )
                    accepted.add(key)
        ordinals = [p.effective_week.ordinal for p in self.policies]
        if ordinals != sorted(set(ordinals)) or ordinals[
            0
        ] > self.week.calendar.ordinal(
            self.rankings[0].week.season_index, self.rankings[0].week.week
        ):
            raise ValueError("Policy effective dates are not canonical")
        if len(self.rankings) != len(self.transitions) + 1:
            raise ValueError(
                "Each Week Transition must own exactly one Official ranking"
            )
        for i, snapshot in enumerate(self.rankings):
            snapshot_clock = RunCalendar.from_metadata(snapshot.run_calendar)
            if (
                (snapshot.run_id, snapshot.branch_id) != (self.run_id, self.branch_id)
                or basis(snapshot_clock) != basis(self.week.calendar)
                or snapshot_clock.season_count > self.week.calendar.season_count
            ):
                raise ValueError("Foreign Official ranking")
            if i and (
                snapshot.previous_fingerprint != self.rankings[i - 1].fingerprint
                or self.transitions[i - 1].ranking_fingerprint != snapshot.fingerprint
                or ranking_week(self.transitions[i - 1].target_week) != snapshot.week
            ):
                raise ValueError("Official ranking lineage mismatch")
            if i:
                transition = self.transitions[i - 1]
                previous = self.rankings[i - 1].week
                if (
                    ranking_week(transition.completed_week) != previous
                    or transition.target_week.ordinal
                    != transition.completed_week.ordinal + 1
                    or basis(transition.completed_week.calendar)
                    != basis(self.week.calendar)
                    or transition.completed_week.calendar
                    != transition.target_week.calendar
                ):
                    raise ValueError(
                        "Week Transition chronology differs from Official history"
                    )
        if self.rankings[0].rows or self.rankings[0].previous_fingerprint is not None:
            raise ValueError("Native Tour must start with its empty initial ranking")
        if self.rankings[-1].week != ranking_week(self.week):
            raise ValueError("Official ranking and global native clock differ")
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def effective_policy(state, week):
    return next(
        p for p in reversed(state.policies) if p.effective_week.ordinal <= week.ordinal
    )


def lifecycle_calendars(state):
    """Retain the exact clock originally effective at each generated boundary."""
    initial = RunCalendar.from_metadata(state.rankings[0].run_calendar)
    transitions = {
        t.target_week.ordinal: t.target_week.calendar for t in state.transitions
    }
    return {
        ordinal: transitions.get(ordinal, initial)
        for ordinal in range(1, state.week.ordinal + 1)
    }


def edition_results(authority, event):
    """One authoritative result per player; immutable Edition table is the source."""
    played_fingerprint = event.fingerprint
    if authority.tournament_fingerprint != played_fingerprint:
        raise ValueError("Edition result is detached from played MatchEngine evidence")
    if (
        event.schema_version != "calendar_followup_knockout.v5"
        or event.edition_authority_fingerprint != authority.execution_fingerprint
    ):
        raise ValueError(
            "Exhibition or unbound event cannot become an Official Tour result"
        )
    slots = tuple(s.player_id for s in authority.draw.main.slots)
    if (
        event.tournament_id != authority.edition.edition_id
        or event.entrant_ids != slots
        or (event.week.season_index, event.week.week)
        != (authority.edition.week.season_index, authority.edition.week.week)
        or (
            event.week.calendar.weeks_per_year,
            event.week.calendar.start_year,
            event.week.calendar.season_start_year_week,
        )
        != (
            authority.edition.week.calendar.weeks_per_year,
            authority.edition.week.calendar.start_year,
            authority.edition.week.calendar.season_start_year_week,
        )
        or event.week.calendar.season_count
        < authority.edition.week.calendar.season_count
    ):
        raise ValueError(
            "Played bracket differs from the Edition's approved Saved draw"
        )
    points = authority.edition.point_table
    if (
        event.prepared_policy is None
        or any(
            getattr(event.prepared_policy, stage) != value
            for stage, value in points.items()
        )
        or event.prepared_policy.validity_weeks != authority.edition.validity_weeks
    ):
        raise ValueError(
            "Played point policy differs from the pre-existing Edition table"
        )
    completed = ranking_week(event.week)
    target = event.week.calendar.position_at_ordinal(event.week.ordinal + 1)
    published = CalendarRankingWeek(
        season_index=target.season_index, week=target.season_week
    )
    source = {
        "edition": authority.edition.fingerprint,
        "field": authority.field.fingerprint,
        "draw": authority.draw.fingerprint,
        "played": played_fingerprint,
    }
    return tuple(
        CalendarRankingResult(
            edition_id=event.tournament_id,
            player_id=award.player_id,
            source_fingerprint=canonical_hash(
                {
                    **source,
                    "award": award.model_dump(mode="json"),
                }
            ),
            completed_week=completed,
            first_publication_week=published,
            main_points=award.main_points,
            validity_weeks=authority.edition.validity_weeks,
            ranked=authority.edition.ranked,
        )
        for award in event.prepared_awards
    )


def ranking_players(state, submissions, *, retired=()):
    first = {}
    for submission in submissions:
        if (submission.run_id, submission.branch_id) != (state.run_id, state.branch_id):
            raise ValueError("Foreign Tour submission")
        prior = first.get(submission.player_id)
        if prior is None or submission.decision_position < prior.decision_position:
            first[submission.player_id] = submission
    return tuple(
        CalendarRankingPlayer(
            player_id=pid,
            tie_break_token=s.nr_tie_break_token,
            tour_entry_week=ranking_week(s.submission_week),
            retired=pid in retired,
        )
        for pid, s in sorted(first.items())
    )


def calculate_tour_ranking(state, checkpoint, *, target, retired=()):
    events = {t.tournament_id: t for t in checkpoint.tournaments}
    results = tuple(
        r
        for a in state.editions
        if a.result_confirmed and a.edition.week.ordinal < target.ordinal
        for r in edition_results(a, events[a.edition.edition_id])
    )
    submissions = tuple(
        s
        for a in state.editions
        for s in a.submissions
        if s.submission_week.ordinal < target.ordinal
    )
    return calculate_calendar_official_ranking(
        run_id=state.run_id,
        branch_id=state.branch_id,
        run_calendar=target.calendar,
        week=ranking_week(target),
        policy=effective_policy(state, target).ranking,
        players=ranking_players(state, submissions, retired=retired),
        results=results,
        previous=state.rankings[-1],
    )

"""Run-calendar adapter joining existing Entry, draw, sporting and ranking rules.

This authority applies only to newly configured Editions. Historical exhibitions
never acquire an Edition or become ranking sources through this adapter.
"""

import itertools
import json
from typing import Literal

from pydantic import Field, model_serializer, model_validator

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
from beta_engine.domain.rankings.calendar_terminal_result import (
    CalendarTerminalRankingResult,
)
from beta_engine.domain.players.turn_pro import PlayerTurnProDecision
from beta_engine.domain.players.turn_pro_model import TurnProModelPolicy
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


from beta_engine.domain.tournaments.native_canonical_knockout import (
    NativeCanonicalDrawBinding, is_canonical_edition, canonical_announcement_week,
    saved_ranked_point_table, validate_ranked_publication_week,
)

def ranking_week(week):
    return CalendarRankingWeek(season_index=week.season_index, week=week.week)


from beta_engine.domain.tournaments.calendar_groups import NativeGroupConfiguration, NativeGroupDraw, build_group_draw, knockout_stages


class CalendarTourEdition(FrozenInput):
    schema_version: Literal["calendar_tournament_edition.v1", "calendar_tournament_edition.v2", "calendar_tournament_edition.v3", "calendar_tournament_edition.v4"] = (
        "calendar_tournament_edition.v1"
    )
    edition_id: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    week: RunWeekPosition
    announcement_week: RunWeekPosition
    # v1 retains its sequential executor. v2 uses the shared Branch slot ledger.
    start_slot: int = Field(ge=1)
    simulation_seed: int = 1
    main_entrant_count: int = Field(ge=2, le=128)
    ranked: bool = True
    point_table: dict[str, int]
    validity_weeks: int = Field(ge=1)
    group_configuration: NativeGroupConfiguration | None = Field(default=None, exclude_if=lambda v: v is None)
    # Master v87 home opportunity input; omitted when absent so earlier Editions
    # keep their exact bytes.
    host_country_code: str | None = Field(
        default=None, pattern=r"^[A-Z]{3}$", exclude_if=lambda v: v is None
    )
    best_of: Literal[5] = 5
    games_to: Literal[11] = 11
    win_by: Literal[2] = 2

    @model_serializer(mode="wrap")
    def historical_shape(self, handler):
        body = handler(self)
        if self.schema_version == "calendar_tournament_edition.v1":
            body.pop("simulation_seed", None)
        return body

    @property
    def capacity(self):
        if self.schema_version in {"calendar_tournament_edition.v3", "calendar_tournament_edition.v4"}:
            return TournamentEntryFieldCapacity(geometry_kind="fixed_participant_field", main_draw_size=self.main_entrant_count)
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
        if self.schema_version == "calendar_tournament_edition.v3":
            config = self.group_configuration
            if config is None or config.groups.participant_capacity != self.main_entrant_count:
                raise ValueError("Group Edition requires its exact equal-group capacity")
            if config.rules.effective_from_season_index > self.week.season_index:
                raise ValueError("Group rules are not yet effective")
            count = config.groups.group_count * config.groups.advancing_per_group
            stages = knockout_stages(count) if config.format_kind == 'groups_knockout' else ()
            if not self.ranked and config.played_group_win_points:
                raise ValueError("Unranked group Edition cannot grant ranking rewards")
        else:
            if self.group_configuration is not None:
                raise ValueError("Historical knockout Edition cannot carry group configuration")
            stages = required_stages(self.capacity.main_draw_size)
        if self.ranked and self.schema_version == "calendar_tournament_edition.v4":
            # Reachable stages and exact values are verified against the Saved
            # source in CalendarEditionAuthority, not the legacy Main-only table.
            if not self.point_table or any(type(v) is not int or v < 0 for v in self.point_table.values()):
                raise ValueError("Canonical Ranked Edition requires a complete Saved point table")
        elif self.ranked and (
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
    draw: TournamentDrawAuthority | NativeGroupDraw | None = None
    draw_seed: int | None = None
    draw_command_id: str | None = None
    played_saved_head: str | None = None
    tournament_fingerprint: str | None = None
    result_confirmed: bool = False
    canonical_binding: NativeCanonicalDrawBinding | None = Field(default=None, exclude_if=lambda v: v is None)

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
                **({"canonical_binding": self.canonical_binding.fingerprint} if self.canonical_binding is not None else {}),
            }
        )

    @model_validator(mode="after")
    def validate_sources(self):
        if is_canonical_edition(self):
            binding = self.canonical_binding
            if binding is None or self.draw is None or self.submissions or self.field is not None or self.ranking_authority is not None:
                raise ValueError("Canonical Edition requires its sole exact Saved Draw binding")
            binding.plan(self.draw)
            event = binding.source_event
            if self.edition.announcement_week != canonical_announcement_week(binding):
                raise ValueError("Canonical announcement differs from its Saved source")
            if self.edition.ranked != (event.ranking_status == "ranked"):
                raise ValueError("Canonical Edition ranking status differs from its Saved source")
            if self.edition.ranked:
                validate_ranked_publication_week(self.edition.week)
                if self.edition.point_table != saved_ranked_point_table(event):
                    raise ValueError("Canonical Edition changes its Saved point table")
            if event.duration_in_season_weeks != 1 or event.start_season_week != event.season_week or event.end_season_week != event.season_week:
                raise ValueError("Canonical native v4 requires an explicit same-week source; multi-week execution is not yet supported")
            if (self.edition.name, self.edition.start_slot, self.edition.simulation_seed, self.edition.validity_weeks) != (event.event_name, binding.schedule.qualification[0], binding.draw_input.draw_seed, binding.calendar.weeks_per_year):
                raise ValueError("Canonical Edition changes its frozen name/schedule/seed/validity")
            if (self.edition.edition_id, self.edition.main_entrant_count, self.edition.week.calendar,
                self.edition.week.week, self.created_saved_head, self.played_saved_head,
                self.draw_seed, self.draw_command_id) != (
                event.event_id, event.main_draw_size, binding.calendar, event.season_week,
                binding.saved_revision_id, binding.saved_revision_id, binding.draw_input.draw_seed,
                self.draw.generated_by_command_id,
            ):
                raise ValueError("Canonical Edition changes its frozen source identity/clock/Draw")
            if self.edition.week.season_index != int(str(event.season).split('/')[0]) - binding.calendar.start_year:
                raise ValueError("Canonical Edition changes its source season")
            position = self.edition.week.calendar_position
            if (event.calendar_year, event.year_week) != (position.calendar_year, position.year_week):
                raise ValueError("Canonical source dates require an explicit compatible Run calendar; no silent conversion")
            return self
        if self.canonical_binding is not None:
            raise ValueError("Historical Edition cannot acquire canonical v4 source binding")
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
    if authority.edition.schema_version == "calendar_tournament_edition.v3":
        return build_group_draw(authority, command_id, seed)
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
    # Master v87: Turn Pro decisions made at this transition and the exact model
    # policy that made them. Both are omitted when absent so historical
    # transitions keep their bytes.
    turn_pro_decisions: tuple[PlayerTurnProDecision, ...] = ()
    turn_pro_model: TurnProModelPolicy | None = None

    @model_serializer(mode="wrap")
    def _omit_absent_turn_pro(self, handler):
        body = handler(self)
        if not self.turn_pro_decisions:
            body.pop("turn_pro_decisions", None)
        if self.turn_pro_model is None:
            body.pop("turn_pro_model", None)
        return body

    @model_validator(mode="after")
    def _turn_pro_belongs_to_this_transition(self):
        if self.turn_pro_decisions and self.turn_pro_model is None:
            raise ValueError("Turn Pro decisions require the model policy that made them")
        if any(
            d.effective_week.ordinal != self.target_week.ordinal
            for d in self.turn_pro_decisions
        ):
            raise ValueError("Turn Pro decision is not effective at its transition week")
        ids = [d.player_id for d in self.turn_pro_decisions]
        if ids != sorted(set(ids)):
            raise ValueError("Turn Pro decisions require canonical distinct players")
        return self


def tour_turn_pro_decisions(state) -> tuple[PlayerTurnProDecision, ...]:
    """Every Turn Pro decision recorded by this Tour's Week Transitions."""
    if state is None:
        return ()
    return tuple(
        d for t in getattr(state, "transitions", ()) for d in t.turn_pro_decisions
    )


class CalendarTourState(FrozenInput):
    schema_version: Literal["calendar_tour_authority.v1", "calendar_tour_authority.v2"] = "calendar_tour_authority.v1"
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
                    if key in accepted and authority.edition.schema_version.endswith(".v1"):
                        raise ValueError(
                            "Week Tournament Lock conflict in approved native fields"
                        )
                    if authority.edition.schema_version.endswith(".v1"):
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
                        "Week/Season Transition chronology differs from Official history"
                    )
                crosses = (
                    transition.completed_week.week
                    == transition.completed_week.calendar.weeks_per_year
                    and transition.target_week.week == 1
                    and transition.target_week.season_index
                    == transition.completed_week.season_index + 1
                )
                if crosses and self.schema_version == "calendar_tour_authority.v1":
                    raise ValueError("Historical Tour v1 cannot gain a Season Transition")
                if not crosses and transition.completed_week.season_index != transition.target_week.season_index:
                    raise ValueError("Official Tour cannot skip a season")
                if transition.public_event.get("kind") != (
                    "season_transition_completed" if crosses else "week_transition_completed"
                ):
                    raise ValueError("Native transition kind disagrees with Run calendar")
        if (
            self.schema_version == "calendar_tour_authority.v2"
            and not any(
                t.completed_week.season_index != t.target_week.season_index
                for t in self.transitions
            )
        ):
            raise ValueError("Tour v2 requires an actual Season Transition")
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


def parse_tour_json(raw):
    body = json.loads(raw)
    if isinstance(body, dict) and body.get("schema_version") == "calendar_tour_authority.v5":
        from beta_engine.domain.tournaments.calendar_global_slots import GlobalTourState
        return GlobalTourState.model_validate_json(raw)
    if isinstance(body, dict) and body.get("schema_version") == "calendar_tour_authority.v3":
        from beta_engine.domain.tournaments.calendar_native_tour import (
            CalendarNativeTourState,
        )
        return CalendarNativeTourState.model_validate_json(raw)
    if isinstance(body, dict) and body.get("schema_version") == "calendar_tour_authority.v4":
        from beta_engine.domain.tournaments.calendar_native_tour import (
            CalendarNativeCompetitionTourState,
        )
        return CalendarNativeCompetitionTourState.model_validate_json(raw)
    return CalendarTourState.model_validate_json(raw)


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
    if is_canonical_edition(authority):
        expected_schema = (
            "native_canonical_tournament_result.v2"
            if authority.edition.ranked else "native_canonical_tournament_result.v1"
        )
        if (event.schema_version != expected_schema
            or authority.tournament_fingerprint != played_fingerprint
            or event.edition_authority_fingerprint != authority.execution_fingerprint
            or event.binding != authority.canonical_binding
            or event.draw != authority.draw
            or event.week.ordinal != authority.edition.week.ordinal
            or event.prepared_awards):
            raise ValueError("Canonical result differs from its exact terminal source")
        event.actual_terminal()
        if not authority.edition.ranked:
            return ()
        target = event.week.calendar.position_at_ordinal(event.week.ordinal + 1)
        published = CalendarRankingWeek(season_index=target.season_index, week=target.season_week)
        completed = ranking_week(event.week)
        results = []
        for award in event.ranking_awards:
            qualification = (
                award.ranking_points_awarded
                if award.reached_stage.startswith("qualification_")
                else (award.qualification_points_awarded or 0)
            )
            results.append(CalendarRankingResult(
                edition_id=event.tournament_id,
                player_id=award.player_id,
                source_fingerprint=canonical_hash({
                    "edition": authority.edition.fingerprint,
                    "played": played_fingerprint,
                    "award": award.award_fingerprint,
                }),
                completed_week=completed,
                first_publication_week=published,
                qualification_points=qualification,
                main_points=award.ranking_points_awarded - qualification,
                validity_weeks=authority.edition.validity_weeks,
            ))
        return tuple(results)
    if authority.tournament_fingerprint != played_fingerprint:
        raise ValueError("Edition result is detached from played MatchEngine evidence")
    if (
        event.schema_version not in {"calendar_followup_knockout.v5", "calendar_followup_knockout.v6", "calendar_followup_knockout.v7", "calendar_followup_knockout.v8", "calendar_group_tournament_result.v1", "calendar_group_tournament_result.v2"}
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
    if authority.edition.schema_version == "calendar_tournament_edition.v3":
        from beta_engine.domain.tournaments.calendar_groups import group_point_policy
        valid_policy = event.prepared_policy == group_point_policy(authority)
    else:
        valid_policy = event.prepared_policy is not None and all(
            getattr(event.prepared_policy, stage) == value for stage, value in points.items()
        ) and event.prepared_policy.validity_weeks == authority.edition.validity_weeks
    if not valid_policy:
        raise ValueError("Played point policy differs from the pre-existing Edition table")
    completed = ranking_week(event.week)
    terminal = event.week.ordinal + 1 == event.week.calendar.weeks_per_year * event.week.calendar.season_count
    if not terminal:
        target = event.week.calendar.position_at_ordinal(event.week.ordinal + 1)
        published = CalendarRankingWeek(season_index=target.season_index, week=target.season_week)
    source = {
        "edition": authority.edition.fingerprint,
        "field": authority.field.fingerprint,
        "draw": authority.draw.fingerprint,
        "played": played_fingerprint,
    }
    if terminal:
        inherited = event.schema_version in {"calendar_followup_knockout.v8", "calendar_group_tournament_result.v1", "calendar_group_tournament_result.v2"} and event.branch_id != authority.ranking_authority.branch_id
        if event.run_id != authority.ranking_authority.run_id or event.source_saved_head != authority.played_saved_head or (event.branch_id != authority.ranking_authority.branch_id and not inherited):
            raise ValueError("Terminal Edition has a foreign played owner/source")
        from beta_engine.domain.rankings.calendar_terminal_result import CalendarInheritedTerminalRankingResult
        result_type = CalendarInheritedTerminalRankingResult if inherited else CalendarTerminalRankingResult
        inherited_source = {"source_edition_branch_id":authority.ranking_authority.branch_id} if inherited else {}
        return tuple(result_type(
            **inherited_source,
            run_id=event.run_id, branch_id=event.branch_id,
            edition_id=event.tournament_id, player_id=award.player_id,
            completed_week=event.week, closing_eligibility_ordinal=event.week.ordinal + 1,
            created_saved_head=authority.created_saved_head, played_saved_head=authority.played_saved_head,
            edition_fingerprint=authority.edition.fingerprint,
            execution_fingerprint=authority.execution_fingerprint, played_fingerprint=played_fingerprint,
            source_fingerprint=canonical_hash({**source, "award": award.model_dump(mode="json")}),
            main_points=award.main_points, validity_weeks=authority.edition.validity_weeks,
            ranked=authority.edition.ranked,
        ) for award in event.prepared_awards)
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


def published_edition_results(authority, event, calendar):
    return tuple(
        r.for_publication(calendar) if isinstance(r, CalendarTerminalRankingResult) else r
        for r in edition_results(authority, event)
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


def turn_pro_public_player_ids(decisions):
    """Public part of a transition's Turn Pro decisions: who turned pro, in order.

    The model's chance, draw and source fingerprint stay Admin-only evidence.
    """
    return sorted(
        d["player_id"] if isinstance(d, dict) else d.player_id for d in decisions
    )


def retired_without_turn_pro_player_ids(lifecycle, target):
    """Master v87 decision B: careers that end at ``target`` without Turn Pro.

    Turn Pro is never forced, so in extremely rare cases a generated prospect
    retires without ever becoming a professional. Such a career is recorded as
    an explicit, public exception instead of passing silently.
    """
    if lifecycle is None or not lifecycle.policy.requires_turn_pro:
        return []
    return sorted(
        p.player_id
        for p in lifecycle.players
        if getattr(p, "retirement_effective_week", None) is not None
        and p.retirement_effective_week.ordinal == target.ordinal
        and getattr(p, "tour_entry_week", None) is None
    )


def turn_pro_public_fields(decisions, lifecycle, target):
    """Optional Master v87 public-event fields; empty under the historical rule."""
    fields = {}
    turned = turn_pro_public_player_ids(decisions)
    if turned:
        fields["turned_pro_player_ids"] = turned
    never = retired_without_turn_pro_player_ids(lifecycle, target)
    if never:
        fields["retired_without_turn_pro_player_ids"] = never
    return fields


def turn_pro_home_opportunities(state, target, country_by_player):
    """Master v87: players with a public, not-yet-played Edition in their country.

    Only information known through the end of the completed week is used: the
    Edition must have been announced before ``target`` (an announcement that
    becomes public at this very transition is not yet known) and must be played
    at or after ``target``. Editions without a host country never count.
    """
    hosts = {
        a.edition.host_country_code
        for a in (state.editions if state is not None else ())
        if a.edition.host_country_code is not None
        and a.edition.announcement_week.ordinal < target.ordinal
        and a.edition.week.ordinal >= target.ordinal
    }
    return {
        pid: True for pid, country in sorted(country_by_player.items()) if country in hosts
    }


def professional_ranking_players(lifecycle, *, before=None, retired=()):
    """Master v87 roster: Tour Players come from Turn Pro, not from applications.

    A player whose Turn Pro week precedes ``before`` is in the roster even without
    any application; like an application entrant, a player who turned pro in the
    week being published is not inserted into that already-opened snapshot.
    """
    if not lifecycle.policy.requires_turn_pro:
        raise ValueError("Professional roster requires the v87 lifecycle policy")
    return tuple(
        CalendarRankingPlayer(
            player_id=p.player_id,
            tie_break_token=p.tie_break_token,
            tour_entry_week=ranking_week(p.tour_entry_week),
            retired=p.player_id in retired,
        )
        for p in sorted(lifecycle.players, key=lambda item: item.player_id)
        if getattr(p, "tour_entry_week", None) is not None
        and (before is None or p.tour_entry_week.ordinal < before.ordinal)
    )


def calculate_tour_ranking(state, checkpoint, *, target, retired=(), lifecycle=None):
    events = {t.tournament_id: t for t in checkpoint.tournaments}
    results = tuple(
        r
        for a in state.editions
        if a.result_confirmed and a.edition.week.ordinal < target.ordinal
        for r in published_edition_results(a, events[a.edition.edition_id], target.calendar)
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
        players=(
            professional_ranking_players(lifecycle, before=target, retired=retired)
            if lifecycle is not None and lifecycle.policy.requires_turn_pro
            else ranking_players(state, submissions, retired=retired)
        ),
        results=results,
        previous=state.rankings[-1],
    )

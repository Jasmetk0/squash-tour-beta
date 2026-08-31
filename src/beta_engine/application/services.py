"""Application orchestration services for deterministic season simulation commands."""

from __future__ import annotations

from dataclasses import dataclass, field

from beta_engine.application.season_models import (
    ActiveTournamentState,
    RaceSnapshot,
    RankingSnapshot,
    SeasonSimulationResult,
    SeasonState,
    SimulationStepResult,
    TournamentSimulationResult,
    WeeklySimulationResult,
)
from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.countries import Country
from beta_engine.domain.draws import DrawEngine
from beta_engine.domain.entries import (
    AcceptanceList,
    AcceptanceStatus,
    EntryEngine,
    EntryTuningConfig,
    TournamentEntry,
)
from beta_engine.domain.players import Player
from beta_engine.domain.rankings import (
    CompletedTournamentPointsInput,
    RankingRaceEngine,
    RankingRaceReport,
)
from beta_engine.domain.tournaments import (
    CalendarEvent,
    SeasonCalendar,
    TournamentTemplate,
)
from beta_engine.domain.tournaments.progression import (
    TournamentProgressionEngine,
    TournamentResult,
)


@dataclass(slots=True)
class SeasonSimulationOrchestrator:
    """Coordinates deterministic season flow without persistence/UI concerns."""

    calendar: SeasonCalendar
    templates_by_id: dict[str, TournamentTemplate]
    players_by_id: dict[str, Player]
    countries_by_code: dict[str, Country]
    ranking_engine: RankingRaceEngine
    entry_engine: EntryEngine
    draw_engine: DrawEngine
    progression_engine: TournamentProgressionEngine
    wildcard_assignments_by_event: dict[str, dict[int, str]] = field(default_factory=dict)
    pre_draw_withdrawal_replacements_by_event: dict[str, list[dict[str, object]]] = field(default_factory=dict)
    late_replacements_by_event: dict[str, list[dict[str, object]]] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        calendar: SeasonCalendar,
        templates: list[TournamentTemplate],
        players: list[Player],
        countries_by_code: dict[str, Country],
        points_by_ref: dict[str, dict[str, int]],
        entry_tuning: EntryTuningConfig,
        seed: int,
        wildcard_assignments_by_event: dict[str, dict[int, str]] | None = None,
        pre_draw_withdrawal_replacements_by_event: dict[str, list[dict[str, object]]] | None = None,
        late_replacements_by_event: dict[str, list[dict[str, object]]] | None = None,
    ) -> SeasonSimulationOrchestrator:
        rng = DeterministicRng(seed)
        return cls(
            calendar=calendar,
            templates_by_id={template.template_id: template for template in templates},
            players_by_id={player.player_id: player for player in players},
            countries_by_code=dict(countries_by_code),
            ranking_engine=RankingRaceEngine(point_distributions_by_ref=points_by_ref),
            entry_engine=EntryEngine(rng=rng.branch(SeedScope.SEASON, calendar.season, "entries"), tuning=entry_tuning),
            draw_engine=DrawEngine(rng=rng.branch(SeedScope.SEASON, calendar.season, "draws")),
            progression_engine=TournamentProgressionEngine(
                rng=rng.branch(SeedScope.SEASON, calendar.season, "tournament_progression")
            ),
            wildcard_assignments_by_event=(
                {}
                if wildcard_assignments_by_event is None
                else {event_id: dict(assignments) for event_id, assignments in wildcard_assignments_by_event.items()}
            ),
            pre_draw_withdrawal_replacements_by_event=(
                {}
                if pre_draw_withdrawal_replacements_by_event is None
                else {
                    event_id: [dict(item) for item in replacements]
                    for event_id, replacements in pre_draw_withdrawal_replacements_by_event.items()
                }
            ),
            late_replacements_by_event=(
                {}
                if late_replacements_by_event is None
                else {
                    event_id: [dict(item) for item in replacements]
                    for event_id, replacements in late_replacements_by_event.items()
                }
            ),
        )

    def initialize_state(self) -> SeasonState:
        ordered_events = sorted(self.calendar.events, key=self._event_order_key)
        return SeasonState(season=self.calendar.season, ordered_events=ordered_events)

    def simulate_next_tournament(self, *, state: SeasonState) -> SimulationStepResult:
        self._validate_state(state)
        if state.active_tournament is not None:
            completed_tournament = state.active_tournament.full_result
            next_state = self._finalize_active_tournament(state=state)
            return SimulationStepResult(
                mode="simulate_next_tournament",
                season_state=next_state,
                tournament_result=completed_tournament,
            )
        if not state.has_remaining_events:
            return SimulationStepResult(mode="simulate_next_tournament", season_state=state)

        event = state.ordered_events[state.next_event_index]
        tournament_result, report, completed_inputs = self._simulate_event(event=event, state=state)
        next_state = self._state_after_events(
            state=state,
            processed_events=[event],
            completed_inputs=completed_inputs,
            report=report,
        )
        return SimulationStepResult(
            mode="simulate_next_tournament",
            season_state=next_state,
            tournament_result=tournament_result,
        )

    def simulate_next_week(self, *, state: SeasonState) -> SimulationStepResult:
        self._validate_state(state)
        if state.active_tournament is not None:
            state = self._finalize_active_tournament(state=state)
        if not state.has_remaining_events:
            return SimulationStepResult(mode="simulate_next_week", season_state=state)

        first_event = state.ordered_events[state.next_event_index]
        target_key = (first_event.season, first_event.week)
        week_events: list[CalendarEvent] = []
        for event in state.ordered_events[state.next_event_index :]:
            if (event.season, event.week) != target_key:
                break
            week_events.append(event)

        weekly_result, next_state = self._simulate_events_group(
            state=state,
            events=week_events,
            mode="simulate_next_week",
        )
        return SimulationStepResult(
            mode="simulate_next_week",
            season_state=next_state,
            weekly_result=weekly_result,
        )

    def simulate_full_season(self, *, state: SeasonState) -> SimulationStepResult:
        self._validate_state(state)

        current_state = self._finalize_active_tournament(state=state) if state.active_tournament is not None else state
        weekly_results: list[WeeklySimulationResult] = []
        while current_state.has_remaining_events:
            weekly_step = self.simulate_next_week(state=current_state)
            if weekly_step.weekly_result is None:
                break
            weekly_results.append(weekly_step.weekly_result)
            current_state = weekly_step.season_state

        season_result = SeasonSimulationResult(
            season=current_state.season,
            weekly_results=weekly_results,
            ranking_snapshot=current_state.ranking_snapshot,
            race_snapshot=current_state.race_snapshot,
        )
        return SimulationStepResult(
            mode="simulate_full_season",
            season_state=current_state,
            season_result=season_result,
        )

    def simulate_next_match(self, *, state: SeasonState) -> SimulationStepResult:
        self._validate_state(state)
        if not state.has_remaining_events and state.active_tournament is None:
            return SimulationStepResult(mode="simulate_next_match", season_state=state)

        active_state = state.active_tournament or self._start_active_tournament(state=state)
        next_revealed_count = min(
            active_state.revealed_match_count + 1,
            self._total_match_count(active_state.full_result.tournament_result),
        )
        active_state = active_state.model_copy(update={"revealed_match_count": next_revealed_count})
        updated = state.model_copy(update={"active_tournament": active_state})
        if self._is_tournament_fully_revealed(active_state):
            updated = self._finalize_active_tournament(state=updated)

        return SimulationStepResult(
            mode="simulate_next_match",
            season_state=updated,
            tournament_result=self._visible_tournament_result(state=updated, active_state=active_state),
        )

    def simulate_next_round(self, *, state: SeasonState) -> SimulationStepResult:
        self._validate_state(state)
        if not state.has_remaining_events and state.active_tournament is None:
            return SimulationStepResult(mode="simulate_next_round", season_state=state)

        active_state = state.active_tournament or self._start_active_tournament(state=state)
        round_end_index = self._next_round_end_match_count(
            tournament=active_state.full_result.tournament_result,
            revealed_match_count=active_state.revealed_match_count,
        )
        active_state = active_state.model_copy(update={"revealed_match_count": round_end_index})
        updated = state.model_copy(update={"active_tournament": active_state})
        if self._is_tournament_fully_revealed(active_state):
            updated = self._finalize_active_tournament(state=updated)

        return SimulationStepResult(
            mode="simulate_next_round",
            season_state=updated,
            tournament_result=self._visible_tournament_result(state=updated, active_state=active_state),
        )

    def _simulate_events_group(
        self,
        *,
        state: SeasonState,
        events: list[CalendarEvent],
        mode: str,
    ) -> tuple[WeeklySimulationResult, SeasonState]:
        if not events:
            raise ValueError("events must be non-empty")

        completed_inputs = list(state.completed_tournament_inputs)
        tournament_results: list[TournamentSimulationResult] = []
        report: RankingRaceReport | None = None

        for event in events:
            tournament_result, report, completed_inputs = self._simulate_event(
                event=event,
                state=state.model_copy(update={"completed_tournament_inputs": completed_inputs}),
            )
            tournament_results.append(tournament_result)

        if report is None:
            raise RuntimeError(f"{mode} failed to produce ranking/race report")

        next_state = self._state_after_events(
            state=state,
            processed_events=events,
            completed_inputs=completed_inputs,
            report=report,
        )

        weekly_result = WeeklySimulationResult(
            season=events[0].season,
            week=events[0].week,
            tournaments=tournament_results,
            ranking_snapshot=next_state.ranking_snapshot,
            race_snapshot=next_state.race_snapshot,
        )
        return weekly_result, next_state

    def _simulate_event(
        self,
        *,
        event: CalendarEvent,
        state: SeasonState,
    ) -> tuple[TournamentSimulationResult, RankingRaceReport, list[CompletedTournamentPointsInput]]:
        template = self.templates_by_id[event.template_id]
        players = list(self.players_by_id.values())

        acceptance = self.entry_engine.build_acceptance_list(
            event=event,
            template=template,
            players=players,
            countries_by_code=self.countries_by_code,
        )
        acceptance = self._apply_wildcard_assignments(
            acceptance=acceptance,
            assignments=self.wildcard_assignments_by_event.get(event.event_id, {}),
        )
        acceptance = self._apply_pre_draw_withdrawal_replacements(
            acceptance=acceptance,
            replacements=self.pre_draw_withdrawal_replacements_by_event.get(event.event_id, []),
        )
        acceptance = self._apply_late_replacements(
            acceptance=acceptance,
            replacements=self.late_replacements_by_event.get(event.event_id, []),
        )
        qualification_draw = self.draw_engine.generate_qualification_draw(
            acceptance_list=acceptance,
            template=template,
        )
        main_draw = self.draw_engine.generate_main_draw(
            acceptance_list=acceptance,
            template=template,
        )
        tournament = self.progression_engine.run_tournament(
            event_id=event.event_id,
            season=event.season,
            week=event.week,
            template=template,
            qualification_draw=qualification_draw,
            main_draw=main_draw,
            players_by_id=self.players_by_id,
        )

        completed_input = self._to_completed_points_input(
            event=event,
            template=template,
            tournament=tournament,
        )
        completed_inputs = [*state.completed_tournament_inputs, completed_input]

        report = self.ranking_engine.build_report(
            completed_tournaments=completed_inputs,
            as_of_season=event.season,
            as_of_week=event.week,
            target_season=self.calendar.season,
        )
        ranking_snapshot, race_snapshot = self._build_snapshots(report=report, as_of_season=event.season, as_of_week=event.week)

        result = TournamentSimulationResult(
            event=event,
            acceptance_list=acceptance,
            qualification_draw=qualification_draw,
            main_draw=main_draw,
            tournament_result=tournament,
            ranking_snapshot=ranking_snapshot,
            race_snapshot=race_snapshot,
            completed_tournament_input=completed_input,
        )
        return result, report, completed_inputs

    @staticmethod
    def _apply_wildcard_assignments(*, acceptance: AcceptanceList, assignments: dict[int, str]) -> AcceptanceList:
        if not assignments:
            return acceptance

        wildcard_entries = sorted(
            [entry for entry in acceptance.main_draw_entries if entry.status == AcceptanceStatus.WILD_CARD_PLACEHOLDER],
            key=lambda entry: (10_000 if entry.ranking_priority is None else entry.ranking_priority, entry.entry_id),
        )
        entries_by_slot = {slot_index: entry for slot_index, entry in enumerate(wildcard_entries, start=1)}

        updates_by_entry_id: dict[str, TournamentEntry] = {}
        for slot_index, player_id in assignments.items():
            entry = entries_by_slot.get(slot_index)
            if entry is None:
                continue
            updates_by_entry_id[entry.entry_id] = entry.model_copy(update={"player_id": player_id})

        if not updates_by_entry_id:
            return acceptance

        updated_main_entries = [updates_by_entry_id.get(entry.entry_id, entry) for entry in acceptance.main_draw_entries]
        return acceptance.model_copy(update={"main_draw_entries": updated_main_entries})

    @staticmethod
    def _apply_pre_draw_withdrawal_replacements(
        *,
        acceptance: AcceptanceList,
        replacements: list[dict[str, object]],
    ) -> AcceptanceList:
        if not replacements:
            return acceptance

        entries_by_id = {entry.entry_id: entry for entry in acceptance.main_draw_entries}
        for replacement in replacements:
            withdrawn_entry_id = replacement.get("withdrawn_entry_id")
            replacement_entry_id = replacement.get("replacement_entry_id")
            replacement_player_id = replacement.get("replacement_player_id")
            replacement_source = replacement.get("replacement_source")
            if (
                not isinstance(withdrawn_entry_id, str)
                or not isinstance(replacement_entry_id, str)
                or not isinstance(replacement_player_id, str)
                or replacement_source not in {"main_draw_waitlist", "qualification_waitlist"}
            ):
                continue
            if withdrawn_entry_id not in entries_by_id or replacement_entry_id not in entries_by_id:
                continue

            entries_by_id[withdrawn_entry_id] = entries_by_id[withdrawn_entry_id].model_copy(update={"player_id": None})
            entries_by_id[replacement_entry_id] = entries_by_id[replacement_entry_id].model_copy(
                update={"player_id": replacement_player_id}
            )

        updated_main_entries = [entries_by_id.get(entry.entry_id, entry) for entry in acceptance.main_draw_entries]
        return acceptance.model_copy(update={"main_draw_entries": updated_main_entries})

    @staticmethod
    def _apply_late_replacements(
        *,
        acceptance: AcceptanceList,
        replacements: list[dict[str, object]],
    ) -> AcceptanceList:
        if not replacements:
            return acceptance

        entries_by_id = {entry.entry_id: entry for entry in acceptance.main_draw_entries}
        for replacement in replacements:
            withdrawn_entry_id = replacement.get("withdrawn_entry_id")
            replacement_entry_id = replacement.get("replacement_entry_id")
            replacement_player_id = replacement.get("replacement_player_id")
            replacement_source = replacement.get("replacement_source")
            candidate_slot_index = replacement.get("candidate_slot_index")
            if (
                not isinstance(withdrawn_entry_id, str)
                or not isinstance(replacement_entry_id, str)
                or not isinstance(replacement_player_id, str)
                or replacement_source not in {"main_draw_waitlist", "qualification_waitlist"}
                or (candidate_slot_index is not None and not isinstance(candidate_slot_index, int))
            ):
                continue
            if withdrawn_entry_id not in entries_by_id or replacement_entry_id not in entries_by_id:
                continue

            entries_by_id[withdrawn_entry_id] = entries_by_id[withdrawn_entry_id].model_copy(update={"player_id": None})
            entries_by_id[replacement_entry_id] = entries_by_id[replacement_entry_id].model_copy(
                update={"player_id": replacement_player_id}
            )

        updated_main_entries = [entries_by_id.get(entry.entry_id, entry) for entry in acceptance.main_draw_entries]
        return acceptance.model_copy(update={"main_draw_entries": updated_main_entries})

    def _state_after_events(
        self,
        *,
        state: SeasonState,
        processed_events: list[CalendarEvent],
        completed_inputs: list[CompletedTournamentPointsInput],
        report: RankingRaceReport,
    ) -> SeasonState:
        last_event = processed_events[-1]
        ranking_snapshot, race_snapshot = self._build_snapshots(
            report=report,
            as_of_season=last_event.season,
            as_of_week=last_event.week,
        )
        return state.model_copy(
            update={
                "next_event_index": state.next_event_index + len(processed_events),
                "completed_event_ids": [*state.completed_event_ids, *(event.event_id for event in processed_events)],
                "completed_tournament_inputs": completed_inputs,
                "ranking_snapshot": ranking_snapshot,
                "race_snapshot": race_snapshot,
            }
        )

    def _start_active_tournament(self, *, state: SeasonState) -> ActiveTournamentState:
        event = state.ordered_events[state.next_event_index]
        tournament_result, _, _ = self._simulate_event(event=event, state=state)
        return ActiveTournamentState(event=event, full_result=tournament_result, revealed_match_count=0)

    def _finalize_active_tournament(self, *, state: SeasonState) -> SeasonState:
        active = state.active_tournament
        if active is None:
            return state
        if (
            active.full_result.ranking_snapshot is None
            or active.full_result.race_snapshot is None
            or active.full_result.completed_tournament_input is None
        ):
            raise ValueError("active tournament finalization requires complete tournament artifacts")

        return state.model_copy(
            update={
                "next_event_index": state.next_event_index + 1,
                "completed_event_ids": [*state.completed_event_ids, active.event.event_id],
                "completed_tournament_inputs": [*state.completed_tournament_inputs, active.full_result.completed_tournament_input],
                "ranking_snapshot": active.full_result.ranking_snapshot,
                "race_snapshot": active.full_result.race_snapshot,
                "active_tournament": None,
            }
        )

    @staticmethod
    def _is_tournament_fully_revealed(active_state: ActiveTournamentState) -> bool:
        return active_state.revealed_match_count >= SeasonSimulationOrchestrator._total_match_count(active_state.full_result.tournament_result)

    @staticmethod
    def _total_match_count(tournament: TournamentResult) -> int:
        qualification = sum(len(round_result.matches) for round_result in tournament.qualification.rounds)
        main_draw = sum(len(round_result.matches) for round_result in tournament.main_draw.rounds)
        return qualification + main_draw

    @staticmethod
    def _next_round_end_match_count(*, tournament: TournamentResult, revealed_match_count: int) -> int:
        offset = 0
        for round_result in [*tournament.qualification.rounds, *tournament.main_draw.rounds]:
            offset += len(round_result.matches)
            if revealed_match_count < offset:
                return offset
        return offset

    def _visible_tournament_result(
        self,
        *,
        state: SeasonState,
        active_state: ActiveTournamentState,
    ) -> TournamentSimulationResult:
        full = active_state.full_result
        visible_qualification, remaining = self._truncate_rounds(
            rounds=full.tournament_result.qualification.rounds,
            reveal_budget=active_state.revealed_match_count,
        )
        visible_main, _ = self._truncate_rounds(
            rounds=full.tournament_result.main_draw.rounds,
            reveal_budget=remaining,
        )
        is_complete = state.active_tournament is None
        tournament_payload = full.tournament_result.model_copy(
            update={
                "qualification": full.tournament_result.qualification.model_copy(
                    update={
                        "rounds": visible_qualification,
                        "qualifiers_in_order": (
                            full.tournament_result.qualification.qualifiers_in_order
                            if visible_qualification == full.tournament_result.qualification.rounds
                            else []
                        ),
                    }
                ),
                "qualifier_slot_resolutions": (
                    full.tournament_result.qualifier_slot_resolutions
                    if visible_qualification == full.tournament_result.qualification.rounds
                    else []
                ),
                "main_draw": full.tournament_result.main_draw.model_copy(
                    update={
                        "rounds": visible_main,
                        "champion_player_id": full.tournament_result.main_draw.champion_player_id if is_complete else None,
                        "finalist_player_id": full.tournament_result.main_draw.finalist_player_id if is_complete else None,
                        "placements": full.tournament_result.main_draw.placements if is_complete else [],
                    }
                ),
            }
        )
        if is_complete:
            return full.model_copy(update={"tournament_result": tournament_payload})
        return full.model_copy(
            update={
                "tournament_result": tournament_payload,
                "ranking_snapshot": None,
                "race_snapshot": None,
                "completed_tournament_input": None,
            }
        )

    @staticmethod
    def _truncate_rounds(
        *,
        rounds: list,
        reveal_budget: int,
    ) -> tuple[list, int]:
        visible = []
        remaining = reveal_budget
        for round_result in rounds:
            if remaining <= 0:
                break
            if remaining >= len(round_result.matches):
                visible.append(round_result)
                remaining -= len(round_result.matches)
                continue

            visible.append(round_result.model_copy(update={"matches": round_result.matches[:remaining]}))
            remaining = 0
        return visible, remaining

    def _build_snapshots(self, *, report: RankingRaceReport, as_of_season: int, as_of_week: int) -> tuple[RankingSnapshot, RaceSnapshot]:
        ranking = RankingSnapshot(as_of_season=as_of_season, as_of_week=as_of_week, report=report)
        race = RaceSnapshot(
            target_season=self.calendar.season,
            as_of_season=as_of_season,
            as_of_week=as_of_week,
            report=report,
        )
        return ranking, race

    @staticmethod
    def _to_completed_points_input(
        *,
        event: CalendarEvent,
        template: TournamentTemplate,
        tournament: TournamentResult,
    ) -> CompletedTournamentPointsInput:
        return CompletedTournamentPointsInput(
            event_id=event.event_id,
            season=event.season,
            week=event.week,
            template_id=template.template_id,
            point_distribution_ref=template.point_distribution_ref,
            point_distribution=(
                template.point_distribution.model_dump() if template.point_distribution is not None else None
            ),
            placements=[placement.model_dump() for placement in tournament.main_draw.placements],
            rounds=[
                {
                    "round_number": round_result.round_number,
                    "matches": [
                        {"loser_player_id": match.loser_player_id}
                        for match in round_result.matches
                        if match.loser_player_id is not None
                    ],
                }
                for round_result in tournament.main_draw.rounds
            ],
        )

    def _validate_state(self, state: SeasonState) -> None:
        if state.season != self.calendar.season:
            raise ValueError(
                f"SeasonState season {state.season} does not match orchestrator calendar season {self.calendar.season}"
            )
        if state.next_event_index > len(state.ordered_events):
            raise ValueError("SeasonState next_event_index cannot exceed event count")
        missing_templates = [event.template_id for event in state.ordered_events if event.template_id not in self.templates_by_id]
        if missing_templates:
            raise ValueError(f"SeasonState includes events with missing templates: {sorted(set(missing_templates))}")

    @staticmethod
    def _event_order_key(event: CalendarEvent) -> tuple[int, int, str]:
        return (event.season, event.week, event.event_id)

"""Application orchestration services for deterministic season simulation commands."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.countries import Country
from beta_engine.domain.draws import DrawEngine
from beta_engine.domain.entries import EntryEngine, EntryTuningConfig
from beta_engine.domain.players import Player
from beta_engine.domain.rankings import CompletedTournamentPointsInput, RankingRaceEngine, RankingRaceReport
from beta_engine.domain.tournaments import CalendarEvent, SeasonCalendar, TournamentTemplate
from beta_engine.domain.tournaments.progression import TournamentProgressionEngine, TournamentResult

from beta_engine.application.season_models import (
    RaceSnapshot,
    RankingSnapshot,
    SeasonSimulationResult,
    SeasonState,
    SimulationStepResult,
    TournamentSimulationResult,
    WeeklySimulationResult,
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
    ) -> "SeasonSimulationOrchestrator":
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
        )

    def initialize_state(self) -> SeasonState:
        ordered_events = sorted(self.calendar.events, key=self._event_order_key)
        return SeasonState(season=self.calendar.season, ordered_events=ordered_events)

    def simulate_next_tournament(self, *, state: SeasonState) -> SimulationStepResult:
        self._validate_state(state)
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

        current_state = state
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
            rounds=[round_result.model_dump() for round_result in tournament.main_draw.rounds],
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

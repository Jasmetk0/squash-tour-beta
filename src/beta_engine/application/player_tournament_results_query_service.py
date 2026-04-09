"""Read-side query service for truthful player tournament results timeline."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from beta_engine.application.season_models import RankingSnapshot
from beta_engine.domain.players import Player
from beta_engine.domain.tournaments import TournamentTemplate
from beta_engine.infrastructure.db import SimulationPersistenceRepository, SimulationRunInfo
from beta_engine.infrastructure.db.repositories import PersistedCompletedEventRecord
from beta_engine.infrastructure.tournament_config import load_tournament_templates_config


@dataclass(frozen=True)
class PlayerTournamentResultEntry:
    run_id: str
    season: int
    week: int | None
    event_sequence: int
    event_id: str
    event_name: str | None
    event_category: str | None
    template_id: str | None
    finish: str | None
    is_title: bool
    wins: int
    losses: int
    ranking_points_awarded: int | None


@dataclass(frozen=True)
class PlayerTournamentResultsTimeline:
    requested_run_id: str
    player_id: str
    player_name: str | None
    country_code: str | None
    entries: list[PlayerTournamentResultEntry]


class PlayerTournamentResultsQueryService:
    """Builds chronological tournament outcomes from persisted completed-event records."""

    def __init__(
        self,
        *,
        repository: SimulationPersistenceRepository,
        load_players_for_run: Callable[[SimulationRunInfo], dict[str, Player]],
    ) -> None:
        self._repository = repository
        self._load_players_for_run = load_players_for_run

    def get_player_tournament_results_timeline(self, *, run_id: str, player_id: str) -> PlayerTournamentResultsTimeline:
        requested_run = self._repository.get_simulation_run(run_id=run_id)
        if requested_run is None:
            raise KeyError(f"run_id {run_id} was not found")

        requested_players = self._load_players_for_run(requested_run)
        requested_player = requested_players.get(player_id)
        if requested_player is None:
            raise KeyError(f"player_id {player_id} was not found in run_id {run_id}")

        templates_by_id = {template.template_id: template for template in load_tournament_templates_config().templates}
        connected_runs = self._resolve_connected_lineage_runs(run_id=run_id)

        entries: list[PlayerTournamentResultEntry] = []
        for run_info in connected_runs:
            players_by_id = self._load_players_for_run(run_info)
            if player_id not in players_by_id:
                continue

            ranking_points_by_event = self._resolve_ranking_points_for_run(run_id=run_info.run_id, player_id=player_id)
            for event in self._repository.list_completed_events(run_id=run_info.run_id):
                result_entry = self._to_result_entry(
                    run_info=run_info,
                    event=event,
                    player_id=player_id,
                    templates_by_id=templates_by_id,
                    ranking_points_by_event=ranking_points_by_event,
                )
                if result_entry is not None:
                    entries.append(result_entry)

        ordered_entries = sorted(
            entries,
            key=lambda item: (
                item.season,
                item.week if item.week is not None else 999,
                item.event_sequence,
                item.run_id,
                item.event_id,
            ),
        )
        return PlayerTournamentResultsTimeline(
            requested_run_id=run_id,
            player_id=player_id,
            player_name=requested_player.name,
            country_code=requested_player.nationality,
            entries=ordered_entries,
        )

    def _resolve_connected_lineage_runs(self, *, run_id: str) -> list[SimulationRunInfo]:
        all_runs = self._repository.list_simulation_runs()
        runs_by_id = {run.run_id: run for run in all_runs}

        requested = runs_by_id.get(run_id)
        if requested is None:
            return []

        root = requested
        while root.parent_run_id is not None and root.parent_run_id in runs_by_id:
            root = runs_by_id[root.parent_run_id]

        children_by_parent: dict[str, list[SimulationRunInfo]] = defaultdict(list)
        for run in all_runs:
            if run.parent_run_id is not None:
                children_by_parent[run.parent_run_id].append(run)

        ordered: list[SimulationRunInfo] = []
        stack = [root]
        visited: set[str] = set()
        while stack:
            current = stack.pop()
            if current.run_id in visited:
                continue
            visited.add(current.run_id)
            ordered.append(current)
            for child in sorted(children_by_parent.get(current.run_id, []), key=lambda item: item.run_id, reverse=True):
                stack.append(child)

        return ordered

    def _resolve_ranking_points_for_run(self, *, run_id: str, player_id: str) -> dict[tuple[str, int, int], int]:
        snapshots = self._repository.list_ranking_snapshots(run_id=run_id)
        if not snapshots:
            return {}
        latest_snapshot: RankingSnapshot = snapshots[-1][3]
        for standing in latest_snapshot.report.ranking.standings:
            if standing.player_id != player_id:
                continue
            return {
                (contribution.event_id, contribution.season, contribution.week): contribution.points_awarded
                for contribution in standing.contributions
            }
        return {}

    def _to_result_entry(
        self,
        *,
        run_info: SimulationRunInfo,
        event: PersistedCompletedEventRecord,
        player_id: str,
        templates_by_id: dict[str, TournamentTemplate],
        ranking_points_by_event: dict[tuple[str, int, int], int],
    ) -> PlayerTournamentResultEntry | None:
        if event.tournament_result is None:
            return None

        placements = self._normalize_placements(event)
        player_finishes = [
            placement.get("finish")
            for placement in placements
            if placement.get("player_id") == player_id and isinstance(placement.get("finish"), str)
        ]
        finish = self._best_finish(player_finishes)

        wins, losses, match_presence = self._count_wins_losses(event=event, player_id=player_id)
        placement_presence = any(placement.get("player_id") == player_id for placement in placements)
        if not placement_presence and not match_presence:
            return None

        template = templates_by_id.get(event.template_id) if event.template_id is not None else None

        points_key = None
        if event.season is not None and event.week is not None:
            points_key = (event.event_id, event.season, event.week)
        ranking_points_awarded = ranking_points_by_event.get(points_key) if points_key is not None else None

        return PlayerTournamentResultEntry(
            run_id=run_info.run_id,
            season=event.season if event.season is not None else run_info.season,
            week=event.week,
            event_sequence=event.event_sequence,
            event_id=event.event_id,
            event_name=template.event_name if template is not None else None,
            event_category=template.category if template is not None else None,
            template_id=event.template_id,
            finish=finish,
            is_title=finish == "CHAMPION",
            wins=wins,
            losses=losses,
            ranking_points_awarded=ranking_points_awarded,
        )

    @staticmethod
    def _normalize_placements(event: PersistedCompletedEventRecord) -> list[dict[str, object]]:
        if event.tournament_result is None:
            return []
        main_draw = event.tournament_result.get("main_draw")
        if not isinstance(main_draw, dict):
            return []
        placements = main_draw.get("placements")
        if not isinstance(placements, list):
            return []
        return [placement for placement in placements if isinstance(placement, dict)]

    @staticmethod
    def _best_finish(finishes: list[str]) -> str | None:
        if not finishes:
            return None
        order = {
            "CHAMPION": 0,
            "FINALIST": 1,
            "SEMIFINALIST": 2,
            "QUARTERFINALIST": 3,
            "ROUND_OF_16": 4,
            "ROUND_OF_32": 5,
        }
        return min(finishes, key=lambda finish: (order.get(finish, 999), finish))

    @staticmethod
    def _count_wins_losses(*, event: PersistedCompletedEventRecord, player_id: str) -> tuple[int, int, bool]:
        if event.tournament_result is None:
            return 0, 0, False

        wins = 0
        losses = 0
        seen_match = False

        for draw_key in ("qualification", "main_draw"):
            draw_payload = event.tournament_result.get(draw_key)
            if not isinstance(draw_payload, dict):
                continue
            rounds = draw_payload.get("rounds")
            if not isinstance(rounds, list):
                continue
            for round_payload in rounds:
                if not isinstance(round_payload, dict):
                    continue
                matches = round_payload.get("matches")
                if not isinstance(matches, list):
                    continue
                for match in matches:
                    if not isinstance(match, dict):
                        continue
                    top_player_id = match.get("top_player_id")
                    bottom_player_id = match.get("bottom_player_id")
                    winner_player_id = match.get("winner_player_id")
                    loser_player_id = match.get("loser_player_id")
                    disposition = match.get("disposition")
                    if not isinstance(disposition, str) or disposition == "UNRESOLVED":
                        continue
                    if top_player_id != player_id and bottom_player_id != player_id:
                        continue

                    seen_match = True
                    opponent_id = bottom_player_id if top_player_id == player_id else top_player_id
                    if not isinstance(opponent_id, str) or not opponent_id:
                        continue
                    if winner_player_id == player_id:
                        wins += 1
                    elif loser_player_id == player_id:
                        losses += 1

        return wins, losses, seen_match

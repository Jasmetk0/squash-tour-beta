from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from beta_engine.application.season_models import RaceSnapshot, RankingSnapshot
from beta_engine.domain.players import Player
from beta_engine.infrastructure.db import SimulationPersistenceRepository, SimulationRunInfo
from beta_engine.infrastructure.db.repositories import PersistedCompletedEventRecord


@dataclass(frozen=True)
class PlayerCareerSeasonPerformanceEntry:
    run_id: str
    season: int
    ranking_position: int | None
    race_position: int | None
    tournaments_played: int
    titles: int
    finals: int
    semifinals: int
    quarterfinals: int
    wins: int
    losses: int


@dataclass(frozen=True)
class PlayerCareerPerformance:
    requested_run_id: str
    player_id: str
    player_name: str | None
    country_code: str | None
    entries: list[PlayerCareerSeasonPerformanceEntry]


@dataclass(frozen=True)
class _SeasonAggregate:
    tournaments_played: int
    titles: int
    finals: int
    semifinals: int
    quarterfinals: int
    wins: int
    losses: int


class PlayerCareerPerformanceQueryService:
    """Builds truthful per-season performance snapshots across connected run lineage."""

    def __init__(
        self,
        *,
        repository: SimulationPersistenceRepository,
        load_players_for_run: Callable[[SimulationRunInfo], dict[str, Player]],
    ) -> None:
        self._repository = repository
        self._load_players_for_run = load_players_for_run

    def get_player_career_performance(self, *, run_id: str, player_id: str) -> PlayerCareerPerformance:
        requested_run = self._repository.get_simulation_run(run_id=run_id)
        if requested_run is None:
            raise KeyError(f"run_id {run_id} was not found")

        requested_players = self._load_players_for_run(requested_run)
        requested_player = requested_players.get(player_id)
        if requested_player is None:
            raise KeyError(f"player_id {player_id} was not found in run_id {run_id}")

        connected_runs = self._resolve_connected_lineage_runs(run_id=run_id)
        entries: list[PlayerCareerSeasonPerformanceEntry] = []
        for run_info in connected_runs:
            players_by_id = self._load_players_for_run(run_info)
            if player_id not in players_by_id:
                continue

            ranking_position = self._resolve_ranking_position(run_id=run_info.run_id, player_id=player_id)
            race_position = self._resolve_race_position(run_id=run_info.run_id, player_id=player_id)
            aggregate = self._aggregate_season_results(run_id=run_info.run_id, player_id=player_id)

            entries.append(
                PlayerCareerSeasonPerformanceEntry(
                    run_id=run_info.run_id,
                    season=run_info.season,
                    ranking_position=ranking_position,
                    race_position=race_position,
                    tournaments_played=aggregate.tournaments_played,
                    titles=aggregate.titles,
                    finals=aggregate.finals,
                    semifinals=aggregate.semifinals,
                    quarterfinals=aggregate.quarterfinals,
                    wins=aggregate.wins,
                    losses=aggregate.losses,
                )
            )

        ordered_entries = sorted(entries, key=lambda item: (item.season, item.run_id))
        return PlayerCareerPerformance(
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

    def _resolve_ranking_position(self, *, run_id: str, player_id: str) -> int | None:
        snapshots = self._repository.list_ranking_snapshots(run_id=run_id)
        if not snapshots:
            return None
        latest = snapshots[-1][3]
        return self._rank_from_ranking_snapshot(snapshot=latest, player_id=player_id)

    def _resolve_race_position(self, *, run_id: str, player_id: str) -> int | None:
        snapshots = self._repository.list_race_snapshots(run_id=run_id)
        if not snapshots:
            return None
        latest = snapshots[-1][3]
        return self._rank_from_race_snapshot(snapshot=latest, player_id=player_id)

    def _aggregate_season_results(self, *, run_id: str, player_id: str) -> _SeasonAggregate:
        events = self._repository.list_completed_events(run_id=run_id)
        tournaments_played = 0
        titles = 0
        finals = 0
        semifinals = 0
        quarterfinals = 0
        wins = 0
        losses = 0

        for event in events:
            if event.tournament_result is None:
                continue
            player_in_event = False

            placements = self._normalize_placements(event)
            for placement in placements:
                if placement.get("player_id") != player_id:
                    continue
                player_in_event = True
                finish = placement.get("finish")
                if finish == "CHAMPION":
                    titles += 1
                elif finish == "FINALIST":
                    finals += 1
                elif finish == "SEMIFINALIST":
                    semifinals += 1
                elif finish == "QUARTERFINALIST":
                    quarterfinals += 1

            event_wins, event_losses, match_presence = self._count_wins_losses(event=event, player_id=player_id)
            wins += event_wins
            losses += event_losses
            player_in_event = player_in_event or match_presence

            if player_in_event:
                tournaments_played += 1

        return _SeasonAggregate(
            tournaments_played=tournaments_played,
            titles=titles,
            finals=finals,
            semifinals=semifinals,
            quarterfinals=quarterfinals,
            wins=wins,
            losses=losses,
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

    @staticmethod
    def _rank_from_ranking_snapshot(*, snapshot: RankingSnapshot, player_id: str) -> int | None:
        for standing in snapshot.report.ranking.standings:
            if standing.player_id == player_id:
                return standing.rank
        return None

    @staticmethod
    def _rank_from_race_snapshot(*, snapshot: RaceSnapshot, player_id: str) -> int | None:
        for standing in snapshot.report.race.standings:
            if standing.player_id == player_id:
                return standing.rank
        return None

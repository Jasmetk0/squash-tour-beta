"""Deterministic ranking/race engine for tournament-result derived points."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from beta_engine.domain.rankings.models import (
    CompletedTournamentPointsInput,
    PlayerRaceEntry,
    PlayerRankingEntry,
    RaceTable,
    RankedResultContribution,
    RankingRaceReport,
    RankingTable,
    TournamentPointAward,
)

FINISH_TO_POINTS_KEY: dict[str, str] = {
    "CHAMPION": "winner",
    "FINALIST": "finalist",
    "SEMIFINALIST": "semifinalist",
    "QUARTERFINALIST": "quarterfinalist",
    "ROUND_OF_16": "round_of_16",
    "ROUND_OF_32": "round_of_32",
}


@dataclass(slots=True)
class RankingRaceEngine:
    """Pure ranking/race domain service over completed tournament inputs."""

    point_distributions_by_ref: dict[str, dict[str, int]]

    def build_report(
        self,
        *,
        completed_tournaments: list[CompletedTournamentPointsInput],
        as_of_season: int,
        as_of_week: int,
        target_season: int,
        window_weeks: int = 61,
        best_of_results: int = 12,
    ) -> RankingRaceReport:
        awards = self.resolve_point_awards(completed_tournaments=completed_tournaments)
        ranking = self._build_ranking(
            awards=awards,
            as_of_season=as_of_season,
            as_of_week=as_of_week,
            window_weeks=window_weeks,
            best_of_results=best_of_results,
            target_season=target_season,
        )
        race = self._build_race(awards=awards, target_season=target_season)
        return RankingRaceReport(point_awards=awards, ranking=ranking, race=race)

    def resolve_point_awards(
        self,
        *,
        completed_tournaments: list[CompletedTournamentPointsInput],
    ) -> list[TournamentPointAward]:
        awards: list[TournamentPointAward] = []
        for tournament in sorted(completed_tournaments, key=self._tournament_order_key):
            point_distribution = self._resolve_point_distribution(tournament)
            for player_id, finish in self._extract_finishes(tournament):
                points_key = FINISH_TO_POINTS_KEY.get(finish)
                points = 0 if points_key is None else int(point_distribution.get(points_key, 0))
                awards.append(
                    TournamentPointAward(
                        event_id=tournament.event_id,
                        season=tournament.season,
                        week=tournament.week,
                        template_id=tournament.template_id,
                        player_id=player_id,
                        finish=finish,
                        points_awarded=max(0, points),
                    )
                )
        return awards

    def _build_ranking(
        self,
        *,
        awards: list[TournamentPointAward],
        as_of_season: int,
        as_of_week: int,
        window_weeks: int,
        best_of_results: int,
        target_season: int,
    ) -> RankingTable:
        by_player: dict[str, list[TournamentPointAward]] = defaultdict(list)
        as_of_key = self._week_key(as_of_season, as_of_week)

        for award in awards:
            if self._in_rolling_window(award=award, as_of_key=as_of_key, window_weeks=window_weeks):
                by_player[award.player_id].append(award)

        standings: list[PlayerRankingEntry] = []
        for player_id, player_awards in sorted(by_player.items()):
            best_awards = sorted(player_awards, key=self._best_result_order_key)[:best_of_results]
            best_keys = {(a.event_id, a.player_id, a.finish) for a in best_awards}
            contributions = [
                RankedResultContribution(
                    event_id=award.event_id,
                    season=award.season,
                    week=award.week,
                    finish=award.finish,
                    points_awarded=award.points_awarded,
                    active_in_rolling_window=True,
                    counted_in_best_12=(award.event_id, award.player_id, award.finish) in best_keys,
                    counted_in_race=award.season == target_season,
                )
                for award in sorted(player_awards, key=self._contribution_order_key)
            ]
            points = sum(c.points_awarded for c in contributions if c.counted_in_best_12)
            counted_results = sum(1 for c in contributions if c.counted_in_best_12)
            standings.append(
                PlayerRankingEntry(
                    rank=1,
                    player_id=player_id,
                    ranking_points=points,
                    counted_results=counted_results,
                    contributions=contributions,
                )
            )

        ordered = sorted(
            standings,
            key=lambda e: (-e.ranking_points, -e.counted_results, e.player_id),
        )
        with_ranks = [entry.model_copy(update={"rank": i + 1}) for i, entry in enumerate(ordered)]
        return RankingTable(
            as_of_season=as_of_season,
            as_of_week=as_of_week,
            window_weeks=window_weeks,
            best_of_results=best_of_results,
            standings=with_ranks,
        )

    def _build_race(self, *, awards: list[TournamentPointAward], target_season: int) -> RaceTable:
        by_player: dict[str, list[TournamentPointAward]] = defaultdict(list)
        for award in awards:
            if award.season == target_season:
                by_player[award.player_id].append(award)

        standings: list[PlayerRaceEntry] = []
        for player_id, player_awards in sorted(by_player.items()):
            contributions = [
                RankedResultContribution(
                    event_id=award.event_id,
                    season=award.season,
                    week=award.week,
                    finish=award.finish,
                    points_awarded=award.points_awarded,
                    active_in_rolling_window=False,
                    counted_in_best_12=False,
                    counted_in_race=True,
                )
                for award in sorted(player_awards, key=self._contribution_order_key)
            ]
            standings.append(
                PlayerRaceEntry(
                    rank=1,
                    player_id=player_id,
                    race_points=sum(c.points_awarded for c in contributions),
                    counted_results=len(contributions),
                    contributions=contributions,
                )
            )

        ordered = sorted(
            standings,
            key=lambda e: (-e.race_points, -e.counted_results, e.player_id),
        )
        with_ranks = [entry.model_copy(update={"rank": i + 1}) for i, entry in enumerate(ordered)]
        return RaceTable(target_season=target_season, standings=with_ranks)

    def _resolve_point_distribution(self, tournament: CompletedTournamentPointsInput) -> dict[str, int]:
        if tournament.point_distribution is not None:
            return dict(tournament.point_distribution)
        if tournament.point_distribution_ref is None:
            raise ValueError(
                f"Tournament {tournament.event_id} must provide point_distribution or point_distribution_ref"
            )
        if tournament.point_distribution_ref not in self.point_distributions_by_ref:
            raise ValueError(
                f"Tournament {tournament.event_id} references unknown point distribution: "
                f"{tournament.point_distribution_ref}"
            )
        return dict(self.point_distributions_by_ref[tournament.point_distribution_ref])

    def _extract_finishes(self, tournament: CompletedTournamentPointsInput) -> list[tuple[str, str]]:
        results: dict[tuple[str, str], None] = {}
        for placement in tournament.placements:
            player_id = placement.get("player_id")
            finish = placement.get("finish")
            if player_id and finish:
                results[(player_id, finish)] = None

        if tournament.rounds:
            max_round = max((int(round_result.get("round_number", 0)) for round_result in tournament.rounds), default=0)
            for round_result in tournament.rounds:
                round_number = int(round_result.get("round_number", 0))
                finish = self._round_loser_finish(round_number=round_number, final_round=max_round)
                if finish is None:
                    continue
                for match in round_result.get("matches", []):
                    loser_id = match.get("loser_player_id")
                    if loser_id:
                        results[(loser_id, finish)] = None

        return sorted(results.keys(), key=lambda item: (item[0], item[1]))

    @staticmethod
    def _round_loser_finish(*, round_number: int, final_round: int) -> str | None:
        delta = final_round - round_number
        if delta == 0:
            return "FINALIST"
        if delta == 1:
            return "SEMIFINALIST"
        if delta == 2:
            return "QUARTERFINALIST"
        if delta == 3:
            return "ROUND_OF_16"
        if delta == 4:
            return "ROUND_OF_32"
        return None

    @staticmethod
    def _week_key(season: int, week: int) -> int:
        return season * 61 + week

    def _in_rolling_window(self, *, award: TournamentPointAward, as_of_key: int, window_weeks: int) -> bool:
        delta = as_of_key - self._week_key(award.season, award.week)
        return 0 <= delta < window_weeks

    @staticmethod
    def _tournament_order_key(tournament: CompletedTournamentPointsInput) -> tuple[int, int, str]:
        return (tournament.season, tournament.week, tournament.event_id)

    @staticmethod
    def _best_result_order_key(award: TournamentPointAward) -> tuple[int, int, int, str, str]:
        return (-award.points_awarded, -award.season, -award.week, award.event_id, award.finish)

    @staticmethod
    def _contribution_order_key(award: TournamentPointAward) -> tuple[int, int, str, str]:
        return (award.season, award.week, award.event_id, award.finish)

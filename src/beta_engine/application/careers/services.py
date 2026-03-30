"""Application services for deterministic season rollover and career progression."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.domain.careers import CareerProgressionEngine, SeasonHealthInput, SeasonRolloverResult
from beta_engine.domain.players import Player
from beta_engine.domain.rankings import CompletedTournamentPointsInput


@dataclass(slots=True)
class SeasonRolloverService:
    """Transforms one completed season player pool into next season states."""

    progression_engine: CareerProgressionEngine

    def rollover(
        self,
        *,
        season: int,
        players: list[Player],
        completed_tournaments: list[CompletedTournamentPointsInput] | None = None,
        health_inputs_by_player_id: dict[str, SeasonHealthInput] | None = None,
    ) -> SeasonRolloverResult:
        derived_health = self._derive_health_inputs(
            players=players,
            completed_tournaments=completed_tournaments or [],
        )
        explicit_inputs = health_inputs_by_player_id or {}
        merged_health = {
            player.player_id: explicit_inputs.get(player.player_id, derived_health.get(player.player_id, SeasonHealthInput()))
            for player in players
        }
        return self.progression_engine.rollover_season(
            season=season,
            players=players,
            health_inputs_by_player_id=merged_health,
        )

    @staticmethod
    def _derive_health_inputs(
        *,
        players: list[Player],
        completed_tournaments: list[CompletedTournamentPointsInput],
    ) -> dict[str, SeasonHealthInput]:
        players_by_id = {player.player_id: player for player in players}
        matches_played: dict[str, int] = {player.player_id: 0 for player in players}
        retirement_losses: dict[str, int] = {player.player_id: 0 for player in players}

        for tournament in completed_tournaments:
            for round_payload in tournament.rounds:
                matches = round_payload.get("matches", []) if isinstance(round_payload, dict) else []
                for match in matches:
                    if not isinstance(match, dict):
                        continue
                    if match.get("disposition") != "PLAYED":
                        continue

                    for side in ("top_player_id", "bottom_player_id"):
                        player_id = match.get(side)
                        if player_id in matches_played:
                            matches_played[player_id] += 1

                    termination_reason = None
                    match_result = match.get("match_result")
                    if isinstance(match_result, dict):
                        termination_reason = match_result.get("termination_reason")
                    loser_id = match.get("loser_player_id")
                    if termination_reason == "RETIREMENT" and loser_id in retirement_losses:
                        retirement_losses[loser_id] += 1

        if matches_played:
            max_matches = max(matches_played.values())
        else:
            max_matches = 0

        health: dict[str, SeasonHealthInput] = {}
        for player_id, player in players_by_id.items():
            played = matches_played[player_id]
            retirement_count = retirement_losses[player_id]
            normalized_workload = (played / max_matches) if max_matches > 0 else 0.0
            fatigue = min(1.0, normalized_workload * 0.7 + (1.0 - player.recovery / 99.0) * 0.25)
            wear = min(1.0, normalized_workload * 0.65 + player.hidden_career_traits.injury_proneness * 0.2)
            health[player_id] = SeasonHealthInput(
                fatigue_load=round(fatigue, 4),
                wear_load=round(wear, 4),
                injury_events=retirement_count,
            )

        return health

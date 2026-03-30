"""Deterministic World Tour Finals qualification/seeding/event simulation engine."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.finals.models import (
    FinalsGroup,
    FinalsGroupMatch,
    FinalsGroupSlot,
    FinalsGroupStandingEntry,
    FinalsKnockoutMatch,
    FinalsPlacement,
    FinalsQualificationResult,
    FinalsQualifiedPlayer,
    FinalsResult,
)
from beta_engine.domain.matches import MatchContext, MatchEngine, MatchParticipantContext
from beta_engine.domain.players import Player
from beta_engine.domain.rankings import RaceTable


@dataclass(slots=True)
class FinalsEngine:
    """Pure deterministic service for module-12 World Tour Finals flow."""

    rng: DeterministicRng
    qualifier_count: int = 8
    reserve_count: int = 2

    def build_qualification(self, *, race_table: RaceTable, players_by_id: dict[str, Player]) -> FinalsQualificationResult:
        eligible = [entry for entry in race_table.standings if entry.player_id in players_by_id]
        ineligible = [entry.player_id for entry in race_table.standings if entry.player_id not in players_by_id]

        qualified = [
            FinalsQualifiedPlayer(
                player_id=entry.player_id,
                race_rank=entry.rank,
                race_points=entry.race_points,
                seed=index + 1,
            )
            for index, entry in enumerate(eligible[: self.qualifier_count])
        ]
        reserves = [
            FinalsQualifiedPlayer(
                player_id=entry.player_id,
                race_rank=entry.rank,
                race_points=entry.race_points,
                seed=self.qualifier_count + index + 1,
            )
            for index, entry in enumerate(eligible[self.qualifier_count : self.qualifier_count + self.reserve_count])
        ]

        return FinalsQualificationResult(
            target_season=race_table.target_season,
            qualifier_count=self.qualifier_count,
            reserve_count=self.reserve_count,
            qualified=qualified,
            reserves=reserves,
            ineligible_race_entries=ineligible,
        )

    def seed_groups(self, *, qualification: FinalsQualificationResult) -> list[FinalsGroup]:
        if len(qualification.qualified) != self.qualifier_count:
            raise ValueError(
                f"Finals seeding requires exactly {self.qualifier_count} qualified players; "
                f"got {len(qualification.qualified)}"
            )

        by_seed = {player.seed: player for player in qualification.qualified}
        # Standard MVP mapping: #1/#4 in Group A, #2/#3 in Group B.
        slot_assignments = {
            "A": [by_seed[1], by_seed[4]],
            "B": [by_seed[2], by_seed[3]],
        }

        remaining = [by_seed[seed] for seed in sorted(by_seed) if seed > 4]
        for idx, player in enumerate(remaining):
            target_group = "A" if idx % 2 == 0 else "B"
            slot_assignments[target_group].append(player)

        groups: list[FinalsGroup] = []
        for group_id in ("A", "B"):
            slots = [
                FinalsGroupSlot(group_id=group_id, slot=slot_index + 1, player=player)
                for slot_index, player in enumerate(slot_assignments[group_id])
            ]
            groups.append(FinalsGroup(group_id=group_id, slots=slots))

        return groups

    def simulate_event(
        self,
        *,
        event_id: str,
        season: int,
        race_table: RaceTable,
        players_by_id: dict[str, Player],
    ) -> FinalsResult:
        qualification = self.build_qualification(race_table=race_table, players_by_id=players_by_id)
        groups = self.seed_groups(qualification=qualification)

        match_engine = MatchEngine(rng=self.rng.branch(SeedScope.SEASON, season, event_id, "matches"))
        simulated_groups = [
            self._simulate_group(
                event_id=event_id,
                season=season,
                group=group,
                players_by_id=players_by_id,
                match_engine=match_engine,
            )
            for group in groups
        ]

        top_a = simulated_groups[0].standings[:2]
        top_b = simulated_groups[1].standings[:2]

        semifinal_1 = self._play_knockout_match(
            event_id=event_id,
            season=season,
            stage="SEMIFINAL",
            tie_label="SF1_A1_vs_B2",
            player_a_id=top_a[0].player_id,
            player_b_id=top_b[1].player_id,
            players_by_id=players_by_id,
            match_engine=match_engine,
        )
        semifinal_2 = self._play_knockout_match(
            event_id=event_id,
            season=season,
            stage="SEMIFINAL",
            tie_label="SF2_B1_vs_A2",
            player_a_id=top_b[0].player_id,
            player_b_id=top_a[1].player_id,
            players_by_id=players_by_id,
            match_engine=match_engine,
        )

        final_match = self._play_knockout_match(
            event_id=event_id,
            season=season,
            stage="FINAL",
            tie_label="F",
            player_a_id=semifinal_1.winner_player_id,
            player_b_id=semifinal_2.winner_player_id,
            players_by_id=players_by_id,
            match_engine=match_engine,
        )

        placements = self._build_placements(
            qualification=qualification,
            groups=simulated_groups,
            semifinals=[semifinal_1, semifinal_2],
            final_match=final_match,
        )

        return FinalsResult(
            event_id=event_id,
            season=season,
            qualification=qualification,
            groups=simulated_groups,
            knockout=[semifinal_1, semifinal_2, final_match],
            placements=placements,
        )

    def _simulate_group(
        self,
        *,
        event_id: str,
        season: int,
        group: FinalsGroup,
        players_by_id: dict[str, Player],
        match_engine: MatchEngine,
    ) -> FinalsGroup:
        player_ids = [slot.player.player_id for slot in group.slots]
        if len(player_ids) != 4:
            raise ValueError(f"Group {group.group_id} requires exactly 4 players for MVP finals format")

        pairings = [
            (player_ids[0], player_ids[1]),
            (player_ids[2], player_ids[3]),
            (player_ids[0], player_ids[2]),
            (player_ids[1], player_ids[3]),
            (player_ids[0], player_ids[3]),
            (player_ids[1], player_ids[2]),
        ]

        matches: list[FinalsGroupMatch] = []
        for index, (player_a_id, player_b_id) in enumerate(pairings, start=1):
            match_id = f"{event_id}:{season}:GROUP_{group.group_id}:M{index}"
            result = match_engine.simulate(
                MatchContext(
                    match_id=match_id,
                    player_a=MatchParticipantContext(player=players_by_id[player_a_id]),
                    player_b=MatchParticipantContext(player=players_by_id[player_b_id]),
                )
            )
            matches.append(
                FinalsGroupMatch(
                    match_id=match_id,
                    group_id=group.group_id,
                    match_number=index,
                    player_a_id=player_a_id,
                    player_b_id=player_b_id,
                    winner_player_id=result.winner_player_id,
                    loser_player_id=result.loser_player_id,
                    match_result=result,
                )
            )

        standings = self._build_group_standings(group=group, matches=matches)
        return group.model_copy(update={"matches": matches, "standings": standings})

    def _build_group_standings(self, *, group: FinalsGroup, matches: list[FinalsGroupMatch]) -> list[FinalsGroupStandingEntry]:
        by_player = {slot.player.player_id: self._empty_standing(group.group_id, slot.player) for slot in group.slots}
        head_to_head_winner: dict[frozenset[str], str] = {}

        for match in matches:
            winner = by_player[match.winner_player_id]
            loser = by_player[match.loser_player_id]

            winner.match_wins += 1
            loser.match_losses += 1

            sets_for_winner = match.match_result.sets_won[match.winner_player_id]
            sets_for_loser = match.match_result.sets_won[match.loser_player_id]

            winner.set_wins += sets_for_winner
            winner.set_losses += sets_for_loser
            loser.set_wins += sets_for_loser
            loser.set_losses += sets_for_winner

            winner_games = 0
            loser_games = 0
            for set_result in match.match_result.sets:
                if set_result.winner_player_id == match.winner_player_id:
                    winner_games += set_result.winner_games
                    loser_games += set_result.loser_games
                else:
                    winner_games += set_result.loser_games
                    loser_games += set_result.winner_games

            winner.game_wins += winner_games
            winner.game_losses += loser_games
            loser.game_wins += loser_games
            loser.game_losses += winner_games

            tie_key = frozenset((match.player_a_id, match.player_b_id))
            head_to_head_winner[tie_key] = match.winner_player_id

        entries = [
            entry.model_copy(
                update={
                    "set_differential": entry.set_wins - entry.set_losses,
                    "game_differential": entry.game_wins - entry.game_losses,
                }
            )
            for entry in by_player.values()
        ]

        ordered = sorted(
            entries,
            key=lambda entry: self._standing_sort_key(entry=entry, entries=entries, head_to_head_winner=head_to_head_winner),
        )
        return [entry.model_copy(update={"rank": idx + 1}) for idx, entry in enumerate(ordered)]

    def _standing_sort_key(
        self,
        *,
        entry: FinalsGroupStandingEntry,
        entries: list[FinalsGroupStandingEntry],
        head_to_head_winner: dict[frozenset[str], str],
    ) -> tuple:
        same_win_players = [candidate.player_id for candidate in entries if candidate.match_wins == entry.match_wins]
        two_way_flag = 0
        if len(same_win_players) == 2:
            other_id = next(player_id for player_id in same_win_players if player_id != entry.player_id)
            h2h = head_to_head_winner.get(frozenset((entry.player_id, other_id)))
            if h2h == entry.player_id:
                two_way_flag = 1

        return (
            -entry.match_wins,
            -two_way_flag,
            -entry.set_differential,
            -entry.game_differential,
            entry.seed,
            entry.player_id,
        )

    def _play_knockout_match(
        self,
        *,
        event_id: str,
        season: int,
        stage: str,
        tie_label: str,
        player_a_id: str,
        player_b_id: str,
        players_by_id: dict[str, Player],
        match_engine: MatchEngine,
    ) -> FinalsKnockoutMatch:
        match_id = f"{event_id}:{season}:{stage}:{tie_label}"
        result = match_engine.simulate(
            MatchContext(
                match_id=match_id,
                player_a=MatchParticipantContext(player=players_by_id[player_a_id]),
                player_b=MatchParticipantContext(player=players_by_id[player_b_id]),
            )
        )
        return FinalsKnockoutMatch(
            stage=stage,
            match_id=match_id,
            player_a_id=player_a_id,
            player_b_id=player_b_id,
            winner_player_id=result.winner_player_id,
            loser_player_id=result.loser_player_id,
            match_result=result,
        )

    def _build_placements(
        self,
        *,
        qualification: FinalsQualificationResult,
        groups: list[FinalsGroup],
        semifinals: list[FinalsKnockoutMatch],
        final_match: FinalsKnockoutMatch,
    ) -> list[FinalsPlacement]:
        placements: list[FinalsPlacement] = [
            FinalsPlacement(player_id=final_match.winner_player_id, finish="CHAMPION"),
            FinalsPlacement(player_id=final_match.loser_player_id, finish="FINALIST"),
        ]
        semifinal_losers = sorted(match.loser_player_id for match in semifinals)
        placements.extend(FinalsPlacement(player_id=player_id, finish="SEMIFINALIST") for player_id in semifinal_losers)

        semifinalists = {match.winner_player_id for match in semifinals} | set(semifinal_losers)
        for group in groups:
            for standing in group.standings:
                if standing.player_id in semifinalists:
                    continue
                placements.append(
                    FinalsPlacement(
                        player_id=standing.player_id,
                        finish=f"GROUP_{group.group_id}_R{standing.rank}",
                    )
                )

        qualification_order = {player.player_id: player.seed for player in qualification.qualified}
        return sorted(placements, key=lambda placement: (self._finish_order(placement.finish), qualification_order[placement.player_id]))

    @staticmethod
    def _finish_order(finish: str) -> tuple[int, str]:
        if finish == "CHAMPION":
            return (0, finish)
        if finish == "FINALIST":
            return (1, finish)
        if finish == "SEMIFINALIST":
            return (2, finish)
        return (3, finish)

    @staticmethod
    def _empty_standing(group_id: str, player: FinalsQualifiedPlayer) -> FinalsGroupStandingEntry:
        return FinalsGroupStandingEntry(
            group_id=group_id,
            rank=1,
            player_id=player.player_id,
            seed=player.seed,
            match_wins=0,
            match_losses=0,
            set_wins=0,
            set_losses=0,
            set_differential=0,
            game_wins=0,
            game_losses=0,
            game_differential=0,
        )

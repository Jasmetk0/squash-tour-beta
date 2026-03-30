from __future__ import annotations

from beta_engine.core import DeterministicRng
from beta_engine.domain.finals import FinalsEngine, FinalsGroup, FinalsGroupMatch, FinalsGroupSlot
from beta_engine.domain.matches import MatchResult, MatchTerminationReason, SetResult
from beta_engine.domain.players import HiddenCareerTraits, Player
from beta_engine.domain.rankings import PlayerRaceEntry, RaceTable


def _player(*, player_id: str, base: int) -> Player:
    return Player(
        player_id=player_id,
        name=player_id,
        age=27,
        nationality="TST",
        technique=base,
        movement=base,
        physical=base,
        mental=base,
        consistency=base,
        clutch=base,
        recovery=base,
        play_style="tempo-controller",
        archetype="all-court tactician",
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=90,
            growth_curve="balanced",
            professionalism=0.7,
            ambition=0.7,
            travel_tolerance=0.7,
            schedule_aggression=0.6,
            injury_proneness=0.2,
            resilience=0.8,
        ),
    )


def _race_table() -> RaceTable:
    return RaceTable(
        target_season=2027,
        standings=[
            PlayerRaceEntry(rank=i + 1, player_id=f"p{i + 1}", race_points=10000 - i * 100, counted_results=9, contributions=[])
            for i in range(10)
        ],
    )


def test_finals_event_is_replay_deterministic_for_same_seed_and_race_input() -> None:
    race = _race_table()
    players = {f"p{i}": _player(player_id=f"p{i}", base=88 - i) for i in range(1, 11)}

    engine_a = FinalsEngine(rng=DeterministicRng(777), qualifier_count=8, reserve_count=2)
    engine_b = FinalsEngine(rng=DeterministicRng(777), qualifier_count=8, reserve_count=2)

    result_a = engine_a.simulate_event(event_id="wtf_2027", season=2027, race_table=race, players_by_id=players)
    result_b = engine_b.simulate_event(event_id="wtf_2027", season=2027, race_table=race, players_by_id=players)

    assert result_a.model_dump() == result_b.model_dump()


def test_qualification_uses_top_8_and_deterministic_reserves() -> None:
    race = _race_table()
    players = {f"p{i}": _player(player_id=f"p{i}", base=82) for i in range(1, 11)}
    qualification = FinalsEngine(rng=DeterministicRng(1), qualifier_count=8, reserve_count=2).build_qualification(
        race_table=race,
        players_by_id=players,
    )

    assert [player.player_id for player in qualification.qualified] == [f"p{i}" for i in range(1, 9)]
    assert [player.seed for player in qualification.qualified] == list(range(1, 9))
    assert [player.player_id for player in qualification.reserves] == ["p9", "p10"]


def test_seeding_places_top_four_in_standard_split_and_rest_deterministically() -> None:
    race = _race_table()
    players = {f"p{i}": _player(player_id=f"p{i}", base=82) for i in range(1, 11)}
    engine = FinalsEngine(rng=DeterministicRng(3), qualifier_count=8, reserve_count=2)

    qualification = engine.build_qualification(race_table=race, players_by_id=players)
    groups = engine.seed_groups(qualification=qualification)

    assert [(slot.group_id, slot.slot, slot.player.player_id) for slot in groups[0].slots] == [
        ("A", 1, "p1"),
        ("A", 2, "p4"),
        ("A", 3, "p5"),
        ("A", 4, "p7"),
    ]
    assert [(slot.group_id, slot.slot, slot.player.player_id) for slot in groups[1].slots] == [
        ("B", 1, "p2"),
        ("B", 2, "p3"),
        ("B", 3, "p6"),
        ("B", 4, "p8"),
    ]


def test_group_tiebreak_uses_head_to_head_for_two_way_match_win_tie() -> None:
    engine = FinalsEngine(rng=DeterministicRng(5))
    qualified = [
        engine.build_qualification(
            race_table=RaceTable(
                target_season=2027,
                standings=[
                    PlayerRaceEntry(rank=i + 1, player_id=f"p{i + 1}", race_points=1000 - i, counted_results=1, contributions=[])
                    for i in range(8)
                ],
            ),
            players_by_id={f"p{i + 1}": _player(player_id=f"p{i + 1}", base=80) for i in range(8)},
        ).qualified[i]
        for i in range(4)
    ]
    group = FinalsGroup(group_id="A", slots=[FinalsGroupSlot(group_id="A", slot=i + 1, player=qualified[i]) for i in range(4)])

    def _group_match(n: int, a: str, b: str, winner: str, sets_won: dict[str, int], games_won: dict[str, int]) -> FinalsGroupMatch:
        loser = b if winner == a else a
        return FinalsGroupMatch(
            match_id=f"g{n}",
            group_id="A",
            match_number=n,
            player_a_id=a,
            player_b_id=b,
            winner_player_id=winner,
            loser_player_id=loser,
            match_result=MatchResult(
                match_id=f"g{n}",
                winner_player_id=winner,
                loser_player_id=loser,
                player_a_id=a,
                player_b_id=b,
                best_of=5,
                games_to=11,
                win_by=2,
                sets=[
                    SetResult(
                        set_number=1,
                        winner_player_id=winner,
                        loser_player_id=loser,
                        winner_games=11,
                        loser_games=games_won[loser],
                    )
                ],
                sets_won=sets_won,
                termination_reason=MatchTerminationReason.COMPLETED,
            ),
        )

    matches = [
        _group_match(1, "p1", "p2", "p1", {"p1": 3, "p2": 2}, {"p1": 44, "p2": 42}),
        _group_match(2, "p1", "p3", "p3", {"p1": 2, "p3": 3}, {"p1": 50, "p3": 40}),
        _group_match(3, "p1", "p4", "p1", {"p1": 3, "p4": 0}, {"p1": 33, "p4": 18}),
        _group_match(4, "p2", "p3", "p2", {"p2": 3, "p3": 0}, {"p2": 33, "p3": 20}),
        _group_match(5, "p2", "p4", "p2", {"p2": 3, "p4": 0}, {"p2": 33, "p4": 20}),
        _group_match(6, "p3", "p4", "p3", {"p3": 3, "p4": 0}, {"p3": 33, "p4": 17}),
    ]

    standings = engine._build_group_standings(group=group, matches=matches)

    assert standings[0].player_id == "p2"
    assert standings[1].player_id == "p1"
    assert standings[0].match_wins == standings[1].match_wins == 2


def test_knockout_progression_uses_a1_vs_b2_b1_vs_a2_then_final() -> None:
    race = _race_table()
    players = {f"p{i}": _player(player_id=f"p{i}", base=89 - i) for i in range(1, 11)}
    result = FinalsEngine(rng=DeterministicRng(11), qualifier_count=8, reserve_count=2).simulate_event(
        event_id="wtf_2027",
        season=2027,
        race_table=race,
        players_by_id=players,
    )

    group_a_top2 = [entry.player_id for entry in result.groups[0].standings[:2]]
    group_b_top2 = [entry.player_id for entry in result.groups[1].standings[:2]]

    assert result.knockout[0].stage == "SEMIFINAL"
    assert result.knockout[0].player_a_id == group_a_top2[0]
    assert result.knockout[0].player_b_id == group_b_top2[1]
    assert result.knockout[1].stage == "SEMIFINAL"
    assert result.knockout[1].player_a_id == group_b_top2[0]
    assert result.knockout[1].player_b_id == group_a_top2[1]
    assert result.knockout[2].stage == "FINAL"
    assert {result.knockout[2].player_a_id, result.knockout[2].player_b_id} == {
        result.knockout[0].winner_player_id,
        result.knockout[1].winner_player_id,
    }
    assert result.placements[0].finish == "CHAMPION"
    assert result.placements[1].finish == "FINALIST"

from __future__ import annotations

from beta_engine.domain.rankings import CompletedTournamentPointsInput, RankingRaceEngine
from beta_engine.infrastructure.points_config import load_points_config


def _tournament(
    *,
    event_id: str,
    season: int,
    week: int,
    template_id: str = "wt_platinum_32",
    point_distribution_ref: str | None = "world_tour_platinum",
    point_distribution: dict[str, int] | None = None,
    placements: list[dict[str, str]] | None = None,
    rounds: list[dict] | None = None,
) -> CompletedTournamentPointsInput:
    return CompletedTournamentPointsInput(
        event_id=event_id,
        season=season,
        week=week,
        template_id=template_id,
        point_distribution_ref=point_distribution_ref,
        point_distribution=point_distribution,
        placements=placements or [],
        rounds=rounds or [],
    )


def test_ranking_race_report_is_deterministic_for_same_inputs() -> None:
    engine = RankingRaceEngine(point_distributions_by_ref=load_points_config())
    tournaments = [
        _tournament(
            event_id="ev_2027_w01_a",
            season=2027,
            week=1,
            placements=[
                {"player_id": "p1", "finish": "CHAMPION"},
                {"player_id": "p2", "finish": "FINALIST"},
            ],
        ),
        _tournament(
            event_id="ev_2027_w03_b",
            season=2027,
            week=3,
            placements=[
                {"player_id": "p2", "finish": "CHAMPION"},
                {"player_id": "p1", "finish": "FINALIST"},
            ],
        ),
    ]

    report_a = engine.build_report(
        completed_tournaments=tournaments,
        as_of_season=2027,
        as_of_week=3,
        target_season=2027,
    )
    report_b = engine.build_report(
        completed_tournaments=tournaments,
        as_of_season=2027,
        as_of_week=3,
        target_season=2027,
    )

    assert report_a.model_dump() == report_b.model_dump()


def test_official_ranking_respects_rolling_61_week_window() -> None:
    engine = RankingRaceEngine(point_distributions_by_ref=load_points_config())

    tournaments = [
        _tournament(
            event_id="ev_2025_w01_old",
            season=2025,
            week=1,
            placements=[{"player_id": "p1", "finish": "CHAMPION"}],
        ),
        _tournament(
            event_id="ev_2026_w02_active",
            season=2026,
            week=2,
            placements=[{"player_id": "p1", "finish": "FINALIST"}],
        ),
        _tournament(
            event_id="ev_2027_w01_active",
            season=2027,
            week=1,
            placements=[{"player_id": "p1", "finish": "SEMIFINALIST"}],
        ),
    ]

    report = engine.build_report(
        completed_tournaments=tournaments,
        as_of_season=2027,
        as_of_week=1,
        target_season=2027,
    )

    ranking_entry = report.ranking.standings[0]
    assert ranking_entry.player_id == "p1"
    assert ranking_entry.ranking_points == 1650 + 1000
    assert len(ranking_entry.contributions) == 2
    assert {contribution.event_id for contribution in ranking_entry.contributions} == {
        "ev_2026_w02_active",
        "ev_2027_w01_active",
    }


def test_official_ranking_counts_only_best_12_results() -> None:
    engine = RankingRaceEngine(point_distributions_by_ref=load_points_config())

    tournaments = [
        _tournament(
            event_id=f"ev_2027_w{week:02d}",
            season=2027,
            week=week,
            placements=[{"player_id": "p1", "finish": "ROUND_OF_32"}],
        )
        for week in range(1, 14)
    ]

    report = engine.build_report(
        completed_tournaments=tournaments,
        as_of_season=2027,
        as_of_week=13,
        target_season=2027,
    )

    ranking_entry = report.ranking.standings[0]
    assert ranking_entry.counted_results == 12
    assert ranking_entry.ranking_points == 12 * 140
    counted = [c for c in ranking_entry.contributions if c.counted_in_best_12]
    not_counted = [c for c in ranking_entry.contributions if not c.counted_in_best_12]
    assert len(counted) == 12
    assert len(not_counted) == 1


def test_race_counts_only_target_season_results() -> None:
    engine = RankingRaceEngine(point_distributions_by_ref=load_points_config())

    tournaments = [
        _tournament(
            event_id="ev_2026_w08",
            season=2026,
            week=8,
            placements=[{"player_id": "p1", "finish": "CHAMPION"}],
        ),
        _tournament(
            event_id="ev_2027_w01",
            season=2027,
            week=1,
            placements=[{"player_id": "p1", "finish": "FINALIST"}],
        ),
        _tournament(
            event_id="ev_2027_w02",
            season=2027,
            week=2,
            placements=[{"player_id": "p1", "finish": "SEMIFINALIST"}],
        ),
    ]

    report = engine.build_report(
        completed_tournaments=tournaments,
        as_of_season=2027,
        as_of_week=2,
        target_season=2027,
    )

    race_entry = report.race.standings[0]
    assert race_entry.player_id == "p1"
    assert race_entry.race_points == 1650 + 1000
    assert all(contribution.season == 2027 for contribution in race_entry.contributions)


def test_point_awards_resolve_from_distribution_ref_and_inline_distribution() -> None:
    engine = RankingRaceEngine(point_distributions_by_ref=load_points_config())
    tournaments = [
        _tournament(
            event_id="ev_2027_w01_ref",
            season=2027,
            week=1,
            point_distribution_ref="world_tour_gold",
            placements=[
                {"player_id": "p1", "finish": "CHAMPION"},
                {"player_id": "p2", "finish": "FINALIST"},
            ],
        ),
        _tournament(
            event_id="ev_2027_w02_inline",
            season=2027,
            week=2,
            point_distribution_ref=None,
            point_distribution={
                "winner": 100,
                "finalist": 60,
                "semifinalist": 30,
                "quarterfinalist": 15,
                "round_of_16": 8,
                "round_of_32": 4,
            },
            placements=[
                {"player_id": "p1", "finish": "CHAMPION"},
                {"player_id": "p3", "finish": "FINALIST"},
            ],
        ),
    ]

    awards = engine.resolve_point_awards(completed_tournaments=tournaments)
    award_lookup = {(award.event_id, award.player_id): award.points_awarded for award in awards}

    assert award_lookup[("ev_2027_w01_ref", "p1")] == 1400
    assert award_lookup[("ev_2027_w01_ref", "p2")] == 920
    assert award_lookup[("ev_2027_w02_inline", "p1")] == 100
    assert award_lookup[("ev_2027_w02_inline", "p3")] == 60


def test_point_awards_infer_round_based_finishes_when_rounds_are_provided() -> None:
    engine = RankingRaceEngine(point_distributions_by_ref=load_points_config())

    tournament = _tournament(
        event_id="ev_2027_w04_rounds",
        season=2027,
        week=4,
        placements=[
            {"player_id": "p1", "finish": "CHAMPION"},
            {"player_id": "p2", "finish": "FINALIST"},
        ],
        rounds=[
            {
                "round_number": 1,
                "matches": [
                    {"loser_player_id": "p16"},
                    {"loser_player_id": "p15"},
                ],
            },
            {
                "round_number": 2,
                "matches": [
                    {"loser_player_id": "p8"},
                ],
            },
            {
                "round_number": 3,
                "matches": [
                    {"loser_player_id": "p4"},
                ],
            },
            {
                "round_number": 4,
                "matches": [
                    {"loser_player_id": "p2"},
                ],
            },
        ],
    )

    awards = engine.resolve_point_awards(completed_tournaments=[tournament])
    finishes = {(award.player_id, award.finish): award.points_awarded for award in awards}

    assert finishes[("p4", "SEMIFINALIST")] == 1000
    assert finishes[("p8", "QUARTERFINALIST")] == 520
    assert finishes[("p16", "ROUND_OF_16")] == 270
    assert finishes[("p15", "ROUND_OF_16")] == 270

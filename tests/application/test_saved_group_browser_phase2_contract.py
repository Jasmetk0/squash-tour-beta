"""Fast guard for genuine group completion versus merely scheduled/partial matches.

The real Chromium production Run (not these minimal data checks) generates
and executes six competitive matches and validates Saved Revision persistence.
"""
import pytest

from scripts.saved_completed_group_browser_checks import assert_real_played_group_table

pytestmark = pytest.mark.pr_critical

SCHEDULE = [
    {"match_id": f"M{i}", "top_player_id": a, "bottom_player_id": b}
    for i, (a, b) in enumerate(
        [("A", "B"), ("A", "C"), ("A", "D"), ("B", "C"), ("B", "D"), ("C", "D")],
        start=1,
    )
]


def _rows():
    return [
        dict(position=i, player_id=player, wins=wins, losses=3-wins,
             played_matches=3, group_points=4*wins,
             walkovers_received=0, walkovers_conceded=0)
        for i, (player, wins) in enumerate(
            [("A", 3), ("B", 2), ("C", 1), ("D", 0)], start=1
        )
    ]


def test_completed_group_requires_six_real_played_games_with_all_players():
    assert_real_played_group_table(_rows(), SCHEDULE)
    partial = _rows()
    partial[0]["played_matches"] = 2
    with pytest.raises(AssertionError):
        assert_real_played_group_table(partial, SCHEDULE)
    partial = _rows()
    partial[0]["wins"] = 2
    with pytest.raises(AssertionError):
        assert_real_played_group_table(partial, SCHEDULE)
    partial = _rows()
    partial[0]["walkovers_received"] = 1
    with pytest.raises(AssertionError):
        assert_real_played_group_table(partial, SCHEDULE)
    partial = _rows()
    partial[0]["player_id"] = "foreign"
    with pytest.raises(AssertionError):
        assert_real_played_group_table(partial, SCHEDULE)


def test_schedule_only_is_never_proof_of_completed_group_results():
    with pytest.raises(AssertionError):
        assert_real_played_group_table([], SCHEDULE)
    with pytest.raises(AssertionError):
        assert_real_played_group_table(_rows(), SCHEDULE[:-1])

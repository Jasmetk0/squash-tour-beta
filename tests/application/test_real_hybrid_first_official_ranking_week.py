"""Focused Week-1 -> Week-2 domain guard for the real hybrid browser path.

The browser acceptance checks the actual persisted tournament source. These
small immutable-domain assertions ensure its zero-based eligibility and
one-Edition/player ranking arithmetic cannot regress independently.
"""
import pytest

from beta_engine.application.hybrid_tournament_closure import (
    _ranking_source_boundary,
    hybrid_completed_week_from_ordinal,
)
from beta_engine.application.ranking_tournament_ingestion import TournamentRankingBinding
from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
    calculate_official_ranking,
)

pytestmark = pytest.mark.pr_critical


def test_first_hybrid_week_source_is_eligible_only_in_next_week():
    completed = hybrid_completed_week_from_ordinal(0)
    first_eligible, final_closing = _ranking_source_boundary(completed)
    assert completed == RankingWeek(season_index=0, week=1)
    assert first_eligible == RankingWeek(season_index=0, week=2)
    assert (completed.ordinal, first_eligible.ordinal, final_closing) == (0, 1, None)
    binding = TournamentRankingBinding(
        run_id="run", branch_id="branch", edition_id="hybrid",
        event_id="hybrid", completed_week=completed,
        first_publication_week=first_eligible, validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint="a" * 64,
        expected_award_fingerprint="b" * 64,
    )
    assert binding.first_publication_week.ordinal == 1
    with pytest.raises(ValueError, match="must follow completion"):
        TournamentRankingBinding(
            **{**binding.model_dump(), "first_publication_week": completed}
        )


def test_one_composed_hybrid_result_per_player_with_best_n():
    completed = RankingWeek(season_index=0, week=1)
    target = RankingWeek(season_index=0, week=2)
    roster = tuple(
        OfficialRankingPlayer(
            player_id=player_id, tie_break_token=player_id,
            tour_entry_week=completed,
        )
        for player_id in ("champion", "finalist", "group_loser_a", "group_loser_b")
    )
    # 10 group win + 100 champion / 60 finalist are ONE composed Edition award
    # per advancing player, never separate group and knockout ranking sources.
    results = tuple(
        OfficialRankingResult(
            edition_id="hybrid", player_id=player_id,
            source_fingerprint="real-composed-source",
            completed_week=completed, first_publication_week=target,
            main_points=points,
        )
        for player_id, points in (
            ("champion", 110),
            ("finalist", 70),
            ("group_loser_a", 0),
            ("group_loser_b", 0),
        )
    )
    assert all(r.eligibility_ordinal == 1 for r in results)
    policy = OfficialRankingPolicy(policy_id="explicit-test-policy", best_n=1)
    snapshot = calculate_official_ranking(
        run_id="run", branch_id="branch", week=target,
        policy=policy, players=roster, results=results,
    )
    by_id = {row.player_id: row for row in snapshot.rows}
    assert {pid: row.points for pid, row in by_id.items()} == {
        "champion": 110,
        "finalist": 70,
        "group_loser_a": 0,
        "group_loser_b": 0,
    }
    assert sum(row.points for row in snapshot.rows) == 180
    assert all(len(row.counted_results) <= policy.best_n for row in snapshot.rows)
    assert all({r.edition_id for r in row.counted_results} <= {"hybrid"}
               for row in snapshot.rows)

    # The authoritative calculator must never accept a second points record
    # from that same Edition/player under a different alleged phase.
    with pytest.raises(ValueError, match="One resolved result per Edition/player"):
        calculate_official_ranking(
            run_id="run", branch_id="branch", week=target,
            policy=policy, players=roster, results=results + (results[0],),
        )

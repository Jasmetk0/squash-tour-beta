"""Ranking-layer Season Closing archive remap; not a post-season fork acceptance.

The production Saved Revision installer still guards against cross-season forks.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.result_history import RankingResultVersion
from beta_engine.domain.rankings.season_closing import calculate_season_closing_ranking
from beta_engine.infrastructure.db.ranking_fork_remap import (
    RankingForkRemapUnsupportedError,
    _remap_season_closing_archives,
)


pytestmark = pytest.mark.pr_critical


def _ledger(*, corrupt_target_points: bool = False):
    week61 = RankingWeek(season_index=0, week=61)
    next_week = RankingWeek(season_index=1, week=1)
    player = OfficialRankingPlayer(
        player_id="player-a",
        tie_break_token="token-a",
        tour_entry_week=RankingWeek(season_index=0, week=1),
    )
    players = (player,)
    policy = OfficialRankingPolicy(policy_id="season-zero", best_n=15)
    source_predecessor = calculate_official_ranking(
        run_id="run", branch_id="source", week=week61,
        policy=policy, players=players, results=(),
    )
    target_predecessor = calculate_official_ranking(
        run_id="run", branch_id="target", week=week61,
        policy=policy, players=players, results=(),
    )
    result = OfficialRankingResult(
        edition_id="week61-tournament", player_id="player-a",
        source_fingerprint="original-tournament",
        completed_week=week61, first_publication_week=next_week,
        main_points=120,
    )
    target_result = result.model_copy(
        update={
            "source_fingerprint": "rebound-tournament",
            "main_points": 140 if corrupt_target_points else 120,
        }
    )
    archive = calculate_season_closing_ranking(
        run_id="run", branch_id="source", completed_week=week61,
        policy=policy, players=players, results=(result,),
        predecessor=source_predecessor,
    )
    source = SimpleNamespace(
        entries=(SimpleNamespace(
            snapshot=source_predecessor,
            inputs=SimpleNamespace(players=players),
        ),),
        season_closing_rankings=(archive,),
        sources=(RankingResultVersion(
            run_id="run", branch_id="source", effective_week=next_week,
            result=result, previous_fingerprint=None,
        ),),
        zero_sources=(),
    )
    target_entries = (SimpleNamespace(
        snapshot=target_predecessor,
        inputs=SimpleNamespace(players=players),
    ),)
    target_sources = (RankingResultVersion(
        run_id="run", branch_id="target", effective_week=next_week,
        result=target_result, previous_fingerprint=None,
    ),)
    return source, target_entries, target_sources


def test_archive_replay_preserves_week61_result_and_rebinds_branch_fingerprints():
    source, entries, results = _ledger()
    args = {
        "target_entries": entries, "target_sources": results,
        "target_zero_sources": (), "target_branch_id": "target",
    }
    (rebound,) = _remap_season_closing_archives(source, **args)
    assert rebound.branch_id == "target"
    assert rebound.fingerprint != source.season_closing_rankings[0].fingerprint
    assert rebound.predecessor_official_fingerprint == entries[0].snapshot.fingerprint
    assert [(row.player_id, row.points) for row in rebound.rows] == [
        ("player-a", 120),
    ]
    assert rebound.rows[0].counted_results[0].source_fingerprint == (
        "rebound-tournament"
    )
    assert _remap_season_closing_archives(source, **args) == (rebound,)


def test_archive_replay_rejects_forged_result_and_missing_week61_publication():
    source, entries, results = _ledger(corrupt_target_points=True)
    with pytest.raises(RankingForkRemapUnsupportedError, match="Season Closing"):
        _remap_season_closing_archives(
            source, target_entries=entries, target_sources=results,
            target_zero_sources=(), target_branch_id="target",
        )
    with pytest.raises(RankingForkRemapUnsupportedError, match="Week-61"):
        _remap_season_closing_archives(
            source, target_entries=(), target_sources=results,
            target_zero_sources=(), target_branch_id="target",
        )


def test_archive_replay_rejects_unproven_source_archive():
    source, entries, results = _ledger()
    archive = source.season_closing_rankings[0]
    source.season_closing_rankings = (
        archive.model_copy(update={"input_fingerprint": "0" * 64}),
    )
    with pytest.raises(RankingForkRemapUnsupportedError, match="Season Closing"):
        _remap_season_closing_archives(
            source, target_entries=entries, target_sources=results,
            target_zero_sources=(), target_branch_id="target",
        )

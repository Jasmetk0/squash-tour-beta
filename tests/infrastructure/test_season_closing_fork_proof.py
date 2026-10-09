"""Pure adversarial evidence for the pre-Season-Transition fork archive adapter.

No actual cross-season Saved Revision fork is enabled by these tests.
"""

from __future__ import annotations

import pytest

from beta_engine.domain.rankings.official import (
    DisciplinaryZero,
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.season_closing import calculate_season_closing_ranking
from beta_engine.infrastructure.db.season_closing_fork_proof import (
    SeasonClosingForkProofError,
    rebind_verified_season_closing_ranking,
)


def _case(*, shared_tournament_provenance: bool = False):
    week60 = RankingWeek(season_index=0, week=60)
    week61 = RankingWeek(season_index=0, week=61)
    next_week = RankingWeek(season_index=1, week=1)
    policy = OfficialRankingPolicy(policy_id="season-2000", best_n=15)
    players = (
        OfficialRankingPlayer(
            player_id="player-a", tie_break_token="token-a",
            tour_entry_week=RankingWeek(season_index=0, week=1),
        ),
        OfficialRankingPlayer(
            player_id="player-b", tie_break_token="token-b",
            tour_entry_week=RankingWeek(season_index=0, week=1),
        ),
    )
    original_results = (
        OfficialRankingResult(
            edition_id="week-60-event", player_id="player-a",
            source_fingerprint="old-week60", completed_week=week60,
            first_publication_week=week61, main_points=40,
        ),
        OfficialRankingResult(
            edition_id="week-61-event", player_id="player-b",
            source_fingerprint=(
                "old-week60" if shared_tournament_provenance else "old-week61"
            ), completed_week=week61, first_publication_week=next_week,
            main_points=120,
        ),
    )
    target_results = tuple(
        v.model_copy(update={
            "source_fingerprint": (
                "fork-week60"
                if i == 0 or shared_tournament_provenance
                else "fork-week61"
            ),
        })
        for i, v in enumerate(original_results)
    )
    zeros = (
        DisciplinaryZero(
            zero_id="zero-b", run_id="run", branch_id="source",
            player_id="player-b", source_fingerprint="zero-source",
            effective_week=week61, duration_weeks=2,
        ),
    )
    target_zeros = (
        zeros[0].model_copy(
            update={"branch_id": "target", "source_fingerprint": "zero-target"}
        ),
    )
    source_predecessor = calculate_official_ranking(
        run_id="run", branch_id="source", week=week61, policy=policy,
        players=players, results=(original_results[0],),
        disciplinary_zeros=zeros,
    )
    target_predecessor = calculate_official_ranking(
        run_id="run", branch_id="target", week=week61, policy=policy,
        players=players, results=(target_results[0],),
        disciplinary_zeros=target_zeros,
    )
    source = calculate_season_closing_ranking(
        run_id="run", branch_id="source", completed_week=week61,
        policy=policy, players=players, results=original_results,
        predecessor=source_predecessor, disciplinary_zeros=zeros,
    )
    proof = dict(
        source_predecessor=source_predecessor,
        target_predecessor=target_predecessor,
        source_players=players,
        target_players=players,
        source_results=original_results,
        target_results=target_results,
        source_zeros=zeros,
        target_zeros=target_zeros,
        result_fingerprint_map={
            "old-week60": "fork-week60",
            **({} if shared_tournament_provenance else {"old-week61": "fork-week61"}),
        },
        zero_fingerprint_map={"zero-source": "zero-target"},
        target_branch_id="target",
    )
    return source, proof


@pytest.mark.pr_critical
@pytest.mark.parametrize("shared", [False, True])
def test_season_closing_fork_recomputes_source_and_target_with_exact_sporting_outcome(shared):
    source, proof = _case(shared_tournament_provenance=shared)
    target = rebind_verified_season_closing_ranking(source, **proof)
    assert target.run_id == source.run_id
    assert target.branch_id == "target"
    assert target.completed_week == source.completed_week
    assert target.policy == source.policy
    assert target.predecessor_official_fingerprint == proof["target_predecessor"].fingerprint
    assert target.predecessor_official_fingerprint != source.predecessor_official_fingerprint
    assert target.fingerprint != source.fingerprint
    assert [(x.player_id, x.points) for x in target.rows] == [
        (x.player_id, x.points) for x in source.rows
    ]
    assert any(
        result.edition_id == "week-61-event"
        for row in target.rows for result in row.counted_results
    )
    assert all(
        zero.branch_id == "target"
        for row in target.rows for zero in row.disciplinary_zeros
    )
    assert rebind_verified_season_closing_ranking(source, **proof) == target


@pytest.mark.pr_critical
@pytest.mark.parametrize("corruption", [
    "missing_fingerprint", "extra_fingerprint", "foreign_target_zero",
    "foreign_source_zero", "target_points", "target_roster",
    "source_archive_input", "source_archive_rows",
    "predecessor_wrong_branch", "target_predecessor_wrong_week",
    "target_predecessor_wrong_ranking", "target_policy_changed",
    "target_result_forged_provenance", "target_zero_forged_provenance",
    "target_branch_matches_source", "duplicate_results", "foreign_target_run",
])
def test_season_closing_archive_rejects_partial_or_forged_cross_branch_proofs(corruption):
    source, proof = _case()
    if corruption == "missing_fingerprint":
        proof["result_fingerprint_map"] = {"old-week60": "fork-week60"}
    elif corruption == "extra_fingerprint":
        proof["result_fingerprint_map"]["phantom"] = "fork-phantom"
    elif corruption == "foreign_target_zero":
        proof["target_zeros"] = (
            proof["target_zeros"][0].model_copy(update={"branch_id": "other"}),
        )
    elif corruption == "foreign_source_zero":
        proof["source_zeros"] = (
            proof["source_zeros"][0].model_copy(update={"branch_id": "other"}),
        )
    elif corruption == "target_points":
        proof["target_results"] = (
            proof["target_results"][0],
            proof["target_results"][1].model_copy(update={"main_points": 130}),
        )
    elif corruption == "target_roster":
        proof["target_players"] = (
            proof["target_players"][0],
            proof["target_players"][1].model_copy(update={"retired": True}),
        )
    elif corruption == "source_archive_input":
        source = source.model_copy(update={"input_fingerprint": "f" * 64})
    elif corruption == "source_archive_rows":
        source = source.model_copy(update={"rows": source.rows[:1]})
    elif corruption == "predecessor_wrong_branch":
        proof["source_predecessor"] = proof["source_predecessor"].model_copy(
            update={"branch_id": "elsewhere"}
        )
    elif corruption == "target_predecessor_wrong_week":
        proof["target_predecessor"] = proof["target_predecessor"].model_copy(
            update={"week": RankingWeek(season_index=0, week=60)}
        )
    elif corruption == "target_predecessor_wrong_ranking":
        proof["target_predecessor"] = proof["target_predecessor"].model_copy(
            update={"rows": ()}
        )
    elif corruption == "target_policy_changed":
        proof["target_predecessor"] = proof["target_predecessor"].model_copy(
            update={"policy": OfficialRankingPolicy(policy_id="not-outgoing", best_n=15)}
        )
    elif corruption == "target_result_forged_provenance":
        proof["target_results"] = (
            proof["target_results"][0],
            proof["target_results"][1].model_copy(
                update={"source_fingerprint": "forged"}
            ),
        )
    elif corruption == "target_zero_forged_provenance":
        proof["target_zeros"] = (
            proof["target_zeros"][0].model_copy(
                update={"source_fingerprint": "forged"}
            ),
        )
    elif corruption == "target_branch_matches_source":
        proof["target_branch_id"] = "source"
    elif corruption == "duplicate_results":
        proof["source_results"] = (*proof["source_results"], proof["source_results"][0])
    else:
        proof["target_predecessor"] = proof["target_predecessor"].model_copy(
            update={"run_id": "other-run"}
        )
    with pytest.raises((SeasonClosingForkProofError, ValueError)):
        rebind_verified_season_closing_ranking(source, **proof)

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    OfficialRankingSnapshot,
    RankingWeek,
    calculate_official_ranking,
    load_official_ranking_snapshot,
    propose_next_season_policy,
)


def week(n: int) -> RankingWeek:
    return RankingWeek(season_index=(n - 1) // 61, week=(n - 1) % 61 + 1)


def player(
    pid: str, *, entered: int = 1, retired: bool = False
) -> OfficialRankingPlayer:
    return OfficialRankingPlayer(
        player_id=pid,
        tie_break_token=pid,
        tour_entry_week=week(entered),
        retired=retired,
    )


def result(
    pid: str = "a",
    *,
    event: str = "e",
    completed: int = 2,
    published: int = 3,
    points: int = 100,
    **kwargs,
) -> OfficialRankingResult:
    return OfficialRankingResult(
        edition_id=event,
        player_id=pid,
        source_fingerprint=event,
        completed_week=week(completed),
        first_publication_week=week(published),
        main_points=points,
        **kwargs,
    )


def calculate(n: int, *, players=None, results=(), previous=None, best_n=15):
    return calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=week(n),
        policy=OfficialRankingPolicy(policy_id=f"best-{best_n}", best_n=best_n),
        players=players if players is not None else (player("a"),),
        results=results,
        previous=previous,
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "points",
        "owner",
        "duplicate_result",
        "rank",
        "duplicate_player",
        "best_n",
        "unranked",
        "future",
        "expired",
        "profile",
        "hash",
    ],
)
def test_stored_snapshot_rejects_inconsistent_content(mutation):
    snapshot = calculate(
        3, results=(result(points=100), result(event="other", points=20))
    )
    data = snapshot.model_dump(mode="json")
    row = data["rows"][0]
    if mutation == "points":
        row["points"] += 1
    elif mutation == "owner":
        row["counted_results"][0]["player_id"] = "foreign"
    elif mutation == "duplicate_result":
        row["counted_results"].append(row["counted_results"][0].copy())
        row["points"] += 100
    elif mutation == "rank":
        row["rank"] = 2
    elif mutation == "duplicate_player":
        data["rows"].append({**row, "rank": 2})
    elif mutation == "best_n":
        data["policy"]["best_n"] = 1
    elif mutation == "unranked":
        row["counted_results"][0]["ranked"] = False
    elif mutation == "future":
        data["week"]["week"] = 2
    elif mutation == "expired":
        row["counted_results"][0]["validity_weeks"] = 1
        data["week"]["week"] = 4
    elif mutation == "profile":
        row["counted_results"].reverse()
    elif mutation == "hash":
        data["input_fingerprint"] = "invalid"
    with pytest.raises(ValidationError):
        OfficialRankingSnapshot.model_validate_json(json.dumps(data))


def test_verified_load_preserves_history_and_rejects_scope_or_hash_changes():
    snapshot = calculate(3, results=(result(),))
    arguments = {
        "expected_fingerprint": snapshot.fingerprint,
        "run_id": "run",
        "branch_id": "branch",
        "week": week(3),
    }
    assert (
        load_official_ranking_snapshot(snapshot.model_dump_json(), **arguments)
        == snapshot
    )
    for key, value in (
        ("run_id", "other"),
        ("branch_id", "other"),
        ("week", week(4)),
        ("expected_fingerprint", "0" * 64),
    ):
        with pytest.raises(ValueError):
            load_official_ranking_snapshot(
                snapshot.model_dump_json(), **{**arguments, key: value}
            )
    data = snapshot.model_dump(mode="json")
    data["policy"]["policy_id"] = "tampered-but-structurally-valid"
    with pytest.raises(ValueError, match="fingerprint"):
        load_official_ranking_snapshot(json.dumps(data), **arguments)


def test_invalid_model_copy_cannot_become_previous_snapshot():
    snapshot = calculate(3, results=(result(),))
    bad = snapshot.model_copy(
        update={"rows": (snapshot.rows[0].model_copy(update={"points": 999}),)}
    )
    with pytest.raises(ValidationError):
        calculate(4, previous=bad)


def test_points_wait_until_following_week_and_expire_from_first_publication():
    awards = (result(),)
    assert calculate(2, results=awards).rows[0].points == 0
    assert calculate(3, results=awards).rows[0].points == 100
    assert calculate(63, results=awards).rows[0].points == 100
    assert calculate(64, results=awards).rows[0].points == 0


def test_delayed_first_publication_and_per_edition_validity():
    awards = (result(published=5, validity_weeks=2),)
    assert calculate(4, results=awards).rows[0].points == 0
    assert calculate(6, results=awards).rows[0].points == 100
    assert calculate(7, results=awards).rows[0].points == 0


def test_week_61_result_appears_in_next_season():
    awards = (result(completed=61, published=62),)
    assert calculate(61, results=awards).rows[0].points == 0
    assert calculate(62, results=awards).rows[0].points == 100


def test_best_15_default_and_explicit_policy_q_main_count_once():
    awards = tuple(result(event=str(i), points=i) for i in range(1, 17))
    snapshot = calculate(3, results=awards)
    assert snapshot.policy.best_n == 15
    assert snapshot.rows[0].points == sum(range(2, 17))
    assert len(snapshot.rows[0].counted_results) == 15
    combined = result(event="q-main", points=20, qualification_points=5)
    assert calculate(3, results=(*awards, combined), best_n=1).rows[0].points == 25


def test_season_policy_inherits_effective_previous_value_and_preserves_override():
    initial = OfficialRankingPolicy(policy_id="first")
    assert initial.best_n == 15
    changed = OfficialRankingPolicy(policy_id="effective", best_n=9)
    inherited = propose_next_season_policy(policy_id="next", previous_effective=changed)
    overridden = propose_next_season_policy(
        policy_id="override", previous_effective=changed, best_n_override=20
    )
    assert inherited.best_n == 9
    assert overridden.best_n == 20
    assert initial.best_n == 15
    assert changed.best_n == 9


def test_unranked_is_excluded_but_abandoned_terminal_result_is_eligible():
    awards = (
        result(event="unranked", ranked=False),
        result(event="abandoned", points=30, terminal_status="abandoned"),
    )
    snapshot = calculate(3, results=awards)
    assert snapshot.rows[0].points == 30
    assert len(snapshot.rows[0].counted_results) == 1


def test_current_week_entrants_wait_and_retired_players_leave():
    roster = (player("a", entered=3), player("b", retired=True), player("c"))
    assert [r.player_id for r in calculate(3, players=roster).rows] == ["c"]
    assert [r.player_id for r in calculate(4, players=roster).rows] == ["a", "c"]


def test_point_profile_beats_token_and_result_count():
    awards = (
        result("a", event="a1", points=50),
        result("a", event="a2", points=50),
        result("b", points=100),
    )
    snapshot = calculate(4, players=(player("a"), player("b")), results=awards)
    assert [r.player_id for r in snapshot.rows] == ["b", "a"]
    assert [r.rank for r in snapshot.rows] == [1, 2]


def test_newer_results_break_identical_point_profiles():
    awards = (result("a"), result("b", completed=3, published=4))
    assert (
        calculate(4, players=(player("a"), player("b")), results=awards)
        .rows[0]
        .player_id
        == "b"
    )


def test_previous_zero_player_precedes_new_entrant_even_with_worse_token():
    previous = calculate(2, players=(player("z"),))
    current = calculate(
        3, players=(player("a", entered=2), player("z")), previous=previous
    )
    assert [r.player_id for r in current.rows] == ["z", "a"]


def test_previous_order_breaks_equal_nonzero_profiles():
    previous = calculate(3, players=(player("a"), player("b")), results=(result("b"),))
    current = calculate(
        4,
        players=(player("a"), player("b")),
        results=(result("a"), result("b")),
        previous=previous,
    )
    assert [r.player_id for r in current.rows] == ["b", "a"]


def test_input_order_does_not_change_snapshot_or_hash():
    roster = (player("b"), player("a"))
    awards = (result("b"), result("a"))
    first = calculate(4, players=roster, results=awards)
    second = calculate(4, players=roster[::-1], results=awards[::-1])
    assert first == second
    assert first.fingerprint == second.fingerprint
    assert [r.player_id for r in first.rows] == ["a", "b"]


def test_new_policy_and_corrected_inputs_do_not_rewrite_old_snapshot():
    old = calculate(3, results=(result(),))
    old_json = old.model_dump_json()
    new = calculate(4, results=(result(points=20),), previous=old, best_n=1)
    assert new.rows[0].points == 20
    assert new.previous_fingerprint == old.fingerprint
    assert old.model_dump_json() == old_json
    assert OfficialRankingSnapshot.model_validate_json(old_json) == old
    with pytest.raises(ValidationError):
        old.rows[0].points = 0


def test_unchanged_week_still_has_distinct_snapshot_identity():
    first = calculate(3)
    second = calculate(4, previous=first)
    assert first.rows == second.rows
    assert first.fingerprint != second.fingerprint


@pytest.mark.parametrize(
    "field,value", [("run_id", "other"), ("branch_id", "other"), ("week", week(1))]
)
def test_previous_snapshot_must_be_immediately_preceding_and_same_scope(field, value):
    previous = calculate(3).model_copy(update={field: value})
    with pytest.raises(ValueError, match="preceding week"):
        calculate(4, previous=previous)


def test_duplicate_results_unknown_players_and_duplicate_tokens_fail_closed():
    with pytest.raises(ValueError, match="One resolved result"):
        calculate(3, results=(result(), result()))
    with pytest.raises(ValueError, match="unknown player"):
        calculate(3, results=(result("missing"),))
    with pytest.raises(ValueError, match="Duplicate player"):
        calculate(3, players=(player("a"), player("a")))
    with pytest.raises(ValueError, match="tokens must be unique"):
        calculate(
            3,
            players=(
                player("a"),
                player("b").model_copy(update={"tie_break_token": "a"}),
            ),
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"published": 2},
        {"points": -1},
        {"points": True},
        {"validity_weeks": 0},
        {"terminal_status": "suspended"},
    ],
)
def test_invalid_or_nonterminal_inputs_rejected(kwargs):
    with pytest.raises(ValidationError):
        result(**kwargs)

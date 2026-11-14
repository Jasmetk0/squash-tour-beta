"""Pre-alpha Turn Pro player-AI model: determinism, calendar invariance, calibration."""

import math

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_lifecycle import advance_calendar_lifecycle
from beta_engine.domain.players.turn_pro_model import (
    TurnProCandidate,
    TurnProModelPolicy,
    decide_turn_pro,
    true_strength_turn_pro_model_policy_v1,
    turn_pro_draw,
    weekly_turn_pro_chance,
)
from tests.domain.test_turn_pro_lifecycle import bootstrap, decision, week

pytestmark = pytest.mark.pr_critical

# v1 math stays valid for replaying history recorded with it.
POLICY = true_strength_turn_pro_model_policy_v1()


def chance(age=17, readiness=0.3, home=False, w=52):
    return weekly_turn_pro_chance(
        POLICY,
        TurnProCandidate(player_id="p", age=age, readiness=readiness, home_opportunity=home),
        weeks_per_year=w,
    )


def test_policy_is_versioned_fingerprinted_and_round_trips():
    raw = POLICY.model_dump_json()
    assert TurnProModelPolicy.model_validate_json(raw) == POLICY
    assert len(POLICY.fingerprint) == 64
    with pytest.raises(ValueError, match="strictly between 0 and 1"):
        TurnProModelPolicy.model_validate(
            {**POLICY.model_dump(), "annual_base_by_age": (0.1, 1.0)}
        )
    with pytest.raises(ValueError, match="must not fall with age"):
        TurnProModelPolicy.model_validate(
            {**POLICY.model_dump(), "annual_base_by_age": (0.5, 0.2)}
        )


def test_chance_rises_with_age_strength_and_home_opportunity():
    assert chance(15) < chance(17) < chance(19) < chance(22)
    assert chance(30) == chance(22)  # last base applies beyond the table
    assert chance(readiness=0.0) < chance(readiness=0.3) < chance(readiness=0.9)
    assert chance(home=True) > chance(home=False)
    assert all(0 < chance(a, r) < 1 for a in (15, 25, 45) for r in (0.0, 1.0))


@pytest.mark.parametrize("w", [52, 61, 80])
def test_annual_rate_is_independent_of_weeks_per_year(w):
    # Neutral readiness reproduces the annual base exactly after W weeks.
    weekly = chance(age=18, w=w)
    assert math.isclose(1 - (1 - weekly) ** w, POLICY.annual_base_by_age[3], rel_tol=1e-12)


def test_draw_is_deterministic_and_keyed_to_player_week_and_seed():
    key = dict(seed=7, run_id="r", branch_id="b", player_id="a", target=week(2))
    first, second = turn_pro_draw(**key), turn_pro_draw(**key)
    assert first == second  # the same inputs must give the same draw
    assert 0 <= first < 1
    assert turn_pro_draw(**{**key, "seed": 8}) != turn_pro_draw(**key)
    assert turn_pro_draw(**{**key, "player_id": "b"}) != turn_pro_draw(**key)
    assert turn_pro_draw(**{**key, "target": week(3)}) != turn_pro_draw(**key)


def _candidates(ready=0.99):
    return [
        TurnProCandidate(player_id="a", age=16, readiness=ready, home_opportunity=True),
        TurnProCandidate(player_id="b", age=16, readiness=ready, home_opportunity=True),
    ]


def _first_seed_where_someone_turns_pro(start):
    for seed in range(1000):
        if decide_turn_pro(predecessor=start, target=week(2), candidates=_candidates(),
                           policy=POLICY, seed=seed):
            return seed
    raise AssertionError("no seed produced a decision")


def test_decisions_are_order_independent_and_feed_the_lifecycle_advance():
    start = bootstrap("turn_pro.v87")
    seed = _first_seed_where_someone_turns_pro(start)
    forward = decide_turn_pro(predecessor=start, target=week(2), candidates=_candidates(),
                              policy=POLICY, seed=seed)
    backward = decide_turn_pro(predecessor=start, target=week(2),
                               candidates=list(reversed(_candidates())),
                               policy=POLICY, seed=seed)
    assert forward == backward and forward
    # Evaluating fewer players never changes another player's outcome.
    only_a = decide_turn_pro(predecessor=start, target=week(2), candidates=_candidates()[:1],
                             policy=POLICY, seed=seed)
    assert {d.player_id for d in only_a} == {d.player_id for d in forward} & {"a"}
    advanced = advance_calendar_lifecycle(start, week(2), (), forward)
    entered = {p.player_id for p in advanced.players if p.tour_entry_week == week(2)}
    assert entered == {d.player_id for d in forward}
    assert all("pre-alpha-turn-pro.v1" in d.provenance for d in forward)


def test_invalid_candidates_and_policies_fail_closed():
    start = bootstrap("turn_pro.v87")
    run = dict(predecessor=start, target=week(2), policy=POLICY, seed=1)
    with pytest.raises(ValueError, match="Duplicate"):
        decide_turn_pro(**run, candidates=_candidates()[:1] * 2)
    with pytest.raises(ValueError, match="absent from lifecycle"):
        decide_turn_pro(**run, candidates=[TurnProCandidate(player_id="zz", age=16, readiness=0)])
    with pytest.raises(ValueError, match="predates its lifecycle age"):
        decide_turn_pro(**run, candidates=[TurnProCandidate(player_id="a", age=15, readiness=0)])
    with pytest.raises(ValueError, match="consecutive Week Transition"):
        decide_turn_pro(**{**run, "target": week(3)}, candidates=[])
    with pytest.raises(ValueError, match="requires the v87 lifecycle policy"):
        decide_turn_pro(**{**run, "predecessor": bootstrap()}, candidates=[])
    pro = advance_calendar_lifecycle(start, week(2), (), (decision("a", 2),))
    with pytest.raises(ValueError, match="must be an active prospect"):
        decide_turn_pro(predecessor=pro, target=week(3), policy=POLICY, seed=1,
                        candidates=[TurnProCandidate(player_id="a", age=16, readiness=0)])


def _turn_pro_ages(readiness, *, w, players=3000):
    """Synthetic cohort from age 15 using only the public per-week functions."""
    clock = RunCalendar(w, 1, 2030, 40)
    ages = []
    for index in range(players):
        pid = f"p{index}"
        for ordinal in range(30 * w):
            age = 15 + ordinal // w
            target = RunWeekPosition(calendar=clock, season_index=ordinal // w, week=ordinal % w + 1)
            p = weekly_turn_pro_chance(
                POLICY, TurnProCandidate(player_id=pid, age=age, readiness=readiness),
                weeks_per_year=w,
            )
            if turn_pro_draw(seed=11, run_id="r", branch_id="b", player_id=pid, target=target) < p:
                ages.append(15 + ordinal / w)
                break
        else:
            ages.append(math.inf)
    return sorted(ages)


@pytest.mark.parametrize("w", [52, 61])
def test_default_calibration_meets_the_provisional_targets(w):
    ages = _turn_pro_ages(POLICY.readiness_reference, w=w)
    median = ages[len(ages) // 2]
    share = lambda limit: sum(a < limit for a in ages) / len(ages)
    assert 17.5 <= median <= 19.0
    assert share(16) <= 0.08  # turning pro at 15 stays the exception
    assert share(19) >= 0.55
    assert share(22) >= 0.97
    assert share(45) == 1.0  # nobody stays a prospect for a whole career
    # A much stronger cohort turns pro clearly earlier; a weak one later but surely.
    strong = _turn_pro_ages(0.9, w=w, players=800)
    weak = _turn_pro_ages(0.0, w=w, players=800)
    assert strong[len(strong) // 2] < median < weak[len(weak) // 2]
    assert weak[-1] < 45

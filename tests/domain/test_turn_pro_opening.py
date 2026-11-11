"""Master v87 opening professionals: retrospective Turn Pro before Run start."""

import json
import math

import pytest

from beta_engine.domain.players.calendar_lifecycle import (
    CalendarInitialProfessionalIdentity,
    CalendarPlayerLifecycleState,
    advance_calendar_lifecycle,
)
from beta_engine.domain.players.turn_pro import (
    is_professional_at,
    opening_turn_pro_tie_break_token,
    require_professional_for_entry,
)
from beta_engine.domain.players.turn_pro_model import (
    InitialTurnProEvidence,
    InitialTurnProPlayer,
    build_turn_pro_candidates,
    default_turn_pro_model_policy,
    initial_professional_ids,
    initial_turn_pro_chance,
)
from beta_engine.domain.tournaments.calendar_tour import professional_ranking_players
from tests.domain.test_turn_pro_lifecycle import bootstrap, decision, week

pytestmark = pytest.mark.pr_critical

MODEL = default_turn_pro_model_policy()


def opening(rule="turn_pro.v87", pros=("a",), **token_override):
    base = bootstrap(rule)
    players = tuple(
        CalendarInitialProfessionalIdentity(
            **p.model_dump(),
            tour_entry_week=week(1),
            tie_break_token=token_override.get(
                p.player_id,
                opening_turn_pro_tie_break_token(run_id="r", player_id=p.player_id),
            ),
        )
        if p.player_id in pros
        else p
        for p in base.players
    )
    return CalendarPlayerLifecycleState.model_validate_json(
        base.model_copy(update={"players": players}).model_dump_json()
    )


@pytest.mark.parametrize("w", [52, 61])
def test_retrospective_chance_integrates_the_weekly_model(w):
    neutral = MODEL.readiness_reference
    chance = lambda weeks: initial_turn_pro_chance(
        MODEL, age_weeks=weeks, readiness=neutral, weeks_per_year=w
    )
    assert chance(15 * w) == 0.0  # nobody can have turned pro before 15
    assert math.isclose(chance(16 * w), MODEL.annual_base_by_age[0], rel_tol=1e-12)
    survive = math.prod(1 - b for b in MODEL.annual_base_by_age[:5])
    assert math.isclose(chance(20 * w), 1 - survive, rel_tol=1e-12)
    # Half a year at 15 is half the annual hazard, whatever W is.
    half = -math.expm1(math.log1p(-MODEL.annual_base_by_age[0]) / 2)
    assert math.isclose(chance(15 * w + w // 2), half, rel_tol=2 / w)
    stronger = initial_turn_pro_chance(MODEL, age_weeks=18 * w, readiness=0.9, weeks_per_year=w)
    assert stronger > chance(18 * w)


def _cohort(n=2000, w=52):
    return [
        InitialTurnProPlayer(
            player_id=f"p{i:04d}", age_weeks=15 * w + 1 + (i * 37) % (15 * w),
            strength=float(30 + (i * 53) % 60),
        )
        for i in range(n)
    ]


def test_opening_selection_is_deterministic_order_free_and_age_driven():
    cohort = _cohort()
    run = dict(run_id="r", policy=MODEL, seed=4, weeks_per_year=52)
    chosen = initial_professional_ids(players=cohort, **run)
    assert chosen == initial_professional_ids(players=list(reversed(cohort)), **run)
    assert chosen != initial_professional_ids(players=cohort, **{**run, "seed": 5})
    assert list(chosen) == sorted(chosen)
    age = {p.player_id: p.age_weeks / 52 for p in cohort}
    share = lambda lo, hi: (
        sum(age[c] < hi and age[c] >= lo for c in chosen)
        / sum(lo <= a < hi for a in age.values())
    )
    assert share(15, 16) < 0.08 and share(18, 19) > 0.4 and share(24, 30) > 0.97
    with pytest.raises(ValueError, match="Duplicate"):
        initial_professional_ids(players=cohort[:1] * 2, **run)
    with pytest.raises(ValueError, match="canonical distinct"):
        InitialTurnProEvidence(model=MODEL, seed=1, professional_player_ids=("b", "a"))


def test_opening_professional_identity_keeps_population_only_bytes():
    plain = json.loads(bootstrap("turn_pro.v87").model_dump_json())
    assert all("tour_entry_week" not in p for p in plain["players"])
    state = opening()
    body = json.loads(state.model_dump_json())
    assert [("tour_entry_week" in p) for p in body["players"]] == [True, False]
    assert CalendarPlayerLifecycleState.model_validate_json(state.model_dump_json()) == state
    with pytest.raises(ValueError, match="requires the v87"):
        opening(rule=None)
    with pytest.raises(ValueError, match="foreign tie-break token"):
        opening(a="x")


def test_opening_professionals_enter_play_and_rank_from_week_one():
    state = opening()
    require_professional_for_entry(state, "a", week(1))
    with pytest.raises(ValueError, match="has not turned pro"):
        require_professional_for_entry(state, "b", week(1))
    w2 = advance_calendar_lifecycle(state, week(2), ())
    entered = {p.player_id: p for p in w2.players}
    assert entered["a"].tour_entry_week == week(1)
    assert entered["a"].tie_break_token == state.players[0].tie_break_token
    assert is_professional_at(w2, "a", week(2)) and not is_professional_at(w2, "b", week(2))
    assert [p.player_id for p in professional_ranking_players(w2, before=week(2))] == ["a"]
    # Opening pros are the readiness reference and never candidates themselves.
    candidates = build_turn_pro_candidates(state, w2, {"a": 50.0, "b": 60.0})
    assert [(c.player_id, c.readiness) for c in candidates] == [("b", 1.0)]
    with pytest.raises(ValueError, match="conflicts with recorded Tour entry"):
        advance_calendar_lifecycle(state, week(2), (), (decision("a", 2),))

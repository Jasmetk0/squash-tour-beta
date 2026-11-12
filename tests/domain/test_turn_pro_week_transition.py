"""Master v87 Week Transition: recorded Turn Pro decisions, candidates and replay."""

import json
from types import SimpleNamespace

import pytest

from beta_engine.application import calendar_tour_service as service
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.calendar.season_weeks import age_at_calendar_position
from beta_engine.domain.players.calendar_lifecycle import (
    CalendarPlayerLifecycleIdentity,
    CalendarPlayerLifecycleState,
    advance_calendar_lifecycle,
    calendar_lifecycle_history,
)
from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.turn_pro_model import (
    build_turn_pro_candidates,
    decide_turn_pro,
    default_turn_pro_model_policy,
    readiness_against,
    true_strength_turn_pro_model_policy_v1,
    turn_pro_candidates_for,
)
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarTourTransition,
    tour_turn_pro_decisions,
)
from tests.domain.test_turn_pro_lifecycle import bootstrap, decision, policy, week

pytestmark = pytest.mark.pr_critical

MODEL = default_turn_pro_model_policy()
# The v2 policy exactly as recorded before decision evidence existed (same bytes).
LEGACY_V2 = MODEL.model_copy(update={"decision_evidence": None})
V1 = true_strength_turn_pro_model_policy_v1()


def record(pid, value):
    """A sporting record with the canonical 57 attributes at one level."""
    return SimpleNamespace(
        player_id=pid,
        attributes=tuple((name, value) for name in CANONICAL_PLAYER_ATTRIBUTES),
        ovr=value,
    )


def transition(target=2, decisions=(), model=None):
    return CalendarTourTransition(
        command_id=f"t{target}", completed_week=week(target - 1), target_week=week(target),
        sporting_advance_fingerprint="s", ranking_fingerprint="r", health_fingerprint="h",
        ages=(("a", 16),), retired_player_ids=(), public_event={"kind": "week_transition_completed"},
        turn_pro_decisions=tuple(decisions), turn_pro_model=model,
    )


def test_historical_transition_bytes_are_unchanged_and_evidence_round_trips():
    plain = transition()
    body = json.loads(plain.model_dump_json())
    assert "turn_pro_decisions" not in body and "turn_pro_model" not in body
    assert CalendarTourTransition.model_validate_json(plain.model_dump_json()) == plain

    rich = transition(decisions=(decision("a", 2),), model=LEGACY_V2)
    assert CalendarTourTransition.model_validate_json(rich.model_dump_json()) == rich
    assert "decision_evidence" not in json.loads(LEGACY_V2.model_dump_json())
    # A v87 transition that evaluated nobody still records the model it used.
    assert "turn_pro_model" in json.loads(transition(model=MODEL).model_dump_json())
    assert tour_turn_pro_decisions(SimpleNamespace(transitions=(plain, rich))) == (
        decision("a", 2),
    )
    assert tour_turn_pro_decisions(None) == ()


@pytest.mark.parametrize("decisions,model,message", [
    ((decision("a", 2),), None, "require the model policy"),
    ((decision("a", 3),), LEGACY_V2, "not effective at its transition week"),
    ((decision("b", 2), decision("a", 2)), LEGACY_V2, "canonical distinct players"),
])
def test_transition_rejects_inconsistent_turn_pro_evidence(decisions, model, message):
    with pytest.raises(ValueError, match=message):
        transition(decisions=decisions, model=model)


def test_readiness_counts_strictly_weaker_reference_players():
    assert readiness_against(50, (40, 50, 60, 45)) == 0.5
    with pytest.raises(ValueError, match="non-empty reference"):
        readiness_against(50, ())


def test_candidates_compare_with_tour_players_and_fall_back_to_population():
    start = bootstrap("turn_pro.v87", retiring_player=True)
    w2 = advance_calendar_lifecycle(start, week(2), ())
    plain_w3 = advance_calendar_lifecycle(w2, week(3), ())  # "c" retires at week 3
    strengths = {"a": 70.0, "b": 50.0, "c": 90.0}
    # Nobody is a pro yet: readiness is relative to the whole active population.
    fallback = build_turn_pro_candidates(w2, plain_w3, strengths)
    assert [(c.player_id, c.readiness) for c in fallback] == [("a", 0.5), ("b", 0.0)]
    # Once "a" is a pro, "b" is measured against Tour Players only.
    pro_w2 = advance_calendar_lifecycle(start, week(2), (), (decision("a", 2),))
    plain = advance_calendar_lifecycle(pro_w2, week(3), (), (decision("a", 2),))
    only_b = build_turn_pro_candidates(pro_w2, plain, {**strengths, "b": 75.0},
                                       home_opportunity_by_player={"b": True})
    assert [(c.player_id, c.readiness, c.home_opportunity) for c in only_b] == [("b", 1.0, True)]
    with pytest.raises(ValueError, match="every active player's strength"):
        build_turn_pro_candidates(w2, plain_w3, {"a": 1.0})


def _population(n=40):
    clock = RunCalendar(52, 35, 2030, 6)
    opening = RunWeekPosition(calendar=clock, season_index=0, week=1)
    year_week = opening.calendar_position
    players = tuple(
        CalendarPlayerLifecycleIdentity(
            player_id=f"p{i:02d}", birth_year=year_week.calendar_year - 15 - (i % 4) - 1,
            birth_year_week=(i * 7) % 52 + 1, age=15 + (i % 4),
            source_generation_fingerprint=f"{i:064x}",
        )
        for i in range(n)
    )
    players = tuple(
        p.model_copy(update={"age": age_at_calendar_position(
            birth_year=p.birth_year, birth_year_week=p.birth_year_week,
            calendar_year=year_week.calendar_year, year_week=year_week.year_week,
            weeks_per_calendar_year=52)})
        for p in players
    )
    return clock, CalendarPlayerLifecycleState(
        run_id="r", branch_id="b", week=opening, players=players,
        source_initial_world_fingerprint="f" * 64, policy=policy("turn_pro.v87"),
    )


def _simulate(weeks, seed):
    clock, state = _population()
    strengths = {p.player_id: 40 + (int(p.player_id[1:]) * 37) % 60 for p in state.players}
    states, recorded = [state], []
    for ordinal in range(1, weeks + 1):
        position = clock.position_at_ordinal(ordinal)
        target = RunWeekPosition(calendar=clock, season_index=position.season_index,
                                 week=position.season_week)
        plain = advance_calendar_lifecycle(states[-1], target, (), tuple(recorded))
        made = decide_turn_pro(
            predecessor=states[-1], target=target, policy=V1, seed=seed,
            candidates=build_turn_pro_candidates(states[-1], plain, strengths),
        )
        recorded.extend(made)
        states.append(advance_calendar_lifecycle(states[-1], target, (), tuple(recorded)))
    return clock, states, tuple(recorded)


def test_recorded_decisions_replay_the_exact_lifecycle_history():
    clock, states, recorded = _simulate(104, seed=42)
    assert recorded, "two simulated years must produce professionals"
    target = states[-1].week
    replay = calendar_lifecycle_history(states[0], target, (), turn_pro=recorded)
    assert [s.fingerprint for s in replay] == [s.fingerprint for s in states]
    # Same inputs, same seed: identical decisions; another seed differs.
    assert _simulate(104, seed=42)[2] == recorded
    assert _simulate(104, seed=43)[2] != recorded
    # The oldest prospects turn pro first on average.
    ages = {p.player_id: p.age for p in states[0].players}
    turned = {d.player_id for d in recorded}
    oldest = [pid for pid, age in ages.items() if age >= 18]
    youngest = [pid for pid, age in ages.items() if age <= 15]
    assert sum(p in turned for p in oldest) / len(oldest) > sum(
        p in turned for p in youngest) / len(youngest)


def test_service_week_runs_the_model_only_under_v87(monkeypatch):
    clock, states, _ = _simulate(3, seed=5)
    target_ordinal = 4
    position = clock.position_at_ordinal(target_ordinal)
    target = RunWeekPosition(calendar=clock, season_index=position.season_index,
                             week=position.season_week)
    state = SimpleNamespace(editions=(), transitions=())
    checkpoint = SimpleNamespace(players=tuple(
        record(p.player_id, 80 + i) for i, p in enumerate(states[0].players)
    ))
    history = calendar_lifecycle_history(states[0], target, ())
    monkeypatch.setattr(service, "_lifecycle_history", lambda world, week, s: history)
    lifecycle, decisions, model = service._turn_pro_week(None, state, target, checkpoint, 9)
    assert model == MODEL
    candidates = turn_pro_candidates_for(
        MODEL, history[-2], history[-1], checkpoint.players, seed=9, target=target,
        traits_by_player={}, home_opportunity_by_player={},
    )
    # Model v2: each candidate carries what the prospect perceived about itself.
    assert candidates and all(c.observation is not None for c in candidates)
    expected = decide_turn_pro(
        predecessor=history[-2], target=target, policy=MODEL, seed=9, candidates=candidates,
    )
    assert decisions == expected
    assert {p.player_id for p in lifecycle.players if p.tour_entry_week == target} == {
        d.player_id for d in decisions
    }

    legacy = calendar_lifecycle_history(bootstrap(), week(2), ())
    monkeypatch.setattr(service, "_lifecycle_history", lambda world, week, s: legacy)
    assert service._turn_pro_week(None, state, week(2), checkpoint, 9) == (legacy[-1], (), None)

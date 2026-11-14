"""Master v87 Turn Pro model v2: a prospect decides from its own imperfect self-view."""

import json
import math
from statistics import mean, pstdev
from types import SimpleNamespace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.attribute_catalog import (
    ATTRIBUTE_TO_GROUP,
    CANONICAL_PLAYER_ATTRIBUTES,
)
from beta_engine.domain.players.calendar_lifecycle import advance_calendar_lifecycle
from beta_engine.domain.players.turn_pro_model import (
    TurnProCandidate,
    TurnProModelPolicy,
    decide_turn_pro,
    default_turn_pro_model_policy,
    true_strength_turn_pro_model_policy_v1,
    turn_pro_candidates_for,
    turn_pro_draw,
    weekly_turn_pro_chance,
)
from beta_engine.domain.players.turn_pro_perception import (
    TurnProObservation,
    default_self_perception_policy,
    perceive_self,
)
from tests.domain.test_turn_pro_lifecycle import bootstrap, week

pytestmark = pytest.mark.pr_critical

MODEL = default_turn_pro_model_policy()
PERCEPTION = default_self_perception_policy()


def attributes(base=100, **overrides):
    return tuple((name, overrides.get(name, base)) for name in CANONICAL_PLAYER_ATTRIBUTES)


def perceive(pid="p", attrs=None, seed=1, ordinal=5, **traits):
    return perceive_self(
        policy=PERCEPTION, run_id="r", player_id=pid, attributes=attrs or attributes(),
        seed=seed, week_ordinal=ordinal, **traits,
    )


def test_policy_versions_and_v1_bytes_are_preserved():
    v1 = true_strength_turn_pro_model_policy_v1()
    raw = json.loads(v1.model_dump_json())
    assert not {"perception", "ambition_weight", "professionalism_weight"} & set(raw)
    assert TurnProModelPolicy.model_validate_json(v1.model_dump_json()) == v1
    assert TurnProModelPolicy.model_validate_json(MODEL.model_dump_json()) == MODEL
    assert MODEL.model_id == "pre-alpha-turn-pro.v2" and MODEL.uses_self_perception
    with pytest.raises(ValueError, match="personality weights"):
        TurnProModelPolicy.model_validate({**MODEL.model_dump(), "ambition_weight": None})


def test_perception_is_deterministic_persistent_and_order_free():
    first = perceive()
    assert first == perceive()
    assert isinstance(first, TurnProObservation) and first.financial_level is None
    # Persistent self-view: another week moves it only by the small weekly part.
    later = perceive(ordinal=40, seed=9)
    assert later != first
    assert abs(later.perceived_overall - first.perceived_overall) < 4 * 1.4 * 2.0 * 2
    with pytest.raises(ValueError, match="not modelled yet"):
        perceive(financial_level=5)


def _many(n=400, **kw):
    return [perceive(pid=f"p{i}", **kw) for i in range(n)]


def test_relative_self_knowledge_beats_absolute_level():
    # Forehand clearly stronger than backhand; endurance clearly above strength.
    attrs = attributes(Forehand=125, Backhand=95, Endurance=125, Strength=95)
    observed = _many(attrs=attrs, n=500)
    seen = [dict(o.perceived_attributes) for o in observed]
    hand = sum(a["Forehand"] > a["Backhand"] for a in seen) / len(seen)
    body = sum(a["Endurance"] > a["Strength"] for a in seen) / len(seen)
    assert hand > 0.99 and body > 0.99
    # The absolute level is much less certain than such relative comparisons.
    level_spread = pstdev(o.perceived_overall for o in observed)
    gap_spread = pstdev(a["Forehand"] - a["Backhand"] for a in seen)
    assert level_spread > 1.5 * gap_spread
    assert 6 < level_spread < 20


def test_confidence_biases_and_reflection_sharpens_the_self_view():
    true_overall = 100
    bold = mean(o.perceived_overall for o in _many(attrs=attributes(Confidence=170)))
    shy = mean(o.perceived_overall for o in _many(attrs=attributes(Confidence=30)))
    assert bold > true_overall + 0.5 and shy < true_overall - 0.5
    sharp = pstdev(o.perceived_overall for o in _many(
        attrs=attributes(Analysis=190, **{"Self Control": 190})))
    blurry = pstdev(o.perceived_overall for o in _many(
        attrs=attributes(Analysis=20, **{"Self Control": 20})))
    assert sharp < blurry


def test_strongest_group_is_judged_most_accurately():
    attrs = attributes(**{n: 150 for n in CANONICAL_PLAYER_ATTRIBUTES
                          if ATTRIBUTE_TO_GROUP[n] == "Mental"})
    group_mean = {}
    for group in ("Mental", "Tactics"):
        names = [n for n in CANONICAL_PLAYER_ATTRIBUTES if ATTRIBUTE_TO_GROUP[n] == group]
        group_mean[group] = sum(dict(attrs)[n] for n in names) / len(names)
    obs = _many(attrs=attrs)
    error = {
        g: pstdev(dict(o.perceived_groups)[g] - o.perceived_overall for o in obs)
        for g in ("Mental", "Tactics")
    }
    # Both have the same base error; Mental is the strongest group, so it is sharper.
    assert error["Mental"] < error["Tactics"]


def _lifecycle():
    start = bootstrap("turn_pro.v87")
    return start, advance_calendar_lifecycle(start, week(2), ())


def test_candidates_read_only_the_prospects_own_record():
    start, plain = _lifecycle()
    records = [SimpleNamespace(player_id="a", attributes=attributes(110)),
               SimpleNamespace(player_id="b", attributes=attributes(90))]
    base = turn_pro_candidates_for(MODEL, start, plain, records, seed=4, target=week(2))
    changed = turn_pro_candidates_for(
        MODEL, start, plain,
        [records[0], SimpleNamespace(player_id="b", attributes=attributes(180))],
        seed=4, target=week(2),
    )
    # Player a's inputs do not depend on anyone else's hidden strength.
    assert base[0] == changed[0]
    assert base[1] != changed[1]
    assert all(c.observation.ambition is None for c in base)  # unknown traits stay neutral
    decisions = decide_turn_pro(predecessor=start, target=week(2), candidates=base,
                                policy=MODEL, seed=4)
    assert all(d.player_id in {"a", "b"} for d in decisions)


def _candidate(readiness=0.5, ambition=0.5, professionalism=0.5, age=18):
    obs = perceive().model_copy(update={
        "readiness": readiness, "ambition": ambition, "professionalism": professionalism,
    })
    return TurnProCandidate(player_id="p", age=age, readiness=readiness, observation=obs)


def test_personality_and_self_view_raise_the_weekly_chance():
    chance = lambda **kw: weekly_turn_pro_chance(MODEL, _candidate(**kw), weeks_per_year=52)
    assert chance(ambition=0.9) > chance() > chance(ambition=0.1)
    assert chance(professionalism=0.9) > chance() > chance(professionalism=0.1)
    assert chance(readiness=0.9) > chance() > chance(readiness=0.1)
    with pytest.raises(ValueError, match="matching observation"):
        weekly_turn_pro_chance(MODEL, TurnProCandidate(player_id="p", age=18, readiness=0.5),
                               weeks_per_year=52)


@pytest.mark.parametrize("w", [52, 61, 80])
def test_neutral_v2_reproduces_the_annual_base_for_every_w(w):
    weekly = weekly_turn_pro_chance(MODEL, _candidate(), weeks_per_year=w)
    assert math.isclose(1 - (1 - weekly) ** w, MODEL.annual_base_by_age[3], rel_tol=1e-12)


def _turn_pro_ages(ovr_at_15, *, w=52, players=600, ambition=0.5):
    """Synthetic prospects who improve ~8 OVR a year from age 15."""
    clock = RunCalendar(w, 1, 2030, 40)
    ages = []
    for index in range(players):
        pid = f"s{index}"
        for ordinal in range(30 * w):
            age = 15 + ordinal // w
            level = min(200, ovr_at_15 + 8 * (age - 15))
            obs = perceive_self(policy=PERCEPTION, run_id="r", player_id=pid,
                                attributes=attributes(level), seed=11, week_ordinal=ordinal,
                                ambition=ambition, professionalism=0.5)
            candidate = TurnProCandidate(player_id=pid, age=age, readiness=obs.readiness,
                                         observation=obs)
            target = RunWeekPosition(calendar=clock, season_index=ordinal // w,
                                     week=ordinal % w + 1)
            p = weekly_turn_pro_chance(MODEL, candidate, weeks_per_year=w)
            if turn_pro_draw(seed=11, run_id="r", branch_id="b", player_id=pid,
                             target=target) < p:
                ages.append(15 + ordinal / w)
                break
        else:
            ages.append(math.inf)
    return sorted(ages)


def test_calibration_typical_prospect_and_talent_and_ambition():
    typical = _turn_pro_ages(78)  # generated median OVR at 15
    median = typical[len(typical) // 2]
    assert 17.0 <= median <= 19.5, median
    assert sum(a < 16 for a in typical) / len(typical) <= 0.10
    assert sum(a < 22 for a in typical) / len(typical) >= 0.95
    talent = _turn_pro_ages(100, players=300)
    ambitious = _turn_pro_ages(78, players=300, ambition=0.9)
    assert talent[len(talent) // 2] < median
    assert ambitious[len(ambitious) // 2] < median

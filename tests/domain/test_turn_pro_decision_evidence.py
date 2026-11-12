"""Master v87: a positive Turn Pro decision stores what the prospect knew.

Domain contract. The model policy version decides whether evidence exists; older
recorded bytes (v1 and v2 without evidence) are unchanged. Mathematical replay
needs only the decision, its recorded model and the command seed.
"""

import json

import pytest

from beta_engine.domain.players.turn_pro import PlayerTurnProDecision
from beta_engine.domain.players.turn_pro_model import (
    default_turn_pro_model_policy,
    verify_turn_pro_decision_evidence,
)
from beta_engine.domain.players.turn_pro_perception import default_self_perception_policy
from tests.domain.test_turn_pro_week_transition import (
    LEGACY_V2,
    MODEL,
    record,
    transition,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_lifecycle import advance_calendar_lifecycle
from beta_engine.domain.players.turn_pro_model import decide_turn_pro, turn_pro_candidates_for
from tests.domain.test_turn_pro_lifecycle import bootstrap

pytestmark = pytest.mark.pr_critical

SEED = 11


def _real_decisions(model, *, weeks=60, level=140):
    """Run the model over a prospect group until it produces positive decisions."""
    start = bootstrap("turn_pro.v87")
    clock = start.week.calendar
    made, state = [], start
    for ordinal in range(start.week.ordinal + 1, start.week.ordinal + 1 + weeks):
        position = clock.position_at_ordinal(ordinal)
        target = RunWeekPosition(
            calendar=clock, season_index=position.season_index, week=position.season_week
        )
        plain = advance_calendar_lifecycle(state, target, (), tuple(made))
        records = [record(p.player_id, level) for p in state.players]
        decisions = decide_turn_pro(
            predecessor=state,
            target=target,
            policy=model,
            seed=SEED,
            candidates=turn_pro_candidates_for(
                model, state, plain, records, seed=SEED, target=target,
            ),
        )
        made.extend(decisions)
        state = advance_calendar_lifecycle(state, target, (), tuple(made))
        if made:
            return tuple(made), model
    pytest.skip("fixture population produced no decision in the window")


def test_default_policy_declares_evidence_and_legacy_bytes_stay_unchanged():
    assert MODEL.decision_evidence == "observation.v1"
    legacy = json.loads(LEGACY_V2.model_dump_json())
    assert "decision_evidence" not in legacy
    # The legacy fingerprint is the fingerprint of today's v2 bytes without the field.
    assert LEGACY_V2.fingerprint != MODEL.fingerprint
    assert default_turn_pro_model_policy() == MODEL


def test_positive_decisions_carry_the_players_own_observation():
    made, model = _real_decisions(MODEL)
    decision = made[0]
    assert decision.evidence is not None
    observation = decision.evidence.observation
    assert observation.player_id == decision.player_id
    assert observation.policy_fingerprint == model.perception.fingerprint
    assert observation.financial_level is None  # explicitly unknown, not guessed
    assert len(observation.perceived_attributes) == 57
    # Round trip keeps the exact evidence and fingerprint.
    again = PlayerTurnProDecision.model_validate_json(decision.model_dump_json())
    assert again == decision and again.fingerprint == decision.fingerprint
    verify_turn_pro_decision_evidence(decision, policy=model, seed=SEED)


def test_legacy_v2_decisions_have_no_evidence_field_and_cannot_be_replayed():
    made, model = _real_decisions(LEGACY_V2)
    assert all(d.evidence is None for d in made)
    assert "evidence" not in json.loads(made[0].model_dump_json())
    with pytest.raises(ValueError, match="recorded no decision evidence"):
        verify_turn_pro_decision_evidence(made[0], policy=model, seed=SEED)


def test_replay_rejects_changed_model_seed_observation_and_week():
    made, model = _real_decisions(MODEL)
    decision = made[0]
    # A different seed gives another draw: provenance (and normally the draw) differs.
    with pytest.raises(ValueError, match="draw|provenance"):
        verify_turn_pro_decision_evidence(decision, policy=model, seed=SEED + 1)
    # A changed model (any weight) changes the recomputed chance.
    other = model.model_copy(update={"readiness_weight": model.readiness_weight + 0.5})
    with pytest.raises(ValueError, match="provenance|draw"):
        verify_turn_pro_decision_evidence(decision, policy=other, seed=SEED)
    # A different perception policy cannot own the recorded observation.
    foreign = model.perception.model_copy(update={"level_error_sd": 11.0})
    with pytest.raises(ValueError, match="different perception policy"):
        verify_turn_pro_decision_evidence(
            decision, policy=model.model_copy(update={"perception": foreign}), seed=SEED
        )
    # An edited observation changes readiness and so the recorded chance.
    evidence = decision.evidence
    edited_obs = evidence.observation.model_copy(
        update={"readiness": round(evidence.observation.readiness * 0.5, 12)}
    )
    edited = decision.model_copy(
        update={"evidence": evidence.model_copy(update={"observation": edited_obs})}
    )
    with pytest.raises(ValueError, match="draw|provenance"):
        verify_turn_pro_decision_evidence(edited, policy=model, seed=SEED)
    # A decision moved to another week draws differently.
    later = RunWeekPosition(
        calendar=decision.effective_week.calendar,
        season_index=decision.effective_week.season_index,
        week=decision.effective_week.week + 1,
    )
    with pytest.raises(ValueError, match="draw|provenance"):
        verify_turn_pro_decision_evidence(
            decision.model_copy(update={"effective_week": later}), policy=model, seed=SEED
        )
    # Evidence of one player cannot be attached to another.
    with pytest.raises(ValueError, match="different player"):
        PlayerTurnProDecision.model_validate_json(
            json.dumps({**decision.model_dump(mode="json"), "player_id": decision.player_id + "x"})
        )
    # Missing evidence under an evidence model, and evidence under a model without it.
    with pytest.raises(ValueError, match="lacks its recorded evidence"):
        verify_turn_pro_decision_evidence(
            decision.model_copy(update={"evidence": None}), policy=model, seed=SEED
        )
    with pytest.raises(ValueError, match="not allowed"):
        verify_turn_pro_decision_evidence(decision, policy=LEGACY_V2, seed=SEED)


def test_transition_requires_evidence_exactly_when_the_recorded_model_has_it():
    made, model = _real_decisions(MODEL)
    legacy_made, legacy = _real_decisions(LEGACY_V2)
    target = made[0].effective_week  # season 0, week == fixture n
    ok = transition(target=target.week, decisions=(made[0],), model=model)
    assert ok.turn_pro_decisions[0].evidence is not None
    with pytest.raises(ValueError, match="evidence differs from its recorded model"):
        transition(
            target=target.week,
            decisions=(made[0].model_copy(update={"evidence": None}),),
            model=model,
        )
    with pytest.raises(ValueError, match="evidence differs from its recorded model"):
        transition(target=legacy_made[0].effective_week.week, decisions=(made[0].model_copy(
            update={"effective_week": legacy_made[0].effective_week}),), model=legacy)
    foreign = default_self_perception_policy().model_copy(update={"attribute_error_sd": 5.0})
    with pytest.raises(ValueError, match="different perception"):
        transition(
            target=target.week,
            decisions=(made[0],),
            model=model.model_copy(update={"perception": foreign}),
        )

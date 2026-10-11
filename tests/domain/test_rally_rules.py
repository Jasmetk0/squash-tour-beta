from __future__ import annotations

import json
from itertools import pairwise
from pathlib import Path

import pytest
from pydantic import ValidationError

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import (
    BallHitPlayerRuleContext,
    EffectiveRallyRulesSnapshot,
    ExternalInterruptionRuleContext,
    InterferenceRuleContext,
    MatchContext,
    MatchEngine,
    MatchInputSnapshot,
    MatchParticipantContext,
    MatchResult,
    MatchTimelineLog,
    RallyEvent,
    RallyRulesResolution,
    RallyRulesResolver,
    StandardRallyRuleContext,
    official_match_format_snapshot,
)
from tests.domain.test_match_rally_log import _player

PLAYERS = {"striker_player_id": "A", "non_striker_player_id": "B"}


@pytest.mark.parametrize(
    ("facts", "call", "winner"),
    [
        ({}, "YES_LET", None),
        ({"direct_access": True}, "NO_LET", "B"),
        ({"good_return_possible": False}, "NO_LET", "B"),
        ({"played_through": True, "winning_return": True}, "NO_LET", "B"),
        ({"minimal_interference": True}, "NO_LET", "B"),
        ({"striker_effort": False}, "NO_LET", "B"),
        ({"self_created_path": True}, "NO_LET", "B"),
        ({"clearing_effort": False}, "STROKE", "A"),
        ({"winning_return": True}, "STROKE", "A"),
        ({"fair_view": False, "direct_access": True}, "YES_LET", None),
        ({"reasonable_swing": False}, "YES_LET", None),
        ({"reasonable_swing": False, "swing_prevented": True}, "STROKE", "A"),
        ({"excessive_swing": "CAUSED"}, "NO_LET", "B"),
        ({"excessive_swing": "EXAGGERATED"}, "YES_LET", None),
        ({"wrong_footed_recovery": True}, "YES_LET", None),
        ({"wrong_footed_recovery": True, "winning_return": True}, "STROKE", "A"),
        ({"turning": True, "turned_to_create_request": True}, "NO_LET", "B"),
        ({"turning": True, "non_striker_had_time_to_clear": False}, "YES_LET", None),
        (
            {"attempt": "FURTHER", "non_striker_had_time_to_clear": False},
            "YES_LET",
            None,
        ),
        ({"front_wall_freedom": False}, "STROKE", "A"),
        (
            {"front_wall_freedom": False, "front_wall_path": "VIA_OTHER_WALL"},
            "YES_LET",
            None,
        ),
        (
            {
                "front_wall_freedom": False,
                "front_wall_path": "VIA_OTHER_WALL",
                "winning_return": True,
            },
            "STROKE",
            "A",
        ),
        ({"front_wall_freedom": False, "turning": True}, "YES_LET", None),
        ({"front_wall_freedom": False, "attempt": "FURTHER"}, "YES_LET", None),
        ({"direct_access": True, "reasonable_fear_of_injury": True}, "YES_LET", None),
    ],
)
def test_interference_rule_table(facts, call, winner):
    resolution = RallyRulesResolver.resolve(InterferenceRuleContext(**PLAYERS, **facts))
    assert resolution.initial_call == resolution.final_call == call
    assert resolution.point_winner_player_id == winner
    assert resolution.replay_required == (call == "YES_LET")
    assert (
        RallyRulesResolution.model_validate_json(resolution.model_dump_json())
        == resolution
    )


@pytest.mark.parametrize(
    ("facts", "call", "winner"),
    [
        ({}, "STROKE", "A"),
        ({"good_return_possible": False}, "POINT_AWARDED", "B"),
        ({"hit_player": "STRIKER"}, "POINT_AWARDED", "B"),
        ({"front_wall_path": "VIA_OTHER_WALL"}, "YES_LET", None),
        ({"front_wall_path": "VIA_OTHER_WALL", "winning_return": True}, "STROKE", "A"),
        ({"attempt": "FURTHER", "winning_return": True}, "YES_LET", None),
        ({"turning": True}, "STROKE", "B"),
        ({"turning": True, "deliberate_interception": True}, "STROKE", "A"),
        ({"turning": True, "good_return_possible": False}, "POINT_AWARDED", "B"),
        (
            {"ball_phase": "FROM_FRONT_WALL", "hit_player": "STRIKER"},
            "POINT_AWARDED",
            "B",
        ),
        ({"ball_phase": "FROM_FRONT_WALL", "attempt": "NONE"}, "POINT_AWARDED", "A"),
        (
            {
                "ball_phase": "FROM_FRONT_WALL",
                "attempt": "NONE",
                "striker_position_caused_hit": True,
            },
            "YES_LET",
            None,
        ),
        ({"ball_phase": "FROM_FRONT_WALL", "attempt": "FIRST"}, "YES_LET", None),
        (
            {
                "ball_phase": "FROM_FRONT_WALL",
                "attempt": "FURTHER",
                "good_return_possible": False,
            },
            "POINT_AWARDED",
            "B",
        ),
    ],
)
def test_ball_hit_rule_table(facts, call, winner):
    values = {
        **PLAYERS,
        "hit_player": "NON_STRIKER",
        "ball_phase": "TO_FRONT_WALL",
        **facts,
    }
    resolution = RallyRulesResolver.resolve(BallHitPlayerRuleContext(**values))
    assert resolution.initial_call == resolution.final_call == call
    assert resolution.point_winner_player_id == winner


def test_ball_hit_striker_can_resolve_related_interference():
    facts = BallHitPlayerRuleContext(
        **PLAYERS,
        hit_player="STRIKER",
        ball_phase="FROM_FRONT_WALL",
        interference=InterferenceRuleContext(**PLAYERS, clearing_effort=False),
    )
    assert RallyRulesResolver.resolve(facts).final_call == "STROKE"


@pytest.mark.parametrize(
    "trigger",
    [
        "GOOD_RETURN_UNANSWERED",
        "SERVE_FAULT",
        "RETURN_DOWN",
        "RETURN_OUT",
        "RETURN_NOT_UP",
    ],
)
def test_standard_rule_table(trigger):
    result = RallyRulesResolver.resolve(
        StandardRallyRuleContext(**PLAYERS, terminal_trigger=trigger)
    )
    assert result.point_winner_player_id == (
        "A" if trigger == "GOOD_RETURN_UNANSWERED" else "B"
    )


@pytest.mark.parametrize(
    "reason", ["COURT_CONDITION", "EXTERNAL_DISTRACTION", "BROKEN_BALL"]
)
def test_external_interruption_is_a_neutral_replay(reason):
    result = RallyRulesResolver.resolve(
        ExternalInterruptionRuleContext(
            **PLAYERS,
            reason=reason,
            interruption_elapsed_seconds=45,
        )
    )
    assert result.final_call == "YES_LET"
    assert result.point_winner_player_id is None


@pytest.mark.parametrize(
    "change",
    [
        {"final_call": "STROKE"},
        {"initial_call": "NO_LET"},
        {"point_winner_player_id": "A"},
        {"replay_required": False},
        {"decision_code": "FAKE"},
    ],
)
def test_stored_verdict_is_recomputed_from_facts_without_rng(change):
    result = RallyRulesResolver.resolve(InterferenceRuleContext(**PLAYERS))
    with pytest.raises(ValidationError, match="ground-truth facts"):
        RallyRulesResolution.model_validate({**result.model_dump(), **change})


def _context():
    return MatchContext(
        match_id="rules-match",
        player_a=MatchParticipantContext(player=_player("A", 84)),
        player_b=MatchParticipantContext(player=_player("B", 81)),
    )


def _simulate(seed=77, **rules):
    snapshot = MatchInputSnapshot.create(
        context=_context(),
        effective_match_format=official_match_format_snapshot(),
        simulation_seed=seed,
        match_engine_version="match_engine_v9",
        effective_rally_rules=EffectiveRallyRulesSnapshot(**rules),
    )
    result = MatchEngine(rng=DeterministicRng(seed)).simulate(
        snapshot.context,
        log_anchor_hash=snapshot.snapshot_hash,
        effective_match_timing=snapshot.effective_match_timing,
        effective_match_stamina=snapshot.effective_match_stamina,
        effective_match_gameplans=snapshot.effective_match_gameplans,
        rally_calibration_profile=snapshot.rally_calibration_profile,
        effective_rally_rules=snapshot.effective_rally_rules,
    )
    return snapshot, result


@pytest.mark.smoke
def test_rules_snapshot_and_full_match_roundtrip_and_determinism():
    inputs, result = _simulate(
        interference_probability=0.25, external_interruption_probability=0.1
    )
    assert (inputs, result) == _simulate(
        interference_probability=0.25, external_interruption_probability=0.1
    )
    assert MatchInputSnapshot.model_validate_json(inputs.model_dump_json()) == inputs
    assert MatchResult.model_validate_json(result.model_dump_json()) == result
    assert result.rally_log.replay_rallies > 0
    assert (
        result.rally_log.total_rallies
        == result.rally_log.scoring_rallies + result.rally_log.replay_rallies
    )
    assert result.rally_log.scoring_rallies == sum(
        s.winner_games + s.loser_games for s in result.sets
    )


@pytest.mark.smoke
def test_yes_let_preserves_score_server_box_and_consumes_workload():
    _, result = _simulate(interference_probability=0.25)
    replay_count = 0
    for rally, following in pairwise(result.rally_log.events):
        if rally.official_resolution != "YES_LET":
            continue
        replay_count += 1
        assert rally.winner_player_id is None and not rally.score_mutations
        assert rally.score_before == rally.score_after == following.score_before
        assert rally.serving_player_id == following.serving_player_id
        assert rally.service_box == rally.next_service_box == following.service_box
        marker = next(
            t
            for t in result.timeline_log.events
            if t.event_type == "RALLY" and t.rally_index == rally.rally_index
        )
        cost = result.stamina_log.transitions[marker.timeline_index - 1]
        assert cost.cause == "RALLY_WORKLOAD" and cost.workload_units > 0
        assert any(
            bar.current < before.current
            for state, old in zip(cost.states_after, cost.states_before, strict=True)
            for bar, before in zip(state.bars, old.bars, strict=True)
        )
        assert all(
            d.observed_neutral_replays > 0
            for d in following.gameplan_context.player_decisions
        )
    assert replay_count > 0


def test_external_delay_and_recovery_are_counted_once():
    _, result = _simulate(external_interruption_probability=0.1)
    timeline = result.timeline_log
    assert timeline.schema_version == "match_timeline_log.v2"
    assert timeline.objective_delay_count > 0
    assert timeline.total_elapsed_seconds == round(
        sum(e.elapsed_seconds for e in timeline.events), 3
    )
    for event in timeline.events:
        if event.event_type != "OBJECTIVE_DELAY":
            continue
        assert event.elapsed_seconds == max(
            event.interruption_elapsed_seconds, event.restart_ready_seconds
        )
        transition = result.stamina_log.transitions[event.timeline_index - 1]
        assert transition.cause == "OBJECTIVE_DELAY_RECOVERY"
        assert transition.workload_units == 0
        assert transition.elapsed_seconds == event.elapsed_seconds
    assert len(result.stamina_log.transitions) == len(timeline.events)


def test_generation_guard_cannot_change_an_existing_verdict():
    _, result = _simulate(
        interference_probability=0.25,
        external_interruption_probability=0.1,
        max_consecutive_replays=1,
    )
    assert result.rally_log.replay_rallies > 0
    for left, right in pairwise(result.rally_log.events):
        assert not (left.winner_player_id is None and right.winner_player_id is None)
    assert (
        RallyRulesResolver.resolve(InterferenceRuleContext(**PLAYERS)).final_call
        == "YES_LET"
    )


def test_rehashed_replay_point_and_service_forgery_are_rejected():
    _, result = _simulate(interference_probability=0.25)
    rally = next(e for e in result.rally_log.events if e.winner_player_id is None)
    for changes in (
        {"winner_player_id": "A"},
        {"next_service_box": "LEFT" if rally.service_box == "RIGHT" else "RIGHT"},
        {
            "score_mutations": [
                {
                    "player_id": "A",
                    "reason": "RALLY_RESULT",
                    "mutation_type": "POINT_AWARDED",
                }
            ]
        },
    ):
        payload = {**rally.model_dump(mode="json"), **changes}
        payload["event_hash"] = RallyEvent._content_hash(
            RallyEvent._hash_payload(payload)
        )
        with pytest.raises(ValidationError, match="rules resolution|Yes Let"):
            RallyEvent.model_validate(payload)


def test_rules_configuration_is_hash_protected():
    snapshot, _ = _simulate()
    payload = snapshot.model_dump(mode="json")
    payload["effective_rally_rules"]["interference_probability"] = 0.2
    with pytest.raises(ValidationError, match="hash mismatch"):
        MatchInputSnapshot.model_validate(payload)


def test_invalid_ground_truth_is_rejected():
    with pytest.raises(ValidationError, match="possible good return"):
        InterferenceRuleContext(
            **PLAYERS, winning_return=True, good_return_possible=False
        )
    with pytest.raises(ValidationError, match="unobstructed"):
        InterferenceRuleContext(**PLAYERS, swing_prevented=True)
    with pytest.raises(ValidationError, match="minimal interference"):
        InterferenceRuleContext(
            **PLAYERS, minimal_interference=True, reasonable_swing=False
        )
    with pytest.raises(ValidationError, match="attempted shot"):
        BallHitPlayerRuleContext(
            **PLAYERS,
            hit_player="NON_STRIKER",
            ball_phase="TO_FRONT_WALL",
            attempt="NONE",
        )


@pytest.mark.smoke
def test_actual_v8_match_fixture_remains_readable_without_rehashing(monkeypatch):
    fixture = json.loads(
        (
            Path(__file__).parents[1] / "fixtures/matches/legacy_engine_v8.json"
        ).read_text()
    )
    monkeypatch.setattr(
        MatchEngine,
        "simulate",
        lambda *args, **kwargs: pytest.fail("historical read must not simulate"),
    )
    snapshot = MatchInputSnapshot.model_validate(fixture["input"])
    result = MatchResult.model_validate(fixture["result"])
    assert snapshot.schema_version == "match_input_snapshot.v8"
    assert snapshot.effective_rally_rules is None
    assert snapshot.snapshot_hash == fixture["input"]["snapshot_hash"]
    assert result.rally_log.schema_version == "match_rally_log.v5"
    assert (
        result.rally_log.match_log_hash
        == fixture["result"]["rally_log"]["match_log_hash"]
    )
    assert (
        result.timeline_log.match_log_hash
        == fixture["result"]["timeline_log"]["match_log_hash"]
    )
    assert (
        result.stamina_log.match_log_hash
        == fixture["result"]["stamina_log"]["match_log_hash"]
    )
    assert (
        result.rally_log.events[0]
        .gameplan_context.player_decisions[0]
        .observed_neutral_replays
        == 0
    )
    assert MatchResult.model_validate_json(result.model_dump_json()) == result


def test_legacy_v8_snapshot_cannot_smuggle_unprotected_rules():
    fixture = json.loads(
        (
            Path(__file__).parents[1] / "fixtures/matches/legacy_engine_v8.json"
        ).read_text()
    )
    fixture["input"]["effective_rally_rules"] = (
        EffectiveRallyRulesSnapshot().model_dump()
    )
    with pytest.raises(ValidationError, match="protected effective rally rules"):
        MatchInputSnapshot.model_validate(fixture["input"])


def test_rehashed_objective_delay_cannot_change_the_rally_reason():
    _, result = _simulate(external_interruption_probability=0.1)
    events = []
    previous_hash = result.timeline_log.input_snapshot_hash
    changed = False
    for event in result.timeline_log.events:
        values = event.model_dump(exclude={"event_hash", "event_hash_algorithm"})
        if event.event_type == "OBJECTIVE_DELAY" and not changed:
            values["reason"] = (
                "BROKEN_BALL" if event.reason != "BROKEN_BALL" else "COURT_CONDITION"
            )
            changed = True
        values["previous_event_hash"] = previous_hash
        replacement = type(event).create(**values)
        events.append(replacement)
        previous_hash = replacement.event_hash
    assert changed
    timeline = MatchTimelineLog.create(
        match_id=result.match_id,
        input_snapshot_hash=result.timeline_log.input_snapshot_hash,
        events=events,
        dynamic_stamina_recovery=True,
        rules_applied=True,
    )
    with pytest.raises(ValueError, match="rally facts"):
        result.rally_log.validate_rules_timeline(timeline)


def test_rehashed_tactical_evidence_cannot_treat_a_let_as_a_scored_rally():
    _, result = _simulate(interference_probability=0.25)
    payload = result.rally_log.model_dump(mode="json")
    changed = False
    previous_hash = payload["input_snapshot_hash"]
    for event in payload["events"]:
        if (
            not changed
            and event["gameplan_context"]["player_decisions"][0][
                "observed_neutral_replays"
            ]
        ):
            for decision in event["gameplan_context"]["player_decisions"]:
                decision["observed_rallies"] += 1
                decision["observed_neutral_replays"] += 1
            changed = True
        event["previous_event_hash"] = previous_hash
        event["event_hash"] = RallyEvent._content_hash(RallyEvent._hash_payload(event))
        previous_hash = event["event_hash"]
    payload["match_log_hash"] = previous_hash
    assert changed
    with pytest.raises(ValidationError, match="prior rally outcomes"):
        type(result.rally_log).model_validate(payload)

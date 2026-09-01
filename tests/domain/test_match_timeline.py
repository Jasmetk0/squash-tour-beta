from __future__ import annotations

from itertools import pairwise
from statistics import mean

import pytest
from pydantic import ValidationError

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import (
    EffectiveMatchTimingSnapshot,
    MatchContext,
    MatchEngine,
    MatchParticipantContext,
    MatchTimelineLog,
    MatchTimingOverride,
    PlayerRestartTimingProfile,
    RestartIntent,
    RetirementRule,
)
from beta_engine.domain.players import HiddenCareerTraits, Player


def _player(player_id: str, strength: int) -> Player:
    return Player(
        player_id=player_id,
        name=player_id,
        age=27,
        nationality="TST",
        technique=strength,
        movement=strength,
        physical=strength,
        mental=strength,
        consistency=strength,
        clutch=strength,
        recovery=strength,
        play_style="tempo-controller",
        archetype="all-court tactician",
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=90,
            growth_curve="balanced",
            professionalism=0.7,
            ambition=0.7,
            travel_tolerance=0.7,
            schedule_aggression=0.6,
            injury_proneness=0.2,
            resilience=0.8,
        ),
    )


def _context(*, retirement_rule: RetirementRule | None = None) -> MatchContext:
    return MatchContext(
        match_id="timed-match",
        player_a=MatchParticipantContext(player=_player("A", 84)),
        player_b=MatchParticipantContext(player=_player("B", 81)),
        retirement_rule=retirement_rule or RetirementRule(),
    )


def _result(*, timing: EffectiveMatchTimingSnapshot | None = None):
    return MatchEngine(rng=DeterministicRng(777)).simulate(
        _context(),
        log_anchor_hash="a" * 64,
        effective_match_timing=timing,
    )


def test_timeline_counts_each_elapsed_component_exactly_once() -> None:
    result = _result()
    assert result.rally_log is not None
    assert result.timeline_log is not None
    timeline = result.timeline_log

    assert timeline.rally_event_count == result.rally_log.total_rallies
    assert timeline.between_rally_interval_count == (
        result.rally_log.total_rallies - len(result.sets)
    )
    assert timeline.game_break_count == len(result.sets) - 1
    assert timeline.total_timeline_events == (
        timeline.rally_event_count
        + timeline.between_rally_interval_count
        + timeline.game_break_count
    )
    assert timeline.rally_elapsed_seconds == result.rally_log.rally_elapsed_seconds
    assert timeline.total_elapsed_seconds == round(
        timeline.rally_elapsed_seconds
        + timeline.between_rally_elapsed_seconds
        + timeline.game_break_elapsed_seconds,
        3,
    )
    assert timeline.match_log_hash == timeline.events[-1].event_hash
    assert timeline.events[0].previous_event_hash == "a" * 64


def test_gap_type_follows_score_transition_without_double_counting() -> None:
    result = _result()
    assert result.timeline_log is not None
    events = result.timeline_log.events

    rally_positions = [
        index for index, event in enumerate(events) if event.event_type == "RALLY"
    ]
    for left, right in pairwise(rally_positions):
        current = events[left]
        following = events[right]
        elapsed = events[left + 1 : right]
        assert len(elapsed) == 1
        expected = (
            "BETWEEN_RALLY_INTERVAL"
            if current.set_number == following.set_number
            else "GAME_BREAK"
        )
        assert elapsed[0].event_type == expected

    game_breaks = [event for event in events if event.event_type == "GAME_BREAK"]
    assert all(event.elapsed_seconds == 120 for event in game_breaks)


def test_between_rally_elapsed_time_is_shared_readiness_maximum() -> None:
    result = _result()
    assert result.timeline_log is not None
    intervals = [
        event
        for event in result.timeline_log.events
        if event.event_type == "BETWEEN_RALLY_INTERVAL"
    ]

    assert intervals
    for interval in intervals:
        readiness = {
            "SERVER": interval.server_ready_seconds,
            "RECEIVER": interval.receiver_ready_seconds,
            "OFFICIAL": interval.official_ready_seconds,
            "COURT": interval.court_ready_seconds,
        }
        assert interval.elapsed_seconds == round(max(readiness.values()), 3)
        assert readiness[interval.dominant_readiness.value] == max(readiness.values())
        assert interval.conduct_outcome == "NONE"
        assert "NATURAL_TENDENCY" in interval.server_decision_factors
        assert "NATURAL_TENDENCY" in interval.receiver_decision_factors


def test_pre_alpha_interval_calibration_stays_in_decided_working_corridor() -> None:
    elapsed: list[float] = []
    for seed in range(100, 140):
        result = MatchEngine(rng=DeterministicRng(seed)).simulate(_context())
        assert result.timeline_log is not None
        elapsed.extend(
            event.elapsed_seconds
            for event in result.timeline_log.events
            if event.event_type == "BETWEEN_RALLY_INTERVAL"
        )

    within_corridor = sum(8 <= value <= 18 for value in elapsed) / len(elapsed)
    assert 12.5 <= mean(elapsed) <= 13.5
    assert within_corridor >= 0.95


def test_timing_override_changes_only_timeline_not_sporting_result() -> None:
    default_result = _result()
    timing = EffectiveMatchTimingSnapshot.create(
        player_a_id="A",
        player_b_id="B",
        override=MatchTimingOverride(
            nominal_game_break_seconds=75,
            player_restart_profiles=(
                PlayerRestartTimingProfile(
                    player_id="A",
                    serve_tendency=RestartIntent.ACCELERATE,
                    return_tendency=RestartIntent.ACCELERATE,
                ),
                PlayerRestartTimingProfile(
                    player_id="B",
                    serve_tendency=RestartIntent.DELAY,
                    return_tendency=RestartIntent.DELAY,
                ),
            ),
        ),
    )
    overridden_result = _result(timing=timing)

    assert overridden_result.winner_player_id == default_result.winner_player_id
    assert overridden_result.sets == default_result.sets
    assert overridden_result.rally_log == default_result.rally_log
    assert overridden_result.timeline_log != default_result.timeline_log
    assert overridden_result.timeline_log is not None
    assert all(
        event.elapsed_seconds == 75
        for event in overridden_result.timeline_log.events
        if event.event_type == "GAME_BREAK"
    )


def test_timeline_rejects_elapsed_or_chain_tampering() -> None:
    result = _result()
    assert result.timeline_log is not None
    payload = result.timeline_log.model_dump(mode="json")
    interval = next(
        event
        for event in payload["events"]
        if event["event_type"] == "BETWEEN_RALLY_INTERVAL"
    )
    interval["server_ready_seconds"] += 1

    with pytest.raises(ValidationError, match="maximum readiness|hash mismatch"):
        MatchTimelineLog.model_validate(payload)

    payload = result.timeline_log.model_dump(mode="json")
    payload["events"] = payload["events"][1:]
    payload["total_timeline_events"] -= 1
    with pytest.raises(ValidationError, match="identity or event order|hash chain"):
        MatchTimelineLog.model_validate(payload)


def test_set_start_retirement_preserves_elapsed_game_break() -> None:
    context = _context(
        retirement_rule=RetirementRule(
            enabled=True,
            retired_player_id="B",
            set_number=2,
        )
    )
    result = MatchEngine(rng=DeterministicRng(777)).simulate(
        context, log_anchor_hash="a" * 64
    )

    assert len(result.sets) == 1
    assert result.timeline_log is not None
    assert result.timeline_log.events[-1].event_type == "GAME_BREAK"
    assert result.timeline_log.game_break_count == 1
    assert result.timeline_log.game_break_elapsed_seconds == 120


def test_timing_snapshot_rejects_unrelated_player_and_tampering() -> None:
    with pytest.raises(ValueError, match="must reference a match participant"):
        EffectiveMatchTimingSnapshot.create(
            player_a_id="A",
            player_b_id="B",
            override=MatchTimingOverride(
                player_restart_profiles=(PlayerRestartTimingProfile(player_id="C"),)
            ),
        )

    payload = EffectiveMatchTimingSnapshot.create(
        player_a_id="A", player_b_id="B"
    ).model_dump(mode="json")
    payload["nominal_game_break_seconds"] = 90
    with pytest.raises(ValidationError, match="snapshot hash mismatch"):
        EffectiveMatchTimingSnapshot.model_validate(payload)

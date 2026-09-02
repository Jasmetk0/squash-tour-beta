from __future__ import annotations

import pytest
from pydantic import ValidationError

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import (
    MatchContext,
    MatchEngine,
    MatchParticipantContext,
    MatchRallyLog,
    MatchResult,
    RallyEvent,
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


def _result():
    context = MatchContext(
        match_id="logged-match",
        player_a=MatchParticipantContext(player=_player("A", 84)),
        player_b=MatchParticipantContext(player=_player("B", 81)),
    )
    return MatchEngine(rng=DeterministicRng(777)).simulate(
        context, log_anchor_hash="a" * 64
    )


def test_every_simulated_point_is_an_ordered_authoritative_rally_event() -> None:
    result = _result()
    assert result.rally_log is not None
    log = result.rally_log

    assert log.total_rallies == sum(
        set_result.winner_games + set_result.loser_games for set_result in result.sets
    )
    assert log.match_log_hash == log.events[-1].event_hash
    assert log.events[0].previous_event_hash == "a" * 64
    assert log.events[-1].post_rally_state.match_complete is True
    assert all(
        event.post_rally_state.next_server_player_id == event.winner_player_id
        for event in log.events
    )
    assert log.rally_elapsed_seconds > 0
    assert log.estimated_shot_count >= log.total_rallies
    assert log.schema_version == "match_rally_log.v2"
    assert "between_rally_intervals" not in log.unsupported_timeline_components
    assert "game_breaks" not in log.unsupported_timeline_components


def test_reloading_stored_log_does_not_run_rng_and_preserves_truth() -> None:
    result = _result()
    assert result.rally_log is not None

    restored = MatchRallyLog.model_validate(result.rally_log.model_dump(mode="json"))

    assert restored == result.rally_log


def test_v1_rally_event_remains_hash_compatible_without_stamina_context() -> None:
    result = _result()
    assert result.rally_log is not None
    payload = result.rally_log.events[0].model_dump(mode="json")
    payload["schema_version"] = "rally_event.v1"
    payload.pop("stamina_outcome_context")
    payload["event_hash"] = RallyEvent._content_hash(
        RallyEvent._hash_payload(payload)
    )

    restored = RallyEvent.model_validate(payload)

    assert restored.schema_version == "rally_event.v1"
    assert restored.stamina_outcome_context is None


def test_v1_rally_log_remains_readable() -> None:
    result = _result()
    assert result.rally_log is not None
    payload = result.rally_log.model_dump(mode="json")
    payload["schema_version"] = "match_rally_log.v1"
    payload["unsupported_timeline_components"] = [
        "between_rally_intervals",
        "game_breaks",
        *payload["unsupported_timeline_components"],
    ]

    restored = MatchRallyLog.model_validate(payload)

    assert restored.schema_version == "match_rally_log.v1"


def test_rally_event_rejects_score_tampering() -> None:
    result = _result()
    assert result.rally_log is not None
    payload = result.rally_log.events[0].model_dump(mode="json")
    payload["score_after"]["points_a"] += 1

    with pytest.raises(ValidationError, match="point mutation|hash mismatch"):
        RallyEvent.model_validate(payload)


def test_v2_rally_event_rejects_missing_stamina_outcome_context() -> None:
    result = _result()
    assert result.rally_log is not None
    payload = result.rally_log.events[0].model_dump(mode="json")
    payload["stamina_outcome_context"] = None

    with pytest.raises(ValidationError, match="requires stamina outcome context"):
        RallyEvent.model_validate(payload)


def test_rally_log_rejects_removed_or_reordered_event() -> None:
    result = _result()
    assert result.rally_log is not None
    payload = result.rally_log.model_dump(mode="json")
    payload["events"] = payload["events"][1:]
    payload["total_rallies"] -= 1

    with pytest.raises(ValidationError, match="identity or event order|hash chain"):
        MatchRallyLog.model_validate(payload)


def test_match_result_rejects_score_that_disagrees_with_rally_truth() -> None:
    payload = _result().model_dump(mode="json")
    payload["sets"][0]["winner_games"] += 1

    with pytest.raises(ValidationError, match="rally count|authoritative rally events"):
        MatchResult.model_validate(payload)

from __future__ import annotations

import pytest
from pydantic import ValidationError

from beta_engine.domain.matches import (
    MatchContext,
    MatchInputSnapshot,
    MatchParticipantContext,
    official_match_format_snapshot,
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


def _snapshot() -> MatchInputSnapshot:
    context = MatchContext(
        match_id="match-one",
        player_a=MatchParticipantContext(player=_player("A", 84)),
        player_b=MatchParticipantContext(player=_player("B", 81)),
    )
    return MatchInputSnapshot.create(
        context=context,
        effective_match_format=official_match_format_snapshot(),
        simulation_seed=777,
        match_engine_version="match_engine_v1",
    )


def test_match_input_snapshot_round_trips_exact_current_engine_inputs() -> None:
    snapshot = _snapshot()
    restored = MatchInputSnapshot.model_validate(snapshot.model_dump(mode="json"))

    assert restored == snapshot
    assert restored.context.player_a.player.player_id == "A"
    assert restored.context.player_b.player.player_id == "B"
    assert restored.unsupported_future_inputs == (
        "active_gameplans",
        "rally_model_configuration",
        "rally_seed_stream",
    )


def test_match_input_snapshot_rejects_player_or_seed_tampering() -> None:
    for field in ("player", "seed"):
        payload = _snapshot().model_dump(mode="json")
        if field == "player":
            payload["context"]["player_a"]["player"]["technique"] = 1
        else:
            payload["simulation_seed"] = 778

        with pytest.raises(ValidationError, match="snapshot hash mismatch"):
            MatchInputSnapshot.model_validate(payload)


def test_match_input_snapshot_rejects_format_context_mismatch() -> None:
    payload = _snapshot().model_dump(mode="json")
    payload["context"]["games_to"] = 9

    with pytest.raises(ValidationError, match="does not match effective format"):
        MatchInputSnapshot.model_validate(payload)

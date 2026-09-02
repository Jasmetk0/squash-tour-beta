from __future__ import annotations

import pytest
from pydantic import ValidationError

from beta_engine.domain.matches import (
    EffectiveMatchStaminaSnapshot,
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
        match_engine_version="match_engine_v6",
    )


def test_match_input_snapshot_round_trips_exact_current_engine_inputs() -> None:
    snapshot = _snapshot()
    restored = MatchInputSnapshot.model_validate(snapshot.model_dump(mode="json"))

    assert restored == snapshot
    assert restored.context.player_a.player.player_id == "A"
    assert restored.context.player_b.player.player_id == "B"
    assert restored.schema_version == "match_input_snapshot.v6"
    assert restored.unsupported_future_inputs == ("active_gameplans",)
    assert restored.effective_match_timing is not None
    assert restored.effective_match_stamina is not None
    assert restored.effective_match_stamina.calibration_version == "pre_alpha_physical_v3"
    assert restored.effective_match_stamina.outcome_effect_applied is True
    assert restored.effective_match_stamina.pre_rally_effort_applied is True
    assert restored.effective_match_timing.nominal_game_break_seconds == 120
    assert {
        profile.player_id
        for profile in restored.effective_match_timing.player_restart_profiles
    } == {"A", "B"}


def test_match_input_snapshot_rejects_player_seed_timing_or_stamina_tampering() -> None:
    for field in ("player", "seed", "timing", "stamina"):
        payload = _snapshot().model_dump(mode="json")
        if field == "player":
            payload["context"]["player_a"]["player"]["technique"] = 1
        elif field == "seed":
            payload["simulation_seed"] = 778
        elif field == "timing":
            payload["effective_match_timing"]["nominal_game_break_seconds"] = 90
        else:
            payload["effective_match_stamina"]["player_profiles"][0]["bars"][0][
                "capacity"
            ] -= 1

        with pytest.raises(ValidationError, match="snapshot hash mismatch"):
            MatchInputSnapshot.model_validate(payload)


def test_match_input_snapshot_rejects_format_context_mismatch() -> None:
    payload = _snapshot().model_dump(mode="json")
    payload["context"]["games_to"] = 9

    with pytest.raises(ValidationError, match="does not match effective format"):
        MatchInputSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    ("schema_version", "engine_version", "unsupported"),
    [
        (
            "match_input_snapshot.v1",
            "match_engine_v1",
            (
                "active_gameplans",
                "rally_model_configuration",
                "rally_seed_stream",
            ),
        ),
        (
            "match_input_snapshot.v2",
            "match_engine_v2",
            ("active_gameplans",),
        ),
    ],
)
def test_legacy_match_input_snapshots_remain_readable(
    schema_version: str,
    engine_version: str,
    unsupported: tuple[str, ...],
) -> None:
    current = _snapshot()
    hash_payload = MatchInputSnapshot._hash_payload(
        schema_version=schema_version,
        match_id=current.match_id,
        simulation_seed=current.simulation_seed,
        match_engine_version=engine_version,
        effective_match_format=current.effective_match_format,
        context=current.context,
        unsupported_future_inputs=unsupported,
    )
    payload = current.model_dump(mode="json")
    payload.pop("effective_match_timing")
    payload.pop("effective_match_stamina")
    payload.update(
        schema_version=schema_version,
        match_engine_version=engine_version,
        unsupported_future_inputs=unsupported,
        snapshot_hash=MatchInputSnapshot._content_hash(hash_payload),
    )
    restored = MatchInputSnapshot.model_validate(payload)

    assert restored.schema_version == schema_version
    assert restored.effective_match_timing is None
    assert restored.effective_match_stamina is None


def test_v3_timing_snapshot_remains_readable_without_stamina() -> None:
    current = _snapshot()
    hash_payload = MatchInputSnapshot._hash_payload(
        schema_version="match_input_snapshot.v3",
        match_id=current.match_id,
        simulation_seed=current.simulation_seed,
        match_engine_version="match_engine_v3",
        effective_match_format=current.effective_match_format,
        effective_match_timing=current.effective_match_timing,
        context=current.context,
        unsupported_future_inputs=("active_gameplans",),
    )
    payload = current.model_dump(mode="json")
    payload.pop("effective_match_stamina")
    payload.update(
        schema_version="match_input_snapshot.v3",
        match_engine_version="match_engine_v3",
        snapshot_hash=MatchInputSnapshot._content_hash(hash_payload),
    )

    restored = MatchInputSnapshot.model_validate(payload)

    assert restored.schema_version == "match_input_snapshot.v3"
    assert restored.effective_match_timing == current.effective_match_timing
    assert restored.effective_match_stamina is None


def test_v4_observational_stamina_snapshot_remains_readable() -> None:
    current = _snapshot()
    legacy_stamina = EffectiveMatchStaminaSnapshot.create(
        context=current.context, outcome_effect_applied=False
    )
    hash_payload = MatchInputSnapshot._hash_payload(
        schema_version="match_input_snapshot.v4",
        match_id=current.match_id,
        simulation_seed=current.simulation_seed,
        match_engine_version="match_engine_v4",
        effective_match_format=current.effective_match_format,
        effective_match_timing=current.effective_match_timing,
        effective_match_stamina=legacy_stamina,
        context=current.context,
        unsupported_future_inputs=("active_gameplans",),
    )
    payload = current.model_dump(mode="json")
    payload.update(
        schema_version="match_input_snapshot.v4",
        match_engine_version="match_engine_v4",
        effective_match_stamina=legacy_stamina.model_dump(mode="json"),
        snapshot_hash=MatchInputSnapshot._content_hash(hash_payload),
    )

    restored = MatchInputSnapshot.model_validate(payload)

    assert restored.schema_version == "match_input_snapshot.v4"
    assert restored.effective_match_stamina == legacy_stamina
    assert restored.effective_match_stamina.outcome_effect_applied is False


def test_v5_active_stamina_snapshot_remains_readable_without_effort() -> None:
    current = _snapshot()
    assert current.effective_match_stamina is not None
    legacy_stamina = EffectiveMatchStaminaSnapshot(
        schema_version="effective_match_stamina.v1",
        calibration_version="pre_alpha_physical_v2",
        player_profiles=current.effective_match_stamina.player_profiles,
        outcome_effect_applied=True,
        pre_rally_effort_applied=False,
        unsupported_components=(
            "within_rally_effort_changes",
            "within_rally_explosive_recovery",
            "carried_reserves_between_matches",
            "injury_specific_cost_profiles",
        ),
    )
    hash_payload = MatchInputSnapshot._hash_payload(
        schema_version="match_input_snapshot.v5",
        match_id=current.match_id,
        simulation_seed=current.simulation_seed,
        match_engine_version="match_engine_v5",
        effective_match_format=current.effective_match_format,
        effective_match_timing=current.effective_match_timing,
        effective_match_stamina=legacy_stamina,
        context=current.context,
        unsupported_future_inputs=("active_gameplans",),
    )
    payload = current.model_dump(mode="json")
    payload.update(
        schema_version="match_input_snapshot.v5",
        match_engine_version="match_engine_v5",
        effective_match_stamina=legacy_stamina.model_dump(mode="json"),
        snapshot_hash=MatchInputSnapshot._content_hash(hash_payload),
    )
    payload["effective_match_stamina"].pop("pre_rally_effort_applied")

    restored = MatchInputSnapshot.model_validate(payload)

    assert restored.schema_version == "match_input_snapshot.v5"
    assert restored.effective_match_stamina == legacy_stamina
    assert restored.effective_match_stamina.pre_rally_effort_applied is False

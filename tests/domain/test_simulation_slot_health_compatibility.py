from __future__ import annotations

import json

import pytest

from beta_engine.domain.matches import (
    MatchContext,
    MatchInputSnapshot,
    MatchParticipantContext,
    official_match_format_snapshot,
)
from beta_engine.domain.players import HiddenCareerTraits, Player
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import (
    AuthoritativeMatchInput,
    CanonicalPlayerMatchProjection,
    SimulationMatchEventPlan,
    SimulationSlotPlan,
    fingerprint,
)

pytestmark = pytest.mark.pr_critical


def test_historical_simulation_slot_plan_without_health_keeps_original_fingerprint() -> None:
    payload = {
        "schema_version": "simulation_slot_plan.v1",
        "run_id": "run",
        "branch_id": "branch",
        "week": {"season_index": 0, "week": 1},
        "slot_id": "slot-1",
        "ordinal": 1,
        "ordered_dependency_ids": [],
        "group_ids": ["g1"],
        "match_events": [
            SimulationMatchEventPlan(
                group_id="g1",
                event_id="event",
                match_id="match",
                direct_player_ids=("a", "b"),
            ).model_dump(mode="json")
        ],
        "slot_start_fingerprint": "a" * 64,
        "provenance": "historical slot",
    }
    historical = fingerprint(payload)

    restored = SimulationSlotPlan.model_validate_json(
        json.dumps(payload, sort_keys=True, separators=(",", ":"))
    )

    assert restored.health_state_fingerprint is None
    assert restored.fingerprint == historical

    current = restored.model_copy(update={"health_state_fingerprint": "b" * 64})
    assert current.fingerprint != historical

def _engine_player(player_id: str) -> Player:
    return Player(
        player_id=player_id,
        name=player_id,
        age=27,
        nationality="TST",
        technique=80,
        movement=80,
        physical=80,
        mental=80,
        consistency=80,
        clutch=80,
        recovery=80,
        play_style="tempo-controller",
        archetype="all-court",
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


def _projection(player: Player) -> CanonicalPlayerMatchProjection:
    return CanonicalPlayerMatchProjection(
        player_id=player.player_id,
        canonical_attributes=(("Forehand", 100),),
        current_form=100,
        match_sharpness=80,
        long_term_fatigue=0,
        source_sporting_fingerprint="sporting",
        projection_policy_id="policy",
        projection_policy_fingerprint="a" * 64,
        legacy_engine_values=(
            ("technique", 80),
            ("movement", 80),
            ("physical", 80),
            ("mental", 80),
            ("consistency", 80),
            ("clutch", 80),
            ("recovery", 80),
        ),
        form_modifier=0.0,
        sharpness_modifier=0.0,
        fatigue_modifier=0.0,
        profile_source_fingerprint="profile",
        profile_provenance="historical fixture",
        age=player.age,
        name=player.name,
        nationality=player.nationality,
        play_style=player.play_style,
        archetype=player.archetype,
        hidden_career_traits=player.hidden_career_traits,
    )


def test_historical_authoritative_match_input_without_health_keeps_original_fingerprint() -> None:
    player_a = _engine_player("A")
    player_b = _engine_player("B")
    context = MatchContext(
        match_id="match",
        player_a=MatchParticipantContext(player=player_a),
        player_b=MatchParticipantContext(player=player_b),
    )
    current = MatchInputSnapshot.create(
        context=context,
        effective_match_format=official_match_format_snapshot(),
        simulation_seed=7,
        match_engine_version="match_engine_v11",
    )
    legacy_hash_payload = MatchInputSnapshot._hash_payload(
        schema_version="match_input_snapshot.v10",
        match_id=current.match_id,
        simulation_seed=current.simulation_seed,
        match_engine_version="match_engine_v10",
        effective_match_format=current.effective_match_format,
        effective_match_timing=current.effective_match_timing,
        effective_match_stamina=current.effective_match_stamina,
        rally_calibration_profile=current.rally_calibration_profile,
        effective_match_gameplans=current.effective_match_gameplans,
        effective_rally_rules=current.effective_rally_rules,
        context=current.context,
        unsupported_future_inputs=(),
    )
    legacy_payload = current.model_dump(mode="json")
    legacy_payload.pop("effective_match_health")
    legacy_payload.update(
        schema_version="match_input_snapshot.v10",
        match_engine_version="match_engine_v10",
        snapshot_hash=MatchInputSnapshot._content_hash(legacy_hash_payload),
    )
    legacy_engine = MatchInputSnapshot.model_validate(legacy_payload)
    authoritative = AuthoritativeMatchInput(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=1),
        slot_id="slot",
        slot_start_fingerprint="b" * 64,
        group_id="g1",
        event_id="event",
        match_id="match",
        player_projections=(_projection(player_a), _projection(player_b)),
        engine_input=legacy_engine,
    )
    historical_payload = authoritative.model_dump(mode="json")
    historical_payload["engine_input"].pop("effective_match_health", None)

    assert legacy_engine.effective_match_health is None
    assert authoritative.fingerprint == fingerprint(historical_payload)


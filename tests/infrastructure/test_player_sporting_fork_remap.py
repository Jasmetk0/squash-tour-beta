from __future__ import annotations

import pytest

from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    PlayerSportingWeekState,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.player_sporting_state import (
    PLAYER_SPORTING_COMPONENT_KEY,
    _component,
    load_saved_sporting_bundle,
    remap_saved_sporting_component,
)

pytestmark = pytest.mark.pr_critical


def _source_payload(*, schema_version="completed_week_sporting_context.v1"):
    week1 = RankingWeek(season_index=0, week=1)
    week2 = RankingWeek(season_index=0, week=2)
    first = PlayerSportingWeekState(
        run_id="run",
        branch_id="source",
        week=week1,
        players=(),
        completed_context_fingerprint="bootstrap:not-a-completed-week",
        source_initial_world_fingerprint="shared-origin-world",
        stage_provenance="bootstrap",
    )
    context = CompletedWeekSportingContext(
        schema_version=schema_version,
        run_id="run",
        branch_id="source",
        completed_week=week1,
        competitive_match_counts=(),
        source_fingerprints=("source-tournament-fingerprint",),
        **(
            {
                "terminal_sporting_fingerprint": "a" * 64,
                "match_effect_fingerprints": ("b" * 64,),
            }
            if schema_version == "completed_week_sporting_context.v2"
            else {}
        ),
        provenance="owned tournament evidence",
    )
    second = PlayerSportingWeekState(
        run_id="run",
        branch_id="source",
        week=week2,
        players=(),
        completed_context_fingerprint=context.fingerprint,
        source_initial_world_fingerprint="shared-origin-world",
        predecessor_fingerprint=first.fingerprint,
        stage_provenance="weekly transition",
    )
    return {
        "content": {
            PLAYER_SPORTING_COMPONENT_KEY: _component(
                (first, second),
                (context,),
            )
        }
    }, (first, second), context


def test_v1_sporting_history_rebinds_context_and_snapshot_chain():
    payload, source_states, source_context = _source_payload()

    component = remap_saved_sporting_component(
        payload,
        run_id="run",
        source_branch_id="source",
        target_branch_id="target",
        source_fingerprint_map={
            "source-tournament-fingerprint": "target-tournament-fingerprint"
        },
    )

    assert component is not None
    target_payload = {"content": {PLAYER_SPORTING_COMPONENT_KEY: component}}
    bundle = load_saved_sporting_bundle(
        target_payload,
        run_id="run",
        branch_id="target",
    )
    assert bundle is not None
    target_states, target_contexts = bundle
    target_context = target_contexts[0]

    assert target_context.branch_id == "target"
    assert target_context.source_fingerprints == ("target-tournament-fingerprint",)
    assert target_context.fingerprint != source_context.fingerprint
    assert [state.branch_id for state in target_states] == ["target", "target"]
    assert target_states[0].predecessor_fingerprint is None
    assert target_states[1].predecessor_fingerprint == target_states[0].fingerprint
    assert target_states[1].completed_context_fingerprint == target_context.fingerprint
    assert target_states[0].fingerprint != source_states[0].fingerprint
    assert target_states[1].fingerprint != source_states[1].fingerprint


def test_v1_sporting_history_missing_evidence_mapping_fails_closed():
    payload, _, _ = _source_payload()

    with pytest.raises(ValueError, match="without a target fork mapping"):
        remap_saved_sporting_component(
            payload,
            run_id="run",
            source_branch_id="source",
            target_branch_id="target",
            source_fingerprint_map={},
        )


def test_v2_match_effect_sporting_history_rebinds_all_external_evidence():
    payload, source_states, source_context = _source_payload(
        schema_version="completed_week_sporting_context.v2"
    )

    component = remap_saved_sporting_component(
        payload,
        run_id="run",
        source_branch_id="source",
        target_branch_id="target",
        source_fingerprint_map={
            "source-tournament-fingerprint": "target-slot-result-fingerprint"
        },
        terminal_sporting_fingerprint_map={
            "a" * 64: "c" * 64,
        },
        match_effect_fingerprint_map={
            "b" * 64: "d" * 64,
        },
    )

    assert component is not None
    target_payload = {"content": {PLAYER_SPORTING_COMPONENT_KEY: component}}
    bundle = load_saved_sporting_bundle(
        target_payload,
        run_id="run",
        branch_id="target",
    )
    assert bundle is not None
    target_states, target_contexts = bundle
    target_context = target_contexts[0]
    assert target_context.schema_version == "completed_week_sporting_context.v2"
    assert target_context.source_fingerprints == ("target-slot-result-fingerprint",)
    assert target_context.terminal_sporting_fingerprint == "c" * 64
    assert target_context.match_effect_fingerprints == ("d" * 64,)
    assert target_context.fingerprint != source_context.fingerprint
    assert target_states[1].completed_context_fingerprint == target_context.fingerprint
    assert target_states[1].predecessor_fingerprint == target_states[0].fingerprint
    assert target_states[0].fingerprint != source_states[0].fingerprint
    assert target_states[1].fingerprint != source_states[1].fingerprint


def test_v2_match_effect_sporting_history_missing_slot_mapping_fails_closed():
    payload, _, _ = _source_payload(
        schema_version="completed_week_sporting_context.v2"
    )

    with pytest.raises(ValueError, match="Simulation Slot evidence without a target fork mapping"):
        remap_saved_sporting_component(
            payload,
            run_id="run",
            source_branch_id="source",
            target_branch_id="target",
            source_fingerprint_map={
                "source-tournament-fingerprint": "target-slot-result-fingerprint"
            },
        )

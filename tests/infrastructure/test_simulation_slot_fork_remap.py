from __future__ import annotations

import pytest

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import (
    PlayerMatchSportingEffect,
    PlayerSportingCheckpoint,
)
from beta_engine.infrastructure.db.simulation_slot_fork_remap import (
    SimulationSlotForkRemapUnsupportedError,
    remap_match_effect,
    remap_sporting_checkpoint,
)

pytestmark = pytest.mark.pr_critical


def test_match_effect_rebinds_all_branch_owned_evidence():
    source = PlayerMatchSportingEffect(
        run_id="run",
        branch_id="source",
        week=RankingWeek(season_index=0, week=1),
        slot_id="slot-1",
        group_id="group-1",
        match_id="match-1",
        player_id="p1",
        pre_match_sporting_fingerprint="sporting-source",
        match_input_fingerprint="input-source",
        authoritative_result_fingerprint="result-source",
        form_before=100,
        form_delta=2,
        form_after=102,
        sharpness_before=50,
        sharpness_delta=3,
        sharpness_after=53,
        fatigue_before=10,
        fatigue_delta=4,
        fatigue_after=14,
        policy_id="policy",
        policy_fingerprint="policy-fp",
        provenance="frozen evidence",
    )

    target = remap_match_effect(
        source,
        run_id="run",
        source_branch_id="source",
        target_branch_id="target",
        pre_match_sporting_fingerprint_map={"sporting-source": "sporting-target"},
        match_input_fingerprint_map={"input-source": "input-target"},
        authoritative_result_fingerprint_map={"result-source": "result-target"},
    )

    assert target.branch_id == "target"
    assert target.pre_match_sporting_fingerprint == "sporting-target"
    assert target.match_input_fingerprint == "input-target"
    assert target.authoritative_result_fingerprint == "result-target"
    assert target.fingerprint != source.fingerprint
    assert target.player_id == source.player_id
    assert target.form_after == source.form_after


def test_checkpoint_rebinds_week_slot_predecessor_and_effect_identity():
    source = PlayerSportingCheckpoint(
        run_id="run",
        branch_id="source",
        week=RankingWeek(season_index=0, week=1),
        slot_id="slot-2",
        slot_ordinal=2,
        opening_week_fingerprint="week-source",
        slot_start_fingerprint="start-source",
        predecessor_checkpoint_fingerprint="previous-source",
        applied_effect_fingerprints=("effect-a", "effect-b"),
        players=(),
    )

    target = remap_sporting_checkpoint(
        source,
        run_id="run",
        source_branch_id="source",
        target_branch_id="target",
        opening_week_fingerprint_map={"week-source": "week-target"},
        slot_start_fingerprint_map={"start-source": "start-target"},
        predecessor_checkpoint_fingerprint_map={
            "previous-source": "previous-target"
        },
        match_effect_fingerprint_map={
            "effect-a": "target-a",
            "effect-b": "target-b",
        },
    )

    assert target.branch_id == "target"
    assert target.opening_week_fingerprint == "week-target"
    assert target.slot_start_fingerprint == "start-target"
    assert target.predecessor_checkpoint_fingerprint == "previous-target"
    assert target.applied_effect_fingerprints == ("target-a", "target-b")
    assert target.fingerprint != source.fingerprint


def test_checkpoint_missing_dependency_mapping_fails_closed():
    source = PlayerSportingCheckpoint(
        run_id="run",
        branch_id="source",
        week=RankingWeek(season_index=0, week=1),
        slot_id="slot-1",
        slot_ordinal=1,
        opening_week_fingerprint="week-source",
        slot_start_fingerprint="start-source",
        predecessor_checkpoint_fingerprint=None,
        applied_effect_fingerprints=("effect-source",),
        players=(),
    )

    with pytest.raises(
        SimulationSlotForkRemapUnsupportedError,
        match="without a target fork mapping",
    ):
        remap_sporting_checkpoint(
            source,
            run_id="run",
            source_branch_id="source",
            target_branch_id="target",
            opening_week_fingerprint_map={"week-source": "week-target"},
            slot_start_fingerprint_map={"start-source": "start-target"},
            predecessor_checkpoint_fingerprint_map={},
            match_effect_fingerprint_map={},
        )

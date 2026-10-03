"""Saved Revision / Branch-fork coverage for canonical Health V1."""

from __future__ import annotations

import pytest

from beta_engine.domain.players.health import (
    PermanentHealthConsequence,
    PlayerHealthProfile,
    PlayerHealthRecord,
    bootstrap_health_state,
    carry_health_state_forward,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.player_health_state import (
    PLAYER_HEALTH_COMPONENT_KEY,
    _component,
    load_saved_health,
    remap_saved_health_component,
)

pytestmark = pytest.mark.pr_critical


def test_health_v1_supports_multiple_independent_records_recurrence_and_consequence():
    week1 = RankingWeek(season_index=0, week=1)
    week4 = RankingWeek(season_index=0, week=4)
    week8 = RankingWeek(season_index=0, week=8)

    first = PlayerHealthRecord(
        record_id="001-hamstring",
        kind="Injury",
        condition_key="hamstring_strain",
        lifecycle="Recovered",
        severity=32,
        affected_domains=("lower_body",),
        onset_week=week1,
        recovered_week=week4,
        recovery_window_min_weeks=2,
        recovery_window_max_weeks=5,
        provenance="explicit reviewed fixture",
    )
    recurrent = PlayerHealthRecord(
        record_id="002-hamstring-recurrence",
        kind="Injury",
        condition_key="hamstring_strain",
        lifecycle="Recovering",
        severity=44,
        affected_domains=("lower_body",),
        onset_week=week8,
        recurrence_of_record_id=first.record_id,
        recovery_window_min_weeks=3,
        recovery_window_max_weeks=7,
        provenance="explicit reviewed fixture",
    )
    illness = PlayerHealthRecord(
        record_id="003-illness",
        kind="Illness",
        condition_key="viral_illness",
        lifecycle="Active",
        severity=18,
        affected_domains=("systemic",),
        onset_week=week8,
        provenance="explicit reviewed fixture",
    )
    consequence = PermanentHealthConsequence(
        consequence_id="001-hamstring-residual",
        source_record_id=first.record_id,
        affected_domains=("lower_body",),
        limitation_severity=8,
        provenance="explicit reviewed fixture",
    )

    profile = PlayerHealthProfile(
        player_id="p1",
        records=(first, recurrent, illness),
        permanent_consequences=(consequence,),
    )

    assert tuple(record.record_id for record in profile.active_records) == (
        recurrent.record_id,
        illness.record_id,
    )


def test_health_v1_recurrence_and_permanent_consequence_fail_closed():
    active = PlayerHealthRecord(
        record_id="001-active",
        kind="Injury",
        condition_key="ankle",
        lifecycle="Active",
        severity=20,
        affected_domains=("lower_body",),
        onset_week=RankingWeek(season_index=0, week=1),
        provenance="fixture",
    )

    with pytest.raises(ValueError, match="unknown source record"):
        PlayerHealthProfile(
            player_id="p1",
            records=(
                active,
                PlayerHealthRecord(
                    record_id="002-recurrence",
                    kind="Injury",
                    condition_key="ankle",
                    lifecycle="Active",
                    severity=30,
                    affected_domains=("lower_body",),
                    onset_week=RankingWeek(season_index=0, week=2),
                    recurrence_of_record_id="missing",
                    provenance="fixture",
                ),
            ),
        )

    with pytest.raises(ValueError, match="requires a Recovered source"):
        PlayerHealthProfile(
            player_id="p1",
            records=(active,),
            permanent_consequences=(
                PermanentHealthConsequence(
                    consequence_id="001-residual",
                    source_record_id=active.record_id,
                    affected_domains=("lower_body",),
                    limitation_severity=5,
                    provenance="fixture",
                ),
            ),
        )


def test_health_v1_carry_forward_is_deterministic_and_adds_new_lifecycle_identity():
    first = bootstrap_health_state(
        run_id="run",
        branch_id="branch",
        source_initial_world_fingerprint="world",
        player_ids=("a",),
    )
    second = carry_health_state_forward(
        first,
        target=RankingWeek(season_index=0, week=2),
        target_player_ids=("a", "b"),
    )

    assert second.predecessor_fingerprint == first.fingerprint
    assert tuple(player.player_id for player in second.players) == ("a", "b")
    assert second.players[0] == first.players[0]
    assert second.players[1].records == ()
    assert second.players[1].permanent_consequences == ()


def test_saved_health_branch_remap_rechains_target_owned_fingerprints():
    first = bootstrap_health_state(
        run_id="run",
        branch_id="source",
        source_initial_world_fingerprint="world",
        player_ids=("a",),
    )
    second = carry_health_state_forward(
        first,
        target=RankingWeek(season_index=0, week=2),
        target_player_ids=("a",),
    )
    source_payload = {
        "content": {
            PLAYER_HEALTH_COMPONENT_KEY: _component((first, second)),
        }
    }

    component = remap_saved_health_component(
        source_payload,
        run_id="run",
        source_branch_id="source",
        target_branch_id="target",
    )

    assert component is not None
    target_payload = {"content": {PLAYER_HEALTH_COMPONENT_KEY: component}}
    remapped = load_saved_health(
        target_payload,
        run_id="run",
        branch_id="target",
    )
    assert remapped is not None
    assert tuple(state.branch_id for state in remapped) == ("target", "target")
    assert remapped[0].fingerprint != first.fingerprint
    assert remapped[1].predecessor_fingerprint == remapped[0].fingerprint
    assert remapped[1].fingerprint != second.fingerprint

"""Canonical Health V1 domain contract tests."""

import pytest
from pydantic import ValidationError

from beta_engine.domain.players.health import (
    PermanentHealthConsequence,
    PlayerHealthProfile,
    PlayerHealthRecord,
    bootstrap_health_state,
    carry_health_state_forward,
)
from beta_engine.domain.rankings.official import RankingWeek

pytestmark = pytest.mark.pr_critical


def test_health_supports_multiple_independent_records_recurrence_and_permanent_consequence():
    week1 = RankingWeek(season_index=0, week=1)
    week3 = RankingWeek(season_index=0, week=3)
    first = PlayerHealthRecord(
        record_id="r001",
        kind="Injury",
        condition_key="ankle-sprain",
        lifecycle="Recovered",
        severity=55,
        affected_domains=("movement",),
        onset_week=week1,
        recovered_week=week3,
        recovery_window_min_weeks=1,
        recovery_window_max_weeks=4,
        provenance="explicit historical health fact",
    )
    recurrent = PlayerHealthRecord(
        record_id="r002",
        kind="Injury",
        condition_key="ankle-sprain",
        lifecycle="Active",
        severity=35,
        affected_domains=("movement",),
        onset_week=RankingWeek(season_index=0, week=8),
        recurrence_of_record_id="r001",
        provenance="explicit recurrent health fact",
    )
    illness = PlayerHealthRecord(
        record_id="r003",
        kind="Illness",
        condition_key="viral-illness",
        lifecycle="Recovering",
        severity=20,
        affected_domains=("endurance", "recovery"),
        onset_week=RankingWeek(season_index=0, week=9),
        provenance="independent illness history",
    )
    consequence = PermanentHealthConsequence(
        consequence_id="c001",
        source_record_id="r001",
        affected_domains=("movement",),
        limitation_severity=12,
        provenance="persistent post-recovery limitation",
    )

    profile = PlayerHealthProfile(
        player_id="p1",
        records=(first, recurrent, illness),
        permanent_consequences=(consequence,),
    )

    assert [record.record_id for record in profile.active_records] == ["r002", "r003"]
    assert profile.permanent_consequences == (consequence,)


def test_health_prestart_history_is_explicit_and_never_fabricates_onset_week():
    prestart = PlayerHealthRecord(
        record_id="r001",
        kind="Injury",
        condition_key="old-knee-injury",
        lifecycle="Recovered",
        severity=70,
        affected_domains=("movement",),
        started_before_run=True,
        provenance="explicit pre-start input",
    )
    assert prestart.onset_week is None

    with pytest.raises(ValidationError, match="started_before_run"):
        PlayerHealthRecord(
            record_id="r002",
            kind="Injury",
            condition_key="unknown-onset",
            lifecycle="Active",
            severity=40,
            affected_domains=("movement",),
            provenance="invalid implicit pre-history",
        )


def test_permanent_consequence_requires_recovered_source_and_recurrence_kind_is_closed():
    active = PlayerHealthRecord(
        record_id="r001",
        kind="Injury",
        condition_key="shoulder",
        lifecycle="Active",
        severity=40,
        affected_domains=("power",),
        onset_week=RankingWeek(season_index=0, week=1),
        provenance="test",
    )
    with pytest.raises(ValidationError, match="Recovered source"):
        PlayerHealthProfile(
            player_id="p1",
            records=(active,),
            permanent_consequences=(
                PermanentHealthConsequence(
                    consequence_id="c001",
                    source_record_id="r001",
                    affected_domains=("power",),
                    limitation_severity=5,
                    provenance="invalid test consequence",
                ),
            ),
        )

    recovered = active.model_copy(
        update={
            "lifecycle": "Recovered",
            "recovered_week": RankingWeek(season_index=0, week=2),
        }
    )
    wrong_kind_recurrence = PlayerHealthRecord(
        record_id="r002",
        kind="Illness",
        condition_key="viral",
        lifecycle="Active",
        severity=10,
        affected_domains=("recovery",),
        onset_week=RankingWeek(season_index=0, week=3),
        recurrence_of_record_id="r001",
        provenance="invalid recurrence",
    )
    with pytest.raises(ValidationError, match="cannot cross Injury/Illness"):
        PlayerHealthProfile(
            player_id="p1",
            records=(recovered, wrong_kind_recurrence),
        )


def test_weekly_health_carry_forward_preserves_truth_and_adds_new_identity_empty():
    first = bootstrap_health_state(
        run_id="run",
        branch_id="branch",
        source_initial_world_fingerprint="world-fingerprint",
        player_ids=("a", "b"),
    )
    source_record = PlayerHealthRecord(
        record_id="r001",
        kind="Illness",
        condition_key="viral",
        lifecycle="Recovering",
        severity=15,
        affected_domains=("recovery",),
        onset_week=first.week,
        provenance="explicit current health",
    )
    first = first.model_copy(
        update={
            "players": (
                PlayerHealthProfile(player_id="a", records=(source_record,)),
                PlayerHealthProfile(player_id="b"),
            )
        }
    )

    second = carry_health_state_forward(
        first,
        target=RankingWeek(season_index=0, week=2),
        target_player_ids=("a", "b", "new-prospect"),
    )

    assert second.predecessor_fingerprint == first.fingerprint
    assert second.source_initial_world_fingerprint == first.source_initial_world_fingerprint
    assert second.players[0] == first.players[0]
    assert second.players[1] == first.players[1]
    assert second.players[2] == PlayerHealthProfile(player_id="new-prospect")
    assert "no-stochastic-health-check" in second.stage_provenance


def test_health_carry_forward_never_silently_drops_identity():
    first = bootstrap_health_state(
        run_id="run",
        branch_id="branch",
        source_initial_world_fingerprint="world-fingerprint",
        player_ids=("a", "b"),
    )
    with pytest.raises(ValueError, match="cannot silently drop"):
        carry_health_state_forward(
            first,
            target=RankingWeek(season_index=0, week=2),
            target_player_ids=("a",),
        )

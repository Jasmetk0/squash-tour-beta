from __future__ import annotations

import pytest

from beta_engine.domain.matches.health import (
    EffectiveMatchHealthSnapshot,
    project_player_health,
)
from beta_engine.domain.players.health import (
    PermanentHealthConsequence,
    PlayerHealthProfile,
    PlayerHealthRecord,
)
from beta_engine.domain.rankings.official import RankingWeek


@pytest.mark.pr_critical
def test_match_health_projection_keeps_current_and_permanent_facts_without_numeric_effect() -> None:
    week = RankingWeek(season_index=0, week=5)
    profile = PlayerHealthProfile(
        player_id="P1",
        records=(
            PlayerHealthRecord(
                record_id="ankle-active",
                kind="Injury",
                condition_key="ankle",
                lifecycle="Active",
                severity=42,
                affected_domains=("movement", "stamina"),
                onset_week=week,
                recovery_window_min_weeks=2,
                recovery_window_max_weeks=6,
                provenance="test active ankle",
            ),
            PlayerHealthRecord(
                record_id="knee-old",
                kind="Injury",
                condition_key="knee",
                lifecycle="Recovered",
                severity=0,
                affected_domains=("movement",),
                onset_week=RankingWeek(season_index=0, week=1),
                recovered_week=RankingWeek(season_index=0, week=3),
                provenance="test recovered knee",
            ),
        ),
        permanent_consequences=(
            PermanentHealthConsequence(
                consequence_id="knee-limitation",
                source_record_id="knee-old",
                affected_domains=("movement",),
                limitation_severity=12,
                provenance="test permanent consequence",
            ),
        ),
    )

    projection = project_player_health(profile)

    assert tuple(item.record_id for item in projection.current_records) == (
        "ankle-active",
    )
    assert tuple(
        item.consequence_id for item in projection.permanent_consequences
    ) == ("knee-limitation",)
    assert projection.affected_domains == ("movement", "stamina")
    assert projection.highest_current_severity == 42
    assert projection.highest_permanent_limitation == 12
    assert projection.numeric_calibration_required is True
    assert projection.numeric_effect_applied is False
    assert len(projection.fingerprint) == 64


@pytest.mark.pr_critical
def test_effective_match_health_snapshot_preserves_participant_order_and_healthy_control() -> None:
    snapshot = EffectiveMatchHealthSnapshot.from_profiles(
        player_a=PlayerHealthProfile(
            player_id="A",
            records=(
                PlayerHealthRecord(
                    record_id="illness",
                    kind="Illness",
                    condition_key="viral",
                    lifecycle="Recovering",
                    severity=18,
                    affected_domains=("focus", "stamina"),
                    onset_week=RankingWeek(season_index=0, week=2),
                    recovery_window_min_weeks=1,
                    recovery_window_max_weeks=2,
                    provenance="test illness",
                ),
            ),
        ),
        player_b=PlayerHealthProfile(player_id="B"),
    )

    assert tuple(profile.player_id for profile in snapshot.player_profiles) == ("A", "B")
    assert snapshot.player_profiles[0].highest_current_severity == 18
    assert snapshot.player_profiles[1].highest_current_severity == 0
    assert snapshot.player_profiles[1].numeric_calibration_required is False
    assert snapshot.numeric_effect_applied is False
    assert "numeric_limitation_effects" in snapshot.unsupported_components
    assert len(snapshot.fingerprint) == 64

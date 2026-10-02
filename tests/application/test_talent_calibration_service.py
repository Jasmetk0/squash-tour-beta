from dataclasses import asdict

import pytest

from beta_engine.application.talent_calibration_service import BAND_ORDER, TalentCalibrationService
from beta_engine.domain.players.prospect_sporting_profile import (
    DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY,
    materialize_prospect_sporting_profile,
)
from beta_engine.domain.players.talent_quality_policy import talent_quality_band_from_seed


@pytest.mark.pr_critical
def test_calibration_is_deterministic_complete_and_in_policy_bounds() -> None:
    service = TalentCalibrationService()
    left = service.calibrate(seed=123, sample_count=250)
    right = service.calibrate(seed=123, sample_count=250)
    changed = service.calibrate(seed=124, sample_count=250)

    assert left == right
    assert left != changed
    assert len(left.bands) == len(BAND_ORDER) == 5
    assert sum(row.generated_count for row in left.bands) == left.sample_count
    assert sum(row.expected_count for row in left.bands) == pytest.approx(left.sample_count)
    assert sum(row.generated_share for row in left.bands) == pytest.approx(1)
    for row in left.bands:
        assert row.generated_share == pytest.approx(row.generated_count / left.sample_count)
        assert sum(row.development_timing_counts.values()) == row.generated_count
        assert sum(item.count for item in row.potential_histogram) == row.generated_count
        if row.generated_count:
            stats = row.potential_ovr
            assert DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY.potential_min <= stats.minimum <= stats.maximum <= DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY.potential_max
            assert stats.p10 <= stats.p25 <= stats.p50 <= stats.p75 <= stats.p90
            assert stats.minimum >= row.current_ovr.minimum
    assert left.potential_ovr.p10 <= left.potential_ovr.p25 <= left.potential_ovr.p50 <= left.potential_ovr.p75 <= left.potential_ovr.p90
    assert "seed_digest" not in str(asdict(left))


def test_calibration_matches_production_potential_seed_band_semantics() -> None:
    seed = 31
    sample_count = 40
    result = TalentCalibrationService().calibrate(seed=seed, sample_count=sample_count)

    expected_counts = {band.value: 0 for band in BAND_ORDER}
    for index in range(sample_count):
        identity = f"talent-calibration-lab.v1:{seed}:{index}"
        potential_seed = f"{identity}:potential"
        band = talent_quality_band_from_seed(potential_seed)
        expected_counts[band.value] += 1

        profile = materialize_prospect_sporting_profile(
            player_id=f"calibration://sample/{seed}/{index}",
            profile_seed=f"{identity}:profile",
            development_seed=f"{identity}:development",
            potential_seed=potential_seed,
        )
        assert profile.potential_ovr >= profile.ovr

    assert {row.band: row.generated_count for row in result.bands} == expected_counts


def test_small_sample_keeps_zero_count_bands() -> None:
    result = TalentCalibrationService().calibrate(seed=9, sample_count=1)
    assert len(result.bands) == 5
    assert any(row.generated_count == 0 and row.potential_ovr.minimum is None for row in result.bands)


def _candidate_ranges(minimum: int = 110, maximum: int = 190):
    return {band: (minimum, maximum) for band in BAND_ORDER}


@pytest.mark.pr_critical
def test_candidate_comparison_is_deterministic_aggregated_and_baseline_neutral() -> None:
    service = TalentCalibrationService()
    left = service.compare(seed=41, sample_count=500, candidate_ranges=_candidate_ranges())
    assert left == service.compare(seed=41, sample_count=500, candidate_ranges=_candidate_ranges())
    assert left != service.compare(seed=42, sample_count=500, candidate_ranges=_candidate_ranges())
    assert sum(row.generated_count for row in left.bands) == 500
    assert left.global_comparison.delta.unchanged == 500
    assert left.global_comparison.delta.increased == left.global_comparison.delta.decreased == 0
    assert left.global_comparison.baseline_potential_ovr == left.global_comparison.candidate_potential_ovr
    for row in left.bands:
        assert sum(item.count for item in row.baseline_histogram) == row.generated_count
        assert sum(item.count for item in row.candidate_histogram) == row.generated_count
        assert row.delta.increased + row.delta.unchanged + row.delta.decreased == row.generated_count
        if row.generated_count:
            assert row.delta.minimum <= row.delta.p10 <= row.delta.p50 <= row.delta.p90 <= row.delta.maximum
    for overlap in left.adjacent_overlaps:
        assert overlap.baseline == overlap.candidate
        assert overlap.baseline is None or 0 <= overlap.baseline <= 1


def test_candidate_changes_only_potential_range_and_preserves_policy_identity() -> None:
    policy = DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY
    candidate_policy = policy.model_copy(update={"potential_min": 170, "potential_max": 175})
    assert candidate_policy.policy_id == policy.policy_id
    unchanged = set(type(policy).model_fields) - {"potential_min", "potential_max"}
    for field in unchanged:
        assert getattr(candidate_policy, field) == getattr(policy, field)
    kwargs = dict(player_id="same-player", profile_seed="profile", development_seed="development", potential_seed="potential")
    baseline = materialize_prospect_sporting_profile(**kwargs, policy=policy)
    candidate = materialize_prospect_sporting_profile(**kwargs, policy=candidate_policy)
    assert baseline.attributes == candidate.attributes
    assert baseline.ovr == candidate.ovr
    assert baseline.development_timing == candidate.development_timing
    assert baseline.source_profile_seed_digest == candidate.source_profile_seed_digest
    assert baseline.source_development_seed_digest == candidate.source_development_seed_digest
    assert baseline.source_potential_seed_digest == candidate.source_potential_seed_digest
    assert candidate.potential_ovr != baseline.potential_ovr


def test_candidate_comparison_retains_empty_bands_and_null_overlap() -> None:
    result = TalentCalibrationService().compare(seed=9, sample_count=1, candidate_ranges=_candidate_ranges(100, 200))
    assert len(result.bands) == 5
    empty = [row for row in result.bands if row.generated_count == 0]
    assert empty and all(row.candidate_potential_ovr.minimum is None for row in empty)
    assert any(row.baseline is None and row.candidate is None for row in result.adjacent_overlaps)

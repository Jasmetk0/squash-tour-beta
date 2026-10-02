"""Read-only deterministic diagnostics for the current prospect authorities."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.domain.players.prospect_sporting_profile import (
    DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY,
    materialize_prospect_sporting_profile,
)
from beta_engine.domain.players.talent_models import TalentQualityBand
from beta_engine.domain.players.talent_quality_policy import (
    TALENT_QUALITY_POLICY_ID,
    normalized_talent_quality_weights,
    talent_quality_band_from_seed,
    talent_quality_policy_fingerprint,
)

CALIBRATION_NAMESPACE = "talent-calibration-lab.v1"
BAND_ORDER = (
    TalentQualityBand.SOLID,
    TalentQualityBand.STRONG,
    TalentQualityBand.ELITE,
    TalentQualityBand.SPECIAL,
    TalentQualityBand.GENERATIONAL,
)
TIMINGS = ("Early Bloomer", "Standard", "Late Bloomer")


@dataclass(frozen=True)
class DistributionStats:
    minimum: int | None
    maximum: int | None
    mean: float | None
    p10: float | None
    p25: float | None
    p50: float | None
    p75: float | None
    p90: float | None


@dataclass(frozen=True)
class HistogramBin:
    lower: int
    upper: int
    count: int


@dataclass(frozen=True)
class BandCalibration:
    band: str
    configured_rarity_weight: float
    generated_count: int
    generated_share: float
    expected_count: float
    generated_minus_expected: float
    current_ovr: DistributionStats
    potential_ovr: DistributionStats
    development_timing_counts: dict[str, int]
    potential_histogram: tuple[HistogramBin, ...]


@dataclass(frozen=True)
class TalentCalibrationResult:
    seed: int
    sample_count: int
    quality_policy_id: str
    quality_policy_fingerprint: str
    sporting_profile_policy_id: str
    sporting_profile_policy_fingerprint: str
    current_ovr: DistributionStats
    potential_ovr: DistributionStats
    bands: tuple[BandCalibration, ...]


class TalentCalibrationService:
    """Streams synthetic identities through production kernels without persistence."""

    def calibrate(self, *, seed: int, sample_count: int) -> TalentCalibrationResult:
        if not 1 <= sample_count <= 50_000:
            raise ValueError("sample_count must be between 1 and 50000")
        current = {band: [] for band in BAND_ORDER}
        potential = {band: [] for band in BAND_ORDER}
        timings = {band: {timing: 0 for timing in TIMINGS} for band in BAND_ORDER}

        for index in range(sample_count):
            identity = f"{CALIBRATION_NAMESPACE}:{seed}:{index}"
            potential_seed = f"{identity}:potential"
            band = talent_quality_band_from_seed(potential_seed)
            profile = materialize_prospect_sporting_profile(
                player_id=f"calibration://sample/{seed}/{index}",
                profile_seed=f"{identity}:profile",
                development_seed=f"{identity}:development",
                potential_seed=potential_seed,
            )
            current[band].append(profile.ovr)
            potential[band].append(profile.potential_ovr)
            timings[band][profile.development_timing] += 1

        weights = normalized_talent_quality_weights()
        bands = tuple(
            BandCalibration(
                band=band.value,
                configured_rarity_weight=weights[band],
                generated_count=len(current[band]),
                generated_share=len(current[band]) / sample_count,
                expected_count=sample_count * weights[band],
                generated_minus_expected=len(current[band]) - sample_count * weights[band],
                current_ovr=_stats(current[band]),
                potential_ovr=_stats(potential[band]),
                development_timing_counts=timings[band],
                potential_histogram=_histogram(potential[band]),
            )
            for band in BAND_ORDER
        )
        all_current = [value for band in BAND_ORDER for value in current[band]]
        all_potential = [value for band in BAND_ORDER for value in potential[band]]
        policy = DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY
        return TalentCalibrationResult(
            seed=seed,
            sample_count=sample_count,
            quality_policy_id=TALENT_QUALITY_POLICY_ID,
            quality_policy_fingerprint=talent_quality_policy_fingerprint(),
            sporting_profile_policy_id=policy.policy_id,
            sporting_profile_policy_fingerprint=policy.fingerprint,
            current_ovr=_stats(all_current),
            potential_ovr=_stats(all_potential),
            bands=bands,
        )


def _stats(values: list[int]) -> DistributionStats:
    if not values:
        return DistributionStats(None, None, None, None, None, None, None, None)
    ordered = sorted(values)
    return DistributionStats(
        min(ordered), max(ordered), sum(ordered) / len(ordered),
        *(_percentile(ordered, q) for q in (0.10, 0.25, 0.50, 0.75, 0.90)),
    )


def _percentile(ordered: list[int], quantile: float) -> float:
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    fraction = position - lower
    if fraction == 0:
        return float(ordered[lower])
    return ordered[lower] + (ordered[lower + 1] - ordered[lower]) * fraction


def _histogram(values: list[int]) -> tuple[HistogramBin, ...]:
    counts = [0] * 20
    for value in values:
        counts[min(value // 10, 19)] += 1
    return tuple(HistogramBin(index * 10, index * 10 + 9 if index < 19 else 200, count) for index, count in enumerate(counts))

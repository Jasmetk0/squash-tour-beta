"""Read-only deterministic diagnostics for the current prospect authorities."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from statistics import mean, pstdev

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
MAX_MULTI_SEED_SAMPLES = 250_000
MAX_MULTI_SEED_COUNT = 100


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
    baseline_potential_min: int
    baseline_potential_max: int
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
            baseline_potential_min=policy.potential_min,
            baseline_potential_max=policy.potential_max,
            current_ovr=_stats(all_current),
            potential_ovr=_stats(all_potential),
            bands=bands,
        )

    def compare(
        self,
        *,
        seed: int,
        sample_count: int,
        candidate_ranges: dict[TalentQualityBand, tuple[int, int]],
    ) -> "TalentCalibrationComparison":
        """Compare ephemeral per-band potential ranges against production truth."""
        if not 1 <= sample_count <= 50_000:
            raise ValueError("sample_count must be between 1 and 50000")
        if set(candidate_ranges) != set(BAND_ORDER):
            raise ValueError("candidate_ranges must contain every quality band")
        if any(
            type(minimum) is not int or type(maximum) is not int
            or not 0 <= minimum <= maximum <= 200
            for minimum, maximum in candidate_ranges.values()
        ):
            raise ValueError("candidate ranges must be integer, ordered, and within 0 through 200")
        baseline, candidate, deltas = self._comparison_values(
            seed=seed, sample_count=sample_count, candidate_ranges=candidate_ranges,
        )
        weights = normalized_talent_quality_weights()
        policy = DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY

        return _build_comparison(seed, sample_count, candidate_ranges, baseline, candidate, deltas)

    def _comparison_values(self, *, seed: int, sample_count: int,
                           candidate_ranges: dict[TalentQualityBand, tuple[int, int]]):
        baseline = {band: [] for band in BAND_ORDER}
        candidate = {band: [] for band in BAND_ORDER}
        deltas = {band: [] for band in BAND_ORDER}
        policy = DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY
        for index in range(sample_count):
            identity = f"{CALIBRATION_NAMESPACE}:{seed}:{index}"
            player_id = f"calibration://sample/{seed}/{index}"
            profile_seed = f"{identity}:profile"
            development_seed = f"{identity}:development"
            potential_seed = f"{identity}:potential"
            band = talent_quality_band_from_seed(potential_seed)
            base_profile = materialize_prospect_sporting_profile(
                player_id=player_id, profile_seed=profile_seed,
                development_seed=development_seed, potential_seed=potential_seed,
            )
            candidate_min, candidate_max = candidate_ranges[band]
            candidate_policy = policy.model_copy(update={
                "potential_min": candidate_min, "potential_max": candidate_max,
            })
            candidate_profile = materialize_prospect_sporting_profile(
                player_id=player_id, profile_seed=profile_seed,
                development_seed=development_seed, potential_seed=potential_seed,
                policy=candidate_policy,
            )
            invariant = (
                base_profile.attributes == candidate_profile.attributes
                and base_profile.ovr == candidate_profile.ovr
                and base_profile.development_timing == candidate_profile.development_timing
                and base_profile.source_profile_seed_digest == candidate_profile.source_profile_seed_digest
                and base_profile.source_development_seed_digest == candidate_profile.source_development_seed_digest
                and base_profile.source_potential_seed_digest == candidate_profile.source_potential_seed_digest
            )
            if not invariant:
                raise RuntimeError("candidate comparison changed non-potential prospect truth")
            baseline[band].append(base_profile.potential_ovr)
            candidate[band].append(candidate_profile.potential_ovr)
            deltas[band].append(candidate_profile.potential_ovr - base_profile.potential_ovr)
        return baseline, candidate, deltas

    def compare_multi_seed(self, *, seed_start: int, seed_count: int,
                           sample_count_per_seed: int,
                           candidate_ranges: dict[TalentQualityBand, tuple[int, int]]) -> "MultiSeedComparison":
        if seed_count < 1 or sample_count_per_seed < 1:
            raise ValueError("seed_count and sample_count_per_seed must be at least 1")
        if seed_count > MAX_MULTI_SEED_COUNT:
            raise ValueError(f"seed_count must not exceed {MAX_MULTI_SEED_COUNT}")
        total = seed_count * sample_count_per_seed
        if total > MAX_MULTI_SEED_SAMPLES:
            raise ValueError(f"total samples must not exceed {MAX_MULTI_SEED_SAMPLES}")
        if sample_count_per_seed > 50_000:
            raise ValueError("sample_count_per_seed must not exceed 50000")
        if set(candidate_ranges) != set(BAND_ORDER) or any(
            type(low) is not int or type(high) is not int or not 0 <= low <= high <= 200
            for low, high in candidate_ranges.values()
        ):
            raise ValueError("candidate_ranges must contain valid ranges for every quality band")
        pooled_b = {band: [] for band in BAND_ORDER}; pooled_c = {band: [] for band in BAND_ORDER}; pooled_d = {band: [] for band in BAND_ORDER}
        seed_rows = []; per_band = {band: {"medians": [], "means": [], "counts": []} for band in BAND_ORDER}
        overlap_values = {(a, b): {"baseline": [], "candidate": [], "missing": 0} for a, b in zip(BAND_ORDER, BAND_ORDER[1:])}
        seeds = tuple(range(seed_start, seed_start + seed_count))
        for seed in seeds:
            baseline, candidate, deltas = self._comparison_values(seed=seed, sample_count=sample_count_per_seed, candidate_ranges=candidate_ranges)
            comparison = _build_comparison(seed, sample_count_per_seed, candidate_ranges, baseline, candidate, deltas)
            for band in BAND_ORDER:
                pooled_b[band].extend(baseline[band]); pooled_c[band].extend(candidate[band]); pooled_d[band].extend(deltas[band])
                per_band[band]["counts"].append(len(candidate[band]))
                if candidate[band]:
                    per_band[band]["medians"].append(_stats(candidate[band]).p50)
                    per_band[band]["means"].append(_stats(candidate[band]).mean)
            overlap_map = {}
            for overlap in comparison.adjacent_overlaps:
                pair = (TalentQualityBand(overlap.lower_band), TalentQualityBand(overlap.upper_band))
                overlap_map[f"{overlap.lower_band}|{overlap.upper_band}"] = overlap.candidate
                if overlap.candidate is None:
                    overlap_values[pair]["missing"] += 1
                else:
                    overlap_values[pair]["candidate"].append(overlap.candidate)
                    overlap_values[pair]["baseline"].append(overlap.baseline)
            seed_rows.append(SeedComparison(seed, sample_count_per_seed,
                {band.value: len(candidate[band]) for band in BAND_ORDER},
                comparison.global_comparison.baseline_potential_ovr.p50,
                comparison.global_comparison.candidate_potential_ovr.p50,
                comparison.global_comparison.delta.p50, overlap_map))
        pooled = _build_comparison(seed_start, total, candidate_ranges, pooled_b, pooled_c, pooled_d)
        robustness = tuple(BandRobustness(band.value, len(pooled_c[band]),
            sum(count > 0 for count in per_band[band]["counts"]), sum(count == 0 for count in per_band[band]["counts"]),
            _variability(per_band[band]["medians"]), _variability(per_band[band]["means"]),
            _variability(per_band[band]["counts"])) for band in BAND_ORDER)
        overlaps = tuple(OverlapRobustness(a.value, b.value, _overlap(pooled_b[a], pooled_b[b]), _overlap(pooled_c[a], pooled_c[b]),
            _variability(overlap_values[(a,b)]["baseline"]), _variability(overlap_values[(a,b)]["candidate"]),
            overlap_values[(a,b)]["missing"]) for a,b in zip(BAND_ORDER, BAND_ORDER[1:]))
        return MultiSeedComparison(seed_start, seed_count, sample_count_per_seed, total, seeds,
            pooled.quality_policy_id, pooled.quality_policy_fingerprint, pooled.baseline_policy_id,
            pooled.baseline_policy_fingerprint, pooled.candidate_sandbox_configuration_fingerprint,
            pooled.global_comparison, pooled.bands, robustness, overlaps, tuple(seed_rows))


def _build_comparison(seed, sample_count, candidate_ranges, baseline, candidate, deltas):
        weights = normalized_talent_quality_weights()
        policy = DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY
        bands = tuple(
            BandComparison(
                band=band.value,
                generated_count=len(baseline[band]),
                expected_count=sample_count * weights[band],
                generated_share=len(baseline[band]) / sample_count,
                configured_rarity_weight=weights[band],
                candidate_range=PotentialRange(*candidate_ranges[band]),
                baseline_potential_ovr=_stats(baseline[band]),
                candidate_potential_ovr=_stats(candidate[band]),
                delta=_delta_stats(deltas[band]),
                baseline_histogram=_histogram(baseline[band]),
                candidate_histogram=_histogram(candidate[band]),
            ) for band in BAND_ORDER
        )
        all_baseline = [value for band in BAND_ORDER for value in baseline[band]]
        all_candidate = [value for band in BAND_ORDER for value in candidate[band]]
        all_deltas = [value for band in BAND_ORDER for value in deltas[band]]
        config_payload = {band.value: {
            "potential_min": candidate_ranges[band][0],
            "potential_max": candidate_ranges[band][1],
        } for band in BAND_ORDER}
        return TalentCalibrationComparison(
            seed=seed, sample_count=sample_count,
            baseline_policy_id=policy.policy_id,
            baseline_policy_fingerprint=policy.fingerprint,
            candidate_sandbox_configuration_fingerprint=_fingerprint(config_payload),
            quality_policy_id=TALENT_QUALITY_POLICY_ID,
            quality_policy_fingerprint=talent_quality_policy_fingerprint(),
            bands=bands,
            global_comparison=GlobalComparison(
                baseline_potential_ovr=_stats(all_baseline),
                candidate_potential_ovr=_stats(all_candidate),
                delta=_delta_stats(all_deltas),
            ),
            adjacent_overlaps=tuple(
                AdjacentOverlap(
                    lower_band=left.value, upper_band=right.value,
                    baseline=_overlap(baseline[left], baseline[right]),
                    candidate=_overlap(candidate[left], candidate[right]),
                ) for left, right in zip(BAND_ORDER, BAND_ORDER[1:])
            ),
        )


@dataclass(frozen=True)
class PotentialRange:
    potential_min: int
    potential_max: int


@dataclass(frozen=True)
class DeltaStats:
    minimum: int | None
    maximum: int | None
    mean: float | None
    p10: float | None
    p50: float | None
    p90: float | None
    increased: int
    unchanged: int
    decreased: int


@dataclass(frozen=True)
class BandComparison:
    band: str
    generated_count: int
    expected_count: float
    generated_share: float
    configured_rarity_weight: float
    candidate_range: PotentialRange
    baseline_potential_ovr: DistributionStats
    candidate_potential_ovr: DistributionStats
    delta: DeltaStats
    baseline_histogram: tuple[HistogramBin, ...]
    candidate_histogram: tuple[HistogramBin, ...]


@dataclass(frozen=True)
class GlobalComparison:
    baseline_potential_ovr: DistributionStats
    candidate_potential_ovr: DistributionStats
    delta: DeltaStats


@dataclass(frozen=True)
class AdjacentOverlap:
    lower_band: str
    upper_band: str
    baseline: float | None
    candidate: float | None


@dataclass(frozen=True)
class TalentCalibrationComparison:
    seed: int
    sample_count: int
    baseline_policy_id: str
    baseline_policy_fingerprint: str
    candidate_sandbox_configuration_fingerprint: str
    quality_policy_id: str
    quality_policy_fingerprint: str
    bands: tuple[BandComparison, ...]
    global_comparison: GlobalComparison
    adjacent_overlaps: tuple[AdjacentOverlap, ...]


@dataclass(frozen=True)
class VariabilityStats:
    minimum: float | None
    maximum: float | None
    mean: float | None
    standard_deviation: float | None


@dataclass(frozen=True)
class BandRobustness:
    band: str
    total_generated_samples: int
    seeds_with_samples: int
    seeds_without_samples: int
    candidate_median: VariabilityStats
    candidate_mean: VariabilityStats
    generated_count: VariabilityStats


@dataclass(frozen=True)
class OverlapRobustness:
    lower_band: str
    upper_band: str
    baseline_pooled: float | None
    candidate_pooled: float | None
    baseline_per_seed: VariabilityStats
    candidate_per_seed: VariabilityStats
    missing_seed_count: int


@dataclass(frozen=True)
class SeedComparison:
    seed: int
    total_samples: int
    generated_counts: dict[str, int]
    baseline_potential_median: float | None
    candidate_potential_median: float | None
    median_delta: float | None
    adjacent_candidate_overlaps: dict[str, float | None]


@dataclass(frozen=True)
class MultiSeedComparison:
    seed_start: int
    seed_count: int
    sample_count_per_seed: int
    total_sample_count: int
    seeds: tuple[int, ...]
    quality_policy_id: str
    quality_policy_fingerprint: str
    baseline_policy_id: str
    baseline_policy_fingerprint: str
    candidate_sandbox_configuration_fingerprint: str
    pooled_global_comparison: GlobalComparison
    pooled_bands: tuple[BandComparison, ...]
    band_robustness: tuple[BandRobustness, ...]
    overlap_robustness: tuple[OverlapRobustness, ...]
    per_seed: tuple[SeedComparison, ...]


def _stats(values: list[int]) -> DistributionStats:
    if not values:
        return DistributionStats(None, None, None, None, None, None, None, None)
    ordered = sorted(values)
    return DistributionStats(
        min(ordered), max(ordered), sum(ordered) / len(ordered),
        *(_percentile(ordered, q) for q in (0.10, 0.25, 0.50, 0.75, 0.90)),
    )


def _variability(values: list[float | int | None]) -> VariabilityStats:
    present = [float(value) for value in values if value is not None]
    if not present:
        return VariabilityStats(None, None, None, None)
    return VariabilityStats(min(present), max(present), mean(present), pstdev(present))


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


def _delta_stats(values: list[int]) -> DeltaStats:
    if not values:
        return DeltaStats(None, None, None, None, None, None, 0, 0, 0)
    ordered = sorted(values)
    return DeltaStats(
        minimum=ordered[0], maximum=ordered[-1], mean=sum(ordered) / len(ordered),
        p10=_percentile(ordered, .10), p50=_percentile(ordered, .50),
        p90=_percentile(ordered, .90),
        increased=sum(value > 0 for value in ordered),
        unchanged=sum(value == 0 for value in ordered),
        decreased=sum(value < 0 for value in ordered),
    )


def _overlap(left: list[int], right: list[int]) -> float | None:
    if not left or not right:
        return None
    left_counts = [item.count for item in _histogram(left)]
    right_counts = [item.count for item in _histogram(right)]
    return sum(min(a / len(left), b / len(right)) for a, b in zip(left_counts, right_counts))


def _fingerprint(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

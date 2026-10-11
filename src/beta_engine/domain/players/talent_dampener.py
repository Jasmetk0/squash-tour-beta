"""Country-scoped recent greatness dampening for top-end talent odds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from beta_engine.domain.players.talent_models import TalentQualityBand


@dataclass(frozen=True, slots=True)
class RecentGreatnessSignal:
    country_code: str
    season: int
    source: str
    quality_band: TalentQualityBand
    raw_weight: float
    reference_id: str | None = None


@dataclass(frozen=True, slots=True)
class DampenerContribution:
    source: str
    season: int
    quality_band: TalentQualityBand
    reference_id: str | None
    raw_weight: float
    decay_factor: float
    effective_weight: float


@dataclass(frozen=True, slots=True)
class CountryDampenerDiagnostics:
    country_code: str
    year: int
    recent_greatness_score: float
    signal_count: int
    multipliers: dict[TalentQualityBand, float]
    active: bool
    contributions: list[DampenerContribution]


class RecentGreatnessDampener(Protocol):
    """Interface for country-scoped top-end talent dampening."""

    def quality_multiplier(self, *, country_code: str, year: int, band: TalentQualityBand) -> float:
        """Return multiplicative weight for the provided quality band."""

    def diagnostics(self, *, country_code: str, year: int) -> CountryDampenerDiagnostics:
        """Return deterministic diagnostics for inspectable planner behavior."""


@dataclass(frozen=True, slots=True)
class NeutralRecentGreatnessDampener:
    """Default no-op dampener used in pure preview paths without history context."""

    def quality_multiplier(self, *, country_code: str, year: int, band: TalentQualityBand) -> float:
        _ = (country_code, year, band)
        return 1.0

    def diagnostics(self, *, country_code: str, year: int) -> CountryDampenerDiagnostics:
        multipliers = {
            TalentQualityBand.GENERATIONAL: 1.0,
            TalentQualityBand.SPECIAL: 1.0,
            TalentQualityBand.ELITE: 1.0,
            TalentQualityBand.STRONG: 1.0,
            TalentQualityBand.SOLID: 1.0,
        }
        return CountryDampenerDiagnostics(
            country_code=country_code,
            year=year,
            recent_greatness_score=0.0,
            signal_count=0,
            multipliers=multipliers,
            active=False,
            contributions=[],
        )


@dataclass(frozen=True, slots=True)
class WeightedRecentGreatnessDampener:
    """Deterministic recent-greatness dampener with simple linear time decay."""

    signals: tuple[RecentGreatnessSignal, ...]
    lookback_years: int = 8
    max_reduction_by_band: dict[TalentQualityBand, float] | None = None
    floor_by_band: dict[TalentQualityBand, float] | None = None

    def __post_init__(self) -> None:
        if self.lookback_years <= 0:
            raise ValueError("lookback_years must be positive")

    def quality_multiplier(self, *, country_code: str, year: int, band: TalentQualityBand) -> float:
        diagnostics = self.diagnostics(country_code=country_code, year=year)
        return diagnostics.multipliers.get(band, 1.0)

    def diagnostics(self, *, country_code: str, year: int) -> CountryDampenerDiagnostics:
        contributions: list[DampenerContribution] = []
        normalized_country = country_code.upper()
        for signal in self.signals:
            if signal.country_code != normalized_country:
                continue
            age = year - signal.season
            if age <= 0 or age > self.lookback_years:
                continue
            decay = max(0.0, 1.0 - (age / self.lookback_years))
            effective = signal.raw_weight * decay
            if effective <= 0:
                continue
            contributions.append(
                DampenerContribution(
                    source=signal.source,
                    season=signal.season,
                    quality_band=signal.quality_band,
                    reference_id=signal.reference_id,
                    raw_weight=round(signal.raw_weight, 6),
                    decay_factor=round(decay, 6),
                    effective_weight=round(effective, 6),
                )
            )

        score = round(sum(item.effective_weight for item in contributions), 6)
        multipliers = self._multipliers_for_score(score)
        return CountryDampenerDiagnostics(
            country_code=normalized_country,
            year=year,
            recent_greatness_score=score,
            signal_count=len(contributions),
            multipliers=multipliers,
            active=score > 0,
            contributions=sorted(
                contributions,
                key=lambda item: (item.effective_weight, item.season, item.source, item.reference_id or ""),
                reverse=True,
            ),
        )

    def _multipliers_for_score(self, score: float) -> dict[TalentQualityBand, float]:
        reduction_strength = {
            TalentQualityBand.GENERATIONAL: 0.34,
            TalentQualityBand.SPECIAL: 0.23,
            TalentQualityBand.ELITE: 0.08,
        }
        max_reduction_by_band = self.max_reduction_by_band or {
            TalentQualityBand.GENERATIONAL: 0.72,
            TalentQualityBand.SPECIAL: 0.58,
            TalentQualityBand.ELITE: 0.22,
        }
        floor_by_band = self.floor_by_band or {
            TalentQualityBand.GENERATIONAL: 0.28,
            TalentQualityBand.SPECIAL: 0.42,
            TalentQualityBand.ELITE: 0.78,
        }

        multipliers = {
            TalentQualityBand.GENERATIONAL: 1.0,
            TalentQualityBand.SPECIAL: 1.0,
            TalentQualityBand.ELITE: 1.0,
            TalentQualityBand.STRONG: 1.0,
            TalentQualityBand.SOLID: 1.0,
        }
        for band, strength in reduction_strength.items():
            reduction = min(max_reduction_by_band[band], score * strength)
            multipliers[band] = max(floor_by_band[band], round(1.0 - reduction, 6))
        return multipliers

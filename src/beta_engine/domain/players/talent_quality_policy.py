"""Shared provisional innate talent quality-band rarity policy.

This module is the single technical calibration authority for the pre-alpha
quality-band rarity distribution. It deliberately defines probabilities only;
it does not assign bands to persisted prospects or define potential-OVR ranges.
"""

from __future__ import annotations

from beta_engine.domain.players.talent_models import TalentQualityBand


PROVISIONAL_TALENT_QUALITY_WEIGHTS: dict[TalentQualityBand, float] = {
    TalentQualityBand.GENERATIONAL: 0.001,
    TalentQualityBand.SPECIAL: 0.016,
    TalentQualityBand.ELITE: 0.080,
    TalentQualityBand.STRONG: 0.270,
    TalentQualityBand.SOLID: 0.633,
}


def normalized_talent_quality_weights() -> dict[TalentQualityBand, float]:
    """Return normalized quality-band weights without exposing mutable shared state."""

    total = sum(PROVISIONAL_TALENT_QUALITY_WEIGHTS.values())
    if total <= 0.0:
        raise ValueError("Talent quality rarity weights must sum to a positive value")
    return {
        band: weight / total
        for band, weight in PROVISIONAL_TALENT_QUALITY_WEIGHTS.items()
    }

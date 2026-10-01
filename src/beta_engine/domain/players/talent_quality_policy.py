"""Shared provisional innate talent quality-band rarity policy.

This module is the single technical calibration authority for the pre-alpha
quality-band rarity distribution. It defines probabilities and deterministic
band selection only; it does not define potential-OVR ranges.
"""

from __future__ import annotations

import hashlib
import json

from beta_engine.domain.players.talent_models import TalentQualityBand


PROVISIONAL_TALENT_QUALITY_WEIGHTS: dict[TalentQualityBand, float] = {
    TalentQualityBand.GENERATIONAL: 0.001,
    TalentQualityBand.SPECIAL: 0.016,
    TalentQualityBand.ELITE: 0.080,
    TalentQualityBand.STRONG: 0.270,
    TalentQualityBand.SOLID: 0.633,
}

TALENT_QUALITY_POLICY_ID = "talent-quality-rarity.provisional.v1"


def normalized_talent_quality_weights() -> dict[TalentQualityBand, float]:
    """Return normalized quality-band weights without exposing mutable shared state."""

    total = sum(PROVISIONAL_TALENT_QUALITY_WEIGHTS.values())
    if total <= 0.0:
        raise ValueError("Talent quality rarity weights must sum to a positive value")
    return {
        band: weight / total
        for band, weight in PROVISIONAL_TALENT_QUALITY_WEIGHTS.items()
    }


def talent_quality_policy_fingerprint() -> str:
    payload = {
        "policy_id": TALENT_QUALITY_POLICY_ID,
        "weights": {
            band.value: weight
            for band, weight in normalized_talent_quality_weights().items()
        },
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def talent_quality_band_from_seed(seed: str) -> TalentQualityBand:
    """Map one stable seed to a quality band using the shared rarity policy."""

    if not seed:
        raise ValueError("talent quality seed must be non-empty")
    digest = hashlib.sha256(
        f"{TALENT_QUALITY_POLICY_ID}|{seed}".encode("utf-8")
    ).digest()
    roll = int.from_bytes(digest[:8], "big") / float(1 << 64)
    cumulative = 0.0
    order = (
        TalentQualityBand.GENERATIONAL,
        TalentQualityBand.SPECIAL,
        TalentQualityBand.ELITE,
        TalentQualityBand.STRONG,
        TalentQualityBand.SOLID,
    )
    weights = normalized_talent_quality_weights()
    for band in order:
        cumulative += weights[band]
        if roll < cumulative:
            return band
    return TalentQualityBand.SOLID

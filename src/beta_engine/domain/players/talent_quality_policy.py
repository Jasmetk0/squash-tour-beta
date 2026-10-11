"""Shared provisional innate talent quality-band rarity policy.

This module is the single technical calibration authority for the pre-alpha
quality-band rarity distribution. It defines probabilities and deterministic
band selection only; it does not define potential-OVR ranges.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from beta_engine.domain.players.talent_models import TalentQualityBand


_V1_WEIGHTS: dict[TalentQualityBand, float] = {
    TalentQualityBand.GENERATIONAL: 0.001,
    TalentQualityBand.SPECIAL: 0.016,
    TalentQualityBand.ELITE: 0.080,
    TalentQualityBand.STRONG: 0.270,
    TalentQualityBand.SOLID: 0.633,
}

# Mutable defaults remain intentionally available to the calibration lab/tests. Persisted
# history must never resolve through this mapping; it uses an immutable snapshot instead.
PROVISIONAL_TALENT_QUALITY_WEIGHTS: dict[TalentQualityBand, float] = dict(_V1_WEIGHTS)

TALENT_QUALITY_POLICY_ID = "talent-quality-rarity.provisional.v1"
TALENT_QUALITY_POLICY_SCHEMA = "talent_quality_policy_snapshot.v1"
TALENT_QUALITY_SELECTION_VERSION = "sha256-policy-seed-u64.v1"


@dataclass(frozen=True)
class TalentQualityPolicySnapshot:
    schema_version: str
    policy_id: str
    selection_version: str
    normalized_weights: dict[str, float]
    fingerprint: str


def _normalized(weights: Mapping[TalentQualityBand, float]) -> dict[TalentQualityBand, float]:
    total = sum(weights.values())
    if total <= 0.0:
        raise ValueError("Talent quality rarity weights must sum to a positive value")
    return {band: weights[band] / total for band in TalentQualityBand}


def normalized_talent_quality_weights() -> dict[TalentQualityBand, float]:
    """Return current normalized defaults without exposing mutable shared state."""

    return _normalized(PROVISIONAL_TALENT_QUALITY_WEIGHTS)


def _snapshot(*, policy_id: str, weights: Mapping[TalentQualityBand, float]) -> TalentQualityPolicySnapshot:
    normalized = _normalized(weights)
    payload = {
        "schema_version": TALENT_QUALITY_POLICY_SCHEMA,
        "policy_id": policy_id,
        "selection_version": TALENT_QUALITY_SELECTION_VERSION,
        "normalized_weights": {band.value: normalized[band] for band in TalentQualityBand},
    }
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return TalentQualityPolicySnapshot(**payload, fingerprint=fingerprint)


def current_talent_quality_policy_snapshot() -> TalentQualityPolicySnapshot:
    return _snapshot(policy_id=TALENT_QUALITY_POLICY_ID, weights=PROVISIONAL_TALENT_QUALITY_WEIGHTS)


def legacy_v1_talent_quality_policy_snapshot() -> TalentQualityPolicySnapshot:
    """Known derivation for records created before policy provenance was persisted."""

    return _snapshot(policy_id=TALENT_QUALITY_POLICY_ID, weights=_V1_WEIGHTS)


def talent_quality_policy_fingerprint() -> str:
    return current_talent_quality_policy_snapshot().fingerprint


def talent_quality_band_from_seed_with_snapshot(
    seed: str,
    snapshot: TalentQualityPolicySnapshot,
) -> TalentQualityBand:
    if not seed:
        raise ValueError("talent quality seed must be non-empty")
    if snapshot.schema_version != TALENT_QUALITY_POLICY_SCHEMA:
        raise ValueError("Unsupported talent quality policy snapshot schema")
    if snapshot.selection_version != TALENT_QUALITY_SELECTION_VERSION:
        raise ValueError("Unsupported talent quality deterministic selection version")
    expected = hashlib.sha256(
        json.dumps(
            {
                "schema_version": snapshot.schema_version,
                "policy_id": snapshot.policy_id,
                "selection_version": snapshot.selection_version,
                "normalized_weights": snapshot.normalized_weights,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if expected != snapshot.fingerprint:
        raise ValueError("Talent quality policy snapshot fingerprint mismatch")

    digest = hashlib.sha256(f"{snapshot.policy_id}|{seed}".encode("utf-8")).digest()
    roll = int.from_bytes(digest[:8], "big") / float(1 << 64)
    cumulative = 0.0
    for band in (
        TalentQualityBand.GENERATIONAL,
        TalentQualityBand.SPECIAL,
        TalentQualityBand.ELITE,
        TalentQualityBand.STRONG,
        TalentQualityBand.SOLID,
    ):
        try:
            weight = float(snapshot.normalized_weights[band.value])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Talent quality policy snapshot weights are incomplete") from exc
        cumulative += weight
        if roll < cumulative:
            return band
    return TalentQualityBand.SOLID


def talent_quality_band_from_seed(seed: str) -> TalentQualityBand:
    """Map one stable seed using the current policy (new-generation path only)."""

    return talent_quality_band_from_seed_with_snapshot(seed, current_talent_quality_policy_snapshot())


def talent_quality_result_evidence(seed: str, snapshot: TalentQualityPolicySnapshot) -> dict[str, object]:
    band = talent_quality_band_from_seed_with_snapshot(seed, snapshot)
    seed_digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    result_payload = {
        "schema_version": snapshot.schema_version,
        "policy_id": snapshot.policy_id,
        "selection_version": snapshot.selection_version,
        "normalized_weights": dict(snapshot.normalized_weights),
        "policy_fingerprint": snapshot.fingerprint,
        "source_seed_digest": seed_digest,
        "quality_band": band.value,
    }
    result_payload["result_fingerprint"] = hashlib.sha256(
        json.dumps(result_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return result_payload


def resolve_persisted_talent_quality(
    *,
    potential_seed: str,
    potential_json: Mapping[str, object],
    cohort_policy_version: str,
    profile_version: str,
) -> tuple[TalentQualityBand, TalentQualityPolicySnapshot, str]:
    raw = potential_json.get("talent_quality")
    if raw is None:
        # Compatibility is explicit and narrow: these versions are the known pre-provenance
        # v1 derivation. The legacy path never consults today's mutable defaults.
        if cohort_policy_version != "weekly_15yo_cohort_v1" or profile_version != "prospect_profile_v1":
            raise ValueError("Talent quality provenance is missing and cannot be resolved for this legacy record")
        snapshot = legacy_v1_talent_quality_policy_snapshot()
        band = talent_quality_band_from_seed_with_snapshot(potential_seed, snapshot)
        return band, snapshot, "legacy-derived-v1"
    if not isinstance(raw, Mapping):
        raise ValueError("Persisted talent quality provenance must be an object")
    try:
        snapshot = TalentQualityPolicySnapshot(
            schema_version=str(raw["schema_version"]),
            policy_id=str(raw["policy_id"]),
            selection_version=str(raw["selection_version"]),
            normalized_weights={str(k): float(v) for k, v in dict(raw["normalized_weights"]).items()},
            fingerprint=str(raw["policy_fingerprint"]),
        )
        band = talent_quality_band_from_seed_with_snapshot(potential_seed, snapshot)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Persisted talent quality provenance is invalid") from exc
    if raw.get("quality_band") != band.value:
        raise ValueError("Persisted talent quality result does not match its frozen policy/seed")
    evidence = talent_quality_result_evidence(potential_seed, snapshot)
    if raw.get("result_fingerprint") != evidence["result_fingerprint"]:
        raise ValueError("Persisted talent quality result fingerprint mismatch")
    return band, snapshot, "stored"

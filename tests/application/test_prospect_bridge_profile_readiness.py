from __future__ import annotations

import pytest

from beta_engine.application.prospect_bridge_inspection import (
    _canonical_sporting_profile_ready,
)
from beta_engine.domain.players.prospect_sporting_profile import (
    materialize_prospect_sporting_profile,
)


pytestmark = pytest.mark.pr_critical


def _payloads():
    canonical = materialize_prospect_sporting_profile(
        player_id="prospect-1",
        profile_seed="profile-seed",
        development_seed="development-seed",
        potential_seed="potential-seed",
    )
    fingerprint = canonical.fingerprint
    profile = {
        "canonical_sporting_profile": canonical.model_dump(mode="json"),
        "canonical_sporting_profile_fingerprint": fingerprint,
    }
    development = {
        "development_timing": canonical.development_timing,
        "source_development_seed_digest": canonical.source_development_seed_digest,
        "sporting_profile_fingerprint": fingerprint,
    }
    potential = {
        "potential_ovr": canonical.potential_ovr,
        "potential_identity": canonical.potential_identity,
        "potential_provenance": canonical.potential_provenance,
        "source_potential_seed_digest": canonical.source_potential_seed_digest,
        "sporting_profile_fingerprint": fingerprint,
    }
    return profile, development, potential


def test_profile_readiness_accepts_only_consistent_persisted_canonical_payload():
    profile, development, potential = _payloads()

    assert _canonical_sporting_profile_ready(
        profile=profile,
        development=development,
        potential=potential,
    )

    assert not _canonical_sporting_profile_ready(
        profile=profile,
        development=development | {"development_timing": "Late Bloomer"},
        potential=potential,
    )
    assert not _canonical_sporting_profile_ready(
        profile=profile | {"canonical_sporting_profile_fingerprint": "tampered"},
        development=development,
        potential=potential,
    )
    assert not _canonical_sporting_profile_ready(
        profile={},
        development={},
        potential={},
    )

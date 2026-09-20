from __future__ import annotations

from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.prospect_sporting_profile import (
    DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY,
    materialize_prospect_sporting_profile,
)


def _profile(**overrides):
    payload = {
        "player_id": "prospect-1",
        "profile_seed": "profile-secret",
        "development_seed": "development-secret",
        "potential_seed": "potential-secret",
    }
    payload.update(overrides)
    return materialize_prospect_sporting_profile(**payload)


def test_profile_is_exact_canonical_57_and_simulation_valid():
    profile = _profile()

    assert tuple(name for name, _ in profile.attributes) == CANONICAL_PLAYER_ATTRIBUTES
    assert len(profile.attributes) == 57
    assert all(0 <= value <= 200 for _, value in profile.attributes)
    assert profile.potential_ovr >= profile.ovr
    assert profile.profile_policy_id == DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY.policy_id
    assert (
        profile.profile_policy_fingerprint
        == DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY.fingerprint
    )


def test_profile_materialization_is_deterministic_and_seed_sensitive():
    first = _profile()
    retry = _profile()
    changed_profile = _profile(profile_seed="different-profile-secret")
    changed_potential = _profile(potential_seed="different-potential-secret")

    assert retry == first
    assert retry.fingerprint == first.fingerprint
    assert changed_profile.attributes != first.attributes
    assert changed_profile.fingerprint != first.fingerprint
    assert changed_potential.potential_identity != first.potential_identity
    assert changed_potential.fingerprint != first.fingerprint


def test_raw_hidden_seeds_are_not_embedded_in_materialized_payload():
    profile = _profile()
    payload = profile.model_dump_json()

    assert "profile-secret" not in payload
    assert "development-secret" not in payload
    assert "potential-secret" not in payload
    assert len(profile.source_profile_seed_digest) == 64
    assert len(profile.source_development_seed_digest) == 64
    assert len(profile.source_potential_seed_digest) == 64


def test_player_identity_participates_in_profile_identity():
    first = _profile(player_id="prospect-1")
    second = _profile(player_id="prospect-2")

    assert first.attributes != second.attributes
    assert first.potential_identity != second.potential_identity
    assert first.fingerprint != second.fingerprint

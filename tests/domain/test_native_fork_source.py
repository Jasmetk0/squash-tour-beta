"""Pure serialization contract; database authority is tested through real HTTP."""

import json

import pytest
from pydantic import ValidationError

from beta_engine.domain.native_fork_source import NativeForkSourceBinding

pytestmark = pytest.mark.pr_critical


def binding_data():
    return {
        "run_id": "run",
        "source": {
            "revision_id": "saved",
            "branch_id": "original",
            "content_hash": "a" * 64,
        },
        "components": [
            {"key": "initial_world", "content_hash": "b" * 64},
            {"key": "player_lifecycle", "content_hash": "c" * 64},
        ],
        "historical_sources": [
            {
                "revision_id": "pre-play",
                "branch_id": "original",
                "content_hash": "d" * 64,
            },
        ],
    }


def test_native_source_reference_roundtrip_and_original_owner_are_immutable():
    source = NativeForkSourceBinding.model_validate_json(json.dumps(binding_data()))
    assert (
        NativeForkSourceBinding.model_validate_json(source.model_dump_json()) == source
    )
    assert (
        NativeForkSourceBinding.model_validate_json(
            source.model_dump_json()
        ).fingerprint
        == source.fingerprint
    )
    with pytest.raises(ValidationError):
        source.source.branch_id = "rewritten"
    with pytest.raises(ValidationError):
        source.components[0].content_hash = "0" * 64


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_component",
        "unordered_components",
        "duplicate_revision",
        "self_reference",
        "malformed_hash",
    ],
)
def test_native_source_reference_rejects_ambiguous_or_malformed_authority(mutation):
    data = binding_data()
    if mutation == "duplicate_component":
        data["components"].append(data["components"][0])
    elif mutation == "unordered_components":
        data["components"].reverse()
    elif mutation == "duplicate_revision":
        data["historical_sources"].append(data["historical_sources"][0])
    elif mutation == "self_reference":
        data["historical_sources"][0]["revision_id"] = "saved"
    else:
        data["source"]["content_hash"] = "not-a-digest"
    with pytest.raises(ValidationError):
        NativeForkSourceBinding.model_validate_json(json.dumps(data))

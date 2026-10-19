"""Component-boundary test: native proofs include every new authority input."""

from copy import deepcopy

import pytest

from beta_engine.infrastructure.db import calendar_sporting_checkpoint, calendar_tour
from beta_engine.infrastructure.db import calendar_standalone_match_state as storage

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize(
    "key",
    [
        "calendar_tour_authority",
        "player_lifecycle",
        "player_health_state",
        "run_prospect_source",
    ],
)
def test_native_proof_does_not_cross_a_changed_dependency(monkeypatch, key):
    calls = []
    tours = []
    monkeypatch.setattr(
        storage, "_parse_saved_calendar_match_evidence", lambda *a, **k: None
    )

    def verify(payload, *a, **k):
        calls.append(deepcopy(payload))

    def tour(payload, **k):
        tours.append(deepcopy(payload))

    monkeypatch.setattr(calendar_sporting_checkpoint, "saved_checkpoint", verify)
    monkeypatch.setattr(calendar_tour, "saved_tour", tour)
    payload = {
        "run": {},
        "content": {
            "calendar_player_sporting_checkpoint": {
                "state": {"schema_version": "calendar_sporting_checkpoint.v11"}
            }
        },
    }
    proofs = {}
    for _ in range(2):
        storage.load_saved_calendar_sources(
            payload, run_id="r", branch_id="b", _sporting_component_proofs=proofs
        )
    assert len(calls) == len(tours) == 1
    changed = deepcopy(payload)
    changed["content"][key] = {"changed": "independent authority"}
    storage.load_saved_calendar_sources(
        changed, run_id="r", branch_id="b", _sporting_component_proofs=proofs
    )
    assert len(calls) == len(tours) == 2

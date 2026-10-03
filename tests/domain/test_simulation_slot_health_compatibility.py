from __future__ import annotations

import pytest

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import (
    SimulationMatchEventPlan,
    SimulationSlotPlan,
    fingerprint,
)

pytestmark = pytest.mark.pr_critical


def test_historical_simulation_slot_plan_without_health_keeps_original_fingerprint() -> None:
    payload = {
        "schema_version": "simulation_slot_plan.v1",
        "run_id": "run",
        "branch_id": "branch",
        "week": {"season_index": 0, "week": 1},
        "slot_id": "slot-1",
        "ordinal": 1,
        "ordered_dependency_ids": [],
        "group_ids": ["g1"],
        "match_events": [
            SimulationMatchEventPlan(
                group_id="g1",
                event_id="event",
                match_id="match",
                direct_player_ids=("a", "b"),
            ).model_dump(mode="json")
        ],
        "slot_start_fingerprint": "a" * 64,
        "provenance": "historical slot",
    }
    historical = fingerprint(payload)

    restored = SimulationSlotPlan.model_validate(payload)

    assert restored.health_state_fingerprint is None
    assert restored.fingerprint == historical

    current = restored.model_copy(update={"health_state_fingerprint": "b" * 64})
    assert current.fingerprint != historical

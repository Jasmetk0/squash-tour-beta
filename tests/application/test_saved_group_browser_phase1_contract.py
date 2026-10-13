"""Focused phase-1 contract for the true Saved Group browser acceptance.

The dedicated Chromium test exercises Run+SQLite+real product commands. This
fast regression verifies the immutable projection contract independently:
a real generated group schedule cannot become final standings by itself.
"""
import pytest

from beta_engine.application.run_saved_tour_group_schedule import (
    resolve_saved_tour_group_schedule,
)
from beta_engine.application.run_saved_tour_group_standings import (
    resolve_saved_tour_group_standings,
)
from tests.application.test_run_saved_tour_group_schedule import _component

pytestmark = pytest.mark.pr_critical


def test_saved_group_pre_result_six_real_round_robin_matches_have_no_fake_table():
    component, original = _component(group_count=1, group_size=4)
    projected = resolve_saved_tour_group_schedule(
        component, run_id="run", branch_id="branch",
        event_id="EVENT", published_result=None,
    )
    assert projected is not None
    assert projected.authority_fingerprint == original.fingerprint
    assert projected.group_count == 1
    assert projected.group_size == 4
    assert projected.match_day_count == 3
    assert len(projected.matches) == 6
    assert len({m.match_id for m in projected.matches}) == 6
    assert {m.best_of for m in projected.matches} == {5}
    assert len({(m.top_player_id, m.bottom_player_id) for m in projected.matches}) == 6
    assert resolve_saved_tour_group_standings(
        component, run_id="run", branch_id="branch",
        event_id="EVENT", group_schedule=projected,
    ) is None


def test_group_pre_result_snapshot_is_immutable_and_cannot_claim_foreign_branch():
    component, _ = _component(group_count=1, group_size=4)
    initial = resolve_saved_tour_group_schedule(
        {}, run_id="run", branch_id="branch",
        event_id="EVENT", published_result=None,
    )
    assert initial is None
    with pytest.raises(ValueError, match="another Run/Branch"):
        resolve_saved_tour_group_schedule(
            component, run_id="run", branch_id="foreign",
            event_id="EVENT", published_result=None,
        )
    after = resolve_saved_tour_group_schedule(
        component, run_id="run", branch_id="branch",
        event_id="EVENT", published_result=None,
    )
    assert after is not None and after.match_day_count == 3

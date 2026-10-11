"""Focused 1,000-player production preview and adoption contract.

The separate Chromium + real SQLite workflow covers persisted Save, restart,
canonical Players paging and ranking publication. Do not repeat the multi-world
full Earth season test for an ordinary UI integration PR.
"""
import pytest

from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldInitialPoolPreviewRequest,
)
from beta_engine.application.run_world_initial_world_service import (
    RunWorldInitialWorldAdoptionRequest,
    RunWorldInitialWorldService,
)
from tests.application.test_run_world_session_keep import service


pytestmark = pytest.mark.pr_critical


def test_thousand_player_preview_is_deterministic_and_exact():
    generator = service()
    request = RunWorldInitialPoolPreviewRequest(
        world_package_id="saved-world", season="2000/2001",
        seed=4207, target_pool_size=1000,
    )
    original = generator.preview(
        run_id="run-one", branch_id="branch-one", request=request,
    )
    replayed = generator.preview(
        run_id="run-one", branch_id="branch-one", request=request,
    )
    assert original == replayed
    assert original.preview_fingerprint == replayed.preview_fingerprint
    source = original.result.players
    assert len(source) == original.result.summary.total_players == 1000
    assert len({p.player_id for p in source}) == 1000
    assert all(p.generation_source == "initial_pool" for p in source)
    assert all(p.generation_fingerprint for p in source)
    assert all(not p.locked and not p.manual_override for p in source)

    adoption = RunWorldInitialWorldAdoptionRequest(
        command_id="large-cohort-focused",
        generation=request,
        audit_label="1000-player focused integration",
        audit_reason="Deterministic generated first-season adoption",
        official_run=False, best_n=15, automatic_retirement_age=46,
    )
    world = RunWorldInitialWorldService(generator).preview(
        run_id="run-one", branch_id="branch-one", request=adoption,
    )
    assert world.source_kind == "run_world_generated_pool.v1"
    assert world.world_package_id == "saved-world"
    assert world.run_world_pool_preview_fingerprint == original.preview_fingerprint
    assert len(world.players) == len({p.player_id for p in world.players}) == 1000
    assert {p.source_pool_player_id for p in world.players} == {
        p.player_id for p in source
    }
    assert all(p.source_generation_fingerprint for p in world.players)
    assert all(not p.locked_from_initial_pool for p in world.players)
    assert world.adoption_request_fingerprint == adoption.fingerprint_for_scope(
        run_id="run-one", branch_id="branch-one",
    )

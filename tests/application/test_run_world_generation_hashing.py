"""Real package/generation bootstrap keeps shared hashing independent of roster size."""

import cProfile
import pstats

import pytest

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.application.run_package_service import RunPackageService
from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldInitialPoolPreview,
    RunWorldInitialPoolPreviewRequest,
    RunWorldInitialPoolPreviewService,
)
from beta_engine.application.run_world_initial_world_service import (
    RunWorldInitialWorldAdoptionRequest,
    RunWorldInitialWorldService,
)
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.infrastructure.db.player_lifecycle_state import bootstrap_lifecycle
from beta_engine.world_packages import OFFICIAL_FAX_WORLD_ID
from test_run_package_review_acceptance import _confirm, _empty, _repo


def _calls(profile, getter):
    code = getter.__code__
    return pstats.Stats(profile).stats[(code.co_filename, code.co_firstlineno, code.co_name)][1]


@pytest.mark.pr_critical
def test_thousand_player_initial_world_and_lifecycle_hash_shared_inputs_once():
    repository = _repo()
    _empty(repository)
    adapter = WorldPackageRunAdapter(WorldPackageRegistryService())
    packages = RunPackageService(repository)
    _confirm(packages, adapter.build_document(OFFICIAL_FAX_WORLD_ID),
             command="apply", draft=0, state=None)
    service = RunWorldInitialWorldService(RunWorldInitialPoolPreviewService(packages, adapter))
    request = RunWorldInitialWorldAdoptionRequest(
        command_id="generate", audit_label="Hashing regression",
        audit_reason="Verify real thousand-player generation without repeated shared hashing",
        official_run=True,
        generation=RunWorldInitialPoolPreviewRequest(
            world_package_id=OFFICIAL_FAX_WORLD_ID, seed=2000071, target_pool_size=1000,
        ),
    )
    profile = cProfile.Profile()
    world = profile.runcall(service.preview, run_id="run", branch_id="branch", request=request)
    assert len(world.players) == 1000
    assert _calls(profile, RunWorldInitialPoolPreview.preview_fingerprint.fget) == 1
    assert service.preview(run_id="run", branch_id="branch", request=request) == world
    profile = cProfile.Profile()
    with repository._session_factory.begin() as session:
        lifecycle = profile.runcall(bootstrap_lifecycle, session, world)
    assert _calls(profile, InitialWorldState.fingerprint.fget) == 1
    assert len(lifecycle.players) == 1000
    assert {player.origin for player in lifecycle.players} == {f"initial_world:{world.fingerprint}"}
    assert lifecycle.source_initial_world_fingerprint == world.fingerprint

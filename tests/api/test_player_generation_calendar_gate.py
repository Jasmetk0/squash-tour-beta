"""Real HTTP generation boundaries cannot quietly use the wrong saved clock."""

import json
import sqlite3

import pytest

from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.application.run_package_service import RunPackageService
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.world_package_registry_service import (
    WorldPackageRegistryService,
)
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.models import RunContainerModel
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.application.test_run_package_review_acceptance import _confirm, _ids

pytestmark = pytest.mark.pr_critical


def _world(server, clock, *, world_id="official_fax_world"):
    repo = server.app.state.runtime.repository
    RunContainerCreationService(repo, _ids("run", "branch", "r0", "draft")).create_empty_run(
        display_name="Generation clock", calendar=clock,
    )
    packages = RunPackageService(repo)
    adapter = WorldPackageRunAdapter(WorldPackageRegistryService())
    copied = _confirm(packages, adapter.build_document(world_id),
                      command="copy", draft=0, state=None)
    RunWorkingDraftService(repo, _ids("r1", "save-audit")).save(
        run_id="run", branch_id="branch", expected_draft_version=copied.draft_version,
    )
    return repo, copied.state.fingerprint


def _generation(**changes):
    return {"world_package_id": "official_fax_world", "seed": 802, "target_pool_size": 4, **changes}


def _initial(generation):
    return {"command_id": "generation-1", "generation": generation,
            "audit_label": "Admin", "audit_reason": "Verified calendar preview", "official_run": True}


def _base(server):
    return server.base_url + "/admin/players/runs/run/branches/branch"


def _dump(path):
    with sqlite3.connect(path) as connection:
        return tuple(connection.iterdump())


@pytest.mark.parametrize("clock", [RunCalendar.earth_default(), RunCalendar(52, 35, 2030, 3),
                                   RunCalendar.fax_default(season_count=51)])
def test_every_generation_preview_refuses_an_unsupported_real_saved_run_without_mutation(tmp_path, clock):
    path = tmp_path / "guard.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, package_fingerprint = _world(server, clock)
        before = _dump(path)
        pool = _base(server) + "/initial-pool/world-package/preview"
        requests = [
            _generation(),
            _generation(seed=803, keep_from_seed=802,
                        keep_from_preview_fingerprint="a" * 64, keep_player_ids=["kept-player"]),
            _generation(session_schema_version="run_world_generation_session.v2",
                        session_origin_request=_generation(), session_origin_fingerprint="a" * 64,
                        session_steps=[{"kind": "edit", "source_preview_fingerprint": "a" * 64, "seed": 802}]),
        ]
        for request in requests:
            status, error = _request("POST", pool, request)
            assert status == 409, error
            assert "Initial player generation cannot execute this Run calendar" in error["detail"]["message"]
        status, error = _request("POST", _base(server) + "/initial-world/world-package/preview", _initial(_generation()))
        assert status == 409, error
        assert "Initial player generation cannot execute" in error["detail"]["message"]
        proposal = {"proposal_id": "wrong-clock", "label": "Must not persist",
                    "saved_revision_id": "r1", "draft_version": 2,
                    "package_fingerprint": package_fingerprint, "preview_fingerprint": "a" * 64,
                    "source_seed": 802, "next_seed": 803, "selected_keep_ids": [],
                    "request": _initial(_generation())}
        status, error = _request("POST", _base(server) + "/initial-world/generation-proposals", proposal)
        assert status == 409, error
        assert "Initial player generation cannot execute" in error["detail"]["message"]
        assert _dump(path) == before
        assert repo.verify_branch_saved_revision_hash(revision_id="r0")
        assert repo.verify_branch_saved_revision_hash(revision_id="r1")


def test_default_generation_and_saved_proposal_reads_remain_exact_without_regeneration(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _, package_fingerprint = _world(server, RunCalendar.fax_default())
        before = _dump(path)
        pool_url = _base(server) + "/initial-pool/world-package/preview"
        code, first = _request("POST", pool_url, _generation())
        assert code == 200, first
        assert _request("POST", pool_url, _generation()) == (code, first)
        assert len(first["result"]["players"]) == 4
        assert _dump(path) == before
        request = _initial(_generation())
        code, reviewed = _request("POST", _base(server) + "/initial-world/world-package/preview", request)
        assert code == 200, reviewed
        proposal = {"proposal_id": "candidate", "label": "Reviewed players",
                    "saved_revision_id": "r1", "draft_version": 2,
                    "package_fingerprint": package_fingerprint,
                    "preview_fingerprint": reviewed["fingerprint"],
                    "source_seed": 802, "next_seed": 803, "selected_keep_ids": [], "request": request}
        proposal_url = _base(server) + "/initial-world/generation-proposals"
        code, stored = _request("POST", proposal_url, proposal)
        assert code == 201, stored
        before_reads = _dump(path)
        historical_url = proposal_url + "/candidate/inspection"
        original = _request("GET", historical_url)
        assert original[0] == 200, original
        # Sentinel proves these are stored reads, not a hidden generation retry.
        from beta_engine.application.run_world_generation_calendar_guard import (
            RunWorldGenerationCalendarGuard,
        )

        def refuse_new_generation(*args):
            raise ValueError("Generation deliberately unavailable")

        monkeypatch.setattr(RunWorldGenerationCalendarGuard, "__call__", refuse_new_generation)
        assert _request("GET", historical_url) == original
        assert _request("GET", proposal_url)[0] == 200
        assert _request("GET", proposal_url + "/candidate")[0] == 200
        assert _request("POST", pool_url, _generation())[0] == 409
        assert _dump(path) == before_reads


def test_generation_rejects_damaged_saved_clock_proof_instead_of_falling_back(tmp_path):
    path = tmp_path / "damaged.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, _ = _world(server, RunCalendar.fax_default())
        with repo._session_factory.begin() as session:
            session.get(RunContainerModel, "run").metadata_json = json.dumps({"run_calendar": None})
        before = _dump(path)
        status, error = _request("POST", _base(server) + "/initial-pool/world-package/preview", _generation())
        assert status == 409, error
        assert _dump(path) == before

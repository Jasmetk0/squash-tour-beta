"""Real SQLite cold validation of a native global-slot lineage; nothing is mocked.

A cold read now runs HEAD's complete replay first and then validates unproven
ancestors oldest first. It must return exactly what the original HEAD-first order
returns, stay flat (no nesting of one validation per ancestor) and still reject a
changed or re-hashed ancestor, cold and after a successful warm read.
"""

import json

import pytest

from beta_engine.api.deps import build_runtime
from beta_engine.application.calendar_tour_service import CalendarTourService
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.run_revisions import saved_revision_content_hash
from beta_engine.infrastructure.db import repositories
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from tests.api.test_calendar_global_slots import copy_database

pytestmark = pytest.mark.smoke


def cold_repository(tmp_path, prepared_slots, name):
    path = tmp_path / name
    copy_database(prepared_slots, path)
    return build_runtime(database_url=f"sqlite:///{path}").repository


def read(repository):
    return CalendarTourService(repository).inspect(run_id="run", branch_id="branch")


def oldest_global_ancestor(repository):
    with repository._session_factory() as session:
        rows = session.query(BranchSavedRevisionModel).order_by(BranchSavedRevisionModel.sequence).all()
        globals_ = [r.revision_id for r in rows
                    if json.loads(r.payload_json).get("content", {}).get("calendar_tour_authority", {})
                    .get("state", {}).get("schema_version") == "calendar_tour_authority.v5"]
        return globals_[0], len(globals_)


def rehash_component(repository, revision_id):
    with repository._session_factory.begin() as session:
        row = session.get(BranchSavedRevisionModel, revision_id)
        body = json.loads(row.payload_json)
        component = body["content"]["calendar_tour_authority"]
        component["state"]["rankings"] = component["state"]["rankings"][:-1] or [{"forged": True}]
        component["fingerprint"] = canonical_hash(component["state"])
        row.payload_json = json.dumps(body)
        row.content_hash = saved_revision_content_hash(
            revision_id=row.revision_id, run_id=row.run_id, branch_id=row.branch_id,
            sequence=row.sequence, parent_revision_id=row.parent_revision_id, kind=row.kind,
            payload_schema_version=row.payload_schema_version, payload=body,
            change_summary=json.loads(row.change_summary_json),
        )


def test_cold_lineage_is_flat_and_identical_to_the_original_order(tmp_path, prepared_slots, monkeypatch):
    depth, deepest = [0], [0]
    core = repositories.SimulationPersistenceRepository._validated_saved_revision_core_in_session

    def measured(self, **kwargs):
        depth[0] += 1
        deepest[0] = max(deepest[0], depth[0])
        try:
            return core(self, **kwargs)
        finally:
            depth[0] -= 1

    monkeypatch.setattr(repositories.SimulationPersistenceRepository,
                        "_validated_saved_revision_core_in_session", measured)
    original_order = cold_repository(tmp_path, prepared_slots, "original.db")
    _oldest, global_count = oldest_global_ancestor(original_order)
    assert global_count >= 4
    with monkeypatch.context() as patch:
        patch.setattr(repositories.SimulationPersistenceRepository,
                      "_prevalidate_cold_global_lineage", lambda self, **_: None)
        expected = read(original_order)
    # The original HEAD-first order nests one validation per global ancestor.
    assert deepest[0] >= global_count - 1
    deepest[0] = 0
    assert read(cold_repository(tmp_path, prepared_slots, "cold.db")) == expected
    assert deepest[0] <= 2


@pytest.mark.parametrize("when", ["cold", "after_successful_read"])
def test_changed_ancestor_is_rejected_cold_and_warm(tmp_path, prepared_slots, when):
    repository = cold_repository(tmp_path, prepared_slots, f"{when}.db")
    oldest, _count = oldest_global_ancestor(repository)
    if when == "after_successful_read":
        read(repository)
    rehash_component(repository, oldest)
    with pytest.raises((ValueError, KeyError, TypeError)):
        read(repository)
    # An unrehashed byte change is rejected as well.
    with repository._session_factory.begin() as session:
        row = session.get(BranchSavedRevisionModel, oldest)
        row.content_hash = "0" * 64
    with pytest.raises((ValueError, KeyError, TypeError)):
        read(repository)


@pytest.mark.parametrize("target", ["extension_revision", "old_ancestor"])
def test_extension_save_promotes_only_authenticated_ancestors(tmp_path, prepared_slots, target):
    """After a horizon extension the next read must still reject changed rows.

    The extension Save re-keys proofs of the already authenticated revisions so
    the next read does not re-verify every historical source; the new extension
    revision itself gets no proof and is fully validated by that read.
    """
    from tests.api.test_calendar_sporting_horizon_extension import extend, extension
    from tests.api.test_calendar_tour_flow import tour_url
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    path = tmp_path / "extension.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        assert _request("GET", tour_url(server))[0] == 200
        status, review = extension(server, 4)
        assert status == 200 and review["can_save"], review
        status, receipt = extend(server, review, "promotion-proof")
        assert status == 200, receipt
        repository = server.app.state.runtime.repository
        head_id = receipt["branches"][0]["saved_revision_id"]
        if target == "extension_revision":
            revision_id = head_id
        else:
            revision_id, _count = oldest_global_ancestor(repository)
        rehash_component(repository, revision_id)
        assert _request("GET", tour_url(server))[0] == 409
        assert _request("GET", tour_url(server) + "/seasons")[0] == 409


def test_extension_revision_is_fully_validated_by_the_next_read(tmp_path, prepared_slots, monkeypatch):
    from tests.api.test_calendar_sporting_horizon_extension import extend, extension
    from tests.api.test_calendar_tour_flow import tour_url
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    path = tmp_path / "extension-validation.db"
    copy_database(prepared_slots, path)
    validated = []
    original = repositories.SimulationPersistenceRepository._validate_saved_revision_once

    def observed(self, **kwargs):
        validated.append(kwargs["model"].revision_id)
        return original(self, **kwargs)

    with ApiServer(database_url=f"sqlite:///{path}") as server:
        assert _request("GET", tour_url(server))[0] == 200
        status, review = extension(server, 4)
        status, receipt = extend(server, review, "validated-head")
        assert status == 200, receipt
        head_id = receipt["branches"][0]["saved_revision_id"]
        monkeypatch.setattr(repositories.SimulationPersistenceRepository,
                            "_validate_saved_revision_once", observed)
        assert _request("GET", tour_url(server))[0] == 200
        # The new revision went through the ordinary exact-byte validator
        # (content hash, identity, components) and only then became proven.
        assert head_id in validated
        repository = server.app.state.runtime.repository
        with repository._session_factory() as session:
            row = session.get(repositories.BranchSavedRevisionModel, head_id)
            assert repositories._saved_revision_validation_signature(row) in repository._revision_validation_cache


def test_cold_read_after_extension_replays_each_calendar_binding_once(tmp_path, prepared_slots, monkeypatch):
    """Replay evidence binds the Run calendar; an extension changes it.

    Without a replay of the newest pre-extension revision, oldest-first cold
    validation replayed the whole history again for every ancestor.
    """
    from beta_engine.infrastructure.db import calendar_native_competition
    from tests.api.test_calendar_sporting_horizon_extension import extend, extension
    from tests.api.test_saved_revision_history_api import ApiServer

    path = tmp_path / "extended.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        status, review = extension(server, 4)
        status, receipt = extend(server, review, "binding-replays")
        assert status == 200, receipt
    replays = []
    original = calendar_native_competition._verify_competition_payload

    def counted(*args, **kwargs):
        replays.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(calendar_native_competition, "_verify_competition_payload", counted)

    def cold_replays(name, *, boundary_replay=True):
        copy = tmp_path / name
        copy_database(path, copy)
        with monkeypatch.context() as patch:
            if not boundary_replay:
                patch.setattr(repositories, "_HORIZON_EXTENSION_KIND", "disabled-for-this-check")
            replays.clear()
            repository = build_runtime(database_url=f"sqlite:///{copy}").repository
            view = read(repository)
            return len(replays), view, oldest_global_ancestor(repository)[1]

    without, expected, global_count = cold_replays("without.db", boundary_replay=False)
    with_boundary, view, _count = cold_replays("with.db")
    assert view == expected
    # HEAD + the newest pre-extension revision (+ the unchanged live-state
    # checks of the Tour reader), instead of one per pre-extension ancestor.
    assert with_boundary <= 4 < without, (with_boundary, without, global_count)


def test_failed_extension_save_rolls_back_without_promoting_any_proof(tmp_path, prepared_slots, monkeypatch):
    """Promotion happens only after a successful commit; a rollback leaves none."""
    from beta_engine.application import run_calendar_extension_commit as commit
    from tests.api.test_calendar_sporting_horizon_extension import extend, extension
    from tests.api.test_calendar_tour_flow import tour_url
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    path = tmp_path / "rollback.db"
    copy_database(prepared_slots, path)
    promoted, computed = [], []
    original_appends = commit._verified_ancestor_appends

    def failing_after_promotions(*args, **kwargs):
        result = original_appends(*args, **kwargs)
        computed.append(result)
        raise ValueError("injected failure after the append proof, before commit")

    monkeypatch.setattr(commit, "_verified_ancestor_appends", failing_after_promotions)
    monkeypatch.setattr(commit, "_remember_promotions", lambda *a, **k: promoted.append(a))
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        before = _request("GET", tour_url(server))
        assert before[0] == 200
        repository = server.app.state.runtime.repository
        proofs_before = dict(getattr(repository, "_native_dependency_proofs", {}))
        status, review = extension(server, 4)
        status, _receipt = extend(server, review, "rolled-back")
        assert status == 409
        assert computed and computed[0], "the append proof was computed (non-vacuous)"
        assert promoted == []
        assert dict(getattr(repository, "_native_dependency_proofs", {})) == proofs_before
        after = _request("GET", tour_url(server))
        assert after == before  # the same Saved HEAD; nothing was installed

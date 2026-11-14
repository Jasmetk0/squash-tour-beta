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

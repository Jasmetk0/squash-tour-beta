import pytest
from beta_engine.application.run_cross_saved_comparison import RunCrossSavedComparisonService
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository
import os
import tempfile
from sqlalchemy import create_engine
from beta_engine.infrastructure.db.engine import create_session_factory
from beta_engine.infrastructure.db.models import Base, RunBranchModel, BranchSavedRevisionModel, RunContainerModel

@pytest.fixture
def real_repository():
    # Setup temporary sqlite database
    fd, temp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{temp_db}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    repo = SimulationPersistenceRepository(session_factory=session_factory, engine=engine)
    yield repo, session_factory
    # Cleanup
    os.unlink(temp_db)

def test_cross_run_compare_integration(real_repository):
    repo, session_factory = real_repository
    service = RunCrossSavedComparisonService(repository=repo)

    with session_factory() as session:
        # Create minimal required schema entries directly, as going through all creation services
        # would require massive mock setup or running full application stack.
        # We test the service integration with the actual database.

        # Setup Run A / Branch A
        run_a = RunContainerModel(
            run_id="run-a", display_name="A", storage_kind="built_in", read_only=0,
            timeline_start_season=0, timeline_end_season=50, status="active",
            metadata_json='{"version": 1}'
        )
        branch_a = RunBranchModel(
            branch_id="branch-a", run_id="run-a", display_name="root",
            saved_head_revision_id="rev-a2"
        )

        rev_a1 = BranchSavedRevisionModel(
            revision_id="rev-a1", run_id="run-a", branch_id="branch-a", sequence=1, parent_revision_id=None,
            kind="initial", payload_schema_version="v1", content_hash="hash_a1",
            payload_json='{"content": {"comp1": "A1_comp1"}, "run": {"run_id": "run-a", "version": 1}, "branch": {"branch_id": "branch-a", "name": "b-a"}, "revision_id": "rev-a1"}',
            change_summary_json="{}"
        )
        rev_a2 = BranchSavedRevisionModel(
            revision_id="rev-a2", run_id="run-a", branch_id="branch-a", sequence=2, parent_revision_id="rev-a1",
            kind="save", payload_schema_version="v1", content_hash="hash_a2",
            payload_json='{"content": {"comp1": "A2_comp1", "comp2": "A2_comp2"}, "run": {"run_id": "run-a", "version": 2}, "branch": {"branch_id": "branch-a", "name": "b-a"}, "revision_id": "rev-a2"}',
            change_summary_json="{}"
        )

        # Setup Run B / Branch B
        run_b = RunContainerModel(
            run_id="run-b", display_name="B", storage_kind="built_in", read_only=0,
            timeline_start_season=0, timeline_end_season=50, status="active",
            metadata_json='{"version": 3}'
        )
        branch_b = RunBranchModel(
            branch_id="branch-b", run_id="run-b", display_name="root",
            saved_head_revision_id="rev-b1"
        )

        rev_b1 = BranchSavedRevisionModel(
            revision_id="rev-b1", run_id="run-b", branch_id="branch-b", sequence=1, parent_revision_id=None,
            kind="initial", payload_schema_version="v1", content_hash="hash_b1",
            payload_json='{"content": {"comp1": "B1_comp1", "comp3": "B1_comp3"}, "run": {"run_id": "run-b", "version": 3}, "branch": {"branch_id": "branch-b", "name": "b-b"}, "revision_id": "rev-b1"}',
            change_summary_json="{}"
        )

        session.add_all([run_a, branch_a, rev_a1, rev_a2, run_b, branch_b, rev_b1])
        session.commit()

        # Hack the cache of the repository to bypass the deep complex validation during testing of this high level comparison component.
        from beta_engine.infrastructure.db.repositories import _saved_revision_validation_signature
        repo._revision_validation_cache = {
            _saved_revision_validation_signature(rev_a1): True,
            _saved_revision_validation_signature(rev_a2): True,
            _saved_revision_validation_signature(rev_b1): True,
        }

    # Compare rev-a2 and rev-b1
    comparison = service.compare(
        run_a_id="run-a", branch_a_id="branch-a", revision_a_id="rev-a2",
        run_b_id="run-b", branch_b_id="branch-b", revision_b_id="rev-b1"
    )

    assert comparison.from_source.run_id == "run-a"
    assert comparison.to_source.run_id == "run-b"
    assert comparison.from_source.revision.content_hash == "hash_a2"
    assert comparison.to_source.revision.content_hash == "hash_b1"

    assert "version" in comparison.run_changes
    assert comparison.run_changes["version"]["before"] == 2
    assert comparison.run_changes["version"]["after"] == 3

    assert "name" in comparison.branch_changes
    assert comparison.branch_changes["name"]["before"] == "b-a"
    assert comparison.branch_changes["name"]["after"] == "b-b"

    comp1 = next(c for c in comparison.components if c.component_key == "comp1")
    assert comp1.status == "changed"
    assert comp1.before_fingerprint == "A2_comp1"
    assert comp1.after_fingerprint == "B1_comp1"

    comp2 = next(c for c in comparison.components if c.component_key == "comp2")
    assert comp2.status == "removed"

    comp3 = next(c for c in comparison.components if c.component_key == "comp3")
    assert comp3.status == "added"

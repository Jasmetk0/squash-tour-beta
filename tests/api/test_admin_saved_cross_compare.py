import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from beta_engine.api.routers.admin_saved_cross_compare import router
from beta_engine.api.deps import get_run_cross_saved_comparison_service
from fastapi import FastAPI
from beta_engine.infrastructure.db.repositories import (
    SavedRevisionHistoryNotFoundError,
    SavedRevisionHistoryConflictError
)

app = FastAPI()
app.include_router(router)

def test_compare_endpoint_success():
    mock_service = MagicMock()
    mock_comparison = MagicMock()
    mock_comparison.from_source.run_id = "run-a"
    mock_comparison.from_source.branch_id = "branch-a"
    mock_comparison.from_source.saved_head_revision_id = "head-a"
    mock_comparison.from_source.revision.revision_id = "rev-a"
    mock_comparison.from_source.revision.branch_id = "branch-a"
    mock_comparison.from_source.revision.sequence = 1
    mock_comparison.from_source.revision.parent_revision_id = None
    mock_comparison.from_source.revision.content_hash_algorithm = "sha256"
    mock_comparison.from_source.revision.content_hash = "hash-a"

    mock_comparison.to_source.run_id = "run-b"
    mock_comparison.to_source.branch_id = "branch-b"
    mock_comparison.to_source.saved_head_revision_id = "head-b"
    mock_comparison.to_source.revision.revision_id = "rev-b"
    mock_comparison.to_source.revision.branch_id = "branch-b"
    mock_comparison.to_source.revision.sequence = 1
    mock_comparison.to_source.revision.parent_revision_id = None
    mock_comparison.to_source.revision.content_hash_algorithm = "sha256"
    mock_comparison.to_source.revision.content_hash = "hash-b"

    mock_comparison.run_changes = {}
    mock_comparison.branch_changes = {}
    mock_comparison.components = []

    mock_service.compare.return_value = mock_comparison

    app.dependency_overrides[get_run_cross_saved_comparison_service] = lambda: mock_service

    client = TestClient(app)
    response = client.get(
        "/admin/cross-run-compare",
        params={
            "run_a_id": "run-a",
            "branch_a_id": "branch-a",
            "revision_a_id": "rev-a",
            "run_b_id": "run-b",
            "branch_b_id": "branch-b",
            "revision_b_id": "rev-b",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["from_source"]["run_id"] == "run-a"
    assert data["to_source"]["run_id"] == "run-b"

def test_compare_endpoint_not_found():
    mock_service = MagicMock()
    mock_service.compare.side_effect = SavedRevisionHistoryNotFoundError("Not found")

    app.dependency_overrides[get_run_cross_saved_comparison_service] = lambda: mock_service

    client = TestClient(app)
    response = client.get(
        "/admin/cross-run-compare",
        params={
            "run_a_id": "run-a",
            "branch_a_id": "branch-a",
            "revision_a_id": "rev-a",
            "run_b_id": "run-b",
            "branch_b_id": "branch-b",
            "revision_b_id": "rev-b",
        }
    )
    assert response.status_code == 404

def test_compare_endpoint_conflict():
    mock_service = MagicMock()
    mock_service.compare.side_effect = SavedRevisionHistoryConflictError("Conflict")

    app.dependency_overrides[get_run_cross_saved_comparison_service] = lambda: mock_service

    client = TestClient(app)
    response = client.get(
        "/admin/cross-run-compare",
        params={
            "run_a_id": "run-a",
            "branch_a_id": "branch-a",
            "revision_a_id": "rev-a",
            "run_b_id": "run-b",
            "branch_b_id": "branch-b",
            "revision_b_id": "rev-b",
        }
    )
    assert response.status_code == 409

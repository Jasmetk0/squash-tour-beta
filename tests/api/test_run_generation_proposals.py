"""Production proposal endpoints with real SQLite and exact previews."""
from types import SimpleNamespace as NS

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from beta_engine.api.routers import admin_players
from beta_engine.application.run_world_initial_world_service import (
    RunWorldInitialWorldAdoptionRequest, RunWorldInitialWorldService,
)
from beta_engine.infrastructure.db import DatabaseSettings, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.models import Base, RunGenerationProposalModel
from tests.application.test_run_world_session_keep import source_request, service

pytestmark = pytest.mark.pr_critical


def _runtime(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'proposal.sqlite'}"))
    Base.metadata.create_all(engine)
    sessions = create_session_factory(engine)

    class Repo:
        _session_factory = sessions

        def get_run_container(self, *, run_id):
            return NS(storage_kind="custom_local", read_only=False) if run_id == "run-one" else None

        def get_run_branch(self, *, branch_id):
            return NS(run_id="run-one", read_only=False, status="active") if branch_id == "branch-one" else None

        def get_initial_world(self, *, run_id, branch_id):
            return None

    return NS(repository=Repo()), engine


def _payload():
    generation = source_request()
    request = RunWorldInitialWorldAdoptionRequest(
        command_id="saved-proposal-fixture",
        generation=generation,
        audit_label="Reviewed candidate", audit_reason="Recover the full exact candidate",
        official_run=False, best_n=15, automatic_retirement_age=46,
    )
    state = RunWorldInitialWorldService(service()).preview(
        run_id="run-one", branch_id="branch-one", request=request,
    )
    player_id = sorted(p.player_id for p in state.players)[0]
    payload = admin_players.RunGenerationProposalSave(
        proposal_id="candidate-one", label="First candidate",
        saved_revision_id="saved-head", draft_version=0,
        package_fingerprint="a" * 64, preview_fingerprint=state.fingerprint,
        source_seed=generation.seed, next_seed=generation.seed+1,
        selected_keep_ids=[player_id], request=request,
    )
    return payload, state


def test_actual_sqlite_proposal_save_list_reopen_without_regeneration_and_scope(tmp_path, monkeypatch):
    runtime, engine = _runtime(tmp_path)
    monkeypatch.setattr(
        admin_players, "_assert_reviewed_generation_context", lambda **kwargs: None,
    )
    payload, state = _payload()
    preview = RunWorldInitialWorldService(service())
    created = admin_players.save_run_generation_proposal(
        "run-one", "branch-one", payload,
        package_service=NS(), preview_service=preview, runtime=runtime,
    )
    assert created["preview_fingerprint"] == state.fingerprint
    assert len(created["preview"]["state"]["players"]) == 32
    assert created["selected_keep_ids"] == payload.selected_keep_ids
    assert created["request"]["generation"]["seed"] == 802
    assert not hasattr(runtime.repository, "adopt_initial_world")

    summaries = admin_players.list_run_generation_proposals(
        "run-one", "branch-one", runtime=runtime,
    )["proposals"]
    assert len(summaries) == 1 and summaries[0]["label"] == payload.label
    assert "preview" not in summaries[0]  # no enormous cohort in listing
    with pytest.raises(HTTPException) as wrong_scope:
        admin_players.read_run_generation_proposal(
            "another-run", "branch-one", "candidate-one",
            package_service=NS(), runtime=runtime,
        )
    assert wrong_scope.value.status_code == 409

    # New process/sessionfactory with the same physical SQLite file.
    reopened, _ = _runtime(tmp_path)
    returned = admin_players.read_run_generation_proposal(
        "run-one", "branch-one", "candidate-one",
        package_service=NS(), runtime=reopened,
    )
    assert returned == created
    assert returned["preview"]["fingerprint"] == state.fingerprint
    assert returned["preview"]["state"]["players"] == created["preview"]["state"]["players"]
    # Old command may still be explicitly adopted later through the normal
    # production preview-fingerprint/source recheck. Read never runs generator.

    # Exact retry is idempotent; a changed proposal with the same ID fails.
    assert admin_players.save_run_generation_proposal(
        "run-one", "branch-one", payload,
        package_service=NS(), preview_service=preview, runtime=runtime,
    ) == created
    forged = payload.model_copy(update={"label": "Changed label"})
    with pytest.raises(HTTPException, match="already exists"):
        admin_players.save_run_generation_proposal(
            "run-one", "branch-one", forged,
            package_service=NS(), preview_service=preview, runtime=runtime,
        )
    admin_players.delete_run_generation_proposal(
        "run-one", "branch-one", "candidate-one", runtime=runtime,
    )
    with pytest.raises(HTTPException) as missing:
        admin_players.read_run_generation_proposal(
            "run-one", "branch-one", "candidate-one",
            package_service=NS(), runtime=runtime,
        )
    assert missing.value.status_code == 404


def test_stale_and_corrupt_saved_proposal_fail_closed(tmp_path, monkeypatch):
    runtime, engine = _runtime(tmp_path)
    monkeypatch.setattr(
        admin_players, "_assert_reviewed_generation_context", lambda **kwargs: None,
    )
    payload, state = _payload()
    preview = RunWorldInitialWorldService(service())
    with pytest.raises(HTTPException, match="stale"):
        admin_players.save_run_generation_proposal(
            "run-one", "branch-one",
            payload.model_copy(update={"preview_fingerprint": "b"*64}),
            package_service=NS(), preview_service=preview, runtime=runtime,
        )
    admin_players.save_run_generation_proposal(
        "run-one", "branch-one", payload,
        package_service=NS(), preview_service=preview, runtime=runtime,
    )
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE run_generation_proposals SET payload_json='{}'"
            " WHERE run_id='run-one' AND branch_id='branch-one'"
        ))
    with pytest.raises(HTTPException, match="checksum"):
        admin_players.read_run_generation_proposal(
            "run-one", "branch-one", "candidate-one",
            package_service=NS(), runtime=runtime,
        )

"""F79-06: real SQLite atomic selected append and immutable historical provenance."""
from itertools import count
from types import SimpleNamespace as NS

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.application.run_container_creation_service import RunContainerCreationService
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.run_world_initial_world_service import (
    RunWorldInitialWorldAdoptionRequest,
    RunWorldInitialWorldService,
    RunWorldSelectedInitialWorldAppendRequest,
    compose_selected_initial_world_append,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel, InitialWorldStateModel, PlayerHealthWeekStateModel,
)
from beta_engine.infrastructure.db.player_health_state import get_health
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
from beta_engine.infrastructure.db.player_sporting_state import get_sporting
from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
from tests.api.test_earth_world_run_acceptance import _repository
from tests.application.test_run_world_session_keep import source_request, service

pytestmark = pytest.mark.pr_critical
SHA = "a"*64


def _id_factory():
    seq = count(1)
    return lambda kind: f"append-{kind}-{next(seq)}"


def _prepared(tmp_path, monkeypatch):
    repo = _repository(f"sqlite:///{tmp_path / 'selected-append.sqlite'}")
    from beta_engine.infrastructure.db import repositories as repos
    import beta_engine.infrastructure.db.run_package_state as package_state
    monkeypatch.setattr(repos, "load_saved_run_package_state",
                        lambda *a, **kw: NS(fingerprint=SHA))
    monkeypatch.setattr(package_state, "get_run_package_state",
                        lambda *a, **kw: NS(fingerprint=SHA))
    # This isolated transaction test has no actual World Package fixture;
    # only the target CAS is stubbed, never persist a fabricated Package state.
    monkeypatch.setattr(repos, "capture_saved_run_package_state",
                        lambda *a, **kw: None)
    ids = _id_factory()
    created = RunContainerCreationService(repo, ids).create_empty_run(
        display_name="Selected append SQLite proof"
    )
    run_id, branch_id = created.run_id, created.viewer_branch_id
    assert branch_id
    producer = RunWorldInitialWorldService(service())
    def generated(total):
        req = RunWorldInitialWorldAdoptionRequest(
            command_id=f"generated-{total}", generation=source_request().model_copy(
                update={"country_code": "BOG", "target_pool_size": total}
            ),
            audit_label="Append test", audit_reason="Actual selected production preview",
            official_run=False, best_n=15, automatic_retirement_age=46
        )
        return producer.preview(run_id=run_id, branch_id=branch_id, request=req), req
    initial, _ = generated(3)
    larger, request = generated(6)
    new_ids = sorted({p.player_id for p in larger.players} -
                     {p.player_id for p in initial.players})
    assert new_ids and len(new_ids) == 3
    repo.adopt_initial_world(initial)
    preflight = repo.preview_initial_world_save(run_id=run_id, branch_id=branch_id)
    assert preflight["can_save"]
    RunWorkingDraftService(repo, ids).save_initial_world(
        run_id=run_id, branch_id=branch_id,
        expected_draft_version=preflight["draft_version"],
        expected_initial_world_fingerprint=initial.fingerprint,
    )
    saved = repo.get_branch_revision_state(branch_id=branch_id)
    command = RunWorldSelectedInitialWorldAppendRequest(
        command_id="append-picked-1", generation=request,
        selected_player_ids=tuple(new_ids[:2]),
        audit_label="Pick two", audit_reason="Need exactly two additional players",
    )
    appended = compose_selected_initial_world_append(initial, larger, command)
    return repo, run_id, branch_id, initial, larger, command, appended, saved


def _install(repo, run_id, branch_id, initial, appended, saved):
    return repo.append_selected_initial_world(
        appended=appended,
        expected_initial_world_fingerprint=initial.fingerprint,
        expected_saved_head=saved.saved_revision.revision_id,
        expected_draft_version=saved.working_draft.draft_version,
        expected_package_fingerprint=SHA,
    )


def test_selected_append_real_sqlite_preserves_saved_head_and_rebuilds_week_one(tmp_path, monkeypatch):
    repo, rid, bid, initial, source, cmd, amended, saved = _prepared(tmp_path, monkeypatch)
    assert initial.fingerprint != amended.fingerprint
    assert len(amended.players) == len(initial.players)+2
    assert amended.selected_appends[0].selected_player_ids == cmd.selected_player_ids
    assert amended.selected_appends[0].source_preview_fingerprint == source.run_world_pool_preview_fingerprint
    assert amended.players[:3] == initial.players[:3]
    installed = _install(repo, rid, bid, initial, amended, saved)
    assert installed == amended
    assert repo.get_initial_world(run_id=rid, branch_id=bid) == amended
    still_saved = repo.get_branch_revision_state(branch_id=bid)
    assert still_saved.saved_revision.revision_id == saved.saved_revision.revision_id
    assert load_saved_initial_world(still_saved.saved_revision.payload,
        run_id=rid, branch_id=bid) == initial
    with repo._session_factory() as session:
        week = RankingWeek(season_index=0, week=1)
        lifecycle = get_lifecycle(session,run_id=rid,branch_id=bid,week=week)
        sporting = get_sporting(session,run_id=rid,branch_id=bid,week=week)
        health = get_health(session,run_id=rid,branch_id=bid,week=week)
        for state in (lifecycle, sporting, health):
            assert state is not None
            assert state.source_initial_world_fingerprint == amended.fingerprint
            assert {p.player_id for p in state.players} == {p.player_id for p in amended.players}
    can_save = repo.preview_initial_world_save(run_id=rid, branch_id=bid)
    assert can_save["has_unsaved_changes"] and can_save["can_save"]
    with pytest.raises(ValueError, match="saved InitialWorld"):
        _install(repo, rid, bid, initial, amended, saved)


def test_selected_append_conflicting_ids_and_source_world_fail_closed(tmp_path, monkeypatch):
    repo, rid, bid, initial, source, cmd, amended, saved = _prepared(tmp_path, monkeypatch)
    old = initial.players[0].player_id
    with pytest.raises(ValueError, match="already exists"):
        compose_selected_initial_world_append(initial, source,
            cmd.model_copy(update={"selected_player_ids":(old,)}))
    with pytest.raises(ValidationError):
        RunWorldSelectedInitialWorldAppendRequest(
            **{**cmd.model_dump(), "selected_player_ids":[cmd.selected_player_ids[0]]*2}
        )
    with pytest.raises(ValueError, match="World differs"):
        compose_selected_initial_world_append(initial, source.model_copy(update={
            "world_generation_content_fingerprint": "b"*64,
        }), cmd)
    with pytest.raises(ValueError, match="cannot mutate any existing player"):
        changed = amended.model_copy(update={"players":tuple(
            p.model_copy(update={"name":"Tampered"}) if p.player_id == old else p
            for p in amended.players
        )})
        _install(repo, rid, bid, initial, changed, saved)
    assert repo.get_initial_world(run_id=rid, branch_id=bid) == initial


def test_ranking_activity_blocks_selected_append_atomically(tmp_path, monkeypatch):
    repo, rid, bid, initial, _, _, amended, saved = _prepared(tmp_path, monkeypatch)
    with repo._session_factory.begin() as session:
        session.add(AuthoritativeWorldStateModel(
            run_id=rid,branch_id=bid,current_ordinal=0,ranking_fingerprint=SHA))
    with pytest.raises(ValueError, match="ranking or sporting"):
        _install(repo, rid, bid, initial, amended, saved)
    assert repo.get_initial_world(run_id=rid, branch_id=bid).fingerprint == initial.fingerprint


def test_corrupted_health_evidence_rolls_back_all_append_mutations(tmp_path, monkeypatch):
    repo, rid, bid, initial, _, _, amended, saved = _prepared(tmp_path, monkeypatch)
    with repo._session_factory.begin() as session:
        row = session.get(PlayerHealthWeekStateModel,(rid,bid,0))
        assert row
        row.fingerprint = "f"*64
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        _install(repo, rid, bid, initial, amended, saved)
    assert repo.get_initial_world(run_id=rid, branch_id=bid).fingerprint == initial.fingerprint


def test_old_initial_world_fingerprint_does_not_change_when_append_history_absent(tmp_path, monkeypatch):
    _,_,_,old,_,_,new,_ = _prepared(tmp_path, monkeypatch)
    old_raw=old.model_dump(mode="json")
    old_raw.pop("selected_appends")
    # Fingerprint remains byte-for-byte the v1 hash, despite an opt-in v79 field.
    import hashlib, json
    assert old.fingerprint == hashlib.sha256(
        json.dumps(old_raw,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    assert new.fingerprint != old.fingerprint


def test_direct_preview_and_explicit_commit_use_same_production_generation_and_sqlite(tmp_path, monkeypatch):
    from beta_engine.api.routers import admin_players
    repo, rid, bid, initial, larger, cmd, appended, saved = _prepared(tmp_path, monkeypatch)
    # This isolated DB test stubs the World-Package lookup, not the production
    # player service nor the repository's atomic Run/Draft/InitialWorld CAS.
    monkeypatch.setattr(admin_players, "_assert_reviewed_generation_context",
                        lambda **kw: None)
    context = admin_players.SelectedInitialWorldAppendScopedRequest(
        append=cmd,
        expected_head=saved.saved_revision.revision_id,
        expected_draft_version=saved.working_draft.draft_version,
        expected_package_fingerprint=SHA,
        expected_initial_world_fingerprint=initial.fingerprint,
    )
    args=dict(
        run_id=rid, branch_id=bid, payload=context, runtime=NS(repository=repo),
        package_service=NS(), service=RunWorldInitialWorldService(service()),
    )
    candidate = admin_players.preview_selected_initial_world_append(**args)
    assert candidate["preview_only"] and candidate["fingerprint"]==appended.fingerprint
    assert repo.get_initial_world(run_id=rid,branch_id=bid)==initial
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as wrong:
        admin_players.commit_selected_initial_world_append(
            **args, expected="b"*64
        )
    assert wrong.value.status_code==409
    assert repo.get_initial_world(run_id=rid,branch_id=bid)==initial
    accepted=admin_players.commit_selected_initial_world_append(
        **args, expected=candidate["fingerprint"]
    )
    assert accepted==appended
    with pytest.raises(HTTPException) as second:
        admin_players.commit_selected_initial_world_append(
            **args,expected=candidate["fingerprint"]
        )
    assert second.value.status_code==409


def test_modified_but_validly_checksummed_week_one_health_cannot_be_erased(tmp_path, monkeypatch):
    repo, rid, bid, initial, _, _, amended, saved = _prepared(tmp_path, monkeypatch)
    with repo._session_factory.begin() as session:
        week=RankingWeek(season_index=0,week=1)
        current=get_health(session,run_id=rid,branch_id=bid,week=week)
        assert current
        modified=current.model_copy(update={"stage_provenance":"legitimate-week1-admin-health-change"})
        row=session.get(PlayerHealthWeekStateModel,(rid,bid,0))
        assert row
        row.payload_json=modified.model_dump_json()
        row.fingerprint=modified.fingerprint
    with pytest.raises(ValueError,match="non-bootstrap edits"):
        _install(repo,rid,bid,initial,amended,saved)
    assert repo.get_initial_world(run_id=rid,branch_id=bid)==initial

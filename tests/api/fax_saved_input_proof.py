"""Negative and concurrent Saved-input proof using only disposable SQLite state."""
import json
import threading

from sqlalchemy import event, select

from beta_engine.application.initial_world import parse_initial_world_json
from beta_engine.domain.run_packages import RunPackageState
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    BranchWorkingDraftModel,
    InitialWorldStateModel,
    RunPackageStateModel,
)
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import _request


def verify_saved_inputs(repo, run_id, branch_id, saved_id, profile, path, pre_alpha):
    for model, parse, damage in (
        (InitialWorldStateModel, parse_initial_world_json, "world"),
        (RunPackageStateModel, RunPackageState.model_validate_json, "package"),
    ):
        with repo._session_factory.begin() as session:
            row = session.get(model, (run_id, branch_id))
            original = row.payload_json, row.fingerprint
            state = parse(row.payload_json)
            if damage == "world":
                state = state.model_copy(update={"audit_reason": "Unsaved rehashed input"})
            else:
                version = state.package_versions[0].model_copy(update={"provenance": {"unsaved": True}})
                state = state.model_copy(update={"package_versions": (version, *state.package_versions[1:])})
            row.payload_json, row.fingerprint = state.model_dump_json(), state.fingerprint
        before = _dump(path)
        code, blocked = _request("GET", pre_alpha + "/fax-acceptance-profile")
        assert code == 200 and not blocked["ready_for_long_acceptance"], blocked
        assert "FAX_ACCEPTANCE_INPUTS_NOT_SAVED" in {i["code"] for i in blocked["issues"]}
        code, denied = _request("POST", pre_alpha + "/fax-long-acceptance/probe", {
            "command_id": "unsaved-source", "operator_label": "Admin", "audit_reason": "Refuse rehashed unsaved inputs.",
        })
        assert code == 409 and "FAX_ACCEPTANCE_INPUTS_NOT_SAVED" in denied["detail"]["message"], denied
        assert _dump(path) == before
        with repo._session_factory.begin() as session:
            row = session.get(model, (run_id, branch_id))
            row.payload_json, row.fingerprint = original
        assert _request("GET", pre_alpha + "/fax-acceptance-profile") == (200, profile)

    with repo._session_factory.begin() as session:
        row = session.get(BranchSavedRevisionModel, saved_id)
        original = row.payload_json
        payload = json.loads(original)
        payload["run"]["display_name"] = "Changed without original hash"
        row.payload_json = json.dumps(payload)
    before = _dump(path)
    code, denied = _request("GET", pre_alpha + "/fax-acceptance-profile")
    assert code == 409 and "content-hash" in denied["detail"]["message"], denied
    assert _dump(path) == before
    with repo._session_factory.begin() as session:
        session.get(BranchSavedRevisionModel, saved_id).payload_json = original

    captured, committed, armed = threading.Event(), threading.Event(), threading.Event()
    errors = []
    armed.set()
    with repo._session_factory() as session:
        original_world = session.get(InitialWorldStateModel, (run_id, branch_id)).payload_json
    engine = repo._session_factory.kw["bind"]

    def after_draft_read(connection, cursor, statement, parameters, context, executemany):
        if armed.is_set() and "FROM branch_working_drafts" in statement:
            armed.clear()
            captured.set()
            assert committed.wait(10), "Concurrent writer did not commit"

    def writer():
        try:
            assert captured.wait(10), "Profile did not reach its captured draft"
            with repo._session_factory.begin() as session:
                draft = session.scalar(select(BranchWorkingDraftModel).where(BranchWorkingDraftModel.branch_id == branch_id))
                draft.status = "dirty"
                row = session.get(InitialWorldStateModel, (run_id, branch_id))
                changed = parse_initial_world_json(row.payload_json).model_copy(update={"audit_reason": "Concurrent unsaved world"})
                row.payload_json, row.fingerprint = changed.model_dump_json(), changed.fingerprint
        except Exception as exc:  # noqa: BLE001 - relay worker failures to the test thread
            errors.append(exc)
        finally:
            committed.set()

    event.listen(engine, "after_cursor_execute", after_draft_read)
    thread = threading.Thread(target=writer)
    thread.start()
    try:
        assert _request("GET", pre_alpha + "/fax-acceptance-profile") == (200, profile)
    finally:
        event.remove(engine, "after_cursor_execute", after_draft_read)
        captured.set()
        thread.join(timeout=15)
    assert not thread.is_alive() and not errors, errors
    code, latest = _request("GET", pre_alpha + "/fax-acceptance-profile")
    assert code == 200 and not latest["ready_for_long_acceptance"], latest
    assert {"FAX_ACCEPTANCE_INPUTS_NOT_SAVED", "FAX_ACCEPTANCE_SAVED_DRAFT_REQUIRED"} <= {i["code"] for i in latest["issues"]}
    with repo._session_factory.begin() as session:
        row = session.get(InitialWorldStateModel, (run_id, branch_id))
        row.payload_json = original_world
        row.fingerprint = parse_initial_world_json(original_world).fingerprint
        draft = session.scalar(select(BranchWorkingDraftModel).where(BranchWorkingDraftModel.branch_id == branch_id))
        draft.status = "clean"
    assert _request("GET", pre_alpha + "/fax-acceptance-profile") == (200, profile)

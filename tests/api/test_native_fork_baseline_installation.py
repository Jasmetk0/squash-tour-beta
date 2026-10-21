"""Real MatchEngine/HTTP source and SQLite staging, not native continuation."""

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from threading import Lock

import pytest
from sqlalchemy import event

from beta_engine.application.native_fork_baseline_installation import (
    NativeForkBaselineInstallationService,
)
from beta_engine.application.native_fork_baseline_preparation import (
    NativeForkBaselinePreparationService,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.native_fork_baseline import NativeForkBaseline
from beta_engine.domain.run_revisions import canonical_json
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    RunBranchModel,
)
from beta_engine.infrastructure.db.native_fork_saved_root import (
    COMPONENT_KEY,
    PENDING_STATUS,
)
from beta_engine.infrastructure.db.repositories import (
    BranchRevisionStateConflictError,
    WorkingDraftConflictError,
    _saved_revision_record_content_hash,
)
from tests.api.test_calendar_tour_flow import setup
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def test_native_root_installation_rollback_retry_restart_and_source_integrity(tmp_path):
    path = tmp_path / "native-installation.db"
    url = f"sqlite:///{path}"
    with ApiServer(database_url=url) as server:
        repo, saved = setup(server, RunCalendar(7, 1, 2030, 3), 4)
        source_id = saved["revision_id"]
        baseline = NativeForkBaselinePreparationService(repo).prepare(
            run_id="run",
            source_branch_id="branch",
            source_revision_id=source_id,
            target_branch_id="native-target",
        )
        command = {
            "baseline": baseline,
            "revision_id": "native-root",
            "draft_id": "native-draft",
            "audit_event_id": "native-audit",
            "display_name": "Native target",
            "expected_source_head": source_id,
            "expected_viewer_branch_id": "branch",
        }
        service = NativeForkBaselineInstallationService(repo)
        original_history = repo.get_branch_saved_revision_history(
            run_id="run", branch_id="branch"
        )
        before = _dump(path)
        for change in (
            {"expected_source_head": "stale"},
            {"expected_viewer_branch_id": "stale"},
            {"draft_id": " "},
            {"display_name": " Native target "},
            {"draft_id": repo.get_branch_working_draft(branch_id="branch").draft_id},
            {"revision_id": source_id},
            {"display_name": repo.get_run_branch(branch_id="branch").display_name},
        ):
            with pytest.raises(ValueError):
                service.install(**(command | change))
            assert _dump(path) == before

        def fail_audit(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith("INSERT INTO branch_revision_audit_events"):
                raise RuntimeError("injected late audit failure")

        event.listen(repo._engine, "before_cursor_execute", fail_audit)
        try:
            with pytest.raises(RuntimeError, match="late audit failure"):
                service.install(**command)
        finally:
            event.remove(repo._engine, "before_cursor_execute", fail_audit)
        assert _dump(path) == before
        assert repo.get_run_branch(branch_id="native-target") is None

        # Two first-time installers race through the production transaction, not
        # through mocked locks or hand-authored runtime records.
        with ThreadPoolExecutor(max_workers=2) as executor:
            roots = list(executor.map(lambda _: service.install(**command), range(2)))
        root = roots[0]
        assert roots[1] == root
        installed = _dump(path)
        assert set(before) <= set(installed)
        assert len(set(installed) - set(before)) == 5
        assert service.install(**command) == root
        assert _dump(path) == installed
        target = repo.get_run_branch(branch_id="native-target")
        assert target.read_only and target.status == PENDING_STATUS
        assert not target.is_official
        assert root.parent_revision_id == source_id
        assert root.payload["run"]["viewer_branch_id"] == "branch"
        assert set(root.payload["content"]) == {COMPONENT_KEY}
        assert (
            NativeForkBaseline.model_validate_json(
                canonical_json(root.payload["content"][COMPONENT_KEY]["state"])
            )
            == baseline
        )
        assert (
            repo.get_branch_saved_revision_history(run_id="run", branch_id="branch")
            == original_history
        )
        assert repo.get_branch_saved_revision_history(
            run_id="run", branch_id="native-target"
        ).saved_revisions == (
            *original_history.saved_revisions,
            root,
        )
        assert repo.list_branch_saved_revisions(branch_id="native-target") == [root]
        assert (
            repo.get_branch_working_draft(branch_id="native-target").base_revision_id
            == root.revision_id
        )
        for change in (
            {"display_name": "Other"},
            {"draft_id": "other"},
            {"audit_event_id": "other"},
        ):
            with pytest.raises(ValueError, match="receipt conflicts"):
                service.install(**(command | change))
            assert _dump(path) == installed
        with pytest.raises(WorkingDraftConflictError, match="active"):
            repo.stage_viewer_branch_selection(
                run_id="run",
                branch_id="branch",
                viewer_branch_id="native-target",
                expected_draft_version=repo.get_branch_working_draft(
                    branch_id="branch"
                ).draft_version,
            )
        assert _dump(path) == installed

        # Force every revision to share one stripe. Source proofs must be outside
        # that lock, including the metadata-only history walk.
        repo._revision_validation_work_locks = [Lock()]
        assert repo.get_branch_saved_revision(revision_id="native-root") == root
        assert (
            repo.get_branch_revision_state(branch_id="native-target").saved_revision
            == root
        )
        assert _dump(path) == installed

    with ApiServer(database_url=url) as server:
        repo = server.app.state.runtime.repository
        assert repo.get_branch_saved_revision(revision_id="native-root") == root
        assert NativeForkBaselineInstallationService(repo).install(**command) == root
        code, detail = _request(
            "GET",
            server.base_url
            + "/run-containers/run/branches/native-target/saved-revisions",
        )
        assert code == 200, detail

        # Warm target and source proofs cannot authorize later changed physical
        # source bytes. Restore bytes between cases without mutating old facts.
        source_row = repo.get_branch_saved_revision(revision_id=source_id)
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, source_id)
            source_bytes = row.payload_json
            value = json.loads(source_bytes)
            value["run"]["display_name"] = "corrupted source"
            row.payload_json = canonical_json(value)
        with pytest.raises(BranchRevisionStateConflictError, match="integrity"):
            repo.get_branch_saved_revision(revision_id="native-root")
        with repo._session_factory.begin() as session:
            session.get(BranchSavedRevisionModel, source_id).payload_json = source_bytes
        assert repo.get_branch_saved_revision(revision_id=source_id) == source_row

        # Even a fully rehashed current-fact forgery fails actual source rebuild.
        payload = deepcopy(root.payload)
        component = payload["content"][COMPONENT_KEY]
        component["state"]["source_ranking_fingerprint"] = "0" * 64
        component["fingerprint"] = NativeForkBaseline.model_validate_json(
            canonical_json(component["state"])
        ).fingerprint
        forged = replace(root, payload=payload)
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, root.revision_id)
            original_bytes = row.payload_json
            row.payload_json = canonical_json(payload)
            row.content_hash = _saved_revision_record_content_hash(forged)
        with pytest.raises(
            BranchRevisionStateConflictError, match="actual Saved authority"
        ):
            repo.get_branch_saved_revision(revision_id="native-root")
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, root.revision_id)
            row.payload_json, row.content_hash = original_bytes, root.content_hash

        # Removing both the native schema and component must not downgrade a
        # pending target into an apparently ordinary empty Saved revision.
        downgraded_payload = deepcopy(root.payload)
        downgraded_payload["content"] = {}
        downgraded_payload["branch"]["status"] = "active"
        downgraded = replace(
            root,
            payload=downgraded_payload,
            payload_schema_version="run_saved_revision_v1",
        )
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, root.revision_id)
            row.payload_json = canonical_json(downgraded_payload)
            row.payload_schema_version = downgraded.payload_schema_version
            row.content_hash = _saved_revision_record_content_hash(downgraded)
        with pytest.raises(
            BranchRevisionStateConflictError, match="Pending native fork"
        ):
            repo.get_branch_saved_revision(revision_id="native-root")
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, root.revision_id)
            row.payload_json, row.content_hash = original_bytes, root.content_hash
            row.payload_schema_version = root.payload_schema_version

        # A corrupt cross-Branch source cycle fails before acquiring any work
        # lock recursively. The ContextVar must reset after the failure as well.
        with repo._session_factory.begin() as session:
            session.get(
                RunBranchModel, "branch"
            ).saved_head_revision_id = root.revision_id
        with pytest.raises(BranchRevisionStateConflictError, match="cycle"):
            repo.get_branch_saved_revision(revision_id="native-root")
        with repo._session_factory.begin() as session:
            session.get(RunBranchModel, "branch").saved_head_revision_id = source_id
        assert repo.get_branch_saved_revision(revision_id="native-root") == root
        assert _dump(path) == installed

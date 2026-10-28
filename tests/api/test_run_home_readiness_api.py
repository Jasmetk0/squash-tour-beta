"""Production HTTP/SQLite saved-content readiness across Branches and restart."""

from urllib.parse import urlencode

import pytest

from tests.api.test_run_working_draft_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def _get(server, run, branch):
    return _request("GET", f"{server.base_url}/admin/runs/{run}/branches/{branch}/home-readiness")


def test_real_http_run_readiness_is_saved_branch_owned_and_persists_restart(tmp_path):
    database = f"sqlite:///{tmp_path / 'run-readiness.db'}"
    with ApiServer(database_url=database) as server:
        code, new = _request("POST", server.base_url + "/run-containers", {
            "display_name": "Run readiness W52",
            "calendar": {
                "weeks_per_year": 52, "season_start_year_week": 35,
                "start_year": 2030, "season_count": 3,
            },
        })
        assert code == 201, new
        rid, bid = new["run_id"], new["viewer_branch_id"]
        code, initial = _get(server, rid, bid)
        assert code == 200, initial
        assert initial["source"] == "validated_selected_branch_saved_head"
        assert initial["items"][0]["status"] == "missing"
        assert initial["items"][-1]["status"] == "saved"
        assert initial["sporting_calendar_supported_by_legacy_writers"] is False
        assert initial["requires_operation_preflight"] is True
        assert initial["simulation_started"] is False
        assert _get(server, rid, "nonexistent")[0] == 404

        code, listing = _request(
            "GET", server.base_url + "/run-branches?" + urlencode({"run_id": rid}),
        )
        assert code == 200, listing
        ancestor_id = listing["run_branches"][0]["saved_head_revision_id"]
        code, fork = _request(
            "POST", f"{server.base_url}/run-containers/{rid}/branches",
            {"source_branch_id": bid, "source_saved_revision_id": ancestor_id},
        )
        assert code == 201, fork
        code, second = _get(server, rid, fork["branch_id"])
        assert code == 200, second
        assert second["branch_id"] == fork["branch_id"]
        assert second["saved_revision_id"] == ancestor_id
        assert second["items"][0]["status"] == "missing"
        assert _get(server, rid, bid) == (200, initial)

        code, other = _request("POST", server.base_url + "/run-containers", {
            "display_name": "Another Run",
        })
        assert code == 201, other
        assert _get(server, other["run_id"], bid)[0] == 404
        assert _get(server, rid, other["viewer_branch_id"])[0] == 404

    with ApiServer(database_url=database) as server:
        assert _get(server, rid, bid) == (200, initial)
        assert _get(server, rid, fork["branch_id"]) == (200, second)



def _draft(server, run, branch):
    return _request(
        "GET", f"{server.base_url}/run-containers/{run}/branches/{branch}/working-draft",
    )


def test_real_http_readiness_tracks_explicit_draft_save_without_leaking_across_branches(tmp_path):
    """Saved HEAD, draft version and per-Branch evidence across real HTTP/SQLite."""
    database = f"sqlite:///{tmp_path / 'readiness-draft-save.db'}"
    with ApiServer(database_url=database) as server:
        code, created = _request("POST", server.base_url + "/run-containers", {
            "display_name": "Readiness draft lifecycle",
            "calendar": {
                "weeks_per_year": 52, "season_start_year_week": 1,
                "start_year": 2040, "season_count": 2,
            },
        })
        assert code == 201, created
        rid, source = created["run_id"], created["viewer_branch_id"]
        code, before = _get(server, rid, source)
        assert code == 200, before
        assert before["current_calendar"]["weeks_per_year"] == 52
        assert before["sporting_calendar_supported_by_legacy_writers"] is False
        assert before["items"][-1] == {
            "code": "working_draft", "status": "saved", "evidence_count": 0,
        }
        assert before["saved_transition_count"] == 0
        assert before["saved_published_ranking_count"] == 0
        assert before["phase"] == "preparation"
        code, clean = _draft(server, rid, source)
        assert code == 200, clean
        assert clean["draft_version"] == before["draft_version"]

        code, fork = _request(
            "POST", f"{server.base_url}/run-containers/{rid}/branches",
            {
                "source_branch_id": source,
                "source_saved_revision_id": before["saved_revision_id"],
            },
        )
        assert code == 201, fork
        other = fork["branch_id"]
        code, independent = _get(server, rid, other)
        assert code == 200, independent
        assert independent["saved_revision_id"] == before["saved_revision_id"]

        draft_url = f"{server.base_url}/run-containers/{rid}/branches/{source}/working-draft"
        code, staged = _request("PUT", draft_url + "/viewer-branch", {
            "viewer_branch_id": other, "expected_draft_version": clean["draft_version"],
        })
        assert code == 200, staged
        assert staged["status"] == "dirty"
        assert staged["change_count"] > 0
        code, dirty = _get(server, rid, source)
        assert code == 200, dirty
        assert dirty["saved_revision_id"] == before["saved_revision_id"]
        assert dirty["saved_revision_content_hash"] == before["saved_revision_content_hash"]
        assert dirty["draft_version"] == staged["draft_version"]
        assert dirty["items"][-1] == {
            "code": "working_draft", "status": "unsaved",
            "evidence_count": staged["change_count"],
        }
        assert dirty["items"][:-1] == before["items"][:-1]
        assert dirty["requires_operation_preflight"] is True
        assert dirty["simulation_started"] is False
        assert _get(server, rid, other) == (200, independent)

        # A rejected optimistic Save must leave the dirty draft and HEAD intact.
        code, conflict = _request("POST", draft_url + "/save", {
            "expected_draft_version": clean["draft_version"],
        })
        assert code == 409, conflict
        assert _get(server, rid, source) == (200, dirty)

        code, saved = _request("POST", draft_url + "/save", {
            "expected_draft_version": staged["draft_version"],
        })
        assert code == 201, saved
        assert saved["working_draft"]["status"] == "clean"
        code, after = _get(server, rid, source)
        assert code == 200, after
        assert after["saved_revision_id"] == saved["saved_revision"]["revision_id"]
        assert after["saved_revision_id"] != before["saved_revision_id"]
        assert after["draft_version"] == saved["working_draft"]["draft_version"]
        assert after["items"][-1] == {
            "code": "working_draft", "status": "saved", "evidence_count": 0,
        }
        assert after["items"][:-1] == before["items"][:-1]
        assert after["current_calendar"] == before["current_calendar"]
        assert _get(server, rid, other) == (200, independent)
        code, persisted_run = _request("GET", server.base_url + f"/run-containers/{rid}")
        assert code == 200, persisted_run
        assert persisted_run["viewer_branch_id"] == other

    # Fresh process and SQLAlchemy runtime: the branch-local Saved projection
    # cannot be reconstructed from a stale browser cache or mutable local store.
    with ApiServer(database_url=database) as server:
        assert _get(server, rid, source) == (200, after)
        assert _get(server, rid, other) == (200, independent)
        code, reloaded_draft = _draft(server, rid, source)
        assert code == 200, reloaded_draft
        assert reloaded_draft["draft_version"] == after["draft_version"]
        assert reloaded_draft["status"] == "clean"


def test_real_http_empty_fax_run_has_truthful_optional_foundations_and_no_side_effects(tmp_path):
    """A valid empty Run is not an all-operation-ready or globally blocked Run."""
    database = f"sqlite:///{tmp_path / 'readiness-empty-fax.db'}"
    with ApiServer(database_url=database) as server:
        code, new = _request("POST", server.base_url + "/run-containers", {
            "display_name": "Empty FAX readiness",
        })
        assert code == 201, new
        rid, bid = new["run_id"], new["viewer_branch_id"]
        code, first = _get(server, rid, bid)
        assert code == 200, first
        assert first["current_calendar"] == new["metadata_json"]["run_calendar"]
        assert first["sporting_calendar_supported_by_legacy_writers"] is True
        assert first["requires_operation_preflight"] is True
        assert first["simulation_started"] is False
        assert first["saved_published_ranking_count"] == 0
        assert first["saved_transition_count"] == 0
        assert first["active_full_simulation_task_count"] == 0
        assert first["phase"] == "preparation"
        assert [(row["code"], row["status"], row["evidence_count"]) for row in first["items"]] == [
            ("world", "missing", 0),
            ("calendar_package", "missing", 0),
            ("population", "missing", 0),
            ("health", "optional", 0),
            ("official_ranking", "missing", 0),
            ("working_draft", "saved", 0),
        ]
        code, draft = _draft(server, rid, bid)
        assert code == 200, draft
        assert draft["status"] == "clean"
        assert draft["draft_version"] == first["draft_version"]
        code, listing = _request("GET", server.base_url + "/run-containers")
        assert code == 200, listing
        assert _get(server, rid, bid) == (200, first)
        assert _request("GET", server.base_url + "/run-containers") == (200, listing)
        assert _get(server, rid, "unknown-branch")[0] == 404
    with ApiServer(database_url=database) as server:
        assert _get(server, rid, bid) == (200, first)



def test_real_http_confirmed_create_is_recoverable_by_inventory_without_duplicate(tmp_path):
    """A caller may lose a 201 reply: a fresh read finds the durable Run by name.

    This intentionally discards the original response as a client would; it
    does not simulate a transport fault or claim full idempotency-key semantics.
    """
    database = f"sqlite:///{tmp_path / 'create-reconcile.db'}"
    requested_name = "Uncertain response Run"
    similar_name = "Uncertain response Run other"
    with ApiServer(database_url=database) as server:
        code, committed = _request(
            "POST", server.base_url + "/run-containers",
            {"display_name": requested_name},
        )
        assert code == 201, committed
        # The client uses no ID from the first response for reconciliation.
        code, similar = _request(
            "POST", server.base_url + "/run-containers",
            {"display_name": similar_name},
        )
        assert code == 201, similar

        code, inventory = _request("GET", server.base_url + "/run-containers")
        assert code == 200, inventory
        matches = [
            run for run in inventory["run_containers"]
            if run["display_name"] == requested_name
        ]
        assert len(matches) == 1
        resolved = matches[0]
        assert resolved["run_id"] == committed["run_id"]
        assert resolved["storage_kind"] == "custom_local"
        assert resolved["read_only"] is False
        assert similar["run_id"] != resolved["run_id"]
        assert len(inventory["run_containers"]) == 2

        rid, bid = resolved["run_id"], resolved["viewer_branch_id"]
        code, before_readiness = _get(server, rid, bid)
        assert code == 200, before_readiness
        assert before_readiness["phase"] == "preparation"
        assert before_readiness["saved_published_ranking_count"] == 0
        code, before_draft = _draft(server, rid, bid)
        assert code == 200 and before_draft["status"] == "clean"
        code, branches = _request(
            "GET", server.base_url + "/run-branches?" + urlencode({"run_id": rid}),
        )
        assert code == 200 and len(branches["run_branches"]) == 1
        assert branches["run_branches"][0]["saved_head_revision_id"] == before_readiness["saved_revision_id"]

        # Repeating even a trimmed equivalent name must fail atomically,
        # without changing the original calendar/HEAD/draft or making a third Run.
        code, conflict = _request(
            "POST", server.base_url + "/run-containers",
            {"display_name": "  " + requested_name + "  "},
        )
        assert code == 409, conflict
        assert conflict["detail"]["code"] == "run_display_name_conflict"
        assert _request("GET", server.base_url + "/run-containers") == (200, inventory)
        assert _get(server, rid, bid) == (200, before_readiness)
        assert _draft(server, rid, bid) == (200, before_draft)
    with ApiServer(database_url=database) as server:
        assert _request("GET", server.base_url + "/run-containers") == (200, inventory)
        assert _get(server, rid, bid) == (200, before_readiness)
        assert _draft(server, rid, bid) == (200, before_draft)

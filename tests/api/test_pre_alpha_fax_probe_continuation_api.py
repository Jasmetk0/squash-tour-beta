"""Real copied-FAX probe exact continuation, audit fences and SQLite restart."""
from pathlib import Path

import pytest

from beta_engine.domain.run_packages import canonical_hash
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.support.fax_reference import compute_source_tree_hash, copy_reference_source

pytestmark = pytest.mark.pr_critical


def test_fax_probe_continues_original_parent_and_preserves_audit_after_restart(tmp_path):
    source = copy_reference_source(
        repository_root=Path(__file__).resolve().parents[2],
        destination=tmp_path / "world-packages/official_fax_world",
    )
    path = tmp_path / "probe.db"
    database_url = f"sqlite:///{path}"
    points_path = tmp_path / "category-points.json"

    def api_server():
        server = ApiServer(database_url=database_url)
        server.app.state.world_packages_root = source.root.parent
        server.app.state.season_category_points_registry_path = points_path
        return server

    with api_server() as server:
        points_url = server.base_url + "/admin/seasons/2000/2001/category-points"
        code, points = _request("POST", points_url + "/initialize")
        assert code == 200, points
        for row in points["categories"]:
            if row["category"] not in {"GOLD", "PLATINUM"}:
                continue
            # Explicit disposable fixture awards; no new FAX sporting decision.
            table = {**row["ranking_points_table"], **{stage: 0 for stage in (
                "qualification_winner", "qualification_final",
                "qualification_semifinal", "qualification_round",
            )}}
            assert _request("PUT", points_url + "/" + row["category"], {"ranking_points_table": table})[0] == 200
        reference_url = server.base_url + "/run-containers/pre-alpha/fax-reference"
        request = {"display_name": "Real resumable copied FAX", "world_package_id": "official_fax_world", "target_pool_size": 1000}
        code, preview = _request("POST", reference_url + "/preview", request)
        assert code == 200 and preview["ready_to_materialize"], preview
        code, materialized = _request("POST", reference_url + "/materialize", {
            "request": request, "expected_preview_fingerprint": canonical_hash(preview),
        })
        assert code == 201, materialized
        assert materialized["acceptance_profile"]["initial_player_count"] == 1000
        assert materialized["acceptance_profile"]["world_tour_edition_count"] == 80
        run_id, branch_id = materialized["run_id"], materialized["branch_id"]
        root_path = f"/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
        root = server.base_url + root_path
        probe_path = root_path + "/pre-alpha/fax-long-acceptance/probe"
        request = {"command_id": "exact-probe", "operator_label": "Admin", "audit_reason": "Continue the same copied reference through its real checkpoints."}
        code, first = _request("POST", server.base_url + probe_path, request)
        assert code == 201 and first["execution_status"] == "blocked", first
        assert first["checkpoint"] == "week_preparation_required"
        code, pending = _request("GET", root + "/full-simulation/pending")
        assert code == 200 and len(pending["operations"]) == 1, pending
        original = pending["operations"][0]["command"]
        assert original["expected_preview_fingerprint"] == first["full_simulation_preview_fingerprint"]
        before = _dump(path)
        code, retry = _request("POST", server.base_url + probe_path, request)
        assert code == 201, retry
        assert retry == first
        assert _request("GET", root + "/full-simulation/pending") == (200, pending)
        assert _dump(path) == before
        for field, changed in (("operator_label", "Different operator"), ("audit_reason", "Different reason")):
            code, denied = _request("POST", server.base_url + probe_path, {**request, field: changed})
            assert code == 409 and "different request" in denied["detail"]["message"], denied
            assert _dump(path) == before
        code, other = _request("POST", server.base_url + probe_path, {**request, "command_id": "another-probe"})
        assert code == 201 and other["checkpoint"] == "full_simulation_preview_unavailable", other
        assert _dump(path) == before
        saved_id = materialized["saved_revision_id"]
        saved = server.app.state.runtime.repository.get_branch_saved_revision(revision_id=saved_id)

    with api_server() as restarted:
        assert _request("POST", restarted.base_url + probe_path, request) == (201, first)
        assert _request("GET", restarted.base_url + root_path + "/full-simulation/pending") == (200, pending)
        repo = restarted.app.state.runtime.repository
        assert repo.get_branch_saved_revision(revision_id=saved_id) == saved
        assert repo.verify_branch_saved_revision_hash(revision_id=saved_id)
        assert _dump(path) == before
        controls = restarted.base_url + root_path + "/full-simulation"
        control = {
            "control_command_id": "explicit-pause", "target_command_id": request["command_id"],
            "action": "pause", "operator_label": "Admin", "audit_reason": "Explicit operator pause.",
        }
        code, paused = _request("POST", controls + "/control", control)
        assert code == 200, paused
        code, report = _request("POST", restarted.base_url + probe_path, request)
        assert code == 201 and report["checkpoint"] == "operator_paused", report
        paused_dump = _dump(path)
        assert _request("POST", restarted.base_url + probe_path, request) == (201, report)
        assert _dump(path) == paused_dump
        code, resumed = _request("POST", controls + "/control", {
            **control, "control_command_id": "explicit-resume", "action": "resume",
            "audit_reason": "Only an explicit operator control resumes a paused parent.",
        })
        assert code == 200, resumed
        assert _request("POST", restarted.base_url + probe_path, request) == (201, first)
        code, retargeted = _request("POST", controls + "/target", {
            "control_command_id": "explicit-retarget", "target_command_id": request["command_id"],
            "target_week": {"season_index": 0, "week": 2}, "operator_label": "Admin",
            "audit_reason": "An explicitly shortened parent is no longer the reference probe range.",
        })
        assert code == 200, retargeted
        retargeted_dump = _dump(path)
        code, denied = _request("POST", restarted.base_url + probe_path, request)
        assert code == 409 and "retargeted parent" in denied["detail"]["message"], denied
        assert _dump(path) == retargeted_dump
        assert repo.get_branch_saved_revision(revision_id=saved_id) == saved
    assert compute_source_tree_hash(source.root) == source.source_tree_hash

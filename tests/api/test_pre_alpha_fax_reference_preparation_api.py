"""Real copied 1,000-player/80-Edition HTTP/SQLite preparation, stopping at OPEN policy.

The explicit zero qualification awards are disposable test inputs, never FAX canon.
No service, generator, Entry AI, driver response or persistence boundary is mocked.
"""
from pathlib import Path

import pytest

from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.support.fax_reference import (
    FAX_REFERENCE_V1_SOURCE_TREE_HASH,
    compute_source_tree_hash,
    copy_reference_source,
)

pytestmark = pytest.mark.smoke


def _configured_server(database_url, source_root, points_path):
    server = ApiServer(database_url=database_url)
    server.app.state.world_packages_root = source_root
    server.app.state.season_category_points_registry_path = points_path
    return server


def test_real_fax_reference_prepares_entry_and_reopens_at_unresolved_policy(tmp_path):
    repository_root = Path(__file__).resolve().parents[2]
    built_in = repository_root / "config/world_packages/official_fax_world"
    assert compute_source_tree_hash(built_in) == FAX_REFERENCE_V1_SOURCE_TREE_HASH
    source = copy_reference_source(
        repository_root=repository_root,
        destination=tmp_path / "world-packages/official_fax_world",
    )
    source_root = source.root.parent
    points_path = tmp_path / "category-points.json"
    database_url = f"sqlite:///{tmp_path / 'fax-reference.db'}"
    with _configured_server(database_url, source_root, points_path) as server:
        points_url = server.base_url + "/admin/seasons/2000/2001/category-points"
        code, points = _request("POST", points_url + "/initialize")
        assert code == 200, points
        tables = {}
        for row in points["categories"]:
            if row["category"] not in {"GOLD", "PLATINUM"}:
                continue
            tables[row["category"]] = {
                **row["ranking_points_table"],
                **{stage: 0 for stage in (
                    "qualification_winner", "qualification_final",
                    "qualification_semifinal", "qualification_round",
                )},
            }
            code, updated = _request("PUT", points_url + "/" + row["category"], {
                "ranking_points_table": tables[row["category"]],
            })
            assert code == 200, updated

        reference_url = server.base_url + "/run-containers/pre-alpha/fax-reference"
        request = {
            "display_name": "Disposable FAX reference integration",
            "world_package_id": "official_fax_world", "target_pool_size": 1000,
            "seed": 200001,
        }
        code, preview = _request("POST", reference_url + "/preview", request)
        assert code == 200 and preview["ready_to_materialize"], preview
        assert preview["world_tour_edition_count"] == 80
        assert preview["incomplete_points_event_ids"] == []
        # A changed authored award invalidates the reviewed source before ANY Run exists.
        changed_table = {**tables["PLATINUM"], "champion": 2501}
        assert _request("PUT", points_url + "/PLATINUM", {"ranking_points_table": changed_table})[0] == 200
        code, stale = _request("POST", reference_url + "/materialize", {
            "request": request, "expected_preview_fingerprint": canonical_hash(preview),
        })
        assert code == 409 and "changed since review" in stale["detail"]["message"], stale
        repo = server.app.state.runtime.repository
        assert repo.list_run_containers() == []

        code, preview = _request("POST", reference_url + "/preview", request)
        assert code == 200, preview
        code, materialized = _request("POST", reference_url + "/materialize", {
            "request": request, "expected_preview_fingerprint": canonical_hash(preview),
        })
        assert code == 201, materialized
        profile = materialized["acceptance_profile"]
        assert profile["ready_for_long_acceptance"]
        assert profile["initial_player_count"] == 1000
        assert profile["world_tour_edition_count"] == 80
        assert profile["timeline_season_count"] == 50
        run_id, branch_id = materialized["run_id"], materialized["branch_id"]
        root = server.base_url + f"/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
        pre_alpha = root + "/pre-alpha"
        saved_id = materialized["saved_revision_id"]
        saved = repo.get_branch_saved_revision(revision_id=saved_id)
        world = load_saved_initial_world(saved.payload, run_id=run_id, branch_id=branch_id)
        player_ids = tuple(player.player_id for player in world.players)
        assert len(set(player_ids)) == len(player_ids) == 1000
        assert repo.verify_branch_saved_revision_hash(revision_id=saved_id)
        # Changing LIVE global input cannot retroactively alter the copied Saved source.
        assert _request("PUT", points_url + "/PLATINUM", {"ranking_points_table": {"champion": 99999}})[0] == 200
        assert _request("GET", pre_alpha + "/fax-acceptance-profile") == (200, profile)

        # Deliberately damaged disposable contexts must never be advertised ready.
        from sqlalchemy import select

        from beta_engine.infrastructure.db.models import (
            BranchWorkingDraftModel,
            RunBranchModel,
        )
        from tests.api.test_player_generation_calendar_gate import _dump
        for damage in ("read_only", "dirty", "stale"):
            with repo._session_factory.begin() as session:
                branch = session.get(RunBranchModel, branch_id)
                draft = session.scalar(select(BranchWorkingDraftModel).where(BranchWorkingDraftModel.branch_id == branch_id))
                if damage == "read_only": branch.read_only = True
                elif damage == "dirty": draft.status = "dirty"
                else: draft.base_revision_id = "stale-reference"
            before = _dump(tmp_path / "fax-reference.db")
            code, blocked = _request("GET", pre_alpha + "/fax-acceptance-profile")
            assert code == 200 and not blocked["ready_for_long_acceptance"], blocked
            assert blocked["initial_player_count"] == 1000 and blocked["world_tour_edition_count"] == 80
            expected = "FAX_ACCEPTANCE_BRANCH_READ_ONLY" if damage == "read_only" else "FAX_ACCEPTANCE_SAVED_DRAFT_REQUIRED"
            assert expected in {issue["code"] for issue in blocked["issues"]}
            code, denied = _request("POST", pre_alpha + "/fax-long-acceptance/probe", {
                "command_id": "blocked-context", "operator_label": "Admin", "audit_reason": "Reject unsaved or protected input.",
            })
            assert code == 409 and expected in denied["detail"]["message"], denied
            assert _dump(tmp_path / "fax-reference.db") == before
            with repo._session_factory.begin() as session:
                session.get(RunBranchModel, branch_id).read_only = False
                draft = session.scalar(select(BranchWorkingDraftModel).where(BranchWorkingDraftModel.branch_id == branch_id))
                draft.status = "clean"
                draft.base_revision_id = saved_id
            assert _request("GET", pre_alpha + "/fax-acceptance-profile") == (200, profile)

        from tests.api.fax_saved_input_proof import verify_saved_inputs
        verify_saved_inputs(repo, run_id, branch_id, saved_id, profile, tmp_path / "fax-reference.db", pre_alpha)

        ranking_url = pre_alpha + "/fax-current-week/ranking-snapshots"
        code, ranking = _request("GET", ranking_url + "/preview")
        assert code == 200, ranking
        assert len(ranking["event_ids"]) == 2
        ranking_command = {"command_id": "fax-ranking-snapshots", "expected_preview_fingerprint": ranking["preview_fingerprint"]}
        code, adopted = _request("POST", ranking_url + "/apply", ranking_command)
        assert code == 201 and adopted["all_ranking_snapshots_ready"], adopted
        code, retry = _request("POST", ranking_url + "/apply", ranking_command)
        assert code == 201 and retry["exact_retry_event_ids"] == ranking["event_ids"], retry

        entry_url = pre_alpha + "/fax-current-entry"
        code, entry = _request("GET", entry_url + "/preview")
        assert code == 200 and not entry["persisted"], entry
        assert entry["event_ids"] == ranking["event_ids"]
        assert entry["decision_count"] > 0
        entry_command = {"command_id": "fax-entry-slot", "expected_preview_fingerprint": entry["preview_fingerprint"]}
        code, entry_result = _request("POST", entry_url + "/apply", entry_command)
        assert code == 201 and entry_result["adoption"] == "committed", entry_result
        assert entry_result["validation_required"]
        assert entry_result["validation_policy_status"] == "automatic_policy_unresolved"
        code, gate = _request("GET", pre_alpha + "/fax-entry-validation-policy-gate")
        assert code == 200, gate
        assert gate["current_entry_slot_frozen"]
        assert gate["current_entry_slot_fingerprint"] == entry["slot_fingerprint"]
        assert gate["current_entry_decision_count"] == entry["decision_count"]
        assert gate["current_blocker_code"] == "application_validation_policy_unresolved"
        assert not gate["current_entry_validation_resolved"]
        code, probe = _request("POST", pre_alpha + "/fax-long-acceptance/probe", {
            "command_id": "fax-real-probe", "operator_label": "Admin",
            "audit_reason": "Find the real OPEN policy boundary without fabricating a validation.",
        })
        assert code == 201, probe
        assert probe["execution_status"] == "blocked"
        assert probe["checkpoint"] == "entry_process_required"
        assert probe["release_policy_blocker"] == "application_validation_policy_unresolved"
        assert probe["release_policy_gate_fingerprint"] == gate["gate_fingerprint"]
        assert probe["completed_season_count"] == 0
        assert probe["execution_fingerprint"] is not None
        assert repo.get_branch_saved_revision(revision_id=saved_id) == saved

    # A fresh server, engine and SQLite connection must report the SAME real authority.
    with _configured_server(database_url, source_root, points_path) as restarted:
        repo = restarted.app.state.runtime.repository
        pre_alpha = restarted.base_url + f"/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation/pre-alpha"
        assert _request("GET", pre_alpha + "/fax-acceptance-profile") == (200, profile)
        assert _request("GET", pre_alpha + "/fax-entry-validation-policy-gate") == (200, gate)
        assert repo.get_branch_saved_revision(revision_id=saved_id) == saved
        assert repo.verify_branch_saved_revision_hash(revision_id=saved_id)
        reopened = load_saved_initial_world(saved.payload, run_id=run_id, branch_id=branch_id)
        assert tuple(player.player_id for player in reopened.players) == player_ids
    assert compute_source_tree_hash(source.root) == FAX_REFERENCE_V1_SOURCE_TREE_HASH
    assert compute_source_tree_hash(built_in) == FAX_REFERENCE_V1_SOURCE_TREE_HASH

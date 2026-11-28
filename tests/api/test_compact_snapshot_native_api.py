"""Compact snapshot on a real native Tour Run: supported source, blocked native fork.

The fork's Saved root carries only its runtime aggregate plus *fingerprints* of
the source InitialWorld/baseline; the InitialWorld itself and the Run Package
state live in the source Branch's Saved revision. The Compact scope rejects it
explicitly instead of packaging that foreign revision.
"""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_branch_archive import CompactSnapshot, decode, encode
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_tour_flow import setup
from tests.api.test_compact_snapshot_api import compact_preview, compact_scope
from tests.api.test_native_fork_public_continuation import Tour, fork
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_run_branch_archive_api import archive_root, export, raw_request
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def test_native_tour_source_is_compact_and_native_fork_is_a_named_blocker(tmp_path):
    source = tmp_path / "native-compact.db"
    clock = RunCalendar(7, 1, 2030, 3)
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        repo, _ = setup(server, clock, 4)
        signed = sign_prospects(server, repo, clock)
        created = fork(server, signed["revision_id"])
        bid = created["branch_id"]
        tour = Tour(server, bid)
        tour.execute("transition", "compact-fork-birth")
        saved = tour.save()
        before = _dump(source)

        # Supported: the source Tour Branch, with calendar and Package state.
        preview, command = compact_preview(server, "run", "branch")
        assert preview["selected_head_revision_id"] == signed["revision_id"]
        assert {"initial_world", "run_package_state", "calendar_tour_authority"} <= set(
            preview["included_components"]
        ), preview["included_components"]
        assert preview["run_calendar"] == clock.to_metadata()
        assert preview["package_provenance"]["source_package_ids"]
        status, raw = raw_request(archive_root(server) + "/export", encode(command))
        assert status == 200, raw[:2000]
        assert CompactSnapshot(raw).head.revision_id == signed["revision_id"]

        # Blocked: the native fork. Concrete dependency, as Saved by production.
        fork_payload = repo.get_branch_saved_revision(revision_id=saved["revision_id"]).payload
        content = fork_payload["content"]
        assert {"native_fork_baseline", "native_fork_runtime"} <= content.keys()
        assert "initial_world" not in content and "run_package_state" not in content
        runtime = content["native_fork_runtime"]["state"]
        assert runtime["lifecycle"]["source_initial_world_fingerprint"]
        status, error = _request("POST", archive_root(server) + "/export/preview",
                                 compact_scope("run", bid))
        assert status == 409, error
        assert error["detail"]["code"] == "compact_foreign_source_dependency"
        # The existing Branch archive still carries it with its source history.
        _, branch_preview = export(server, "run", bid)
        assert {b["role"] for b in branch_preview["branches"]} == {"selected", "dependency"}
        assert _dump(source) == before
    assert decode(raw)["selected_branch_id"] == "branch"

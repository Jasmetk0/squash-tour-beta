"""Real native HTTP/SQLite review; unsupported historical re-authority stays blocked.

This is evidence of the remaining fork gap, not successful native Branch support.
"""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_opening_knockout_flow import base
from tests.api.test_calendar_population_sporting_checkpoint import restore
from tests.api.test_calendar_tour_flow import (
    command,
    execute,
    inspect,
    save_tour,
    setup,
)
from tests.api.test_native_prospect_source_epochs_http import (
    _review_new_year,
    _source_url,
)
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_branch_review_api import confirmed, preview
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def saved_bytes(repo, revision_id):
    with repo._session_factory() as session:
        row = session.get(BranchSavedRevisionModel, revision_id)
        return row.payload_json, row.change_summary_json, row.content_hash


def test_native_matched_birth_and_epoch_reviews_preserve_actual_saved_history(tmp_path):
    path = tmp_path / "native-review.db"
    database = f"sqlite:///{path}"
    with ApiServer(database_url=database) as server:
        repo, initial = setup(server, RunCalendar(7, 1, 2030, 3), 4)
        sign_prospects(server, repo, RunCalendar(7, 1, 2030, 3))
        initial = inspect(server)["saved_head_revision_id"]
        snapshots = {}
        immutable_bytes = {}

        def check(revision_id, expected_codes):
            before = _dump(path)
            source, review = preview(server, "run", "branch", revision_id)
            assert not review["can_create"]
            assert review["saved_match_count"] >= 3
            assert review["source_revision_branch_id"] == "branch"
            assert expected_codes <= {b["code"] for b in review["blockers"]}
            assert _dump(path) == before
            assert (
                _request(
                    "POST",
                    server.base_url + "/run-containers/run/branches",
                    confirmed(source, review, "blocked-" + revision_id),
                )[0]
                == 409
            )
            assert _dump(path) == before
            current = repo.get_branch_saved_revision(revision_id=revision_id)
            snapshots.setdefault(revision_id, current)
            immutable_bytes.setdefault(revision_id, saved_bytes(repo, revision_id))
            assert current == snapshots[revision_id]
            assert saved_bytes(repo, revision_id) == immutable_bytes[revision_id]
            return review

        check(initial, {"unsupported_fork_components"})
        execute(
            server, command(inspect(server), "transition", name="admit-before-review")
        )
        born = save_tour(server)["revision_id"]
        check(
            born,
            {
                "native_birth_fork_authority_required",
                "native_health_fork_authority_required",
            },
        )
        url, request, review = _review_new_year(server, season=1)
        status, materialized = _request(
            "POST",
            url + "/materialize",
            {
                "request": request,
                "expected_saved_head": review["saved_head_revision_id"],
                "expected_review_fingerprint": review["review_fingerprint"],
                "explicit_confirmation": True,
                "audit_label": "Admin",
                "audit_reason": "Real future source for Branch boundary validation",
            },
        )
        assert status == 201, materialized
        status, source_review = _request("GET", _source_url(server) + "/preview")
        assert status == 200 and source_review["can_save"], source_review
        status, saved = _request(
            "POST",
            _source_url(server),
            {
                "expected_draft_version": source_review["draft_version"],
                "expected_run_prospect_source_fingerprint": source_review[
                    "run_prospect_source_fingerprint"
                ],
                "expected_saved_head_revision_id": source_review[
                    "saved_head_revision_id"
                ],
            },
        )
        assert status == 201, saved
        epoch = saved["saved_revision"]["revision_id"]
        assert (
            check(epoch, {"native_birth_fork_authority_required"})[
                "prospect_source_schema"
            ]
            == "run_prospect_source_epochs.v2"
        )
        # Earlier source revisions remain reachable and have exactly their old bytes.
        check(initial, {"unsupported_fork_components"})
        for revision_id, snapshot in snapshots.items():
            assert repo.get_branch_saved_revision(revision_id=revision_id) == snapshot
            assert saved_bytes(repo, revision_id) == immutable_bytes[revision_id]
    with ApiServer(database_url=database) as restarted:
        repo = restarted.app.state.runtime.repository
        for revision_id, snapshot in snapshots.items():
            assert repo.get_branch_saved_revision(revision_id=revision_id) == snapshot
            assert saved_bytes(repo, revision_id) == immutable_bytes[revision_id]
            before = _dump(path)
            assert not preview(restarted, "run", "branch", revision_id)[1]["can_create"]
            assert _dump(path) == before
        # Original genuine match remains replayable after source epoch changes.
        code, replay = _request("GET", base(restarted) + "/world-owner/replay")
        assert code == 200 and replay["exact_replay"], replay
        restore(restarted, initial)
        assert inspect(restarted)["state"]["week"]["week"] == 2
        restore(restarted, epoch)
        assert inspect(restarted)["state"]["week"]["week"] == 3

"""Guard the one-source closure-facts reuse in the actual HTTP/SQLite Save.

A successful closure Save MUST reuse the already authenticated _review facts,
but the independent post-write Saved revision verification remains mandatory.
This test checks the production API, persisted canonical marker, and restart.
"""
import inspect as pyinspect

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.application import native_full_simulation_closure as closure_app
from tests.api.test_calendar_tour_flow import inspect, save_tour, setup
from tests.api.test_native_full_simulation_tasks import reviewed, resume, scope, start
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def test_final_closure_save_reuses_verified_review_facts_without_second_direct_fold(
    tmp_path, monkeypatch
):
    db = f"sqlite:///{tmp_path / 'review-facts-reuse.sqlite'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, RunCalendar(3, 2, 2040, 1), count=4)
        command = reviewed(server, name="native-reviewed-facts")
        task = start(server, command)
        assert task["current_week"] == {"season_index": 0, "week": 3}
        save_tour(server)
        task = resume(server, task, "review-facts-last-week-saved")
        assert task["checkpoint"] == "native_final_closure_review_required"
        endpoint = scope(server) + "/native/native-reviewed-facts/closure"
        status, review = _request("GET", endpoint)
        assert status == 200, review

        approval = {
            "request_id": "approve-review-facts",
            "review_fingerprint": review["review_fingerprint"],
            "operator_label": "Admin",
            "audit_reason": "Review exact source-derived final facts",
            "explicit_confirmation": True,
        }
        status, approved = _request("POST", endpoint + "/approve", approval)
        assert status == 200, approved

        original = closure_app.closure_facts
        direct_callers = []

        def observed_facts(*args, **kwargs):
            # Trace only the direct production caller, not nested helper calls:
            # _review must compute facts; save must not compute them twice.
            caller = pyinspect.currentframe().f_back.f_code.co_name
            direct_callers.append(caller)
            return original(*args, **kwargs)

        monkeypatch.setattr(closure_app, "closure_facts", observed_facts)
        request = {**approval, "request_id": "save-reviewed-facts"}
        status, receipt = _request("POST", endpoint + "/save", request)
        assert status == 201, receipt
        assert direct_callers.count("_review") == 1, direct_callers
        assert "save" not in direct_callers, direct_callers
        # This must remain an actual post-write independent integrity check.
        assert "verify_saved_native_closure" in direct_callers, direct_callers

        source = repo.get_branch_saved_revision(revision_id=receipt["revision_id"])
        marker = source.payload["run"][closure_app.KEY]["branch"]
        review_facts = {
            key: value for key, value in review.items()
            if key not in {
                "parent_command_id",
                "expected_position_fingerprint",
                "review_fingerprint",
            }
        }
        for key, value in review_facts.items():
            assert marker[key] == value
        assert marker["fingerprint"] == canonical_hash(
            {key: value for key, value in marker.items() if key != "fingerprint"}
        )
        assert marker["approval"] == approval
        assert marker["save"] == request

        # Idempotent genuine Save with unchanged head and original authenticated
        # sporting result; never invent a second closure.
        assert _request("POST", endpoint + "/save", request) == (201, receipt)
        assert repo.get_branch_saved_revision(
            revision_id=receipt["revision_id"]
        ).content_hash == source.content_hash
        task_id = task["task_id"]

    with ApiServer(database_url=db) as reopened:
        status, restarted = _request(
            "GET", scope(reopened) + "/tasks/" + task_id
        )
        assert status == 200, restarted
        assert inspect(reopened)["saved"]

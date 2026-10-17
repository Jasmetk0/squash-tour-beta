"""Live FastAPI/SQLite: reviewed points become Saved only after explicit Save.

No hand-constructed Saved revision, artificial result, fake publication or W61
calendar conversion. Old signed match history must remain byte-identical.
"""
from __future__ import annotations

import json

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.models import CalendarStandaloneMatchModel
from tests.api.test_calendar_standalone_match_flow import prepare_saved_world
from tests.api.test_calendar_opening_knockout_flow import base
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def saved_bracket(server, clock):
    repository, population_head = prepare_saved_world(server, clock)
    _, inspected = _request("GET", base(server))
    command = {
        "command_id": "scoring-source-play", "match_id": "scoring-source",
        "expected_saved_head": population_head,
        "expected_initial_world_fingerprint": inspected["initial_world_fingerprint"],
        "entrant_ids": inspected["player_ids"],
        "seed": 572, "operator_label": "Admin",
        "audit_reason": "Play real knockout before scoring",
    }
    status, played = _request("POST", base(server) + "/simulate", command)
    assert status == 201, played
    _, preview = _request("GET", base(server) + "/save/preview")
    status, saved = _request("POST", base(server) + "/save", {
        "expected_draft_version": preview["draft_version"],
        "expected_calendar_match_fingerprint": played["fingerprint"],
    })
    assert status == 201, saved
    return repository, population_head, saved["saved_revision"]["revision_id"], played


def policy(w):
    return {
        "schema_version": "calendar_knockout_point_policy.v1",
        "source_kind": "admin_explicit_reviewed",
        "category_label": "Opening experimental ranking points",
        "champion": 100, "finalist": 60, "semifinal": 30,
        "validity_weeks": w,
    }


def proposal(saved_head, source_fp, w):
    return {
        "expected_saved_head": saved_head,
        "expected_knockout_fingerprint": source_fp,
        "policy": policy(w),
        "operator_label": "Admin",
        "audit_reason": "Review preparation, not Official ranking publication",
    }


@pytest.mark.parametrize("clock", [
    RunCalendar(52, 1, 2030, 3),
    RunCalendar(80, 37, 2100, 3),
])
def test_review_and_apply_real_knockout_awards_save_restart_and_restore(tmp_path, clock):
    url = f"sqlite:///{tmp_path / 'scored-knockout.db'}"
    with ApiServer(database_url=url) as server:
        repository, population_head, bracket_head, played = saved_bracket(server, clock)
        original = repository.get_branch_saved_revision(revision_id=bracket_head)
        assert original is not None
        old_hash, old_content = original.content_hash, original.payload
        p = proposal(bracket_head, played["fingerprint"], clock.weeks_per_year)
        before = repository.get_branch_saved_revision(revision_id=bracket_head)
        status, reviewed = _request("POST", base(server) + "/awards/review", p)
        assert status == 200, reviewed
        assert reviewed["publication_status"] == "prepared_not_official"
        assert reviewed["first_publication_week"]["week"] == 2
        assert reviewed["first_publication_week"]["calendar"] == clock.to_metadata()
        assert sorted(a["main_points"] for a in reviewed["awards"]) == [30, 30, 60, 100]
        assert sorted(a["reached_stage"] for a in reviewed["awards"]) == [
            "champion", "finalist", "semifinal", "semifinal",
        ]
        assert repository.get_branch_saved_revision(revision_id=bracket_head).content_hash == old_hash
        command = {
            "command_id": "prepare-scored-awards",
            "proposal": p,
            "expected_preview_fingerprint": reviewed["preview_fingerprint"],
            "explicit_confirmation": True,
        }
        status, result = _request("POST", base(server) + "/awards/apply", {
            **command, "explicit_confirmation": False,
        })
        assert status == 422
        assert _request("POST", base(server) + "/awards/apply", {
            **command, "expected_preview_fingerprint": "0" * 64,
        })[0] == 409
        status, applied = _request("POST", base(server) + "/awards/apply", command)
        assert status == 201, applied
        scored = applied["prepared"]
        assert scored["schema_version"] == "calendar_scored_opening_knockout.v1"
        assert scored["knockout"] == played["knockout"]
        assert scored["policy"] == p["policy"]
        assert sorted(x["main_points"] for x in scored["awards"]) == [30, 30, 60, 100]
        assert _request("POST", base(server) + "/awards/apply", command) == (201, applied)
        assert _request("POST", base(server) + "/awards/apply", {
            **command, "command_id": "other-command",
        })[0] == 409
        status, live = _request("GET", base(server))
        assert status == 200 and not live["saved"]
        assert live["prepared_points"]["publication_status"] == "prepared_not_official"
        assert live["knockout"] == played["knockout"]
        assert live["knockout_fingerprint"] == applied["fingerprint"]
        status, replay = _request("GET", base(server) + "/scoring-source/replay")
        assert status == 200 and replay["exact_replay"]
        assert replay["fingerprint"] == applied["fingerprint"]
        assert _request("POST", base(server) + "/simulate", {
            "command_id": "try-again", "match_id": "other",
            "expected_saved_head": bracket_head,
            "expected_initial_world_fingerprint": played["knockout"]["source_initial_world_fingerprint"],
            "entrant_ids": played["knockout"]["entrant_ids"], "seed": 5,
            "operator_label": "Admin", "audit_reason": "Forbidden duplicate",
        })[0] == 409
        assert repository.get_branch_saved_revision(revision_id=bracket_head).content_hash == old_hash
        status, preview = _request("GET", base(server) + "/save/preview")
        assert status == 200 and preview["can_save"]
        assert preview["calendar_match_fingerprint"] == applied["fingerprint"]
        status, saved = _request("POST", base(server) + "/save", {
            "expected_draft_version": preview["draft_version"],
            "expected_calendar_match_fingerprint": applied["fingerprint"],
        })
        assert status == 201, saved
        awarded_head = saved["saved_revision"]["revision_id"]
        assert saved["saved_revision"]["payload"]["content"]["calendar_standalone_match"]["state"] == scored
        assert repository.verify_branch_saved_revision_hash(revision_id=awarded_head)
        assert repository.verify_branch_saved_revision_hash(revision_id=bracket_head)
        assert repository.get_branch_saved_revision(revision_id=bracket_head).content_hash == old_hash
        assert repository.get_branch_saved_revision(revision_id=bracket_head).payload == old_content
        assert _request("GET", base(server))[1]["saved"] is True
    with ApiServer(database_url=url) as restarted:
        status, view = _request("GET", base(restarted))
        assert status == 200 and view["saved"] and view["prepared_points"]
        assert view["knockout_fingerprint"] == applied["fingerprint"]
        assert _request("GET", base(restarted) + "/scoring-source/replay")[1]["exact_replay"]
        repo = restarted.app.state.runtime.repository
        restore_url = restarted.base_url + (
            f"/run-containers/run/branches/branch/saved-revisions/{bracket_head}/restore"
        )
        status, review = _request("GET", restore_url + "-preflight")
        assert status == 200 and review["can_restore"], review
        status, restored = _request("POST", restore_url, {
            "expected_head_saved_revision_id": awarded_head,
            "expected_draft_version": review["draft_version"],
            "expected_current_viewer_branch_id": "branch",
            "explicit_confirmation": True,
        })
        assert status == 201, restored
        status, after = _request("GET", base(restarted))
        assert status == 200 and after["saved"] and after["prepared_points"] is None
        assert after["knockout_fingerprint"] == played["fingerprint"]
        assert repo.verify_branch_saved_revision_hash(revision_id=awarded_head)
        assert repo.verify_branch_saved_revision_hash(revision_id=bracket_head)


def test_prepared_awards_reject_foreign_source_bad_policy_and_tamper(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'awards-tamper.db'}") as server:
        repository, _, saved_head, played = saved_bracket(server, RunCalendar(52, 1, 2030, 3))
        p = proposal(saved_head, played["fingerprint"], 52)
        endpoint = base(server) + "/awards/review"
        assert _request("POST", endpoint, {**p, "expected_saved_head": "foreign"})[0] == 409
        assert _request("POST", endpoint, {**p, "expected_knockout_fingerprint": "0"*64})[0] == 409
        assert _request("POST", endpoint, {**p, "policy": {**p["policy"], "validity_weeks": 61}})[0] == 409
        assert _request("POST", endpoint, {**p, "policy": {**p["policy"], "finalist": 101}})[0] == 422
        assert _request("POST", endpoint, {**p, "policy": {**p["policy"], "champion": -1}})[0] == 422
        status, reviewed = _request("POST", endpoint, p)
        assert status == 200, reviewed
        status, applied = _request("POST", base(server) + "/awards/apply", {
            "command_id": "tamper-score", "proposal": p,
            "expected_preview_fingerprint": reviewed["preview_fingerprint"],
            "explicit_confirmation": True,
        })
        assert status == 201, applied
        with repository._session_factory.begin() as session:
            row = session.get(CalendarStandaloneMatchModel, ("run", "branch", "scoring-source"))
            assert row is not None
            raw = json.loads(row.payload_json)
            raw["awards"][0]["main_points"] += 1
            row.payload_json = json.dumps(raw)
        assert _request("GET", base(server))[0] == 409
        assert _request("GET", base(server) + "/save/preview")[0] == 409
        assert repository.verify_branch_saved_revision_hash(revision_id=saved_head)

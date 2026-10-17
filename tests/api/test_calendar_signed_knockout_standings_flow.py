"""Production FastAPI/SQLite: historical-as-of real Signed W52/W80 points."""
from __future__ import annotations

import json

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.models import CalendarStandaloneMatchModel
from tests.api.test_calendar_knockout_awards_flow import (
    saved_bracket, proposal,
)
from tests.api.test_calendar_opening_knockout_flow import base
from tests.api.test_calendar_standalone_match_flow import prepare_saved_world
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def make_signed_scores(server, clock):
    repo, original_head, bracket_head, played = saved_bracket(server, clock)
    p = proposal(bracket_head, played["fingerprint"], clock.weeks_per_year)
    status, reviewed = _request("POST", base(server) + "/awards/review", p)
    assert status == 200, reviewed
    status, applied = _request("POST", base(server) + "/awards/apply", {
        "command_id": "signed-standings-award",
        "proposal": p,
        "expected_preview_fingerprint": reviewed["preview_fingerprint"],
        "explicit_confirmation": True,
    })
    assert status == 201, applied
    _, preview = _request("GET", base(server) + "/save/preview")
    status, saved = _request("POST", base(server) + "/save", {
        "expected_draft_version": preview["draft_version"],
        "expected_calendar_match_fingerprint": applied["fingerprint"],
    })
    assert status == 201, saved
    return repo, original_head, bracket_head, saved["saved_revision"]["revision_id"], applied


def standings(server, head, season=0, week=2):
    from urllib.parse import quote

    return _request(
        "GET", base(server) + "/standings?"
        + "expected_saved_head=" + quote(head, safe="")
        + f"&season_index={season}&week={week}",
    )


@pytest.mark.parametrize("clock", [
    RunCalendar(52, 1, 2030, 3),
    RunCalendar(80, 37, 2100, 3),
])
def test_w52_w80_signed_as_of_standings_replay_expiry_restart_restore(tmp_path, clock):
    url = f"sqlite:///{tmp_path / 'signed-standings.sqlite'}"
    with ApiServer(database_url=url) as server:
        repository, initial, old_bracket, head, scored = make_signed_scores(server, clock)
        status, w2 = standings(server, head)
        assert status == 200, w2
        assert w2["schema_version"] == "calendar_signed_knockout_standings.v1"
        assert w2["publication_status"] == "not_official_no_week_transition"
        assert not w2["official_ready"]
        assert len(w2["blockers"]) == 3
        assert w2["saved_head_revision_id"] == head
        assert w2["points_in_period"]
        assert w2["scored_evidence_fingerprint"] == scored["fingerprint"]
        assert w2["as_of"]["calendar"] == clock.to_metadata()
        assert w2["expiration_week_exclusive"] == {"season_index": 1, "week": 2}
        rows = w2["rows"]
        assert len(rows) == 4
        assert [r["tournament_place"] for r in rows] == [1, 2, 3, 3]
        assert [r["points_rank"] for r in rows] == [1, 2, 3, 3]
        assert [r["as_of_counted_points"] for r in rows] == [100, 60, 30, 30]
        assert [r["awarded_main_points"] for r in rows] == [100, 60, 30, 30]
        assert all(r["player_name"] and r["nationality"] for r in rows)
        body = {key: v for key, v in w2.items() if key != "fingerprint"}
        assert canonical_hash(body) == w2["fingerprint"]
        assert standings(server, head) == (200, w2)

        assert standings(server, head, 0, 1)[0] == 409
        assert standings(server, old_bracket)[0] == 409
        assert standings(server, "untrusted")[0] == 409
        assert standings(server, head, 5, 2)[0] == 409
        assert standings(server, head, 0, 0)[0] == 409
        assert standings(server, head, 0, clock.weeks_per_year)[1]["points_in_period"]
        assert standings(server, head, 1, 1)[1]["points_in_period"]
        status, expired = standings(server, head, 1, 2)
        assert status == 200, expired
        assert expired["points_in_period"] is False
        assert [r["as_of_counted_points"] for r in expired["rows"]] == [0, 0, 0, 0]
        assert [r["points_rank"] for r in expired["rows"]] == [None] * 4
        assert [r["awarded_main_points"] for r in expired["rows"]] == [100, 60, 30, 30]
        assert expired["fingerprint"] != w2["fingerprint"]
        assert repository.verify_branch_saved_revision_hash(revision_id=head)
        assert repository.verify_branch_saved_revision_hash(revision_id=old_bracket)

    with ApiServer(database_url=url) as restarted:
        status, after_restart = standings(restarted, head)
        assert status == 200 and after_restart == w2
        # Restoring the genuine earlier Signed revision removes these prepared
        # points, but never re-signs or mutates any historical content/hash.
        restore = (restarted.base_url
                   + f"/run-containers/run/branches/branch/saved-revisions/{old_bracket}/restore")
        status, preflight = _request("GET", restore + "-preflight")
        assert status == 200 and preflight["can_restore"], preflight
        status, applied = _request("POST", restore, {
            "expected_head_saved_revision_id": head,
            "expected_draft_version": preflight["draft_version"],
            "expected_current_viewer_branch_id": "branch",
            "explicit_confirmation": True,
        })
        assert status == 201, applied
        new_head = applied["saved_revision"]["revision_id"]
        assert standings(restarted, new_head)[0] == 409
        repo = restarted.app.state.runtime.repository
        for revision in (initial, old_bracket, head, new_head):
            assert repo.verify_branch_saved_revision_hash(revision_id=revision)


def test_signed_standings_reject_uncommitted_score_and_tamper(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'signed-source.sqlite'}") as server:
        repository, _, bracket_head, played = saved_bracket(
            server, RunCalendar(52, 1, 2030, 3),
        )
        assert standings(server, bracket_head)[0] == 409
        p = proposal(bracket_head, played["fingerprint"], 52)
        _, reviewed = _request("POST", base(server) + "/awards/review", p)
        status, applied = _request("POST", base(server) + "/awards/apply", {
            "command_id": "unsigned-points",
            "proposal": p, "expected_preview_fingerprint": reviewed["preview_fingerprint"],
            "explicit_confirmation": True,
        })
        assert status == 201, applied
        # A live, unapplied-to-Saved HEAD points row is not authority.
        assert standings(server, bracket_head)[0] == 409
        _, preview = _request("GET", base(server) + "/save/preview")
        _, saved = _request("POST", base(server) + "/save", {
            "expected_draft_version": preview["draft_version"],
            "expected_calendar_match_fingerprint": applied["fingerprint"],
        })
        head = saved["saved_revision"]["revision_id"]
        assert standings(server, head)[0] == 200
        with repository._session_factory.begin() as session:
            row = session.get(
                CalendarStandaloneMatchModel, ("run", "branch", "scoring-source"),
            )
            assert row is not None
            data = json.loads(row.payload_json)
            data["awards"][0]["main_points"] += 1
            row.payload_json = json.dumps(data)
        assert standings(server, head)[0] == 409
        assert repository.verify_branch_saved_revision_hash(revision_id=head)


def test_exclusive_expiration_can_be_outside_short_run_horizon(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'short-run.db'}") as server:
        _, _, _, head, _ = make_signed_scores(
            server, RunCalendar(52, 1, 2030, 1),
        )
        status, result = standings(server, head)
        assert status == 200, result
        assert result["expiration_week_exclusive"] == {
            "season_index": 1, "week": 2,
        }
        assert standings(server, head, 1, 1)[0] == 409


def test_forked_saved_population_preserves_lifecycle_source_and_scores(tmp_path):
    """A fork keeps the original lifecycle witness; never re-sign old history."""
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'forked-signed-score.sqlite'}") as server:
        repository, original_head = prepare_saved_world(
            server, RunCalendar(52, 1, 2030, 3),
        )
        status, fork = _request(
            "POST", server.base_url + "/run-containers/run/branches",
            {"source_branch_id": "branch",
             "source_saved_revision_id": original_head,
             "display_name": "Independently Scored Tour Branch"},
        )
        assert status == 201, fork
        new_branch = fork["branch_id"]
        target = (server.base_url + "/admin/runs/run/branches/"
                  + new_branch + "/authoritative-simulation/calendar-opening-knockout")
        status, inspected = _request("GET", target)
        assert status == 200, inspected
        ids = inspected["player_ids"]
        command = {
            "command_id": "fork-match",
            "match_id": "fork-bracket",
            "expected_saved_head": inspected["saved_head_revision_id"],
            "expected_initial_world_fingerprint": inspected["initial_world_fingerprint"],
            "entrant_ids": ids, "seed": 502,
            "operator_label": "Admin", "audit_reason": "Play a real forked calendar bracket",
        }
        status, played = _request("POST", target + "/simulate", command)
        assert status == 201, played
        _, preview = _request("GET", target + "/save/preview")
        status, first = _request("POST", target + "/save", {
            "expected_draft_version": preview["draft_version"],
            "expected_calendar_match_fingerprint": played["fingerprint"],
        })
        assert status == 201, first
        bracket_head = first["saved_revision"]["revision_id"]
        p = proposal(bracket_head, played["fingerprint"], 52)
        status, reviewed = _request("POST", target + "/awards/review", p)
        assert status == 200, reviewed
        status, applied = _request("POST", target + "/awards/apply", {
            "command_id": "fork-awards", "proposal": p,
            "expected_preview_fingerprint": reviewed["preview_fingerprint"],
            "explicit_confirmation": True,
        })
        assert status == 201, applied
        _, second_preview = _request("GET", target + "/save/preview")
        status, second = _request("POST", target + "/save", {
            "expected_draft_version": second_preview["draft_version"],
            "expected_calendar_match_fingerprint": applied["fingerprint"],
        })
        assert status == 201, second
        scored_head = second["saved_revision"]["revision_id"]
        from urllib.parse import quote
        status, standings_view = _request(
            "GET", target + "/standings?"
            + "expected_saved_head=" + quote(scored_head, safe="")
            + "&season_index=0&week=2",
        )
        assert status == 200, standings_view
        assert sorted(r["as_of_counted_points"] for r in standings_view["rows"]) == [30, 30, 60, 100]
        assert not standings_view["official_ready"]
        assert repository.verify_branch_saved_revision_hash(revision_id=original_head)
        assert repository.verify_branch_saved_revision_hash(revision_id=bracket_head)
        assert repository.verify_branch_saved_revision_hash(revision_id=scored_head)

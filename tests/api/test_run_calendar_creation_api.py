"""Real new-Run HTTP/SQLite calendar choices; no rehashed historical fixtures."""

from __future__ import annotations

from urllib.parse import urlencode

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_run_working_draft_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def _clock(*, offset=35, start=2030, count=3):
    return {"weeks_per_year": 52, "season_start_year_week": offset,
            "start_year": start, "season_count": count}


def _branches(server, run_id):
    status, listing = _request("GET", server.base_url + "/run-branches?" + urlencode({"run_id": run_id}))
    assert status == 200, listing
    return listing["run_branches"]


def _planning(server, run_id, branch_id, **query):
    return _request("GET", f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}"
                    "/calendar/target-preview?" + urlencode(query or {"season_index": 0, "week": 1}))


@pytest.mark.parametrize("offset", [1, 35])
def test_real_custom_calendar_create_save_fork_and_runtime_restart(tmp_path, offset):
    db = f"sqlite:///{tmp_path / 'custom-clock.db'}"
    inputs = _clock(offset=offset)
    metadata = RunCalendar(52, offset, 2030, 3).to_metadata()
    with ApiServer(database_url=db) as server:
        status, run = _request("POST", server.base_url + "/run-containers", {
            "display_name": "Earth planning", "calendar": inputs,
        })
        assert status == 201, run
        rid, bid = run["run_id"], run["viewer_branch_id"]
        assert run["metadata_json"]["run_calendar"] == metadata
        assert (run["timeline_start_season"], run["timeline_end_season"]) == (2030, 2032)
        revision_id = _branches(server, rid)[0]["saved_head_revision_id"]
        saved_url = f"{server.base_url}/run-containers/{rid}/branches/{bid}/saved-revisions/{revision_id}"
        code, original = _request("GET", saved_url)
        assert code == 200, original
        assert original["payload"]["run"]["run_calendar"] == metadata

        code, plan = _planning(server, rid, bid, season_index=0, week=52, advance_weeks=1)
        assert code == 200, plan
        assert plan["full_simulation_preview_supported"] is False
        assert plan["target"]["season_week"] == 1
        assert plan["target"]["season_label"] == ("2031" if offset == 1 else "2031/2032")

        # The fork uses the ORIGINAL saved owner; a normal explicit Save on
        # the first Branch must carry this calendar without rewriting history.
        code, branch = _request("POST", f"{server.base_url}/run-containers/{rid}/branches", {
            "source_branch_id": bid, "source_saved_revision_id": revision_id,
        })
        assert code == 201, branch
        fork_id = branch["branch_id"]
        assert _planning(server, rid, fork_id)[0] == 200
        draft_url = f"{server.base_url}/run-containers/{rid}/branches/{bid}/working-draft"
        code, draft = _request("PUT", draft_url + "/viewer-branch", {
            "viewer_branch_id": fork_id, "expected_draft_version": 0,
        })
        assert code == 200, draft
        code, saved = _request("POST", draft_url + "/save", {
            "expected_draft_version": draft["draft_version"],
        })
        assert code == 201, saved
        assert saved["saved_revision"]["parent_revision_id"] == revision_id
        assert _planning(server, rid, bid)[1]["run_calendar"] == metadata
        # Only the derived current-head badge changes, never saved data/hash.
        assert _request("GET", saved_url) == (200, {**original, "is_branch_head": False})

        # Name conflict cannot mutate an existing Run's clock or create a
        # partial Run/Branch when another valid calendar was requested.
        before = _request("GET", server.base_url + "/run-containers")
        assert _request("POST", server.base_url + "/run-containers", {
            "display_name": "Earth planning", "calendar": _clock(start=2040),
        })[0] == 409
        assert _request("GET", server.base_url + "/run-containers") == before

    with ApiServer(database_url=db) as server:
        for selected in (bid, fork_id):
            code, reread = _planning(server, rid, selected)
            assert code == 200, reread
            assert reread["run_calendar"] == metadata
        code, run = _request("GET", f"{server.base_url}/run-containers/{rid}")
        assert code == 200
        assert run["viewer_branch_id"] == fork_id
        assert run["mapped_simulation_run_count"] == 0


def test_pure_creation_preview_end_year_and_count_are_equivalent_without_writes(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'preview.db'}") as server:
        before = _request("GET", server.base_url + "/run-containers")
        code, count = _request("POST", server.base_url + "/run-containers/calendar/creation-preview", _clock())
        assert code == 200, count
        assert count["read_only"] is True and count["run_created"] is False
        assert count["first_week"]["calendar_year"] == 2030
        assert count["first_week"]["year_week"] == 35
        assert count["last_week"]["calendar_year"] == 2033
        assert count["last_week"]["year_week"] == 34
        assert count["sporting_calendar_supported"] is False
        assert count["limitations"] == ["sporting_calendar_execution_not_supported_yet"]
        by_last = _clock()
        by_last.pop("season_count")
        by_last["last_season_start_year"] = 2032
        assert _request("POST", server.base_url + "/run-containers/calendar/creation-preview", by_last) == (200, count)
        assert _request("GET", server.base_url + "/run-containers") == before
        code, created = _request("POST", server.base_url + "/run-containers", {
            "display_name": "End-year input", "calendar": by_last,
        })
        assert code == 201, created
        assert created["metadata_json"]["run_calendar"] == count["run_calendar"]


def test_invalid_calendar_requests_never_silently_fall_back_or_create_a_run(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'invalid.db'}") as server:
        before = _request("GET", server.base_url + "/run-containers")
        invalid = [None, {}, {**_clock(), "weeks_per_year": True},
                   {**_clock(), "weeks_per_year": "52"},
                   {**_clock(), "weeks_per_year": 0},
                   {**_clock(), "season_start_year_week": 53},
                   {**_clock(), "season_count": 0},
                   {**_clock(), "start_year": -1},
                   {**_clock(), "last_season_start_year": 2032},
                   {**_clock(), "schema_version": "legacy_fax_calendar.v0"},
                   {**_clock(), "start_year": 2**31 - 1},
                   {**_clock(), "weeks_per_year": 2**31},
                   {**_clock(), "weeks_per_year": 2**31 - 1, "season_count": 2**30}]
        for clock in invalid:
            status, error = _request("POST", server.base_url + "/run-containers", {
                "display_name": "Invalid must not exist", "calendar": clock,
            })
            assert status == 422, (clock, error)
        assert _request("GET", server.base_url + "/run-containers") == before


def test_name_only_creation_stays_default_fax_and_same_clock_is_supported(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'default.db'}") as server:
        code, run = _request("POST", server.base_url + "/run-containers", {"display_name": "Default FAX"})
        assert code == 201
        assert run["metadata_json"]["run_calendar"] == RunCalendar.fax_default().to_metadata()
        code, preview = _request("POST", server.base_url + "/run-containers/calendar/creation-preview", {
            "weeks_per_year": 61, "season_start_year_week": 37, "start_year": 2000, "season_count": 50,
        })
        assert code == 200 and preview["sporting_calendar_supported"] is True
        assert preview["limitations"] == []

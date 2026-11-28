"""Import both built-in ATP packages and plan a tournament on the same W52 Run."""

from pathlib import Path
from urllib.parse import quote

import pytest

from beta_engine.application.atp_historical_calendar_adapter import CALENDAR_SETUP_ID
from test_simulation_api import ApiServer, _request


pytestmark = pytest.mark.smoke


def test_earth_world_and_atp_tour_packages_share_a_saved_w52_timeline(tmp_path: Path):
    uri = f"sqlite:///{tmp_path / 'atp-w52-setup.db'}"
    clock = {"weeks_per_year": 52, "season_start_year_week": 1,
             "start_year": 2024, "season_count": 3}
    with ApiServer(database_url=uri) as server:
        status, run = _request("POST", server.base_url + "/run-containers", {
            "display_name": "ATP W52 setup", "calendar": clock,
        })
        assert status == 201, run
        run_id, branch_id = run["run_id"], run["viewer_branch_id"]
        target = f"/{quote(run_id, safe='')}/branches/{quote(branch_id, safe='')}"
        packages = server.base_url + "/admin/runs" + target + "/packages"
        draft_path = "/run-containers" + target + "/working-draft"
        draft_url = server.base_url + draft_path
        code, original_draft = _request("GET", draft_url)
        assert code == 200 and original_draft["status"] == "clean"
        head = original_draft["base_saved_revision_id"]

        world = packages + "/source-world/atp_earth/selection-"
        code, available = _request("POST", world + "preview", {})
        assert code == 200, available
        selection = {"selected_entities": sorted(
            row["label"] for row in available["available"] if row["valid"]
        )}
        assert selection["selected_entities"]
        code, review = _request("POST", world + "preview", selection)
        assert code == 200 and review["can_confirm"], review.get("blockers", review)
        assert _request("GET", draft_url) == (200, original_draft)

        # Follow the same two explicit confirm/save operations as the Admin setup.
        calendar = packages + "/source-atp-reference-calendar/"
        for source, extra, command in (
            (world, {**selection, "expected_selection_fingerprint": review["selection_fingerprint"]}, "install-world"),
            (calendar, {}, "install-calendar"),
        ):
            if source == calendar:
                code, review = _request("POST", source + "preview", {})
                assert code == 200 and not review["invalid"] and not review["conflicts"]
            assert review["saved_head_revision_id"] == head
            code, staged = _request("POST", source + "confirm", {
                **extra, "command_id": command,
                "expected_head_revision_id": head,
                "expected_draft_version": review["draft_version"],
                "expected_state_fingerprint": review["current_state_fingerprint"],
                "expected_preview_fingerprint": review["preview_fingerprint"],
                "conflict_resolutions": {},
            })
            assert code == 200, staged
            assert _request("GET", draft_url)[1]["base_saved_revision_id"] == head
            code, saved = _request("POST", draft_url + "/save", {
                "expected_draft_version": staged["draft_version"],
            })
            assert code == 201, saved
            next_head = saved["saved_revision"]["revision_id"]
            assert next_head != head and saved["working_draft"]["status"] == "clean"
            head = next_head

    with ApiServer(database_url=uri) as reopened:
        packages = reopened.base_url + "/admin/runs" + target + "/packages"
        code, persisted = _request("GET", packages)
        assert code == 200, persisted
        assert {version["package_id"] for version in persisted["state"]["package_versions"]} >= {
            "atp_earth", CALENDAR_SETUP_ID,
        }
        code, mapping = _request("GET", packages +
            "/saved-source-atp-reference-calendar/run-week-preview?year=2024&year=2025")
        assert code == 200, mapping
        assert mapping["uses_saved_run_package_snapshot"] is True
        assert mapping["saved_head_revision_id"] == head
        assert mapping["calendar"] == {"schema_version": "run_calendar.v1", **clock}
        assert {row["atp_season_year"] for row in mapping["events"]} == {2024, 2025}
        assert all(1 <= week["season_week"] <= 52 for row in mapping["events"] for week in row["run_weeks"])
        draft_url = reopened.base_url + draft_path
        code, draft = _request("GET", draft_url)
        assert code == 200 and draft["status"] == "clean" and draft["base_saved_revision_id"] == head

        # Consume the package from the same Run after restart, without staging a tournament.
        editions_url = reopened.base_url + "/admin/runs" + target + "/calendar-tour/atp-source-editions"
        code, catalog = _request("GET", editions_url)
        assert code == 200, catalog
        assert catalog["saved_head_revision_id"] == head
        dallas = next(row for row in catalog["entries"]
                      if row["profile"]["occurrence_id"] == "atp_2025_dallas")
        assert dallas["qualification_calendar_projection"]["run_weeks"] == [
            {"season_index": 1, "season_week": 5},
        ]
        assert [(week["season_index"], week["season_week"])
                for week in dallas["calendar_projection"]["run_weeks"]] == [(1, 6)]

        def position(week, slot):
            return {"week": {"calendar": mapping["calendar"], "season_index": 1, "week": week},
                    "slot": slot}

        code, plan = _request("POST", editions_url + "/atp_2025_dallas/schedule-preview", {
            "expected_saved_head": head,
            "expected_profile_fingerprint": dallas["profile_fingerprint"],
            "schedule": {
                "calendar": mapping["calendar"],
                "qualification": [position(5, slot) for slot in range(1, 3)],
                "main": [position(6, slot) for slot in range(1, 6)],
            },
        })
        assert code == 200, plan
        assert plan["actual_match_count"] == 43
        assert plan["qualification_dates_verified"] is True
        assert plan["run_mutated"] is False
        assert _request("GET", draft_url) == (200, draft)

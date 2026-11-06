"""Real HTTP and SQLite Run clock read for original ATP dated source weeks."""
from __future__ import annotations

from urllib.parse import quote

import pytest

from test_simulation_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def _make_run(server, *, name: str, start: int = 2025, count: int = 2,
              offset: int = 1, weeks: int = 52):
    status, run = _request("POST", server.base_url + "/run-containers", {
        "display_name": name,
        "calendar": {
            "weeks_per_year": weeks,
            "season_start_year_week": offset,
            "start_year": start,
            "season_count": count,
        },
    })
    assert status == 201, run
    return run["run_id"], run["viewer_branch_id"]


def _url(server, run_id, branch_id, suffix=""):
    return (
        f"{server.base_url}/admin/runs/{quote(run_id, safe='')}"
        f"/branches/{quote(branch_id, safe='')}/packages/"
        "source-atp-reference-calendar/run-week-preview" + suffix
    )


def test_source_week_preview_on_real_saved_earth_clock_is_nondestructive(tmp_path):
    db = f"sqlite:///{tmp_path / 'atp-saved-week.db'}"
    with ApiServer(database_url=db) as server:
        run_id, branch_id = _make_run(
            server, name="ATP 2025–26 Earth W52", start=2025, count=2
        )
        base = server.base_url + f"/run-containers/{run_id}"
        working = base + f"/branches/{branch_id}/working-draft"
        before_run = _request("GET", base)
        before_draft = _request("GET", working)
        assert before_run[0] == 200
        assert before_draft[0] == 200
        code, preview = _request("GET", _url(
            server, run_id, branch_id, "?year=2025&year=2026"
        ))
        assert code == 200, preview
        assert preview["run_id"] == run_id
        assert preview["branch_id"] == branch_id
        assert preview["saved_run_calendar_verified"] is True
        assert preview["uses_current_server_reference_not_run_snapshot"] is True
        assert preview["run_mutated"] is False
        assert preview["working_draft_mutated"] is False
        assert preview["historical_revision_mutated"] is False
        assert preview["no_sporting_install"] is True
        assert preview["no_simulation_slot_or_match_generation"] is True
        assert preview["selected_atp_years"] == [2025, 2026]
        assert preview["calendar"]["weeks_per_year"] == 52
        assert preview["calendar"]["start_year"] == 2025
        assert len(preview["events"]) > 80
        assert any(
            e["atp_season_year"] == 2026 and
            e["source_status"] == "provisional_published_schedule"
            for e in preview["events"]
        )
        assert all(
            0 <= v["season_index"] < 2
            for e in preview["events"] for v in e["run_weeks"]
        )
        assert _request("GET", base) == before_run
        assert _request("GET", working) == before_draft
        fingerprint = preview["preview_fingerprint"]
    with ApiServer(database_url=db) as server:
        code, reread = _request("GET", _url(
            server, run_id, branch_id, "?year=2026&year=2025"
        ))
        assert code == 200, reread
        assert reread == preview
        assert reread["preview_fingerprint"] == fingerprint
        assert _request("GET", server.base_url + f"/run-containers/{run_id}") == before_run
        assert _request(
            "GET", server.base_url + f"/run-containers/{run_id}/branches/{branch_id}/working-draft"
        ) == before_draft


def test_custom_season_offset_projects_to_native_position_and_is_still_readonly(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'atp-offset.db'}") as server:
        run_id, branch_id = _make_run(
            server, name="ATP custom Earth offset", start=2024, count=3, offset=37
        )
        code, preview = _request("GET", _url(
            server, run_id, branch_id, "?year=2025"
        ))
        assert code == 200, preview
        assert preview["calendar"]["season_start_year_week"] == 37
        item = next(
            e for e in preview["events"]
            if e["source_identity"] == "atp_2025_canadian_open"
        )
        assert [v["year_week"] for v in item["run_weeks"]] == [30, 31, 32]
        assert [v["season_week"] for v in item["run_weeks"]] == [46, 47, 48]
        assert all(v["season_index"] == 0 for v in item["run_weeks"])
        assert "three_week_interval_manual_sporting_review" in item["review_flags"]


def test_previewer_rejects_wrong_saved_clock_scope_and_invalid_selected_year(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'atp-bad.db'}") as server:
        r, b = _make_run(server, name="Earth 2025", start=2025, count=2)
        assert _request("GET", _url(server, r, b, "?year=2024"))[0] == 409
        assert _request("GET", _url(server, r, b, "?year=2025&year=2025"))[0] == 409
        assert _request("GET", _url(server, r, b, "?year=2027"))[0] == 422
        assert _request("GET", _url(server, r, "unknown-branch", "?year=2025"))[0] == 409
        # Default all-year request on a two-year Run must not silently omit data.
        assert _request("GET", _url(server, r, b))[0] == 409
        other_run, other_branch = _make_run(
            server, name="Default FAX W61", start=2000, count=50,
            offset=37, weeks=61
        )
        code, body = _request("GET", _url(
            server, other_run, other_branch, "?year=2025"
        ))
        assert code == 409, body
        assert "W=52" in body["detail"]["message"]


def test_api_never_treats_uninstalled_source_as_mutated_run_package(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'atp-ref-only.db'}") as server:
        r, b = _make_run(server, name="Empty Earth reference preview")
        packages = f"{server.base_url}/admin/runs/{r}/branches/{b}/packages"
        code, state = _request("GET", packages)
        assert code == 200, state
        assert state["state"] is None
        code, preview = _request("GET", _url(server, r, b, "?year=2025"))
        assert code == 200, preview
        assert preview["uses_current_server_reference_not_run_snapshot"] is True
        code, after = _request("GET", packages)
        assert code == 200
        assert after == state
        assert all("source_start_date" in item for item in preview["events"])

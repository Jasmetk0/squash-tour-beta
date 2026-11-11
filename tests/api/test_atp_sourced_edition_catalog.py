"""Real Saved Package reads remain independent from current source files."""
import pytest

from tests.api.test_atp_saved_run_week_preview_api import _make_run
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def test_sporting_catalog_uses_saved_profiles_and_retains_outside_horizon_sources(tmp_path, monkeypatch):
    from beta_engine.application import atp_historical_calendar_adapter

    def unavailable(*args, **kwargs):
        raise AssertionError("Current server source must not reinterpret a Saved Run")

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'atp-sporting-source.db'}") as server:
        r, b = _make_run(server, name="ATP sporting snapshots", start=2026, count=1)
        branch = server.base_url + f"/run-containers/{r}/branches/{b}/working-draft"
        root = server.base_url + f"/admin/runs/{r}/branches/{b}"
        source = root + "/packages/source-atp-reference-calendar"
        target = root + "/calendar-tour/atp-source-editions"
        assert _request("GET", target)[0] == 409
        code, review = _request("POST", source + "/preview", {})
        assert code == 200, review
        code, applied = _request("POST", source + "/confirm", {
            "command_id": "copy-atp-sporting", "expected_head_revision_id": review["saved_head_revision_id"],
            "expected_draft_version": review["draft_version"], "expected_state_fingerprint": review["current_state_fingerprint"],
            "expected_preview_fingerprint": review["preview_fingerprint"], "conflict_resolutions": {},
        })
        assert code == 200, applied
        assert _request("GET", target)[0] == 409
        code, saved = _request("POST", branch + "/save", {"expected_draft_version": applied["draft_version"]})
        assert code == 201, saved
        before = _request("GET", branch)
        monkeypatch.setattr(atp_historical_calendar_adapter, "build_atp_sporting_package", unavailable)
        code, catalog = _request("GET", target)
        assert code == 200, catalog
        assert catalog["run_id"] == r and catalog["branch_id"] == b
        assert len(catalog["entries"]) == 3
        assert [e["profile"]["played_group_win_points"] for e in catalog["entries"] if e["execution_supported"]] == [200, 0]
        assert all(e["calendar_projection"]["outside_year_weeks"] for e in catalog["entries"])
        knockout = catalog['entries'][2]
        assert knockout['profile']['occurrence_id'] == 'atp_2025_rotterdam'
        assert knockout['knockout_geometry']['actual_match_count'] == 43
        assert knockout['execution_supported'] is False
        code, refused = _request('POST', target + '/atp_2025_rotterdam/preview', {
            'command_id': 'blocked-knockout', 'expected_saved_head': catalog['saved_head_revision_id'],
            'expected_checkpoint_fingerprint': 'a'*64, 'expected_tour_fingerprint': 'b'*64,
            'start_slot':1, 'seed':1, 'operator_label':'Admin', 'audit_reason':'Check unsupported execution',
        })
        assert code == 409, refused
        assert 'native W52 Ranked integration' in refused['detail']['message']
        code, rejected = _request("POST", target + "/atp_2025_atp_finals/preview", {
            "command_id": "outside-atp", "expected_saved_head": catalog["saved_head_revision_id"],
            "expected_checkpoint_fingerprint": "a" * 64, "expected_tour_fingerprint": "b" * 64,
            "start_slot": 1, "seed": 1, "operator_label": "Admin", "audit_reason": "Check horizon",
        })
        assert code == 409, rejected
        assert "outside the Run horizon" in rejected["detail"]["message"]
        assert _request("GET", branch) == before

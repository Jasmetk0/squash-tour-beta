"""Actual HTTP/SQLite Saved HEAD + shared Run source preflight acceptance."""
import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.repositories import RunProspectRecord
from tests.api.test_calendar_tour_flow import setup, tour_url
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.application.test_prospect_persistence import _record

pytestmark = pytest.mark.pr_critical


def test_native_intake_preflight_requires_signed_shared_source_and_never_activates(
    tmp_path,
):
    database_url = f"sqlite:///{tmp_path / 'native-intake-preflight.db'}"
    with ApiServer(database_url=database_url) as server:
        repo, _ = setup(server, RunCalendar(4, 1, 2030, 3), 8)
        route = tour_url(server) + "/prospect-intake/preflight"
        status, empty = _request("GET", route)
        assert status == 200, empty
        assert empty["native_activation_supported"] is False
        assert empty["source_fingerprint"] is None
        assert empty["due"] == [] and not empty["blocked"]
        assert empty["target_week"]["week"] == 3

        template = _record()
        world = repo.get_initial_world(run_id="run", branch_id="branch")
        assert world is not None
        record = RunProspectRecord(**(
            template.__dict__ | {
                "run_id": "run", "world_id": world.world_package_id,
                "prospect_id": "intake-prospect",
                "season_start_year": 2030, "season_label": "2030",
                "season_week": 3, "calendar_year": 2030,
                "year_week": 3, "birth_year": 2015, "birth_year_week": 3,
                "display_name": "Verified Birthday Prospect",
            }
        ))
        repo.upsert_run_prospects([record])
        unsigned, response = _request("GET", route)
        assert unsigned == 409, response

        source_route = (
            server.base_url + "/admin/runs/run/branches/branch/"
            "authoritative-simulation/prospect-source/save"
        )
        code, review = _request("GET", source_route + "/preview")
        assert code == 200, review
        code, saved = _request("POST", source_route, {
            "expected_draft_version": review["draft_version"],
            "expected_run_prospect_source_fingerprint":
                review["run_prospect_source_fingerprint"],
        })
        assert code == 201, saved
        code, report = _request("GET", route)
        assert code == 200, report
        assert report["source_fingerprint"] == review["run_prospect_source_fingerprint"]
        assert report["due_count"] == 0
        assert report["problems"] == [{
            "prospect_id": "intake-prospect",
            "code": "prospect_sporting_profile_unready",
        }]
        assert report["native_activation_supported"] is False
        assert _request("GET", route) == (code, report)

        # A shared Run prospect source is immutable with respect to this
        # signed branch: a new unsaved mutation cannot be read as authentic.
        altered = RunProspectRecord(**(
            record.__dict__ | {"display_name": "Unsaved changed identity"}
        ))
        repo.upsert_run_prospects([altered])
        status, response = _request("GET", route)
        assert status == 409, response

    with ApiServer(database_url=database_url) as restarted:
        status, response = _request("GET", tour_url(restarted) + "/prospect-intake/preflight")
        assert status == 409, response

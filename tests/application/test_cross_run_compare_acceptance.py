"""Real HTTP/SQLite native Saved source comparison and physical-corruption rejection."""
import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from tests.api.test_calendar_tour_flow import setup
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.support.cross_run_compare import params, snapshot

pytestmark = pytest.mark.pr_critical


def test_native_saved_compare_survives_restart_and_rejects_warmed_source_corruption(tmp_path):
    database = tmp_path / "native-cross.db"
    url = f"sqlite:///{database}"
    with ApiServer(database_url=url) as server:
        repo, source = setup(server, RunCalendar(7, 1, 2030, 3), 4)
        code, other = _request("POST", server.base_url + "/run-containers", {"display_name": "Independent Run B"})
        assert code == 201, other
        code, branches = _request("GET", server.base_url + "/run-branches?run_id=" + other["run_id"])
        assert code == 200
        a = ("run", "branch", source["revision_id"])
        b = (other["run_id"], other["viewer_branch_id"], branches["run_branches"][0]["saved_head_revision_id"])
        from urllib.parse import urlencode
        route = "/admin/cross-run-compare?" + urlencode(params(a, b))
        before = snapshot(database)
        code, comparison = _request("GET", server.base_url + route)
        assert code == 200, comparison
        assert any(c["component_key"] == "calendar_tour_authority" for c in comparison["components"])
        assert all(c["before_fingerprint"] is None or len(c["before_fingerprint"]) == 64 for c in comparison["components"])
        assert snapshot(database) == before
    with ApiServer(database_url=url) as server:
        assert _request("GET", server.base_url + route) == (200, comparison)
        repo = server.app.state.runtime.repository
        with repo._session_factory.begin() as session:
            session.get(BranchSavedRevisionModel, a[2]).change_summary_json = '{"corrupt_actual_source":true}'
        damaged = snapshot(database)
        assert _request("GET", server.base_url + route)[0] == 409
        assert snapshot(database) == damaged

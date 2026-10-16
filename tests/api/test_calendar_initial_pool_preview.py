"""HTTP -> verified Saved clock -> real World projection/kernel -> no writes."""

import json

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.calendar_initial_pool import CalendarInitialPoolResult
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    RunContainerModel,
)
from tests.api.test_player_generation_calendar_gate import (
    _base,
    _dump,
    _generation,
    _initial,
    _world,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def url(server, branch="branch"):
    return server.base_url + f"/admin/players/runs/run/branches/{branch}/initial-pool/world-package/calendar-preview"


@pytest.mark.parametrize("world_id", ["fifa_earth", "atp_earth"])
def test_real_earth_package_generates_1000_players_under_its_52_week_clock(tmp_path, world_id):
    path = tmp_path / "earth.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _world(server, RunCalendar.earth_default(start_year=1955), world_id=world_id)
        before = _dump(path)
        status, preview = _request("POST", url(server), _generation(
            world_package_id=world_id, target_pool_size=1000, min_age=18, max_age=25,
        ))
        assert status == 200, preview
        result = CalendarInitialPoolResult.model_validate(preview["result"])
        assert len(result.players) == 1000
        assert len({p.player_id for p in result.players}) == 1000
        assert all(18 <= p.current_age_years <= 25 and p.birth_year_week <= 52 for p in result.players)
        assert all(p.created_for_season == "1955" for p in result.players)
        assert any(d.estimated_weight_share > 0 for d in result.metadata.population_weighting_diagnostics)
        assert any(row["kind"] == "nearest_fallback" for c in preview["country_rating_sources"] for row in c["years"])
        assert _dump(path) == before


@pytest.mark.parametrize("clock", [RunCalendar.earth_default(start_year=1955),
    RunCalendar(52, 35, 2030, 3), RunCalendar(80, 80, 2100, 300),
    RunCalendar(1, 1, 0, 1), RunCalendar.fax_default(season_count=51)])
def test_real_preview_uses_saved_clock_and_survives_restart_without_changing_saved_history(tmp_path, clock):
    path = tmp_path / "preview.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, _ = _world(server, clock)
        before = _dump(path)
        code, preview = _request("POST", url(server), _generation(target_pool_size=40))
        assert code == 200, preview
        assert preview["schema_version"] == "run_calendar_initial_pool_preview.v2"
        assert preview["run_calendar"] == clock.to_metadata()
        assert preview["calendar_saved_revision_id"] == "r1"
        assert preview["preview_only"] is True and preview["adoption_supported"] is False
        result = CalendarInitialPoolResult.model_validate(preview["result"])
        assert len(result.players) == 40
        assert result.metadata.season == clock.label(0)
        assert result.metadata.time_basis.weeks_per_year == clock.weeks_per_year
        assert len(preview["country_rating_sources"]) > 0
        assert _request("POST", url(server), _generation(target_pool_size=40)) == (code, preview)
        assert _dump(path) == before
        assert repo.verify_branch_saved_revision_hash(revision_id="r0")
        assert repo.verify_branch_saved_revision_hash(revision_id="r1")
        # A new preview is not consent to install a v2 cohort into v1 state.
        code, error = _request("POST", _base(server) + "/initial-world/world-package/preview", _initial(_generation()))
        assert code == 409, error
        assert _dump(path) == before
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        assert _request("POST", url(server), _generation(target_pool_size=40)) == (200, preview)
        assert _dump(path) == before


def test_preview_uses_shared_saved_ancestry_after_real_fork(tmp_path):
    path = tmp_path / "fork.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _world(server, RunCalendar(52, 35, 2030, 3))
        code, fork = _request("POST", server.base_url + "/run-containers/run/branches", {
            "source_branch_id": "branch", "source_saved_revision_id": "r1",
        })
        assert code == 201, fork
        before = _dump(path)
        code, preview = _request("POST", url(server, fork["branch_id"]), _generation())
        assert code == 200, preview
        assert preview["calendar_saved_revision_id"] == fork["saved_head_revision_id"]
        assert preview["branch_id"] == fork["branch_id"]
        assert _dump(path) == before


@pytest.mark.parametrize("damage", ["null", "saved_hash", "different_current"])
def test_invalid_clock_proof_cannot_fall_back_or_generate(tmp_path, damage):
    path = tmp_path / "bad.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, _ = _world(server, RunCalendar.earth_default())
        with repo._session_factory.begin() as session:
            if damage == "saved_hash":
                session.get(BranchSavedRevisionModel, "r1").content_hash = "0" * 64
            else:
                clock = None if damage == "null" else RunCalendar.fax_default().to_metadata()
                session.get(RunContainerModel, "run").metadata_json = json.dumps({"run_calendar": clock})
        before = _dump(path)
        status, error = _request("POST", url(server), _generation())
        assert status == 409, error
        assert _dump(path) == before


def test_conditions_are_strict_no_clock_injection_and_country_failures_do_not_write(tmp_path):
    path = tmp_path / "conditions.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _world(server, RunCalendar.earth_default())
        before = _dump(path)
        for extra in ({"season": "2030"}, {"run_calendar": {}}, {"weeks_per_year": 61},
                      {"keep_player_ids": []}, {"seed": True}, {"target_pool_size": 1.5},
                      {"min_age": 25, "max_age": 18}):
            status, error = _request("POST", url(server), _generation(**extra))
            assert status == 422, error
        for extra in ({"country_code": "ZZZ"}, {"geographic_region": "missing"},
                      {"country_quotas": [{"country_code": "ZZZ", "count": 4}]}):
            status, error = _request("POST", url(server), _generation(**extra))
            assert status == 409, error
        status, preview = _request("POST", url(server), _generation(
            min_age=18, max_age=18, country_quotas=[{"country_code": "GER", "count": 4}],
        ))
        assert status == 200, preview
        assert {p["country_code"] for p in preview["result"]["players"]} == {"GER"}
        assert all(p["current_age_years"] == 18 for p in preview["result"]["players"])
        assert _dump(path) == before

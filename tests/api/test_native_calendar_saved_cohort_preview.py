"""Real Run/Branch HTTP+SQLite W52/W61/W80 prospective intake generation."""
import json

import pytest

from beta_engine.application.native_calendar_cohort_service import (
    NativeCalendarCohortRequest, NativeCalendarCohortService,
    build_native_calendar_cohort,
)
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.prospect_sporting_profile import (
    validate_persisted_prospect_sporting_profile,
)
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from beta_engine.infrastructure.db.run_package_state import get_run_package_state
from tests.api.test_player_generation_calendar_gate import _base, _dump, _world
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def url(server):
    return _base(server) + "/intake/native-calendar/preview"


@pytest.mark.parametrize("clock,season_index", [
    (RunCalendar(52, 1, 1955, 4), 0),
    (RunCalendar(52, 35, 2030, 4), 1),
    (RunCalendar(61, 37, 2000, 4), 0),
    (RunCalendar(80, 15, 2030, 4), 1),
])
def test_saved_world_native_cohort_preview_generates_exact_w_and_profiles_without_writes(
    tmp_path, clock, season_index,
):
    path = tmp_path / f"cohort-{clock.weeks_per_year}-{clock.season_start_year_week}.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, _ = _world(server, clock)
        before = _dump(path)
        command = dict(
            world_package_id="official_fax_world",
            season_index=season_index, base_annual_intake_target=12,
            country_code="GER",
        )
        code, review = _request("POST", url(server), command)
        assert code == 200, review
        assert review["schema_version"] == "native_calendar_cohort_preview.v1"
        assert review["run_calendar"] == clock.to_metadata()
        assert review["request"]["season_index"] == season_index
        assert review["season_label"] == clock.label(season_index)
        assert len(review["week_counts"]) == clock.weeks_per_year
        assert sum(review["week_counts"]) == review["annual_target"]
        assert review["country_counts"] == {"GER": review["annual_target"]}
        assert review["prepared_profile_count"] == review["annual_target"]
        assert review["preview_only"] and not review["materialization_supported"]
        assert not review["native_tour_activation_supported"]
        assert len(review["record_content_fingerprint"]) == 64
        assert _request("POST", url(server), command) == (code, review)
        assert _dump(path) == before
        assert repo.verify_branch_saved_revision_hash(revision_id="r1")

        with repo._session_factory() as session:
            state = get_run_package_state(session, run_id="run", branch_id="branch")
        projection = WorldPackageRunAdapter(WorldPackageRegistryService()).project_countries(
            state, package_id="official_fax_world",
        )
        cohort = build_native_calendar_cohort(
            clock=clock, run_id="run", world_id="official_fax_world",
            season_index=season_index,
            countries=[x for x in projection.countries if x.code == "GER"],
            base_annual_intake_target=12,
            country_content_fingerprint=projection.content_fingerprint,
        )
        assert review["record_content_fingerprint"] == cohort.content_fingerprint
        assert len(cohort.records) == review["annual_target"]
        assert len(set(row.prospect_id for row in cohort.records)) == len(cohort.records)
        for row in cohort.records:
            birth = clock.season_to_calendar(season_index, row.season_week)
            assert row.season_start_year == clock.start_year + season_index
            assert row.calendar_year == birth.calendar_year
            assert row.year_week == row.birth_year_week == birth.year_week
            assert row.birth_year + 15 == birth.calendar_year
            verified = validate_persisted_prospect_sporting_profile(
                profile=row.profile_json, development=row.development_json,
                potential=row.potential_json,
            )
            assert verified.player_id == row.prospect_id
            assert len(verified.attributes) == 57

    with ApiServer(database_url=f"sqlite:///{path}") as restarted:
        assert _request("POST", url(restarted), command) == (200, review)


def test_native_cohort_preview_rejects_forged_clock_and_world_scopes_without_writes(tmp_path):
    path = tmp_path / "invalid-cohort.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, _ = _world(server, RunCalendar(52, 35, 2030, 3))
        before = _dump(path)
        basic = {"world_package_id": "official_fax_world", "season_index": 1}
        for wrong in [
            {"season_index": 3},
            {"world_package_id": "foreign-world"},
            {"country_code": "ZZZ"},
        ]:
            code, result = _request("POST", url(server), basic | wrong)
            assert code == 409, result
        for invalid in [
            {"season_index": -1},
            {"season_index": True},
            {"weeks_per_year": 61},
            {"base_annual_intake_target": 0},
            {"country_code": "ČŘÁ"},
        ]:
            code, result = _request("POST", url(server), basic | invalid)
            assert code == 422, result
        assert _dump(path) == before
        with repo._session_factory.begin() as session:
            session.get(BranchSavedRevisionModel, "r1").content_hash = "0" * 64
        bad_before = _dump(path)
        code, result = _request("POST", url(server), basic)
        assert code == 409, result
        assert _dump(path) == bad_before


def test_native_cohort_distinct_clock_w_changes_source_ids_and_never_reuses_legacy_version(
    tmp_path,
):
    path = tmp_path / "clock-seeds.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, _ = _world(server, RunCalendar(52, 35, 2030, 3))
        with repo._session_factory() as session:
            source = get_run_package_state(session, run_id="run", branch_id="branch")
        countries = WorldPackageRunAdapter(WorldPackageRegistryService()).project_countries(
            source, package_id="official_fax_world",
        )
        selected = [x for x in countries.countries if x.code == "GER"]
        args = dict(
            run_id="run", world_id="official_fax_world", season_index=0,
            countries=selected, base_annual_intake_target=15,
            country_content_fingerprint=countries.content_fingerprint,
        )
        earth = build_native_calendar_cohort(clock=RunCalendar(52, 35, 2030, 3), **args)
        fax = build_native_calendar_cohort(clock=RunCalendar(61, 37, 2030, 3), **args)
        assert len(earth.week_counts) == 52 and len(fax.week_counts) == 61
        assert earth.content_fingerprint != fax.content_fingerprint
        assert all(
            row.cohort_policy_version == "native_calendar_15yo_cohort_v1"
            and row.source_type == "native_calendar_15yo_cohort"
            for row in earth.records + fax.records
        )
        assert _request("POST", url(server), {
            "world_package_id": "official_fax_world",
            "season_index": 0, "country_code": "GER",
        })[0] == 200

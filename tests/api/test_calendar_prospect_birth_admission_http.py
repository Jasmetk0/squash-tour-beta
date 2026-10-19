"""Real HTTP/SQLite Signed W-aware 15yo birth and lifecycle projection."""
import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.infrastructure.db.repositories import RunProspectRecord
from tests.application.test_calendar_native_prospect_intake import source_at
from tests.application.test_prospect_persistence import _record
from tests.api.test_calendar_tour_flow import setup, tour_url
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def test_saved_native_birth_week_projects_full_v4_successor_without_any_admission(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'native-birth-v4.db'}"
    clock = RunCalendar(4, 1, 2030, 3)
    with ApiServer(database_url=database_url) as server:
        repo, _ = setup(server, clock, 8)
        world = repo.get_initial_world(run_id="run", branch_id="branch")
        assert world is not None
        new = source_at(
            clock, RunWeekPosition(calendar=clock, season_index=0, week=3),
            pid="native-new-15yo",
        )
        template = _record()
        record = RunProspectRecord(**(template.__dict__ | {
            "prospect_id": new["prospect_id"],
            "run_id": "run", "world_id": world.world_package_id,
            "season_start_year": new["season_start_year"],
            "season_label": "2030",
            "season_week": new["season_week"],
            "calendar_year": new["calendar_year"], "year_week": new["year_week"],
            "birth_year": new["birth_year"], "birth_year_week": new["birth_year_week"],
            "age": 15, "country_code": new["country_code"],
            "status": "prospect",
            "source_type": "native_calendar_15yo_cohort",
            "cohort_policy_version": "native_calendar_15yo_cohort_v1",
            "profile_version": "prospect_profile_v1",
            "profile_seed": "profile", "development_seed": "development",
            "potential_seed": "potential",
            "profile_json": new["profile"], "development_json": new["development"],
            "potential_json": new["potential"],
        }))
        repo.upsert_run_prospects([record])
        source_url = (
            server.base_url
            + "/admin/runs/run/branches/branch/authoritative-simulation/prospect-source/save"
        )
        code, review = _request("GET", source_url + "/preview")
        assert code == 200 and review["can_save"], review
        code, saved = _request("POST", source_url, {
            "expected_draft_version": review["draft_version"],
            "expected_run_prospect_source_fingerprint":
                review["run_prospect_source_fingerprint"],
        })
        assert code == 201, saved
        preflight_url = tour_url(server) + "/prospect-intake/preflight"
        code, verified = _request("GET", preflight_url)
        assert code == 200, verified
        assert verified["due_count"] == 1 and verified["problems"] == []
        stage = verified["lifecycle_admission_projection"]
        assert stage["birth_count"] == 1
        assert stage["proposed_lifecycle_schema"] == "player_lifecycle_calendar_state.v4"
        assert stage["proposed_health_population_count"] == 9
        assert len(stage["source_health_fingerprint"]) == 64
        assert len(stage["proposed_health_fingerprint"]) == 64
        assert len(stage["admission_bundle_fingerprint"]) == 64
        assert stage["ranking_and_entry_adoption_supported"] is False
        assert stage["projected_population_count"] == 9
        assert len(stage["birth_event_fingerprint"]) == 64
        assert len(stage["proposed_lifecycle_fingerprint"]) == 64
        assert stage["sporting_health_saved_activation_supported"] is False
        assert verified["blocked"] and not verified["native_activation_supported"]
        assert _request("GET", preflight_url) == (code, verified)
        current = _request("GET", tour_url(server))[1]
        assert all(player["player_id"] != "native-new-15yo" for player in current["players"])
        # Only the caller-selected, current Signed Head/Checkpoint/Tour and
        # actual completed-week match count are accepted. No birth is written.
        seeded_url = tour_url(server) + "/prospect-intake/sporting-preflight"
        cmd = {
            "expected_saved_head": verified["saved_head_revision_id"],
            "expected_checkpoint_fingerprint": verified["checkpoint_fingerprint"],
            "expected_tour_fingerprint": current["tour_fingerprint"],
            "seed": 927,
        }
        status, seeded_review = _request("POST", seeded_url, cmd)
        assert status == 200, seeded_review
        sporting = seeded_review["sporting_week_projection"]
        assert sporting["old_population_count"] == 8
        assert sporting["new_population_count"] == 9
        assert sporting["seed"] == 927
        assert len(sporting["signed_admission_week_fingerprint"]) == 64
        assert len(sporting["sporting_birth_advance_fingerprint"]) == 64
        assert sporting["signed_writer_supported"] is False
        assert sporting["source_saved_head"] == cmd["expected_saved_head"]
        assert sporting["played_player_count"] <= 8
        assert seeded_review["blocked"] and not seeded_review["native_activation_supported"]
        assert _request("POST", seeded_url, cmd) == (200, seeded_review)
        mutated_seed = _request("POST", seeded_url, {**cmd, "seed": 928})
        assert mutated_seed[0] == 200
        assert mutated_seed[1]["sporting_week_projection"][
            "signed_admission_week_fingerprint"
        ] != sporting["signed_admission_week_fingerprint"]
        for key, wrong in (
            ("expected_saved_head", "foreign-revision"),
            ("expected_checkpoint_fingerprint", "0" * 64),
            ("expected_tour_fingerprint", "0" * 64),
        ):
            assert _request("POST", seeded_url, {**cmd, key: wrong})[0] == 409
        assert _request("POST", seeded_url, {**cmd, "seed": True})[0] == 422
        assert _request("POST", seeded_url, {**cmd, "seed": "927"})[0] == 422
        assert _request("POST", seeded_url, {**cmd, "invented": "no"})[0] == 422
        assert _request("GET", preflight_url) == (200, verified)
        assert _request("GET", tour_url(server))[1] == current
        assert repo.verify_branch_saved_revision_hash(
            revision_id=saved["saved_revision"]["revision_id"]
        )

    with ApiServer(database_url=database_url) as restarted:
        assert _request(
            "GET", tour_url(restarted) + "/prospect-intake/preflight",
        ) == (200, verified)
        assert _request(
            "POST", tour_url(restarted) + "/prospect-intake/sporting-preflight", cmd,
        ) == (200, seeded_review)

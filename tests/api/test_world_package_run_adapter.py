from __future__ import annotations

from urllib.parse import quote

import pytest

from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore
from beta_engine.world_packages import OFFICIAL_FAX_WORLD_ID
from tests.api.test_initial_world_ranking_integration import _post_headers
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.support.world_packages import copy_builtin_world_packages


def _custom_player(country_code: str) -> dict:
    return {
        "player_id": "WORLD-PACKAGE-PLAYER",
        "name": "World Package Player",
        "country_code": country_code,
        "birth_year": 1978,
        "birth_year_week": 12,
        "current_ability": 75,
        "potential_ability": 85,
        "potential_tier": "A",
        "career_stage": "prime",
        "play_style": "balanced",
        "archetype": "all_court",
        "attributes": {
            "technique": 75,
            "movement": 75,
            "physical": 75,
            "mental": 75,
            "consistency": 75,
            "clutch": 75,
            "recovery": 75,
        },
        "hidden_career_traits": {
            "potential_ceiling": 85,
            "growth_curve": "steady",
            "professionalism": 0.8,
            "ambition": 0.7,
            "travel_tolerance": 0.6,
            "schedule_aggression": 0.5,
            "injury_proneness": 0.2,
            "resilience": 0.7,
        },
        "reason": "Run World Package InitialWorld binding acceptance",
        "actor": "package-adapter-test",
    }


@pytest.mark.pr_critical
def test_source_world_package_applies_to_run_and_binds_initial_world_without_live_link(
    tmp_path,
):
    url = f"sqlite:///{tmp_path / 'world-package-api.db'}"
    world_root = copy_builtin_world_packages(tmp_path / "world-packages")
    pool_path = tmp_path / "initial-pool.json"

    server = ApiServer(database_url=url)
    server.app.state.world_packages_root = world_root
    server.app.state.initial_player_pool_config_path = pool_path

    with server:
        status, created = _request(
            "POST",
            f"{server.base_url}/run-containers",
            {"display_name": "Run World adapter"},
        )
        assert status == 201, created
        run_id = created["run_id"]
        branch_id = created["viewer_branch_id"]
        base = (
            f"{server.base_url}/admin/runs/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/packages"
        )
        source_base = base + f"/source-world/{OFFICIAL_FAX_WORLD_ID}"

        status, stale_preview = _request("POST", source_base + "/preview")
        assert status == 200, stale_preview
        source_store = WorldPackageCountryStore(world_root / OFFICIAL_FAX_WORLD_ID)
        first_source_country = source_store.load_config().countries[0]
        source_store.replace_country(
            first_source_country.model_copy(
                update={"notes": "source changed between preview and confirm"}
            )
        )
        stale_confirm = {
            "command_id": "stale-world-apply",
            "expected_head_revision_id": stale_preview["saved_head_revision_id"],
            "expected_draft_version": stale_preview["draft_version"],
            "expected_state_fingerprint": stale_preview["current_state_fingerprint"],
            "expected_preview_fingerprint": stale_preview["preview_fingerprint"],
            "conflict_resolutions": {},
        }
        assert _request("POST", source_base + "/confirm", stale_confirm)[0] == 409

        status, preview = _request("POST", source_base + "/preview")
        assert status == 200, preview
        confirm = {
            "command_id": "apply-world",
            "expected_head_revision_id": preview["saved_head_revision_id"],
            "expected_draft_version": preview["draft_version"],
            "expected_state_fingerprint": preview["current_state_fingerprint"],
            "expected_preview_fingerprint": preview["preview_fingerprint"],
            "conflict_resolutions": {},
        }
        status, applied = _request("POST", source_base + "/confirm", confirm)
        assert status == 200, applied
        assert applied["draft_version"] == 1

        projection_url = base + f"/world/{OFFICIAL_FAX_WORLD_ID}/countries"
        status, projection = _request("GET", projection_url)
        assert status == 200, projection
        assert projection["countries"]
        projection_fingerprint = projection["fingerprint"]
        content_fingerprint = projection["fingerprint"]
        run_country_codes = {country["code"] for country in projection["countries"]}

        save_url = (
            f"{server.base_url}/run-containers/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/working-draft/save"
        )
        status, saved_package = _request(
            "POST", save_url, {"expected_draft_version": 1}
        )
        assert status == 201, saved_package

        source_country = source_store.load_country(next(iter(sorted(run_country_codes))))
        source_store.replace_country(
            source_country.model_copy(update={"notes": "changed after Run Save"})
        )
        status, still_run_owned = _request("GET", projection_url)
        assert status == 200, still_run_owned
        assert still_run_owned["fingerprint"] == projection_fingerprint

        status, global_countries = _request("GET", server.base_url + "/world/countries")
        assert status == 200, global_countries
        global_codes = {country["code"] for country in global_countries["countries"]}
        country_code = next(code for code in sorted(run_country_codes) if code in global_codes)
        status, custom = _request(
            "POST",
            server.base_url + "/admin/players/custom",
            _custom_player(country_code),
        )
        assert status == 200, custom

        world_root_url = (
            f"{server.base_url}/admin/players/runs/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/initial-world"
        )
        adoption = {
            "command_id": "adopt-world-bound-initial-world",
            "source_season": "2000/2001",
            "bootstrap_seed": 200001,
            "audit_label": "World Package adapter acceptance",
            "audit_reason": "Bind Initial World to Run-owned World Package countries",
            "official_run": True,
            "world_package_id": OFFICIAL_FAX_WORLD_ID,
        }
        status, initial_preview = _request(
            "POST", world_root_url + "/preview", adoption
        )
        assert status == 200, initial_preview
        assert initial_preview["state"]["world_package_id"] == OFFICIAL_FAX_WORLD_ID
        assert (
            initial_preview["state"]["world_country_content_fingerprint"]
            is not None
        )

        status, adopted = _post_headers(
            world_root_url,
            adoption,
            {
                "X-Initial-World-Preview-Fingerprint": initial_preview[
                    "fingerprint"
                ]
            },
        )
        assert status == 201, adopted
        bound_content_fingerprint = adopted["world_country_content_fingerprint"]

        status, save_preview = _request("GET", world_root_url + "/save/preview")
        assert status == 200, save_preview
        status, saved_world = _request(
            "POST",
            world_root_url + "/save",
            {
                "expected_draft_version": save_preview["draft_version"],
                "expected_initial_world_fingerprint": save_preview[
                    "initial_world_fingerprint"
                ],
            },
        )
        assert status == 201, saved_world

    reopened = ApiServer(database_url=url)
    reopened.app.state.world_packages_root = world_root
    reopened.app.state.initial_player_pool_config_path = pool_path
    with reopened:
        base = (
            f"{reopened.base_url}/admin/runs/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/packages"
        )
        status, reopened_projection = _request(
            "GET", base + f"/world/{OFFICIAL_FAX_WORLD_ID}/countries"
        )
        assert status == 200, reopened_projection
        assert reopened_projection["fingerprint"] == projection_fingerprint
        world_root_url = (
            f"{reopened.base_url}/admin/players/runs/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/initial-world"
        )
        status, reopened_world = _request("GET", world_root_url)
        assert status == 200, reopened_world
        assert reopened_world["world_package_id"] == OFFICIAL_FAX_WORLD_ID
        assert (
            reopened_world["world_country_content_fingerprint"]
            == bound_content_fingerprint
        )

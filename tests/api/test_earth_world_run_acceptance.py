"""End-to-end acceptance for the built-in FIFA Earth and ATP Earth worlds.

This deliberately covers both production Run layers that exist in R1:

* canonical Product Run/Branch state owns the World Package snapshot and InitialWorld;
* legacy season-attempt runtime owns weekly simulation and persisted talent intake.

The test does not pretend those layers are one object.  It proves that both Earth
packages can cross the real boundaries they currently support without falling back to
live authoring files or flattening their historical country data.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import shutil
from urllib.parse import quote

import pytest

from beta_engine.world_packages import ATP_EARTH_ID, FIFA_EARTH_ID
from tests.api.test_initial_world_ranking_integration import _post_headers
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.support.world_packages import copy_builtin_world_packages


EARTH_WORLD_IDS = (FIFA_EARTH_ID, ATP_EARTH_ID)
INITIAL_POOL_SIZE = 1_000
INITIAL_POOL_SEED = 20261007
REPOSITORY_WORLD_PACKAGES_ROOT = Path("config/world_packages")


def _copy_world_packages_with_earth(destination: Path) -> Path:
    copy_builtin_world_packages(destination)
    for world_id in EARTH_WORLD_IDS:
        shutil.copytree(
            REPOSITORY_WORLD_PACKAGES_ROOT / world_id,
            destination / world_id,
        )
    return destination


def _rating_vector(country: dict[str, object], year: int) -> tuple[float, ...]:
    history = country["rating_history"]
    assert isinstance(history, dict)
    years = history["years"]
    assert isinstance(years, dict)
    entry = years[str(year)]
    assert isinstance(entry, dict)
    ratings = entry["ratings"]
    assert isinstance(ratings, dict)
    return tuple(
        float(ratings[name]["value"])
        for name in (
            "squash_popularity",
            "squash_access",
            "development_quality",
            "competition_quality",
            "elite_support",
            "squash_tradition",
        )
    )


def _apply_earth_world_and_adopt_1000(
    server: ApiServer,
    *,
    world_id: str,
) -> dict[str, object]:
    status, created = _request(
        "POST",
        f"{server.base_url}/run-containers",
        {"display_name": f"Earth acceptance {world_id}"},
    )
    assert status == 201, created
    run_id = created["run_id"]
    branch_id = created["viewer_branch_id"]

    package_root = (
        f"{server.base_url}/admin/runs/{quote(run_id, safe='')}"
        f"/branches/{quote(branch_id, safe='')}/packages"
    )
    source_world_root = package_root + f"/source-world/{world_id}"
    status, package_preview = _request("POST", source_world_root + "/preview")
    assert status == 200, package_preview
    status, applied = _request(
        "POST",
        source_world_root + "/confirm",
        {
            "command_id": f"earth-acceptance-apply-{world_id}",
            "expected_head_revision_id": package_preview["saved_head_revision_id"],
            "expected_draft_version": package_preview["draft_version"],
            "expected_state_fingerprint": package_preview["current_state_fingerprint"],
            "expected_preview_fingerprint": package_preview["preview_fingerprint"],
            "conflict_resolutions": {},
        },
    )
    assert status == 200, applied

    save_url = (
        f"{server.base_url}/run-containers/{quote(run_id, safe='')}"
        f"/branches/{quote(branch_id, safe='')}/working-draft/save"
    )
    status, saved_package = _request(
        "POST",
        save_url,
        {"expected_draft_version": applied["draft_version"]},
    )
    assert status == 201, saved_package

    status, projection = _request(
        "GET",
        package_root + f"/world/{world_id}/countries",
    )
    assert status == 200, projection
    countries = projection["countries"]
    assert len(countries) == 250
    assert all(country["rating_history"] is not None for country in countries)
    assert all(
        set(country["rating_history"]["years"]) == {str(year) for year in range(1955, 2027)}
        for country in countries
    )

    initial_pool_request = {
        "world_package_id": world_id,
        "season": "2000/2001",
        "seed": INITIAL_POOL_SEED,
        "target_pool_size": INITIAL_POOL_SIZE,
    }
    initial_pool_url = (
        f"{server.base_url}/admin/players/runs/{quote(run_id, safe='')}"
        f"/branches/{quote(branch_id, safe='')}"
        "/initial-pool/world-package/preview"
    )
    status, pool = _request("POST", initial_pool_url, initial_pool_request)
    assert status == 200, pool
    assert pool["preview_only"] is True
    assert len(pool["result"]["players"]) == INITIAL_POOL_SIZE
    assert pool["result"]["metadata"]["target_pool_size"] == INITIAL_POOL_SIZE
    assert pool["result"]["metadata"]["population_weighting"] == (
        "effective_population_birth_year_aggregate"
    )
    assert pool["result"]["metadata"]["population_year_min"] < 2000
    assert pool["result"]["metadata"]["population_year_max"] < 2000

    world_root = (
        f"{server.base_url}/admin/players/runs/{quote(run_id, safe='')}"
        f"/branches/{quote(branch_id, safe='')}/initial-world"
    )
    adoption = {
        "command_id": f"earth-acceptance-adopt-{world_id}",
        "generation": initial_pool_request,
        "audit_label": "Earth World integration acceptance",
        "audit_reason": (
            "Bind the reviewed Run-owned Earth World snapshot to a 1000-player "
            "InitialWorld for end-to-end acceptance"
        ),
        "official_run": True,
    }
    status, world_preview = _request(
        "POST",
        world_root + "/world-package/preview",
        adoption,
    )
    assert status == 200, world_preview
    assert len(world_preview["state"]["players"]) == INITIAL_POOL_SIZE
    assert world_preview["state"]["world_package_id"] == world_id
    assert world_preview["state"]["source_kind"] == "run_world_generated_pool.v1"

    status, adopted = _post_headers(
        world_root + "/world-package",
        adoption,
        {
            "X-Initial-World-Preview-Fingerprint": world_preview["fingerprint"],
        },
    )
    assert status == 201, adopted
    assert len(adopted["players"]) == INITIAL_POOL_SIZE

    status, save_preview = _request("GET", world_root + "/save/preview")
    assert status == 200, save_preview
    status, saved_world = _request(
        "POST",
        world_root + "/save",
        {
            "expected_draft_version": save_preview["draft_version"],
            "expected_initial_world_fingerprint": save_preview[
                "initial_world_fingerprint"
            ],
        },
    )
    assert status == 201, saved_world

    return {
        "run_id": run_id,
        "branch_id": branch_id,
        "saved_revision_id": saved_world["saved_revision"]["revision_id"],
        "countries": countries,
        "pool": pool,
        "pool_counts": Counter(
            player["country_code"] for player in pool["result"]["players"]
        ),
        "world_country_content_fingerprint": adopted[
            "world_country_content_fingerprint"
        ],
        "world_generation_content_fingerprint": adopted[
            "world_generation_content_fingerprint"
        ],
        "initial_world_fingerprint": adopted["fingerprint"],
    }


@pytest.mark.pr_critical
def test_both_earth_packages_drive_1000_player_product_runs_save_reopen_and_fork(
    tmp_path,
):
    db_path = tmp_path / "earth-product-run.db"
    world_root = _copy_world_packages_with_earth(tmp_path / "world-packages")
    results: dict[str, dict[str, object]] = {}

    server = ApiServer(database_url=f"sqlite:///{db_path}")
    server.app.state.world_packages_root = world_root
    with server:
        for world_id in EARTH_WORLD_IDS:
            results[world_id] = _apply_earth_world_and_adopt_1000(
                server,
                world_id=world_id,
            )

    fifa_countries = {
        country["code"]: country for country in results[FIFA_EARTH_ID]["countries"]
    }
    atp_countries = {
        country["code"]: country for country in results[ATP_EARTH_ID]["countries"]
    }
    differing_2000 = {
        code
        for code in sorted(set(fifa_countries) & set(atp_countries))
        if _rating_vector(fifa_countries[code], 2000)
        != _rating_vector(atp_countries[code], 2000)
    }
    assert differing_2000

    # Same seed, same season and the same Earth identities still produce different
    # generated worlds when the package histories differ.  This catches accidental
    # flattening/ignoring of the package-owned historical ratings at the Run boundary.
    fifa_pool = results[FIFA_EARTH_ID]["pool"]
    atp_pool = results[ATP_EARTH_ID]["pool"]
    assert fifa_pool["preview_fingerprint"] != atp_pool["preview_fingerprint"]
    assert fifa_pool["result"]["players"] != atp_pool["result"]["players"]
    assert (
        results[FIFA_EARTH_ID]["pool_counts"]
        != results[ATP_EARTH_ID]["pool_counts"]
    )

    reopened = ApiServer(database_url=f"sqlite:///{db_path}")
    reopened.app.state.world_packages_root = world_root
    with reopened:
        for world_id in EARTH_WORLD_IDS:
            result = results[world_id]
            run_id = result["run_id"]
            branch_id = result["branch_id"]
            package_root = (
                f"{reopened.base_url}/admin/runs/{quote(run_id, safe='')}"
                f"/branches/{quote(branch_id, safe='')}/packages"
            )
            status, projection = _request(
                "GET",
                package_root + f"/world/{world_id}/countries",
            )
            assert status == 200, projection
            assert projection["countries"] == result["countries"]

            world_root_url = (
                f"{reopened.base_url}/admin/players/runs/{quote(run_id, safe='')}"
                f"/branches/{quote(branch_id, safe='')}/initial-world"
            )
            status, loaded_world = _request("GET", world_root_url)
            assert status == 200, loaded_world
            assert len(loaded_world["players"]) == INITIAL_POOL_SIZE
            assert loaded_world["world_package_id"] == world_id
            assert loaded_world["world_country_content_fingerprint"] == result[
                "world_country_content_fingerprint"
            ]
            assert loaded_world["world_generation_content_fingerprint"] == result[
                "world_generation_content_fingerprint"
            ]

            status, fork = _request(
                "POST",
                f"{reopened.base_url}/run-containers/{quote(run_id, safe='')}/branches",
                {
                    "source_branch_id": branch_id,
                    "source_saved_revision_id": result["saved_revision_id"],
                    "display_name": f"{world_id} integration fork",
                },
            )
            assert status == 201, fork
            fork_id = fork["branch_id"]

            fork_package_root = (
                f"{reopened.base_url}/admin/runs/{quote(run_id, safe='')}"
                f"/branches/{quote(fork_id, safe='')}/packages"
            )
            status, fork_projection = _request(
                "GET",
                fork_package_root + f"/world/{world_id}/countries",
            )
            assert status == 200, fork_projection
            assert fork_projection["countries"] == result["countries"]

            fork_world_root = (
                f"{reopened.base_url}/admin/players/runs/{quote(run_id, safe='')}"
                f"/branches/{quote(fork_id, safe='')}/initial-world"
            )
            status, fork_world = _request("GET", fork_world_root)
            assert status == 200, fork_world
            assert fork_world["branch_id"] == fork_id
            assert len(fork_world["players"]) == INITIAL_POOL_SIZE
            assert fork_world["world_country_content_fingerprint"] == result[
                "world_country_content_fingerprint"
            ]
            assert fork_world["world_generation_content_fingerprint"] == result[
                "world_generation_content_fingerprint"
            ]


@pytest.mark.pr_critical
@pytest.mark.parametrize("world_id", EARTH_WORLD_IDS)
def test_earth_season_runtime_materializes_generation_and_survives_three_weeks_and_restart(
    tmp_path,
    world_id: str,
):
    db_path = tmp_path / f"{world_id}-season-runtime.db"
    world_root = _copy_world_packages_with_earth(
        tmp_path / f"{world_id}-runtime-world-packages"
    )
    run_id = f"earth-runtime-{world_id}"

    server = ApiServer(database_url=f"sqlite:///{db_path}")
    server.app.state.world_packages_root = world_root
    with server:
        status, created = _request(
            "POST",
            f"{server.base_url}/runs",
            {
                "run_id": run_id,
                "seed": INITIAL_POOL_SEED,
                "season": 2027,
                "world_id": world_id,
            },
        )
        assert status == 201, created
        assert created["world_id"] == world_id

        status, players = _request(
            "GET",
            f"{server.base_url}/runs/{run_id}/players?limit=500",
        )
        assert status == 200, players
        assert players["total"] > 0

        status, cohort = _request(
            "GET",
            f"{server.base_url}/runs/{run_id}/weekly-intake/cohort-season/preview"
            "?base_annual_intake_target=200&season_growth_rate=0.015",
        )
        assert status == 200, cohort
        assert cohort["world_id"] == world_id
        assert len(cohort["weeks"]) == 61
        assert cohort["total_weekly_target"] == cohort["annual_target"]
        assert cohort["annual_target"] > 0

        status, materialized = _request(
            "POST",
            f"{server.base_url}/runs/{run_id}/prospects/materialize-15yo-cohort",
            {
                "base_annual_intake_target": 200,
                "season_growth_rate": 0.015,
                "overwrite": False,
                "expected_review_fingerprint": cohort["review_fingerprint"],
            },
        )
        assert status == 200, materialized
        assert materialized["world_id"] == world_id
        assert materialized["requested_prospect_count"] == cohort["annual_target"]
        assert materialized["created_count"] == cohort["annual_target"]
        assert materialized["total_persisted_for_scope"] == cohort["annual_target"]

        status, before = _request("GET", f"{server.base_url}/runs/{run_id}")
        assert status == 200, before
        for _ in range(3):
            status, step = _request(
                "POST",
                f"{server.base_url}/runs/{run_id}/simulate/next-week",
            )
            assert status == 200, step
        status, after = _request("GET", f"{server.base_url}/runs/{run_id}")
        assert status == 200, after
        assert after != before

        status, persisted_prospects = _request(
            "GET",
            f"{server.base_url}/runs/{run_id}/prospects"
            "?season_start_year=2027&limit=500",
        )
        assert status == 200, persisted_prospects
        assert persisted_prospects["total"] == cohort["annual_target"]
        durable_after = after

    reopened = ApiServer(database_url=f"sqlite:///{db_path}")
    reopened.app.state.world_packages_root = world_root
    with reopened:
        status, loaded = _request("GET", f"{reopened.base_url}/runs/{run_id}")
        assert status == 200, loaded
        assert loaded == durable_after
        assert loaded["run"]["world_id"] == world_id

        status, persisted_prospects = _request(
            "GET",
            f"{reopened.base_url}/runs/{run_id}/prospects"
            "?season_start_year=2027&limit=500",
        )
        assert status == 200, persisted_prospects
        assert persisted_prospects["total"] == cohort["annual_target"]

        status, world_status = _request(
            "GET",
            f"{reopened.base_url}/runs/{run_id}/world-status",
        )
        assert status == 200, world_status
        assert world_status["world_id"] == world_id
        assert world_status["is_stale"] is False

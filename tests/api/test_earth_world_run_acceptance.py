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
from itertools import count
from pathlib import Path
import shutil

import pytest

from beta_engine.application.run_branch_creation_service import RunBranchCreationService
from beta_engine.application.run_container_creation_service import RunContainerCreationService
from beta_engine.application.run_package_service import RunPackageService
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldInitialPoolPreviewRequest,
    RunWorldInitialPoolPreviewService,
)
from beta_engine.application.run_world_initial_world_service import (
    RunWorldInitialWorldAdoptionRequest,
    RunWorldInitialWorldService,
)
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.world_packages import ATP_EARTH_ID, FIFA_EARTH_ID
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


def _id_factory(prefix: str):
    sequence = count(1)

    def make(kind: str) -> str:
        return f"{prefix}-{kind}-{next(sequence)}"

    return make


def _repository(url: str) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    repository = SimulationPersistenceRepository(
        engine=engine,
        session_factory=create_session_factory(engine),
    )
    repository.bootstrap_schema()
    return repository


def _materialize_product_run(
    repository: SimulationPersistenceRepository,
    *,
    world_root: Path,
    world_id: str,
) -> dict[str, object]:
    ids = _id_factory(world_id)
    created = RunContainerCreationService(repository, ids).create_empty_run(
        display_name=f"Earth acceptance {world_id}"
    )
    run_id = created.run_id
    branch_id = created.viewer_branch_id
    assert branch_id is not None

    registry = WorldPackageRegistryService(world_packages_root=world_root)
    adapter = WorldPackageRunAdapter(registry_service=registry)
    package_service = RunPackageService(repository)
    draft_service = RunWorkingDraftService(repository, ids)

    document = adapter.build_document(world_id)
    package_preview = package_service.preview(
        run_id=run_id,
        branch_id=branch_id,
        document=document,
    )
    applied = package_service.confirm(
        run_id=run_id,
        branch_id=branch_id,
        document=document,
        command_id=f"earth-acceptance-apply-{world_id}",
        expected_head_revision_id=package_preview.saved_head_revision_id,
        expected_draft_version=package_preview.draft_version,
        expected_state_fingerprint=package_preview.current_state_fingerprint,
        expected_preview_fingerprint=package_preview.preview_fingerprint,
    )
    draft_service.save(
        run_id=run_id,
        branch_id=branch_id,
        expected_draft_version=applied.draft_version,
    )

    state = package_service.get(run_id=run_id, branch_id=branch_id)
    assert state is not None
    projection = adapter.project_countries(state, package_id=world_id)
    countries = [
        country.model_dump(mode="json") for country in projection.countries
    ]
    assert len(countries) == 250
    assert all(country["rating_history"] is not None for country in countries)
    assert all(
        set(country["rating_history"]["years"])
        == {str(year) for year in range(1955, 2027)}
        for country in countries
    )

    pool_service = RunWorldInitialPoolPreviewService(
        package_service=package_service,
        world_adapter=adapter,
    )
    initial_world_service = RunWorldInitialWorldService(
        preview_service=pool_service
    )
    generation = RunWorldInitialPoolPreviewRequest(
        world_package_id=world_id,
        season="2000/2001",
        seed=INITIAL_POOL_SEED,
        target_pool_size=INITIAL_POOL_SIZE,
    )
    pool = pool_service.preview(
        run_id=run_id,
        branch_id=branch_id,
        request=generation,
    )
    assert len(pool.result.players) == INITIAL_POOL_SIZE
    assert pool.result.metadata.target_pool_size == INITIAL_POOL_SIZE
    assert (
        pool.result.metadata.population_weighting
        == "effective_population_birth_year_aggregate"
    )
    assert pool.result.metadata.population_year_min is not None
    assert pool.result.metadata.population_year_max is not None
    assert pool.result.metadata.population_year_min < 2000
    assert pool.result.metadata.population_year_max < 2000

    adoption_request = RunWorldInitialWorldAdoptionRequest(
        command_id=f"earth-acceptance-adopt-{world_id}",
        generation=generation,
        audit_label="Earth World integration acceptance",
        audit_reason=(
            "Bind the reviewed Run-owned Earth World snapshot to a 1000-player "
            "InitialWorld for end-to-end acceptance"
        ),
        official_run=False,
        best_n=15,
        automatic_retirement_age=46,
    )
    preview_world = initial_world_service.preview(
        run_id=run_id,
        branch_id=branch_id,
        request=adoption_request,
    )
    assert len(preview_world.players) == INITIAL_POOL_SIZE
    assert preview_world.world_package_id == world_id
    assert preview_world.source_kind == "run_world_generated_pool.v1"

    adopted = repository.adopt_initial_world(
        preview_world,
        lifecycle_policy=PlayerLifecyclePolicy(
            policy_id="earth-integration-lifecycle.v1",
            automatic_retirement_age=46,
            provenance="Earth Run integration acceptance",
        ),
    )
    revision_state = repository.get_branch_revision_state(branch_id=branch_id)
    saved_world = draft_service.save_initial_world(
        run_id=run_id,
        branch_id=branch_id,
        expected_draft_version=revision_state.working_draft.draft_version,
        expected_initial_world_fingerprint=adopted.fingerprint,
    )

    return {
        "run_id": run_id,
        "branch_id": branch_id,
        "saved_revision_id": saved_world.saved_revision.revision_id,
        "countries": countries,
        "pool": pool,
        "pool_counts": Counter(
            player.country_code for player in pool.result.players
        ),
        "world_country_content_fingerprint": adopted.world_country_content_fingerprint,
        "world_generation_content_fingerprint": (
            adopted.world_generation_content_fingerprint
        ),
        "initial_world_fingerprint": adopted.fingerprint,
    }


@pytest.mark.pr_critical
def test_both_earth_packages_drive_1000_player_product_runs_save_reopen_and_fork(
    tmp_path,
):
    db_path = tmp_path / "earth-product-run.db"
    database_url = f"sqlite:///{db_path}"
    world_root = _copy_world_packages_with_earth(tmp_path / "world-packages")
    repository = _repository(database_url)
    results: dict[str, dict[str, object]] = {}

    for world_id in EARTH_WORLD_IDS:
        results[world_id] = _materialize_product_run(
            repository,
            world_root=world_root,
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

    fifa_pool = results[FIFA_EARTH_ID]["pool"]
    atp_pool = results[ATP_EARTH_ID]["pool"]
    assert fifa_pool.preview_fingerprint != atp_pool.preview_fingerprint
    assert fifa_pool.result.players != atp_pool.result.players
    assert (
        results[FIFA_EARTH_ID]["pool_counts"]
        != results[ATP_EARTH_ID]["pool_counts"]
    )

    # Reopen through a fresh engine/session factory, then fork the exact Saved
    # Revision. This proves persistence rather than process-local object reuse.
    reopened = _repository(database_url)
    registry = WorldPackageRegistryService(world_packages_root=world_root)
    adapter = WorldPackageRunAdapter(registry_service=registry)
    for world_id in EARTH_WORLD_IDS:
        result = results[world_id]
        run_id = result["run_id"]
        branch_id = result["branch_id"]

        package_state = RunPackageService(reopened).get(
            run_id=run_id,
            branch_id=branch_id,
        )
        assert package_state is not None
        projection = adapter.project_countries(
            package_state,
            package_id=world_id,
        )
        assert [
            country.model_dump(mode="json") for country in projection.countries
        ] == result["countries"]

        loaded_world = reopened.get_initial_world(
            run_id=run_id,
            branch_id=branch_id,
        )
        assert loaded_world is not None
        assert len(loaded_world.players) == INITIAL_POOL_SIZE
        assert loaded_world.world_package_id == world_id
        assert loaded_world.world_country_content_fingerprint == result[
            "world_country_content_fingerprint"
        ]
        assert loaded_world.world_generation_content_fingerprint == result[
            "world_generation_content_fingerprint"
        ]

        fork = RunBranchCreationService(
            reopened,
            _id_factory(f"{world_id}-fork"),
        ).create_from_saved_revision(
            run_id=run_id,
            source_branch_id=branch_id,
            source_saved_revision_id=result["saved_revision_id"],
            display_name=f"{world_id} integration fork",
        )
        fork_state = RunPackageService(reopened).get(
            run_id=run_id,
            branch_id=fork.branch_id,
        )
        assert fork_state is not None
        fork_projection = adapter.project_countries(
            fork_state,
            package_id=world_id,
        )
        assert [
            country.model_dump(mode="json") for country in fork_projection.countries
        ] == result["countries"]

        fork_world = reopened.get_initial_world(
            run_id=run_id,
            branch_id=fork.branch_id,
        )
        assert fork_world is not None
        assert fork_world.branch_id == fork.branch_id
        assert len(fork_world.players) == INITIAL_POOL_SIZE
        assert fork_world.world_country_content_fingerprint == result[
            "world_country_content_fingerprint"
        ]
        assert fork_world.world_generation_content_fingerprint == result[
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

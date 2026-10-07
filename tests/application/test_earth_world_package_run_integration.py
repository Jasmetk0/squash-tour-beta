"""End-to-end Earth World Package Run integration acceptance.

This is deliberately broader than the adapter unit/contract tests.  It exercises the
real HTTP/application/persistence path with the checked-in FIFA/ATP Earth packages:
source Package -> independent Run snapshot -> historical initial generation ->
InitialWorld -> ranking -> three empty authoritative weeks -> Save/reopen -> Branch.
"""

from __future__ import annotations

import math

import pytest

from beta_engine.api.deps import (
    get_season_match_service,
    get_season_point_awards_service,
)
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.countries.population_resolver import resolve_effective_population
from beta_engine.domain.players.initial_pool import initial_pool_birth_year_weights
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.player_sporting_state import get_sporting
from tests.api.test_initial_world_ranking_integration import _post_headers
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.support.world_packages import copy_builtin_world_packages

from test_authoritative_simulation_api import _server_state, confirm
from test_authoritative_three_completed_weeks import _save_ranking, _save_simulation
from test_official_run_full_season_acceptance import (
    _derive_transition_authority,
    _prepare_initial_ranking,
    _save_initial_world,
)


EARTH_WORLD_IDS = ("fifa_earth", "atp_earth")
TARGET_POOL_SIZE = 1_000
GENERATION_SEED = 2_000_071


def _remove_first_three_source_events(server: ApiServer) -> None:
    """Make Weeks 1-3 genuinely empty before their Calendar becomes Run-owned."""

    matches = server.app.dependency_overrides[get_season_match_service]()
    registry = matches._load_registry()
    registry.matches_by_event_id = {
        event_id: package
        for event_id, package in registry.matches_by_event_id.items()
        if not (
            package.season == "2000/2001"
            and package.season_week in {1, 2, 3}
        )
    }
    matches._save_registry(registry)

    awards = server.app.dependency_overrides[get_season_point_awards_service]()
    calendars = awards.calendar_service._load_registry()
    calendar = calendars.calendars_by_season["2000/2001"]
    calendar.events = [
        event for event in calendar.events if event.season_week not in {1, 2, 3}
    ]
    if calendar.metadata is not None:
        calendar.metadata.event_count = len(calendar.events)
    awards.calendar_service._save_registry(calendars)
    server.app.state.season_calendar_registry_path = (
        awards.calendar_service.calendar_registry_path
    )


def _save_package_draft(server: ApiServer, run_id: str, branch_id: str, draft: int) -> str:
    status, saved = _request(
        "POST",
        f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}"
        "/working-draft/save",
        {"expected_draft_version": draft},
    )
    assert status == 201, saved
    return saved["saved_revision"]["revision_id"]


def _apply_source_package(
    server: ApiServer,
    *,
    run_id: str,
    branch_id: str,
    source_suffix: str,
    command_id: str,
) -> tuple[dict, str]:
    base = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/packages"
    source = base + source_suffix
    status, preview = _request("POST", source + "/preview")
    assert status == 200, preview
    status, applied = _request(
        "POST",
        source + "/confirm",
        {
            "command_id": command_id,
            "expected_head_revision_id": preview["saved_head_revision_id"],
            "expected_draft_version": preview["draft_version"],
            "expected_state_fingerprint": preview["current_state_fingerprint"],
            "expected_preview_fingerprint": preview["preview_fingerprint"],
            "conflict_resolutions": {},
        },
    )
    assert status == 200, applied
    revision = _save_package_draft(
        server, run_id, branch_id, applied["draft_version"]
    )
    return applied, revision


def _assert_historical_rating_weighting(pool_preview: dict, country_payload: dict) -> None:
    """Prove allocation used cohort-year ratings rather than flattening to 2026."""

    country = Country.model_validate(country_payload)
    assert country.code == "QAT"
    assert country.rating_history is not None

    # Both checked-in Earth packages have materially different historical QAT
    # values, so this would fail if the Run silently replaced history with 2026.
    historical = country.at_rating_year(1980)
    current = country.at_rating_year(2026)
    assert (
        historical.squash_popularity,
        historical.squash_access,
        historical.development_quality,
    ) != (
        current.squash_popularity,
        current.squash_access,
        current.development_quality,
    )

    diagnostic = next(
        row
        for row in pool_preview["result"]["metadata"]["population_weighting_diagnostics"]
        if row["country_code"] == "QAT"
    )
    birth_year_weights = initial_pool_birth_year_weights(2000)
    model = CountryTalentModel()
    expected_historical_weight = sum(
        cohort_weight
        * model.effective_squash_pool_weight(
            country.at_rating_year(year),
            resolve_effective_population(country, year).effective_population,
        )
        for year, cohort_weight in birth_year_weights.items()
    )
    flattened_current_weight = sum(
        cohort_weight
        * model.effective_squash_pool_weight(
            current,
            resolve_effective_population(country, year).effective_population,
        )
        for year, cohort_weight in birth_year_weights.items()
    )
    assert diagnostic["allocation_weight"] == pytest.approx(
        expected_historical_weight, rel=1e-12, abs=1e-12
    )
    assert not math.isclose(
        expected_historical_weight,
        flattened_current_weight,
        rel_tol=1e-4,
        abs_tol=1e-8,
    )


def _advance_empty_week(
    server: ApiServer,
    *,
    run_id: str,
    branch_id: str,
    revision: str,
    week: int,
) -> str:
    ranking_root = (
        f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
        "/ranking-candidates"
    )
    transition_root = (
        f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
        "/week-transitions"
    )
    sim_root = (
        f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
        "/authoritative-simulation"
    )

    status, position = _request("GET", sim_root + "/position")
    assert status == 200, position
    assert position["current_week"] == {"season_index": 0, "week": week}

    status, completed = _request(
        "POST",
        sim_root + "/empty-week/complete",
        {
            "command_id": f"earth-empty-week-{week}",
            "expected_week": position["current_week"],
            "expected_position_fingerprint": position["position_fingerprint"],
            "expected_revision_id": revision,
            "operator_label": "Earth integration acceptance",
            "audit_reason": "Exercise a real Run-owned Earth package through an event-free week",
        },
    )
    assert status == 201, completed
    assert completed["competitive_match_count"] == 0

    # Capture the completed-week evidence before deriving the next ranking state.
    revision = _save_simulation(sim_root)

    _derive_transition_authority(ranking_root, completed_week=week)
    revision = _save_ranking(server, ranking_root)

    status, preview = _request(
        "POST",
        transition_root + "/derived/preview",
        {"command_id": f"earth-transition-{week}"},
    )
    assert status == 200, preview
    assert preview["command"]["completed_week"] == {
        "season_index": 0,
        "week": week,
    }
    assert preview["command"]["target_week"] == {
        "season_index": 0,
        "week": week + 1,
    }
    status, transitioned = confirm(
        transition_root, preview["command"], preview
    )
    assert status == 201, transitioned
    return _save_ranking(server, ranking_root)


@pytest.mark.pr_critical
@pytest.mark.parametrize("world_id", EARTH_WORLD_IDS)
def test_earth_package_survives_real_run_generation_weeks_reopen_and_fork(
    tmp_path,
    world_id: str,
):
    case_root = tmp_path / world_id
    server, _ = _server_state(case_root)
    database_url = f"sqlite:///{case_root / 'api.sqlite'}"
    world_packages_root = copy_builtin_world_packages(case_root / "world-packages")
    server.app.state.world_packages_root = world_packages_root
    _remove_first_three_source_events(server)

    with server:
        run_id, branch_id, revision = _create_run(
            server,
            display_name=f"{world_id} Earth integration",
        )

        _, revision = _apply_source_package(
            server,
            run_id=run_id,
            branch_id=branch_id,
            source_suffix=f"/source-world/{world_id}",
            command_id=f"apply-{world_id}",
        )
        _, revision = _apply_source_package(
            server,
            run_id=run_id,
            branch_id=branch_id,
            source_suffix="/source-calendar/2000-2001",
            command_id=f"apply-calendar-{world_id}",
        )

        package_root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/packages"
        )
        status, countries = _request(
            "GET", package_root + f"/world/{world_id}/countries"
        )
        assert status == 200, countries
        assert len(countries["countries"]) == 250
        qatar = next(
            country for country in countries["countries"] if country["code"] == "QAT"
        )

        generation = {
            "world_package_id": world_id,
            "season": "2000/2001",
            "seed": GENERATION_SEED,
            "target_pool_size": TARGET_POOL_SIZE,
        }
        pool_url = (
            f"{server.base_url}/admin/players/runs/{run_id}/branches/{branch_id}"
            "/initial-pool/world-package/preview"
        )
        status, pool_preview = _request("POST", pool_url, generation)
        assert status == 200, pool_preview
        assert pool_preview["result"]["summary"]["total_players"] == TARGET_POOL_SIZE
        assert pool_preview["result"]["metadata"]["generated_count"] == TARGET_POOL_SIZE
        assert pool_preview["result"]["summary"]["countries_represented"] > 20
        _assert_historical_rating_weighting(pool_preview, qatar)

        world_root = (
            f"{server.base_url}/admin/players/runs/{run_id}/branches/{branch_id}"
            "/initial-world"
        )
        adoption = {
            "command_id": f"adopt-{world_id}-earth-world",
            "generation": generation,
            "audit_label": "Earth integration acceptance",
            "audit_reason": "Adopt the full reviewed 1000-player Earth integration pool",
            "official_run": True,
        }
        status, world_preview = _request(
            "POST", world_root + "/world-package/preview", adoption
        )
        assert status == 200, world_preview
        assert len(world_preview["state"]["players"]) == TARGET_POOL_SIZE
        assert world_preview["state"]["world_package_id"] == world_id
        status, adopted = _post_headers(
            world_root + "/world-package",
            adoption,
            {
                "X-Initial-World-Preview-Fingerprint": world_preview[
                    "fingerprint"
                ]
            },
        )
        assert status == 201, adopted
        assert len(adopted["players"]) == TARGET_POOL_SIZE
        revision = _save_initial_world(world_root)

        ranking_root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/ranking-candidates"
        )
        initial_ranking_fingerprint = _prepare_initial_ranking(ranking_root)
        revision = _save_ranking(server, ranking_root)
        status, published = _request(
            "POST",
            ranking_root + "/publish-initial",
            {"expected_ranking_fingerprint": initial_ranking_fingerprint},
        )
        assert status == 201, published

        for week in (1, 2, 3):
            revision = _advance_empty_week(
                server,
                run_id=run_id,
                branch_id=branch_id,
                revision=revision,
                week=week,
            )

        sim_root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/authoritative-simulation"
        )
        status, position = _request("GET", sim_root + "/position")
        assert status == 200, position
        assert position["current_week"] == {"season_index": 0, "week": 4}

        with server.app.state.runtime.repository._session_factory() as session:
            week_one = get_sporting(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=RankingWeek(season_index=0, week=1),
            )
            week_four = get_sporting(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=RankingWeek(season_index=0, week=4),
            )
            assert week_one is not None and week_four is not None
            assert len(week_one.players) == TARGET_POOL_SIZE
            assert len(week_four.players) == TARGET_POOL_SIZE
            before = {player.player_id: player for player in week_one.players}
            changed = sum(
                before[player.player_id].attributes != player.attributes
                for player in week_four.players
            )
            assert changed > 0

        source_world_fingerprint = countries["fingerprint"]

    # Restart the API process against the exact same SQLite Run.
    reopened = ApiServer(database_url=database_url)
    reopened.app.state.world_packages_root = world_packages_root
    with reopened:
        package_root = (
            f"{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}/packages"
        )
        status, reopened_countries = _request(
            "GET", package_root + f"/world/{world_id}/countries"
        )
        assert status == 200, reopened_countries
        assert reopened_countries["fingerprint"] == source_world_fingerprint

        world_root = (
            f"{reopened.base_url}/admin/players/runs/{run_id}/branches/{branch_id}"
            "/initial-world"
        )
        status, reopened_world = _request("GET", world_root)
        assert status == 200, reopened_world
        assert len(reopened_world["players"]) == TARGET_POOL_SIZE

        sim_root = (
            f"{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/authoritative-simulation"
        )
        status, reopened_position = _request("GET", sim_root + "/position")
        assert status == 200, reopened_position
        assert reopened_position["current_week"] == {
            "season_index": 0,
            "week": 4,
        }

        status, fork = _request(
            "POST",
            f"{reopened.base_url}/run-containers/{run_id}/branches",
            {
                "source_branch_id": branch_id,
                "source_saved_revision_id": revision,
                "display_name": f"{world_id} week-4 fork",
            },
        )
        assert status == 201, fork
        fork_id = fork["branch_id"]

        status, fork_world = _request(
            "GET",
            f"{reopened.base_url}/admin/players/runs/{run_id}/branches/"
            f"{fork_id}/initial-world",
        )
        assert status == 200, fork_world
        assert len(fork_world["players"]) == TARGET_POOL_SIZE
        assert fork_world["world_package_id"] == world_id

        status, fork_countries = _request(
            "GET",
            f"{reopened.base_url}/admin/runs/{run_id}/branches/{fork_id}/packages"
            f"/world/{world_id}/countries",
        )
        assert status == 200, fork_countries
        assert fork_countries["countries"] == reopened_countries["countries"]

        status, fork_position = _request(
            "GET",
            f"{reopened.base_url}/admin/runs/{run_id}/branches/{fork_id}"
            "/authoritative-simulation/position",
        )
        assert status == 200, fork_position
        assert fork_position["current_week"] == {
            "season_index": 0,
            "week": 4,
        }

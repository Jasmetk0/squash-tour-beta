"""Admin API acceptance for canonical Finals participant selection."""

import pytest

from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.domain.finals import (
    WorldTourFinalsRaceConfiguration,
    WorldTourFinalsRaceInput,
    WorldTourFinalsRacePlayer,
    calculate_world_tour_finals_race,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.run_packages import (
    AppliedPackageVersion,
    PackageType,
    RunPackageEntity,
    RunPackageState,
)
from beta_engine.infrastructure.db.finals_race_authority import (
    WorldTourFinalsRaceAuthorityStore,
)
from beta_engine.infrastructure.db.run_package_state import put_run_package_state
from tests.api.test_saved_revision_history_api import (
    ApiServer,
    _create_run,
    _request,
)


def fp(char: str) -> str:
    return char * 64


def _seed_calendar_and_race(factory, *, run_id: str, branch_id: str):
    source_fingerprint = fp("a")
    entities = [
        RunPackageEntity(
            run_local_id=1,
            source_package_id="calendar-2000-2001",
            source_package_version=1,
            source_package_fingerprint=source_fingerprint,
            source_entity_id="calendar.metadata",
            entity_kind="calendar.metadata.v1",
            entity_schema_version=1,
            scope="season_calendar",
            payload={
                "season": "2000/2001",
                "metadata": None,
                "validation_warnings": [],
                "validation_errors": [],
            },
            source_baseline_fingerprint=fp("b"),
        ),
        RunPackageEntity(
            run_local_id=2,
            source_package_id="calendar-2000-2001",
            source_package_version=1,
            source_package_fingerprint=source_fingerprint,
            source_entity_id="DIRECT-A",
            entity_kind="calendar.event.v1",
            entity_schema_version=1,
            scope="season_calendar",
            payload={
                "event_id": "DIRECT-A",
                "season": "2000/2001",
                "season_week": 4,
                "template_id": "TPL-DIRECT",
                "event_name": "Direct Entry Event",
                "category": "DIAMOND",
                "tour_level": "WORLD_TOUR",
                "host_country": "CZE",
                "region": "EUROPE",
                "main_draw_size": 16,
            },
            source_baseline_fingerprint=fp("c"),
        ),
        RunPackageEntity(
            run_local_id=3,
            source_package_id="calendar-2000-2001",
            source_package_version=1,
            source_package_fingerprint=source_fingerprint,
            source_entity_id="FINALS",
            entity_kind="calendar.event.v1",
            entity_schema_version=1,
            scope="season_calendar",
            payload={
                "event_id": "FINALS",
                "season": "2000/2001",
                "season_week": 20,
                "template_id": "TPL-FINALS",
                "event_name": "World Tour Finals",
                "category": "FINALS",
                "tour_level": "WORLD_TOUR",
                "host_country": "CZE",
                "region": "EUROPE",
                "main_draw_size": 3,
            },
            source_baseline_fingerprint=fp("d"),
        ),
    ]
    state = RunPackageState(
        run_id=run_id,
        branch_id=branch_id,
        entities=tuple(entities),
        package_versions=(
            AppliedPackageVersion(
                package_type=PackageType.CALENDAR,
                package_id="calendar-2000-2001",
                source_version=1,
                source_fingerprint=source_fingerprint,
                document_explicit_scope=("season_calendar",),
                applied_entity_ids=(
                    "calendar.metadata",
                    "DIRECT-A",
                    "FINALS",
                ),
                provenance={"test": "finals-participant-api"},
            ),
        ),
    )
    projection = CalendarPackageRunAdapter.project_calendar(
        state,
        package_id="calendar-2000-2001",
    )
    race_config = WorldTourFinalsRaceConfiguration(
        run_id=run_id,
        branch_id=branch_id,
        target_season_index=0,
        finals_event_id="FINALS",
        eligible_categories=("DIAMOND",),
        best_n=2,
        cutoff_week=RankingWeek(season_index=0, week=10),
        cutoff_official_ranking_fingerprint=fp("e"),
        cutoff_transition_fingerprint=fp("f"),
        calendar_content_fingerprint=projection.content_fingerprint,
        adopted_by_command_id="race-config",
    )
    race = calculate_world_tour_finals_race(
        WorldTourFinalsRaceInput(
            run_id=run_id,
            branch_id=branch_id,
            target_season_index=0,
            cutoff_week=race_config.cutoff_week,
            cutoff_official_ranking_fingerprint=(
                race_config.cutoff_official_ranking_fingerprint
            ),
            eligibility_fingerprint=race_config.eligibility_fingerprint,
            policy_id=race_config.policy_id,
            best_n=race_config.best_n,
            players=tuple(
                WorldTourFinalsRacePlayer(
                    player_id=f"p{index}",
                    tie_break_token=f"token-{index:02d}",
                )
                for index in range(1, 6)
            ),
            eligible_results=(),
        )
    )
    with factory.begin() as session:
        put_run_package_state(session, state)
        store = WorldTourFinalsRaceAuthorityStore(session)
        store.put_configuration(race_config)
        store.put_snapshot(race)
    return race


@pytest.mark.pr_critical
def test_admin_finals_participant_selection_configure_build_and_inspect(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'finals-participant-api.db'}"
    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, _ = _create_run(
            server,
            display_name="Canonical Finals Participants",
        )
        factory = server.app.state.runtime.repository._session_factory
        race = _seed_calendar_and_race(
            factory,
            run_id=run_id,
            branch_id=branch_id,
        )

        base = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/finals-participants/0"
        )

        status, configured = _request(
            "POST",
            base + "/configuration",
            {
                "direct_entry_event_ids": [],
                "command_id": "configure-participants",
            },
        )
        assert status == 201
        assert configured["participant_capacity"] == 3
        assert configured["finals_event_id"] == "FINALS"
        assert configured["race_snapshot_fingerprint"] == race.fingerprint

        status, selected = _request("POST", base + "/snapshot")
        assert status == 201
        assert len(selected["participants"]) == 3
        assert [row["player_id"] for row in selected["participants"]] == [
            row.player_id for row in race.rows[:3]
        ]
        assert [row["seed"] for row in selected["participants"]] == [1, 2, 3]

        status, replay = _request("POST", base + "/snapshot")
        assert status == 201
        assert replay == selected

        status, inspected = _request("GET", base)
        assert status == 200
        assert inspected["configuration"] == configured
        assert inspected["snapshot"] == selected

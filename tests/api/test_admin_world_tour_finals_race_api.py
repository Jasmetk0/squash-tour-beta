"""Admin API acceptance for canonical World Tour Finals Race authority."""

from __future__ import annotations

import pytest

from beta_engine.domain.rankings.command_audit import RankingCommandAudit
from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.domain.run_packages import (
    AppliedPackageVersion,
    PackageType,
    RunPackageEntity,
    RunPackageState,
)
from beta_engine.infrastructure.db.models import (
    PublishedOfficialRankingModel,
    RankingTransitionAuthorityModel,
)
from beta_engine.infrastructure.db.run_package_state import put_run_package_state
from tests.api.test_saved_revision_history_api import (
    ApiServer,
    _create_run,
    _request,
)


def _install_calendar(session, *, run_id: str, branch_id: str) -> None:
    source_fingerprint = "a" * 64
    entities = (
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
            source_baseline_fingerprint="b" * 64,
        ),
        RunPackageEntity(
            run_local_id=2,
            source_package_id="calendar-2000-2001",
            source_package_version=1,
            source_package_fingerprint=source_fingerprint,
            source_entity_id="event-1",
            entity_kind="calendar.event.v1",
            entity_schema_version=1,
            scope="season_calendar",
            payload={
                "event_id": "event-1",
                "season": "2000/2001",
                "season_week": 1,
                "template_id": "tpl-1",
                "event_name": "Diamond One",
                "category": "DIAMOND",
                "tour_level": "WORLD_TOUR",
                "host_country": "CZE",
                "region": "EUROPE",
                "main_draw_size": 4,
            },
            source_baseline_fingerprint="c" * 64,
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
                "template_id": "finals-tpl",
                "event_name": "World Tour Finals",
                "category": "FINALS",
                "tour_level": "WORLD_TOUR",
                "host_country": "CZE",
                "region": "EUROPE",
                "main_draw_size": 8,
            },
            source_baseline_fingerprint="d" * 64,
        ),
    )
    version = AppliedPackageVersion(
        package_type=PackageType.CALENDAR,
        package_id="calendar-2000-2001",
        source_version=1,
        source_fingerprint=source_fingerprint,
        document_explicit_scope=("season_calendar",),
        applied_entity_ids=("calendar.metadata", "event-1", "FINALS"),
        provenance={"test": "finals-race-api"},
    )
    put_run_package_state(
        session,
        RunPackageState(
            run_id=run_id,
            branch_id=branch_id,
            entities=entities,
            package_versions=(version,),
        ),
    )


def _install_cutoff_authorities(
    session,
    *,
    run_id: str,
    branch_id: str,
) -> RankingWeek:
    week_one = RankingWeek(season_index=0, week=1)
    week_two = RankingWeek(season_index=0, week=2)
    players = (
        OfficialRankingPlayer(
            player_id="p1",
            tie_break_token="token-b",
            tour_entry_week=week_one,
            retired=False,
        ),
        OfficialRankingPlayer(
            player_id="p2",
            tie_break_token="token-a",
            tour_entry_week=week_one,
            retired=False,
        ),
    )
    policy = OfficialRankingPolicy(policy_id="official", best_n=15)
    first = calculate_official_ranking(
        run_id=run_id,
        branch_id=branch_id,
        week=week_one,
        policy=policy,
        players=players,
        results=(),
        previous=None,
    )
    cutoff = calculate_official_ranking(
        run_id=run_id,
        branch_id=branch_id,
        week=week_two,
        policy=policy,
        players=players,
        results=(),
        previous=first,
    )
    transition = RankingTransitionAuthority(
        run_id=run_id,
        branch_id=branch_id,
        base_revision_id="revision-1",
        completed_week=week_one,
        target_week=week_two,
        players=players,
        policy=policy,
        provenance="Finals Race API acceptance",
        adopted_by_command_id="transition-week-two",
        audit=RankingCommandAudit(actor_label="test", reason="Race cutoff"),
    )
    session.add(
        PublishedOfficialRankingModel(
            run_id=run_id,
            branch_id=branch_id,
            week_ordinal=week_two.ordinal,
            snapshot_fingerprint=cutoff.fingerprint,
            payload_json=cutoff.model_dump_json(),
        )
    )
    session.add(
        RankingTransitionAuthorityModel(
            run_id=run_id,
            branch_id=branch_id,
            target_ordinal=week_two.ordinal,
            fingerprint=transition.fingerprint,
            payload_json=transition.model_dump_json(),
        )
    )
    session.flush()
    return week_two


@pytest.mark.pr_critical
def test_admin_finals_race_requires_published_cutoff_then_persists_snapshot(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'finals-race-api.db'}"
    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, _ = _create_run(
            server,
            display_name="Canonical Finals Race",
        )
        factory = server.app.state.runtime.repository._session_factory
        with factory.begin() as session:
            _install_calendar(
                session,
                run_id=run_id,
                branch_id=branch_id,
            )

        base = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/finals-race/0"
        )
        payload = {
            "finals_event_id": "FINALS",
            "best_n": 2,
            "eligible_categories": ["DIAMOND"],
            "cutoff_week": {"season_index": 0, "week": 2},
            "command_id": "configure-race",
        }

        status, body = _request("POST", base + "/configuration", payload)
        assert status == 409
        assert body["detail"]["code"] == "finals_race_configuration_invalid"
        assert "published Official Ranking" in body["detail"]["message"]

        with factory.begin() as session:
            cutoff_week = _install_cutoff_authorities(
                session,
                run_id=run_id,
                branch_id=branch_id,
            )

        status, configured = _request("POST", base + "/configuration", payload)
        assert status == 201
        assert configured["cutoff_week"] == cutoff_week.model_dump(mode="json")
        assert configured["eligible_categories"] == ["DIAMOND"]
        assert configured["best_n"] == 2

        status, race = _request("POST", base + "/snapshot")
        assert status == 201
        assert race["cutoff_week"] == cutoff_week.model_dump(mode="json")
        assert [(row["rank"], row["player_id"], row["race_points"]) for row in race["rows"]] == [
            (1, "p2", 0),
            (2, "p1", 0),
        ]

        status, replay = _request("POST", base + "/snapshot")
        assert status == 201
        assert replay == race

        status, inspected = _request("GET", base)
        assert status == 200
        assert inspected["configuration"] == configured
        assert inspected["snapshot"] == race

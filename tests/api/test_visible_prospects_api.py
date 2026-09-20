from __future__ import annotations

import json

import pytest
from urllib.parse import quote

from test_ranking_preparation_preview_api import dump
from test_simulation_api import ApiServer, _request

from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
)
from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    PlayerLifecycleWeekStateModel,
    RunProspectModel,
)
from beta_engine.infrastructure.db.player_lifecycle_state import put_lifecycle
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PlayerTourEntryTriggerStore,
)


def _canonical_run(server: ApiServer, run_id: str = "run") -> tuple[str, str]:
    assert _request(
        "POST",
        f"{server.base_url}/runs",
        {"run_id": run_id, "seed": 47, "season": 2000},
    )[0] == 201
    status, branches = _request(
        "GET",
        f"{server.base_url}/run-branches?run_id={quote(run_id, safe='')}",
    )
    assert status == 200
    branch_id = branches["run_branches"][0]["branch_id"]
    status, checkpoint = _request(
        "POST",
        f"{server.base_url}/branch-checkpoints/capture-initial",
        {"simulation_run_id": run_id},
    )
    assert status == 200
    return branch_id, checkpoint["checkpoint_id"]


@contextmanager
def _database_session(path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{path}"))
    factory = create_session_factory(engine)
    try:
        with factory.begin() as session:
            yield session
    finally:
        engine.dispose()


def _prospect_row(
    *,
    run_id: str,
    prospect_id: str,
    season_week: int,
    year_week: int,
    country_code: str,
) -> RunProspectModel:
    return RunProspectModel(
        prospect_id=prospect_id,
        run_id=run_id,
        world_id="official-world",
        season_start_year=2000,
        season_label="2000/2001",
        season_week=season_week,
        calendar_year=2000,
        year_week=year_week,
        birth_year=1985,
        birth_year_week=year_week,
        age=15,
        country_code=country_code,
        country_name="Czechia" if country_code == "CZE" else "Egypt",
        status="prospect",
        source_type="weekly_15yo_cohort",
        cohort_policy_version="weekly_15yo_cohort_v1",
        profile_version="prospect_profile_v1",
        first_name=None,
        last_name=None,
        display_name=f"{country_code} Prospect",
        short_name=f"{country_code} P.",
        identity_seed=f"identity-{prospect_id}",
        profile_seed=f"profile-{prospect_id}",
        development_seed=f"development-{prospect_id}",
        potential_seed=f"potential-{prospect_id}",
        trait_seed=f"trait-{prospect_id}",
        profile_json=json.dumps(
            {
                "schema_version": "prospect_profile_v1",
                "reserved_for_future_attributes": True,
            }
        ),
        development_json=json.dumps(
            {
                "schema_version": "prospect_profile_v1",
                "reserved_for_future_development": True,
            }
        ),
        potential_json=json.dumps(
            {
                "schema_version": "prospect_profile_v1",
                "reserved_for_future_potential": True,
            }
        ),
        trait_json=json.dumps(
            {
                "schema_version": "prospect_profile_v1",
                "reserved_for_future_traits": True,
            }
        ),
    )


def test_viewer_next_gen_uses_lifecycle_visibility_and_never_future_pregeneration(
    tmp_path,
) -> None:
    path = tmp_path / "visible-prospects.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        branch_id, _ = _canonical_run(server)
        week_one = RankingWeek(season_index=0, week=1)
        week_two = RankingWeek(season_index=0, week=2)

        with _database_session(path) as session:
            opening = put_lifecycle(
                session,
                PlayerLifecycleWeekState(
                    run_id="run",
                    branch_id=branch_id,
                    week=week_one,
                    players=(),
                    source_initial_world_fingerprint="visible-prospect-test",
                ),
            )
            put_lifecycle(
                session,
                PlayerLifecycleWeekState(
                    run_id="run",
                    branch_id=branch_id,
                    week=week_two,
                    players=(
                        PlayerLifecycleIdentity(
                            player_id="prospect-visible",
                            birth_year=1985,
                            birth_year_week=38,
                            tie_break_token="1" * 64,
                            tie_break_provenance="birth-week activation test",
                            tour_entry_week=None,
                            age=15,
                            status="active",
                            origin="run_prospect:weekly_15yo_cohort:prospect_profile_v1",
                        ),
                    ),
                    source_initial_world_fingerprint="visible-prospect-test",
                    predecessor_fingerprint=opening.fingerprint,
                ),
            )
            session.add(
                AuthoritativeWorldStateModel(
                    run_id="run",
                    branch_id=branch_id,
                    current_ordinal=week_two.ordinal,
                    ranking_fingerprint="a" * 64,
                )
            )
            session.add(
                _prospect_row(
                    run_id="run",
                    prospect_id="prospect-visible",
                    season_week=2,
                    year_week=38,
                    country_code="CZE",
                )
            )
            session.add(
                _prospect_row(
                    run_id="run",
                    prospect_id="prospect-future",
                    season_week=3,
                    year_week=39,
                    country_code="EGY",
                )
            )

        before = dump(path)
        status, viewer = _request(
            "GET",
            f"{server.base_url}/viewer/runs/run/prospects/next-gen",
        )
        assert status == 200, viewer
        assert viewer["schema_version"] == "visible_pre_tour_prospects.v1"
        assert viewer["run_id"] == "run"
        assert viewer["branch_id"] == branch_id
        assert viewer["week"] == {"season_index": 0, "week": 2}
        assert viewer["total"] == 1
        assert viewer["limit"] == 100
        assert viewer["offset"] == 0
        assert [player["player_id"] for player in viewer["prospects"]] == [
            "prospect-visible"
        ]
        prospect = viewer["prospects"][0]
        assert prospect["display_name"] == "CZE Prospect"
        assert prospect["country_code"] == "CZE"
        assert prospect["age"] == 15
        assert prospect["tour_status"] == "pre_tour"
        assert prospect["visible_since_week"] == {"season_index": 0, "week": 2}
        assert "identity_seed" not in prospect
        assert "profile_json" not in prospect
        assert "potential_json" not in prospect
        assert "cohort_policy_version" not in prospect
        assert "profile_version" not in prospect

        # Admin can inspect exact historical branch snapshots. Before the birthday
        # week the player is not visible even though the pregenerated row exists.
        status, before_birth = _request(
            "GET",
            f"{server.base_url}/admin/runs/run/branches/{quote(branch_id, safe='')}"
            "/prospects/visible?season_index=0&week=1",
        )
        assert status == 200, before_birth
        assert before_birth["total"] == 0

        status, at_birth = _request(
            "GET",
            f"{server.base_url}/admin/runs/run/branches/{quote(branch_id, safe='')}"
            "/prospects/visible?season_index=0&week=2",
        )
        assert status == 200, at_birth
        assert [player["player_id"] for player in at_birth["prospects"]] == [
            "prospect-visible"
        ]

        # Pagination is applied after lifecycle visibility. The raw table contains
        # a second, future prospect, but it must not affect public totals/pages.
        status, second_page = _request(
            "GET",
            f"{server.base_url}/viewer/runs/run/prospects/next-gen?limit=1&offset=1",
        )
        assert status == 200, second_page
        assert second_page["total"] == 1
        assert second_page["limit"] == 1
        assert second_page["offset"] == 1
        assert second_page["prospects"] == []
        assert dump(path) == before


@pytest.mark.pr_critical
def test_current_viewer_stops_exposing_prospect_after_midweek_tour_entry_but_history_stays_exact(
    tmp_path,
) -> None:
    path = tmp_path / "visible-prospect-tour-entry.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        branch_id, _ = _canonical_run(server)
        week = RankingWeek(season_index=0, week=2)

        with _database_session(path) as session:
            put_lifecycle(
                session,
                PlayerLifecycleWeekState(
                    run_id="run",
                    branch_id=branch_id,
                    week=week,
                    players=(
                        PlayerLifecycleIdentity(
                            player_id="prospect-entry",
                            birth_year=1985,
                            birth_year_week=38,
                            tie_break_token="3" * 64,
                            tie_break_provenance="tour-entry read projection test",
                            tour_entry_week=None,
                            age=15,
                            status="active",
                            origin="run_prospect:weekly_15yo_cohort:prospect_profile_v1",
                        ),
                    ),
                    source_initial_world_fingerprint="visible-prospect-entry-test",
                ),
            )
            session.add(
                AuthoritativeWorldStateModel(
                    run_id="run",
                    branch_id=branch_id,
                    current_ordinal=week.ordinal,
                    ranking_fingerprint="c" * 64,
                )
            )
            session.add(
                _prospect_row(
                    run_id="run",
                    prospect_id="prospect-entry",
                    season_week=2,
                    year_week=38,
                    country_code="CZE",
                )
            )
            PlayerTourEntryTriggerStore(session).append(
                PlayerTourEntryTrigger(
                    run_id="run",
                    branch_id=branch_id,
                    player_id="prospect-entry",
                    event_id="event-entry",
                    trigger_kind="valid_tournament_application",
                    trigger_week=week,
                    decision_slot_ordinal=4,
                    source_evidence_id="application-entry",
                    source_evidence_fingerprint="d" * 64,
                    provenance="test application submission authority",
                )
            )

        status, current = _request(
            "GET",
            f"{server.base_url}/viewer/runs/run/prospects/next-gen",
        )
        assert status == 200, current
        assert current["week"] == {"season_index": 0, "week": 2}
        assert current["total"] == 0
        assert current["prospects"] == []

        # Explicit historical week access remains the exact immutable week-opening
        # snapshot until Time Machine supports a slot-level as-of cursor.
        status, historical = _request(
            "GET",
            f"{server.base_url}/admin/runs/run/branches/{quote(branch_id, safe='')}"
            "/prospects/visible?season_index=0&week=2",
        )
        assert status == 200, historical
        assert historical["total"] == 1
        assert [player["player_id"] for player in historical["prospects"]] == [
            "prospect-entry"
        ]


def test_viewer_next_gen_fails_closed_without_canonical_world_or_metadata(tmp_path) -> None:
    path = tmp_path / "visible-prospects-fail-closed.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        branch_id, _ = _canonical_run(server)
        week = RankingWeek(season_index=0, week=1)
        with _database_session(path) as session:
            put_lifecycle(
                session,
                PlayerLifecycleWeekState(
                    run_id="run",
                    branch_id=branch_id,
                    week=week,
                    players=(),
                    source_initial_world_fingerprint="visible-prospect-test",
                ),
            )

        assert _request(
            "GET",
            f"{server.base_url}/viewer/runs/run/prospects/next-gen",
        )[0] == 409

        with _database_session(path) as session:
            session.add(
                AuthoritativeWorldStateModel(
                    run_id="run",
                    branch_id=branch_id,
                    current_ordinal=week.ordinal,
                    ranking_fingerprint="b" * 64,
                )
            )
            # Corrupt historical state: lifecycle says this Run prospect is visible,
            # but its metadata row is missing.
            existing = session.get(
                PlayerLifecycleWeekStateModel,
                ("run", branch_id, week.ordinal),
            )
            session.delete(existing)
            put_lifecycle(
                session,
                PlayerLifecycleWeekState(
                    run_id="run",
                    branch_id=branch_id,
                    week=week,
                    players=(
                        PlayerLifecycleIdentity(
                            player_id="missing-prospect-row",
                            birth_year=1985,
                            birth_year_week=37,
                            tie_break_token="2" * 64,
                            tie_break_provenance="corrupt read model fixture",
                            tour_entry_week=None,
                            age=15,
                            status="active",
                            origin="run_prospect:weekly_15yo_cohort:prospect_profile_v1",
                        ),
                    ),
                    source_initial_world_fingerprint="visible-prospect-test",
                ),
            )

        status, body = _request(
            "GET",
            f"{server.base_url}/viewer/runs/run/prospects/next-gen",
        )
        assert status == 409
        assert "missing its Run prospect metadata" in str(body)

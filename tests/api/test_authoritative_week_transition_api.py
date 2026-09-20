"""Real HTTP/file-backed SQLite acceptance tests for atomic Week Transition."""

import sqlite3
import json
from urllib import error, request

import pytest
from beta_engine.application.authoritative_week_transition import AuthoritativeWeekTransitionCommand
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.calendar.season_weeks import (
    birth_year_for_age_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.infrastructure.db.player_lifecycle_state import put_lifecycle
from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.prospect_sporting_profile import (
    DEFAULT_PROSPECT_SPORTING_PROFILE_POLICY,
    materialize_prospect_sporting_profile,
)
from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    CompetitiveMatchCount,
    PlayerSportingRecord,
    PlayerSportingWeekState,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    put_completed_context,
    put_sporting,
)
from beta_engine.infrastructure.db.models import RunProspectModel

from test_admin_ranking_preparation_api import initial
from test_ranking_preparation_preview_api import dump
from test_saved_revision_history_api import ApiServer, _create_run, _request
import beta_engine.infrastructure.db.authoritative_week_transition as transition_module


def confirm(url, command, preview):
    req = request.Request(
        url,
        data=json.dumps(command).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Week-Transition-Request-Fingerprint": preview["request_fingerprint"],
            "X-Week-Transition-Ranking-Fingerprint": preview["result"][
                "official_ranking_fingerprint"
            ],
            "X-Week-Transition-Lifecycle-Fingerprint": preview["result"][
                "player_lifecycle_fingerprint"
            ],
            "X-Week-Transition-Sporting-Fingerprint": preview["result"][
                "player_sporting_fingerprint"
            ],
        },
    )
    try:
        with request.urlopen(req) as response:
            return response.status, json.loads(response.read())
    except error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def counts(path):
    with sqlite3.connect(path) as connection:
        return tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "published_official_rankings",
                "authoritative_world_states",
                "authoritative_world_events",
                "authoritative_week_transition_receipts",
            )
        )


def install_owned_lifecycle(
    server, run_id, branch_id, players, *, ages=None, birth_weeks=None
):
    """This legacy ranking fixture predates initial-world adoption; install owned test truth."""
    week = RankingWeek(season_index=0, week=1)
    position = season_week_to_calendar_position(2000, 1)
    identities = tuple(
        PlayerLifecycleIdentity(
            player_id=player["player_id"],
            birth_year=birth_year_for_age_at_calendar_position(
                age=(ages or {}).get(player["player_id"], 30 - index),
                birth_year_week=(birth_weeks or {}).get(
                    player["player_id"], 40 + index
                ),
                calendar_year=position.calendar_year,
                year_week=position.year_week,
            ),
            birth_year_week=(birth_weeks or {}).get(player["player_id"], 40 + index),
            age=(ages or {}).get(player["player_id"], 30 - index),
            tie_break_token=player["tie_break_token"],
            tie_break_provenance="acceptance fixture",
            tour_entry_week=week,
            status="active",
            origin="isolated acceptance fixture",
        )
        for index, player in enumerate(players)
    )
    with server.app.state.runtime.repository._session_factory.begin() as session:
        put_lifecycle(
            session,
            PlayerLifecycleWeekState(
                run_id=run_id,
                branch_id=branch_id,
                week=week,
                players=identities,
                source_initial_world_fingerprint="acceptance-fixture",
            ),
        )
        put_sporting(
            session,
            PlayerSportingWeekState(
                run_id=run_id,
                branch_id=branch_id,
                week=week,
                players=tuple(
                    PlayerSportingRecord(
                        player_id=identity.player_id,
                        attributes=tuple(
                            (name, 100) for name in CANONICAL_PLAYER_ATTRIBUTES
                        ),
                        potential_ovr=120,
                        potential_identity=f"fixture:{identity.player_id}",
                        potential_provenance="isolated acceptance fixture",
                        development_timing="Standard",
                        current_form=110,
                        long_term_form_norm=100,
                        match_sharpness=90,
                        long_term_fatigue=20,
                    )
                    for identity in identities
                ),
                completed_context_fingerprint="bootstrap:not-a-completed-week",
                source_initial_world_fingerprint="acceptance-fixture",
                stage_provenance="isolated acceptance fixture",
            ),
        )
        put_completed_context(
            session,
            CompletedWeekSportingContext(
                run_id=run_id,
                branch_id=branch_id,
                completed_week=week,
                competitive_match_counts=tuple(
                    CompetitiveMatchCount(player_id=identity.player_id, count=0)
                    for identity in identities
                ),
                source_fingerprints=("isolated-authoritative-fixture",),
                provenance="isolated test authority explicitly proves no matches",
            ),
        )


def prepared_transition(server, name, *, retirement_player=False):
    run_id, branch_id, empty_revision = _create_run(server, display_name=name)
    ranking = (
        f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
    )
    bootstrap = initial() | {"run_id": run_id, "branch_id": branch_id}
    assert _request("POST", ranking + "/prepare/initial", bootstrap)[0] == 201
    selected = bootstrap["players"][0]["player_id"]
    install_owned_lifecycle(
        server,
        run_id,
        branch_id,
        bootstrap["players"],
        ages={selected: 45} if retirement_player else None,
        birth_weeks={selected: 38} if retirement_player else None,
    )
    authority = {
        "run_id": run_id,
        "branch_id": branch_id,
        "base_revision_id": empty_revision,
        "completed_week": {"season_index": 0, "week": 1},
        "target_week": {"season_index": 0, "week": 2},
        "players": bootstrap["players"],
        "policy": bootstrap["policy"],
        "provenance": "Frozen boundary",
        "adopted_by_command_id": "authority",
        "audit": bootstrap["audit"],
    }
    adopted = _request("POST", ranking + "/transition-authorities", authority)[1]
    review = _request("GET", ranking + "/save/preview")[1]
    saved = _request(
        "POST",
        ranking + "/save",
        {
            "expected_draft_version": review["draft_version"],
            "expected_ranking_fingerprint": review["ranking_fingerprint"],
        },
    )[1]
    command = {
        "command_id": "transition",
        "run_id": run_id,
        "branch_id": branch_id,
        "base_revision_id": saved["saved_revision"]["revision_id"],
        "completed_week": authority["completed_week"],
        "target_week": authority["target_week"],
        "authority_fingerprint": RankingTransitionAuthority.model_validate_json(
            json.dumps(adopted)
        ).fingerprint,
        "tournaments": [],
        "audit": bootstrap["audit"],
    }
    return run_id, branch_id, command


def birth_week_prospect_model(
    *,
    run_id: str,
    target: RankingWeek,
    identity_seed: str = "identity-seed",
    canonical_profile: bool = True,
) -> RunProspectModel:
    position = season_week_to_calendar_position(2000 + target.season_index, target.week)
    profile_seed = "profile-seed"
    development_seed = "development-seed"
    potential_seed = "potential-seed"

    if canonical_profile:
        canonical = materialize_prospect_sporting_profile(
            player_id="prospect-week-2",
            profile_seed=profile_seed,
            development_seed=development_seed,
            potential_seed=potential_seed,
        )
        fingerprint = canonical.fingerprint
        profile_json = {
            "schema_version": "prospect_profile_v1",
            "canonical_sporting_profile": canonical.model_dump(mode="json"),
            "canonical_sporting_profile_fingerprint": fingerprint,
            "materialization_policy": {
                "sporting_profile_policy_id": canonical.profile_policy_id,
                "sporting_profile_policy_fingerprint": canonical.profile_policy_fingerprint,
            },
        }
        development_json = {
            "schema_version": "prospect_profile_v1",
            "development_timing": canonical.development_timing,
            "source_development_seed_digest": canonical.source_development_seed_digest,
            "sporting_profile_fingerprint": fingerprint,
        }
        potential_json = {
            "schema_version": "prospect_profile_v1",
            "potential_ovr": canonical.potential_ovr,
            "potential_identity": canonical.potential_identity,
            "potential_provenance": canonical.potential_provenance,
            "source_potential_seed_digest": canonical.source_potential_seed_digest,
            "sporting_profile_fingerprint": fingerprint,
        }
    else:
        profile_json = {
            "schema_version": "prospect_profile_v1",
            "reserved_for_future_attributes": True,
        }
        development_json = {
            "schema_version": "prospect_profile_v1",
            "reserved_for_future_development": True,
        }
        potential_json = {
            "schema_version": "prospect_profile_v1",
            "reserved_for_future_potential": True,
        }

    return RunProspectModel(
        prospect_id="prospect-week-2",
        run_id=run_id,
        world_id="official-world",
        season_start_year=2000 + target.season_index,
        season_label=f"{2000 + target.season_index}/{2001 + target.season_index}",
        season_week=target.week,
        calendar_year=position.calendar_year,
        year_week=position.year_week,
        birth_year=position.calendar_year - 15,
        birth_year_week=position.year_week,
        age=15,
        country_code="CZE",
        country_name="Czechia",
        status="prospect",
        source_type="weekly_15yo_cohort",
        cohort_policy_version="weekly_15yo_cohort_v1",
        profile_version="prospect_profile_v1",
        first_name=None,
        last_name=None,
        display_name="CZE Prospect 0001",
        short_name="CZE Prospect 0001",
        identity_seed=identity_seed,
        profile_seed=profile_seed,
        development_seed=development_seed,
        potential_seed=potential_seed,
        trait_seed="trait-seed",
        profile_json=json.dumps(profile_json),
        development_json=json.dumps(development_json),
        potential_json=json.dumps(potential_json),
        trait_json=json.dumps({
            "schema_version": "prospect_profile_v1",
            "reserved_for_future_traits": True,
        }),
    )


@pytest.mark.pr_critical
def test_prospect_bridge_inspection_exposes_nonblocking_target_week_profile_readiness(tmp_path):
    path = tmp_path / "prospect-bridge-inspection.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, _ = prepared_transition(
            server,
            "Prospect bridge inspection",
        )
        target = RankingWeek(season_index=0, week=2)
        position = season_week_to_calendar_position(2000, target.week)
        with server.app.state.runtime.repository._session_factory.begin() as session:
            session.add(
                RunProspectModel(
                    prospect_id="prospect-week-2",
                    run_id=run_id,
                    world_id="official-world",
                    season_start_year=2000,
                    season_label="2000/2001",
                    season_week=2,
                    calendar_year=position.calendar_year,
                    year_week=position.year_week,
                    birth_year=1985,
                    birth_year_week=position.year_week,
                    age=15,
                    country_code="CZE",
                    country_name="Czechia",
                    status="prospect",
                    source_type="weekly_15yo_cohort",
                    cohort_policy_version="weekly_15yo_cohort_v1",
                    profile_version="prospect_profile_v1",
                    first_name=None,
                    last_name=None,
                    display_name="CZE Prospect 0001",
                    short_name="CZE Prospect 0001",
                    identity_seed="identity-seed",
                    profile_seed="profile-seed",
                    development_seed="development-seed",
                    potential_seed="potential-seed",
                    trait_seed="trait-seed",
                    profile_json=json.dumps({
                        "schema_version": "prospect_profile_v1",
                        "reserved_for_future_attributes": True,
                    }),
                    development_json=json.dumps({
                        "schema_version": "prospect_profile_v1",
                        "reserved_for_future_development": True,
                    }),
                    potential_json=json.dumps({
                        "schema_version": "prospect_profile_v1",
                        "reserved_for_future_potential": True,
                    }),
                    trait_json=json.dumps({
                        "schema_version": "prospect_profile_v1",
                        "reserved_for_future_traits": True,
                    }),
                )
            )

        before = dump(path)
        root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/"
            "authoritative-simulation/prospect-bridge"
        )
        status, inspection = _request("GET", root)
        assert status == 200, inspection
        assert dump(path) == before
        assert inspection["schema_version"] == "prospect_bridge_inspection.v1"
        assert inspection["completed_week"] == {"season_index": 0, "week": 1}
        assert inspection["target_week"] == {"season_index": 0, "week": 2}
        assert inspection["run_scoped_source"] is True
        assert inspection["bridge_supported"] is True
        assert inspection["blocking_code"] == "no_transition_blocker"
        assert inspection["unresolved_contracts"] == [
            "canonical_sporting_profile",
        ]
        assert len(inspection["inspection_fingerprint"]) == 64
        assert inspection["prospects"] == [{
            "prospect_id": "prospect-week-2",
            "display_name": "CZE Prospect 0001",
            "country_code": "CZE",
            "age": 15,
            "status": "prospect",
            "source_type": "weekly_15yo_cohort",
            "cohort_policy_version": "weekly_15yo_cohort_v1",
            "profile_version": "prospect_profile_v1",
            "profile_placeholder": True,
            "development_placeholder": True,
            "potential_placeholder": True,
            "trait_placeholder": True,
        }]


@pytest.mark.pr_critical
def test_week_transition_blocks_birth_week_placeholder_sporting_profile(tmp_path):
    path = tmp_path / "prospect-placeholder-blocker.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(
            server,
            "Prospect placeholder blocker",
        )
        target = RankingWeek(season_index=0, week=2)
        with server.app.state.runtime.repository._session_factory.begin() as session:
            session.add(
                birth_week_prospect_model(
                    run_id=run_id,
                    target=target,
                    canonical_profile=False,
                )
            )

        root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/"
            "week-transitions"
        )
        status, blocked = _request("POST", root + "/preview", command)
        assert status == 409, blocked
        assert "prospect_sporting_profile_unready" in str(blocked)

        with sqlite3.connect(path) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM player_lifecycle_week_states "
                "WHERE week_ordinal=?",
                (target.ordinal,),
            ).fetchone()[0] == 0
            assert connection.execute(
                "SELECT COUNT(*) FROM player_sporting_week_states "
                "WHERE week_ordinal=?",
                (target.ordinal,),
            ).fetchone()[0] == 0


@pytest.mark.pr_critical
def test_week_transition_activates_birth_week_prospect_in_sporting_but_not_ranking(tmp_path):
    path = tmp_path / "prospect-birth-week-transition.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(
            server,
            "Prospect birth-week transition",
        )
        target = RankingWeek(season_index=0, week=2)
        with server.app.state.runtime.repository._session_factory.begin() as session:
            session.add(
                birth_week_prospect_model(
                    run_id=run_id,
                    target=target,
                    canonical_profile=True,
                )
            )

        root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/"
            "week-transitions"
        )
        status, preview = _request("POST", root + "/preview", command)
        assert status == 200, preview

        status, confirmed = confirm(root, command, preview)
        assert status == 201, confirmed

        with sqlite3.connect(path) as connection:
            lifecycle = json.loads(
                connection.execute(
                    "SELECT payload_json FROM player_lifecycle_week_states "
                    "WHERE week_ordinal=?",
                    (target.ordinal,),
                ).fetchone()[0]
            )
            predecessor_lifecycle = json.loads(
                connection.execute(
                    "SELECT payload_json FROM player_lifecycle_week_states "
                    "WHERE week_ordinal=0"
                ).fetchone()[0]
            )
            sporting = json.loads(
                connection.execute(
                    "SELECT payload_json FROM player_sporting_week_states "
                    "WHERE week_ordinal=?",
                    (target.ordinal,),
                ).fetchone()[0]
            )
            ranking_request = json.loads(
                connection.execute(
                    "SELECT request_payload_json FROM official_ranking_commands "
                    "WHERE target_ordinal=?",
                    (target.ordinal,),
                ).fetchone()[0]
            )

        assert "prospect-week-2" not in {
            player["player_id"] for player in predecessor_lifecycle["players"]
        }
        lifecycle_prospect = next(
            player
            for player in lifecycle["players"]
            if player["player_id"] == "prospect-week-2"
        )
        assert lifecycle_prospect["age"] == 15
        assert lifecycle_prospect["tour_entry_week"] is None
        assert lifecycle_prospect["status"] == "active"
        assert len(lifecycle_prospect["tie_break_token"]) == 64

        sporting_prospect = next(
            player
            for player in sporting["players"]
            if player["player_id"] == "prospect-week-2"
        )
        canonical = materialize_prospect_sporting_profile(
            player_id="prospect-week-2",
            profile_seed="profile-seed",
            development_seed="development-seed",
            potential_seed="potential-seed",
        )
        assert sporting_prospect["attributes"] == [
            list(attribute) for attribute in canonical.attributes
        ]
        assert sporting_prospect["potential_ovr"] == canonical.potential_ovr
        assert sporting_prospect["development_timing"] == canonical.development_timing
        defaults = sporting["effective_development_policy"]["bootstrap_policy"]
        assert sporting_prospect["current_form"] == defaults["default_form"]
        assert sporting_prospect["long_term_form_norm"] == defaults["default_form_norm"]
        assert sporting_prospect["match_sharpness"] == defaults["default_match_sharpness"]
        assert sporting_prospect["long_term_fatigue"] == defaults["default_fatigue"]
        assert "birth_week_prospect_sporting_adoption.v1" in sporting["stage_provenance"]

        assert "prospect-week-2" not in {
            player["player_id"]
            for player in ranking_request["context"]["players"]
        }


@pytest.mark.pr_critical
def test_birth_week_prospect_change_after_preview_rolls_back_confirm(tmp_path):
    path = tmp_path / "prospect-preview-stale.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(
            server,
            "Prospect preview stale guard",
        )
        target = RankingWeek(season_index=0, week=2)
        with server.app.state.runtime.repository._session_factory.begin() as session:
            session.add(
                birth_week_prospect_model(
                    run_id=run_id,
                    target=target,
                    identity_seed="identity-seed-before-preview",
                    canonical_profile=True,
                )
            )

        root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/"
            "week-transitions"
        )
        status, preview = _request("POST", root + "/preview", command)
        assert status == 200, preview

        # Birth-week identity contributes to the staged lifecycle while the canonical
        # profile contributes to target sporting. Neither grants Tour/ranking status.
        with sqlite3.connect(path) as connection:
            connection.execute(
                "UPDATE run_prospects SET identity_seed=? "
                "WHERE run_id=? AND prospect_id=?",
                ("identity-seed-after-preview", run_id, "prospect-week-2"),
            )
            connection.commit()

        mutated = dump(path)
        mutated_counts = counts(path)
        status, conflict = confirm(root, command, preview)
        assert status == 409, conflict
        assert "inputs changed since preview" in str(conflict)
        assert dump(path) == mutated
        assert counts(path) == mutated_counts

        with sqlite3.connect(path) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM player_lifecycle_week_states "
                "WHERE week_ordinal=?",
                (target.ordinal,),
            ).fetchone()[0] == 0
            assert connection.execute(
                "SELECT COUNT(*) FROM player_sporting_week_states "
                "WHERE week_ordinal=?",
                (target.ordinal,),
            ).fetchone()[0] == 0
            assert connection.execute(
                "SELECT COUNT(*) FROM official_ranking_commands "
                "WHERE target_ordinal=?",
                (target.ordinal,),
            ).fetchone()[0] == 0


@pytest.mark.pr_critical
def test_server_derived_preview_freezes_current_authoritative_transition_request(tmp_path):
    path = tmp_path / "derived-week-transition.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, manual = prepared_transition(
            server,
            "server derived week transition",
        )
        root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/"
            "week-transitions"
        )
        status, preview = _request(
            "POST",
            root + "/derived/preview",
            {"command_id": "derived-transition"},
        )
        assert status == 200, preview
        command = preview["command"]
        expected = AuthoritativeWeekTransitionCommand.model_validate_json(
            json.dumps(manual | {"command_id": "derived-transition"})
        )
        assert command == expected.model_dump(mode="json")
        assert preview["request_fingerprint"] == expected.fingerprint

        status, confirmed = confirm(root, command, preview)
        assert status == 201
        assert confirmed["result"] == preview["result"]

        # The exact frozen command remains a valid idempotent retry even though
        # current persisted state has already advanced.
        assert confirm(root, command, preview) == (201, confirmed)


def test_real_http_retirement_preview_confirm_and_exact_retry(tmp_path):
    path = tmp_path / "retirement.db"
    retired_revision = None
    retired_draft_version = None
    run_id = branch_id = None
    predecessor_revision = None
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(
            server, "automatic retirement", retirement_player=True
        )
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        status, preview = _request("POST", root + "/preview", command)
        assert status == 200, preview
        lifecycle_fp = preview["result"]["player_lifecycle_fingerprint"]
        sporting_fp = preview["result"]["player_sporting_fingerprint"]
        with sqlite3.connect(path) as connection:
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM player_lifecycle_week_states WHERE week_ordinal=1"
                ).fetchone()[0]
                == 0
            )
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM player_sporting_week_states WHERE week_ordinal=1"
                ).fetchone()[0]
                == 0
            )
        status, result = confirm(root, command, preview)
        assert (
            status == 201
            and result["result"]["player_lifecycle_fingerprint"] == lifecycle_fp
            and result["result"]["player_sporting_fingerprint"] == sporting_fp
        )
        with sqlite3.connect(path) as connection:
            payload = json.loads(
                connection.execute(
                    "SELECT payload_json FROM player_lifecycle_week_states WHERE week_ordinal=1"
                ).fetchone()[0]
            )
            ranking_request = json.loads(
                connection.execute(
                    "SELECT request_payload_json FROM official_ranking_commands WHERE target_ordinal=1"
                ).fetchone()[0]
            )
            sporting_payload = json.loads(
                connection.execute(
                    "SELECT payload_json FROM player_sporting_week_states WHERE week_ordinal=1"
                ).fetchone()[0]
            )
        assert sporting_payload["predecessor_fingerprint"]
        assert all(
            player["current_form"] == 109
            and player["match_sharpness"] == 88
            and player["long_term_fatigue"] == 12
            for player in sporting_payload["players"]
        )
        retired = next(player for player in payload["players"] if player["age"] == 46)
        assert retired["status"] == "retired"
        assert retired["retirement_effective_week"] == {"season_index": 0, "week": 2}
        assert (
            next(
                player
                for player in ranking_request["context"]["players"]
                if player["player_id"] == retired["player_id"]
            )["retired"]
            is True
        )
        assert confirm(root, command, preview) == (201, result)
        with sqlite3.connect(path) as connection:
            payload_retry = connection.execute(
                "SELECT payload_json FROM player_lifecycle_week_states WHERE week_ordinal=1"
            ).fetchone()[0]
            sporting_retry = connection.execute(
                "SELECT payload_json FROM player_sporting_week_states WHERE week_ordinal=1"
            ).fetchone()[0]
        assert json.loads(payload_retry) == payload
        assert json.loads(sporting_retry) == sporting_payload
        ranking = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
        review = _request("GET", ranking + "/save/preview")[1]
        status, saved = _request(
            "POST",
            ranking + "/save",
            {
                "expected_draft_version": review["draft_version"],
                "expected_ranking_fingerprint": review["ranking_fingerprint"],
            },
        )
        assert status == 201
        retired_revision = saved["saved_revision"]["revision_id"]
        retired_draft_version = saved["working_draft"]["draft_version"]
        predecessor_revision = command["base_revision_id"]

    with ApiServer(database_url=f"sqlite:///{path}") as server:
        with sqlite3.connect(path) as connection:
            reopened = json.loads(
                connection.execute(
                    "SELECT payload_json FROM player_lifecycle_week_states WHERE week_ordinal=1"
                ).fetchone()[0]
            )
            reopened_sporting = json.loads(
                connection.execute(
                    "SELECT payload_json FROM player_sporting_week_states WHERE week_ordinal=1"
                ).fetchone()[0]
            )
        assert reopened == payload
        assert reopened_sporting == sporting_payload
        restore_root = f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}/saved-revisions"
        status, back = _request(
            "POST",
            f"{restore_root}/{predecessor_revision}/restore",
            {
                "expected_head_saved_revision_id": retired_revision,
                "expected_draft_version": retired_draft_version,
                "expected_current_viewer_branch_id": branch_id,
                "explicit_confirmation": True,
            },
        )
        assert status == 201, back
        status, forward = _request(
            "POST",
            f"{restore_root}/{retired_revision}/restore",
            {
                "expected_head_saved_revision_id": back["saved_revision"][
                    "revision_id"
                ],
                "expected_draft_version": back["working_draft"]["draft_version"],
                "expected_current_viewer_branch_id": branch_id,
                "explicit_confirmation": True,
            },
        )
        assert status == 201
        with sqlite3.connect(path) as connection:
            restored = json.loads(
                connection.execute(
                    "SELECT payload_json FROM player_lifecycle_week_states WHERE week_ordinal=1"
                ).fetchone()[0]
            )
            restored_sporting = json.loads(
                connection.execute(
                    "SELECT payload_json FROM player_sporting_week_states WHERE week_ordinal=1"
                ).fetchone()[0]
            )
        assert restored == payload
        assert restored_sporting == sporting_payload


def test_post_transition_legacy_revision_without_sporting_restore_is_atomic(tmp_path):
    """A legacy target after Week 1 cannot be reconstructed and changes nothing."""
    from test_initial_world_ranking_integration import (
        _make_legacy_revision_without_sporting,
    )

    path = tmp_path / "post-transition-legacy.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(
            server, "legacy post transition"
        )
        transition_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        preview = _request("POST", transition_root + "/preview", command)[1]
        assert confirm(transition_root, command, preview)[0] == 201
        ranking_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
        review = _request("GET", ranking_root + "/save/preview")[1]
        status, saved = _request(
            "POST",
            ranking_root + "/save",
            {
                "expected_draft_version": review["draft_version"],
                "expected_ranking_fingerprint": review["ranking_fingerprint"],
            },
        )
        assert status == 201
        post_transition_revision = saved["saved_revision"]["revision_id"]
        restore_root = f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}/saved-revisions"
        status, predecessor = _request(
            "POST",
            f"{restore_root}/{command['base_revision_id']}/restore",
            {
                "expected_head_saved_revision_id": post_transition_revision,
                "expected_draft_version": saved["working_draft"]["draft_version"],
                "expected_current_viewer_branch_id": branch_id,
                "explicit_confirmation": True,
            },
        )
        assert status == 201
        _make_legacy_revision_without_sporting(path, post_transition_revision)
        before = dump(path)
        status, rejected = _request(
            "POST",
            f"{restore_root}/{post_transition_revision}/restore",
            {
                "expected_head_saved_revision_id": predecessor["saved_revision"][
                    "revision_id"
                ],
                "expected_draft_version": predecessor["working_draft"]["draft_version"],
                "expected_current_viewer_branch_id": branch_id,
                "explicit_confirmation": True,
            },
        )
        assert status == 409
        assert "sporting" in str(rejected)
        assert "cannot be reconstructed unambiguously" in str(rejected)
        assert dump(path) == before


@pytest.mark.pr_critical
@pytest.mark.smoke
def test_atomic_publication_retry_save_reopen_and_bidirectional_restore(tmp_path):
    path = tmp_path / "week-transition.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, empty_revision = _create_run(
            server, display_name="Atomic week"
        )
        ranking = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
        bootstrap = initial() | {"run_id": run_id, "branch_id": branch_id}
        assert _request("POST", ranking + "/prepare/initial", bootstrap)[0] == 201
        install_owned_lifecycle(server, run_id, branch_id, bootstrap["players"])
        authority = {
            "run_id": run_id,
            "branch_id": branch_id,
            "base_revision_id": empty_revision,
            "completed_week": {"season_index": 0, "week": 1},
            "target_week": {"season_index": 0, "week": 2},
            "players": bootstrap["players"],
            "policy": bootstrap["policy"],
            "provenance": "Frozen supported boundary",
            "adopted_by_command_id": "authority-2",
            "audit": bootstrap["audit"],
        }
        status, adopted = _request(
            "POST", ranking + "/transition-authorities", authority
        )
        assert status == 201
        review = _request("GET", ranking + "/save/preview")[1]
        status, saved_base = _request(
            "POST",
            ranking + "/save",
            {
                "expected_draft_version": review["draft_version"],
                "expected_ranking_fingerprint": review["ranking_fingerprint"],
            },
        )
        assert status == 201
        base_revision = saved_base["saved_revision"]["revision_id"]
        command = {
            "command_id": "transition-week-2",
            "run_id": run_id,
            "branch_id": branch_id,
            "base_revision_id": base_revision,
            "completed_week": authority["completed_week"],
            "target_week": authority["target_week"],
            "authority_fingerprint": RankingTransitionAuthority.model_validate_json(
                json.dumps(adopted)
            ).fingerprint,
            "tournaments": [],
            "audit": bootstrap["audit"],
        }
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        before = dump(path)
        status, preview = _request("POST", root + "/preview", command)
        assert status == 200 and dump(path) == before and counts(path) == (0, 0, 0, 0)
        assert (
            confirm(root, command | {"base_revision_id": empty_revision}, preview)[0]
            == 409
        )
        assert confirm(root, command | {"branch_id": "other"}, preview)[0] == 409
        changed = command | {
            "audit": bootstrap["audit"] | {"reason": "different review"}
        }
        assert confirm(root, changed, preview)[0] == 409
        assert dump(path) == before and counts(path) == (0, 0, 0, 0)
        with sqlite3.connect(path) as connection:
            connection.execute(
                "UPDATE ranking_transition_authorities SET fingerprint = ?", ("0" * 64,)
            )
        corrupted = dump(path)
        assert confirm(root, command, preview)[0] == 409
        assert dump(path) == corrupted and counts(path) == (0, 0, 0, 0)
        with sqlite3.connect(path) as connection:
            connection.execute(
                "UPDATE ranking_transition_authorities SET fingerprint = ?",
                (command["authority_fingerprint"],),
            )
        status, confirmed = confirm(root, command, preview)
        assert status == 201 and confirmed == preview
        assert counts(path) == (2, 1, 1, 1)
        after = dump(path)
        assert confirm(root, command, preview) == (201, confirmed)
        assert dump(path) == after
        assert (
            confirm(
                root,
                command | {"audit": bootstrap["audit"] | {"reason": "different"}},
                preview,
            )[0]
            == 409
        )
        assert dump(path) == after

        review = _request("GET", ranking + "/save/preview")[1]
        status, transitioned_save = _request(
            "POST",
            ranking + "/save",
            {
                "expected_draft_version": review["draft_version"],
                "expected_ranking_fingerprint": review["ranking_fingerprint"],
            },
        )
        assert status == 201
        transition_revision = transitioned_save["saved_revision"]["revision_id"]
        status, restored = _request(
            "POST",
            f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}/saved-revisions/{base_revision}/restore",
            {
                "expected_head_saved_revision_id": transition_revision,
                "expected_draft_version": transitioned_save["working_draft"][
                    "draft_version"
                ],
                "expected_current_viewer_branch_id": branch_id,
                "explicit_confirmation": True,
            },
        )
        assert status == 201 and counts(path) == (0, 0, 0, 0)
        status, forward = _request(
            "POST",
            f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}/saved-revisions/{transition_revision}/restore",
            {
                "expected_head_saved_revision_id": restored["saved_revision"][
                    "revision_id"
                ],
                "expected_draft_version": restored["working_draft"]["draft_version"],
                "expected_current_viewer_branch_id": branch_id,
                "explicit_confirmation": True,
            },
        )
        assert status == 201 and counts(path) == (2, 1, 1, 1)
    with ApiServer(database_url=f"sqlite:///{path}"):
        assert counts(path) == (2, 1, 1, 1)


def test_normal_boundary_accepts_week_60_to_61_and_rejects_season_rollover_without_mutation(
    tmp_path,
):
    from beta_engine.application.authoritative_week_transition import (
        AuthoritativeWeekTransitionCommand,
    )

    base = {
        "command_id": "boundary",
        "run_id": "run",
        "branch_id": "branch",
        "base_revision_id": "revision",
        "authority_fingerprint": "a" * 64,
        "tournaments": [],
        "audit": {"actor_label": "Admin", "reason": "Boundary review"},
    }
    valid = base | {
        "completed_week": {"season_index": 0, "week": 60},
        "target_week": {"season_index": 0, "week": 61},
    }
    assert AuthoritativeWeekTransitionCommand.model_validate_json(json.dumps(valid))
    rollover = base | {
        "completed_week": {"season_index": 0, "week": 61},
        "target_week": {"season_index": 1, "week": 1},
    }
    with pytest.raises(ValueError, match="Season Transition"):
        AuthoritativeWeekTransitionCommand.model_validate_json(json.dumps(rollover))

    path = tmp_path / "season-boundary.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(server, "Season boundary")
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        before = dump(path)
        invalid = command | {
            "completed_week": rollover["completed_week"],
            "target_week": rollover["target_week"],
        }
        assert _request("POST", root + "/preview", invalid)[0] == 422
        assert dump(path) == before and counts(path) == (0, 0, 0, 0)


def test_exact_retry_survives_a_valid_later_published_world_head(tmp_path):
    from sqlalchemy import text
    from beta_engine.domain.rankings.official import (
        OfficialRankingPlayer,
        RankingWeek,
        calculate_official_ranking,
    )
    from beta_engine.infrastructure.db.models import (
        AuthoritativeWorldStateModel,
        PublishedOfficialRankingModel,
    )
    from beta_engine.infrastructure.db.official_rankings import (
        OfficialRankingCandidateStore,
    )

    path = tmp_path / "historical-retry.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(server, "Historical retry")
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        preview = _request("POST", root + "/preview", command)[1]
        assert confirm(root, command, preview)[0] == 201
        factory = server.app.state.runtime.repository._session_factory
        with factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            second = OfficialRankingCandidateStore(session).history(
                run_id=run_id, branch_id=branch_id
            )[-1]
            third = calculate_official_ranking(
                run_id=run_id,
                branch_id=branch_id,
                week=RankingWeek(season_index=0, week=3),
                policy=second.policy,
                players=tuple(
                    OfficialRankingPlayer.model_validate(player)
                    for player in initial()["players"]
                ),
                results=(),
                previous=second,
            )
            session.add(
                PublishedOfficialRankingModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    week_ordinal=third.week.ordinal,
                    snapshot_fingerprint=third.fingerprint,
                    payload_json=third.model_dump_json(),
                )
            )
            world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
            world.current_ordinal = third.week.ordinal
            world.ranking_fingerprint = third.fingerprint
        before_retry = dump(path)
        assert confirm(root, command, preview)[0] == 201
        assert dump(path) == before_retry


def test_exact_retry_rejects_corrupt_canonical_world_event(tmp_path):
    path = tmp_path / "corrupt-event.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(server, "Corrupt event")
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        preview = _request("POST", root + "/preview", command)[1]
        assert confirm(root, command, preview)[0] == 201
        with sqlite3.connect(path) as connection:
            connection.execute(
                "UPDATE authoritative_world_events SET payload_json = ?",
                ('{"corrupt":true}',),
            )
        before = dump(path)
        assert confirm(root, command, preview)[0] == 409
        assert dump(path) == before


def test_missing_completed_week_sporting_evidence_fails_closed(tmp_path):
    path = tmp_path / "missing-sporting-context.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(server, "missing context")
        with sqlite3.connect(path) as connection:
            connection.execute("DELETE FROM completed_week_sporting_contexts")
        before = dump(path)
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        status, rejected = _request("POST", root + "/preview", command)
        assert status == 409
        assert "zero matches cannot be inferred" in str(rejected)
        assert dump(path) == before


def test_reopened_week_two_is_a_real_predecessor_for_week_three(tmp_path):
    path = tmp_path / "repeated-transition.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, first_command = prepared_transition(server, "Repeated path")
        transition_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        first_preview = _request("POST", transition_root + "/preview", first_command)[1]
        first_result = confirm(transition_root, first_command, first_preview)[1]
        ranking_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
        save_preview = _request("GET", ranking_root + "/save/preview")[1]
        saved = _request(
            "POST",
            ranking_root + "/save",
            {
                "expected_draft_version": save_preview["draft_version"],
                "expected_ranking_fingerprint": save_preview["ranking_fingerprint"],
            },
        )[1]
        week_two_revision = saved["saved_revision"]["revision_id"]

    with ApiServer(database_url=f"sqlite:///{path}") as server:
        from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
        from beta_engine.infrastructure.db.official_rankings import (
            OfficialRankingCandidateStore,
        )

        factory = server.app.state.runtime.repository._session_factory
        week_two = RankingWeek(season_index=0, week=2)
        week_three = RankingWeek(season_index=0, week=3)
        with factory.begin() as session:
            lifecycle = get_lifecycle(
                session, run_id=run_id, branch_id=branch_id, week=week_two
            )
            assert lifecycle is not None
            put_completed_context(
                session,
                CompletedWeekSportingContext(
                    run_id=run_id,
                    branch_id=branch_id,
                    completed_week=week_two,
                    competitive_match_counts=tuple(
                        CompetitiveMatchCount(player_id=p.player_id, count=0)
                        for p in lifecycle.players
                    ),
                    source_fingerprints=("authoritative-week-two-empty-manifest",),
                    provenance="test authority explicitly proves Week 2 had no matches",
                ),
            )
            ranking = OfficialRankingCandidateStore(session).history(
                run_id=run_id, branch_id=branch_id
            )[-1]
            roster = lifecycle.ranking_roster()
        authority_payload = {
            "run_id": run_id,
            "branch_id": branch_id,
            "base_revision_id": week_two_revision,
            "completed_week": week_two.model_dump(mode="json"),
            "target_week": week_three.model_dump(mode="json"),
            "players": [player.model_dump(mode="json") for player in roster],
            "policy": ranking.policy.model_dump(mode="json"),
            "provenance": "Repeated acceptance frozen boundary",
            "adopted_by_command_id": "authority-week-three",
            "audit": first_command["audit"],
        }
        ranking_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
        status, authority = _request(
            "POST", ranking_root + "/transition-authorities", authority_payload
        )
        assert status == 201
        save_preview = _request("GET", ranking_root + "/save/preview")[1]
        saved_authority = _request(
            "POST",
            ranking_root + "/save",
            {
                "expected_draft_version": save_preview["draft_version"],
                "expected_ranking_fingerprint": save_preview["ranking_fingerprint"],
            },
        )[1]
        second_command = {
            "command_id": "transition-week-three",
            "run_id": run_id,
            "branch_id": branch_id,
            "base_revision_id": saved_authority["saved_revision"]["revision_id"],
            "completed_week": week_two.model_dump(mode="json"),
            "target_week": week_three.model_dump(mode="json"),
            "authority_fingerprint": RankingTransitionAuthority.model_validate_json(
                json.dumps(authority)
            ).fingerprint,
            "tournaments": [],
            "audit": first_command["audit"],
        }
        transition_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        second_preview = _request("POST", transition_root + "/preview", second_command)[
            1
        ]
        second = confirm(transition_root, second_command, second_preview)[1]
        assert (
            second["result"]["player_sporting_fingerprint"]
            == second_preview["result"]["player_sporting_fingerprint"]
        )
        with sqlite3.connect(path) as connection:
            states = [
                json.loads(row[0])
                for row in connection.execute(
                    "SELECT payload_json FROM player_sporting_week_states ORDER BY week_ordinal"
                )
            ]
        assert len(states) == 3
        assert (
            states[2]["predecessor_fingerprint"]
            == first_result["result"]["player_sporting_fingerprint"]
        )


def test_exact_retry_rejects_missing_completed_context_without_mutation(tmp_path):
    path = tmp_path / "retry-missing-context.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(server, "Retry context link")
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        preview = _request("POST", root + "/preview", command)[1]
        assert confirm(root, command, preview)[0] == 201
        with sqlite3.connect(path) as connection:
            connection.execute("DELETE FROM completed_week_sporting_contexts")
        before = dump(path)
        status, rejected = confirm(root, command, preview)
        assert status == 409
        assert "context" in str(rejected)
        assert dump(path) == before


def test_save_rejects_orphan_sporting_state_without_creating_revision(tmp_path):
    path = tmp_path / "save-orphan-sporting.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(server, "Orphan save")
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        preview = _request("POST", root + "/preview", command)[1]
        assert confirm(root, command, preview)[0] == 201
        ranking_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
        review = _request("GET", ranking_root + "/save/preview")[1]
        with sqlite3.connect(path) as connection:
            connection.execute("DELETE FROM completed_week_sporting_contexts")
        before = dump(path)
        status, rejected = _request(
            "POST",
            ranking_root + "/save",
            {
                "expected_draft_version": review["draft_version"],
                "expected_ranking_fingerprint": review["ranking_fingerprint"],
            },
        )
        assert status == 409
        assert "missing or mismatched predecessor-week context" in str(rejected)
        assert dump(path) == before

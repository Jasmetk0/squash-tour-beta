"""Real HTTP/file-backed SQLite coverage for authoritative simulation routes."""

import hashlib
from pathlib import Path

from beta_engine.api.deps import (
    get_season_match_service,
    get_season_point_awards_service,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.initial_world_state import (
    get_initial_world,
    put_initial_world,
)
from beta_engine.infrastructure.db.player_lifecycle_state import (
    get_lifecycle,
    put_lifecycle,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    get_sporting,
    put_sporting,
)

from test_authoritative_slot_matches import session_at
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from test_season_point_awards_service import make_points_service


def _server_state(tmp_path):
    points, event_id = make_points_service(tmp_path / "source")
    matches = points.result_service.match_service
    registry = matches._load_registry()
    package = registry.matches_by_event_id[event_id]
    package.qualification_matches = []
    registry.matches_by_event_id[event_id] = package
    matches._save_registry(registry)
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'api.sqlite'}")
    server.app.dependency_overrides[get_season_match_service] = lambda: matches
    server.app.dependency_overrides[get_season_point_awards_service] = lambda: points
    return server, package


def _install_owned_state(server, package, run_id, branch_id):
    semifinal = sorted(
        (m for m in package.main_draw_matches if m.round_number == 1),
        key=lambda m: m.bracket_position,
    )
    ids = tuple(p for m in semifinal for p in (m.top_player_id, m.bottom_player_id))
    week = RankingWeek(season_index=0, week=package.season_week)
    source = session_at(
        Path(server.app.state.runtime.repository._engine.url.database + ".source"),
        ids,
        week,
    )
    world = get_initial_world(source, run_id="run", branch_id="branch")
    lifecycle = get_lifecycle(source, run_id="run", branch_id="branch", week=week)
    sporting = get_sporting(source, run_id="run", branch_id="branch", week=week)
    source.close()
    owned_world = world.model_copy(update={"run_id": run_id, "branch_id": branch_id})
    with server.app.state.runtime.repository._session_factory.begin() as session:
        put_initial_world(session, owned_world)
        put_lifecycle(
            session,
            lifecycle.model_copy(
                update={
                    "run_id": run_id,
                    "branch_id": branch_id,
                    "source_initial_world_fingerprint": owned_world.fingerprint,
                }
            ),
        )
        put_sporting(
            session,
            sporting.model_copy(
                update={
                    "run_id": run_id,
                    "branch_id": branch_id,
                    "source_initial_world_fingerprint": owned_world.fingerprint,
                }
            ),
        )
    return week


def test_authoritative_simulation_http_guards_retry_and_close(tmp_path):
    server, package = _server_state(tmp_path)
    legacy_hash = hashlib.sha256(
        server.app.dependency_overrides[
            get_season_match_service
        ]().matches_path.read_bytes()
    ).hexdigest()
    with server:
        run_id, branch_id, revision = _create_run(
            server, display_name="Authoritative HTTP"
        )
        week = _install_owned_state(server, package, run_id, branch_id)
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
        status, opening = _request("GET", root + "/position")
        assert status == 200 and len(opening["eligible_match_ids"]) == 2
        base = {
            "command_id": "sf",
            "run_id": run_id,
            "branch_id": branch_id,
            "expected_week": week.model_dump(mode="json"),
            "expected_position_fingerprint": opening["position_fingerprint"],
            "expected_revision_id": revision,
        }
        assert _request("POST", root + "/simulate-next-match", base)[0] == 409
        assert (
            _request(
                "POST",
                root + "/simulate-next-match",
                base
                | {"command_id": "later", "group_id": opening["blocked_match_ids"][0]},
            )[0]
            == 409
        )
        command = base | {"group_id": opening["eligible_match_ids"][0]}
        status, first = _request("POST", root + "/simulate-next-match", command)
        assert status == 200
        assert _request("POST", root + "/simulate-next-match", command) == (200, first)
        assert (
            _request(
                "POST",
                root + "/simulate-next-match",
                command | {"group_id": opening["eligible_match_ids"][1]},
            )[0]
            == 409
        )
        assert (
            _request(
                "POST",
                root + "/simulate-next-match",
                command
                | {"command_id": "stale", "group_id": opening["eligible_match_ids"][1]},
            )[0]
            == 409
        )
        assert (
            _request(
                "POST",
                root + "/simulate-next-match",
                command
                | {
                    "command_id": "week",
                    "expected_week": {"season_index": 0, "week": 1},
                },
            )[0]
            == 409
        )
        assert (
            _request(
                "POST",
                root + "/simulate-next-match",
                command | {"command_id": "head", "expected_revision_id": "stale"},
            )[0]
            == 409
        )
        assert (
            _request(
                "POST", root.replace(run_id, "wrong") + "/simulate-next-match", command
            )[0]
            == 409
        )
        status, current = _request("GET", root + "/position")
        second = base | {
            "command_id": "sf2",
            "expected_position_fingerprint": current["position_fingerprint"],
            "group_id": current["eligible_match_ids"][0],
        }
        assert _request("POST", root + "/simulate-next-match", second)[0] == 200
        current = _request("GET", root + "/position")[1]
        final = base | {
            "command_id": "final",
            "expected_position_fingerprint": current["position_fingerprint"],
        }
        status, closed = _request("POST", root + "/simulate-next-slot", final)
        assert status == 200 and closed["week_ready_for_transition"] is True
    assert (
        hashlib.sha256(
            server.app.dependency_overrides[
                get_season_match_service
            ]().matches_path.read_bytes()
        ).hexdigest()
        == legacy_hash
    )

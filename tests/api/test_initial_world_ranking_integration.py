"""Real HTTP/SQLite integration for initial world ownership and ranking derivation."""

import json
import hashlib
import sqlite3
from urllib import error, request

import pytest

from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner
from beta_engine.domain.run_revisions import saved_revision_content_hash

from test_saved_revision_history_api import ApiServer, _create_run, _request


def _post_headers(url, payload, headers):
    req = request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    with request.urlopen(req) as response:
        return response.status, json.loads(response.read())


def _make_legacy_revision_without_lifecycle(path, revision_id):
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT revision_id,run_id,branch_id,sequence,parent_revision_id,kind,"
            "payload_schema_version,payload_json,change_summary_json FROM branch_saved_revisions "
            "WHERE revision_id=?",
            (revision_id,),
        ).fetchone()
        payload = json.loads(row[7])
        legacy_payload = json.loads(row[7])
        legacy_payload["content"].pop("player_lifecycle")
        legacy_payload["content"].pop("player_sporting_state", None)
        content_hash = saved_revision_content_hash(
            revision_id=row[0],
            run_id=row[1],
            branch_id=row[2],
            sequence=row[3],
            parent_revision_id=row[4],
            kind=row[5],
            payload_schema_version=row[6],
            payload=legacy_payload,
            change_summary=json.loads(row[8]),
        )
        connection.execute(
            "UPDATE branch_saved_revisions SET payload_json=?,content_hash=? "
            "WHERE revision_id=?",
            (
                json.dumps(legacy_payload, sort_keys=True, separators=(",", ":")),
                content_hash,
                revision_id,
            ),
        )
        return payload, legacy_payload


def _post_headers_result(url, payload, headers):
    try:
        return _post_headers(url, payload, headers)
    except error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _make_legacy_revision_without_sporting(path, revision_id):
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT revision_id,run_id,branch_id,sequence,parent_revision_id,kind,"
            "payload_schema_version,payload_json,change_summary_json FROM branch_saved_revisions "
            "WHERE revision_id=?",
            (revision_id,),
        ).fetchone()
        original = json.loads(row[7])
        legacy = json.loads(row[7])
        legacy["content"].pop("player_sporting_state")
        content_hash = saved_revision_content_hash(
            revision_id=row[0],
            run_id=row[1],
            branch_id=row[2],
            sequence=row[3],
            parent_revision_id=row[4],
            kind=row[5],
            payload_schema_version=row[6],
            payload=legacy,
            change_summary=json.loads(row[8]),
        )
        connection.execute(
            "UPDATE branch_saved_revisions SET payload_json=?,content_hash=? WHERE revision_id=?",
            (
                json.dumps(legacy, sort_keys=True, separators=(",", ":")),
                content_hash,
                revision_id,
            ),
        )
        return original, legacy


def _ranking_row_count(path):
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM official_ranking_candidates"
        ).fetchone()[0]


def _initial_world_row_count(path):
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM initial_world_states"
        ).fetchone()[0]


@pytest.mark.smoke
def test_production_pool_to_owned_world_derived_ranking_save_reopen_restore(tmp_path):
    db = tmp_path / "world.db"
    pool = tmp_path / "initial-player-pool.json"
    active = tmp_path / "unused-active-players.json"
    with ApiServer(database_url=f"sqlite:///{db}") as server:
        server.app.state.initial_player_pool_config_path = pool
        server.app.state.season_active_players_config_path = active
        assert (
            _request(
                "POST",
                server.base_url + "/admin/players/initial-pool/generate",
                {
                    "season": "2000/2001",
                    "seed": 723,
                    "target_pool_size": 12,
                    "dry_run": False,
                },
            )[0]
            == 200
        )
        run_id, branch_id, empty_revision = _create_run(
            server, display_name="Initial world integration"
        )
        world_root = f"{server.base_url}/admin/players/runs/{run_id}/branches/{branch_id}/initial-world"
        adoption = {
            "command_id": "adopt-production-pool",
            "source_season": "2000/2001",
            "bootstrap_seed": 44,
            "audit_label": "Integration admin",
            "audit_reason": "Adopt complete generated source",
            "official_run": False,
            "best_n": 9,
        }
        status, preview = _request("POST", world_root + "/preview", adoption)
        assert (
            status == 200
            and preview["preview_only"]
            and len(preview["state"]["players"]) == 12
        )
        status, adopted = _post_headers(
            world_root,
            adoption,
            {"X-Initial-World-Preview-Fingerprint": preview["fingerprint"]},
        )
        assert status == 201 and adopted["policies"][0]["best_n"] == 9

        # Mutating the disposable global source after adoption cannot alter owned state.
        original_owned = _request("GET", world_root)[1]
        assert (
            _request(
                "POST",
                server.base_url + "/admin/players/initial-pool/generate",
                {
                    "season": "2000/2001",
                    "seed": 999,
                    "target_pool_size": 5,
                    "dry_run": False,
                },
            )[0]
            == 200
        )
        assert _request("GET", world_root)[1] == original_owned
        # Exact command retry resolves from owned state before touching the now
        # different global source and does not duplicate persistence rows.
        before_retry = _initial_world_row_count(db)
        assert _post_headers(
            world_root,
            adoption,
            {"X-Initial-World-Preview-Fingerprint": preview["fingerprint"]},
        ) == (201, original_owned)
        assert _initial_world_row_count(db) == before_retry == 1
        pool.unlink()
        # Simulate a pre-#726 owned InitialWorldState: exact retry must backfill
        # solely from that stored world even though the global source is gone.
        with sqlite3.connect(db) as connection:
            connection.execute("DELETE FROM player_lifecycle_week_states")
        assert _post_headers(
            world_root,
            adoption,
            {"X-Initial-World-Preview-Fingerprint": preview["fingerprint"]},
        ) == (201, original_owned)
        with sqlite3.connect(db) as connection:
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM player_lifecycle_week_states"
                ).fetchone()[0]
                == 1
            )
        assert (
            _post_headers_result(
                world_root,
                adoption | {"best_n": 8},
                {"X-Initial-World-Preview-Fingerprint": preview["fingerprint"]},
            )[0]
            == 409
        )
        assert (
            _post_headers_result(
                world_root, adoption, {"X-Initial-World-Preview-Fingerprint": "0" * 64}
            )[0]
            == 409
        )

        status, save_preview = _request("GET", world_root + "/save/preview")
        assert status == 200 and save_preview["can_save"]
        status, world_saved = _request(
            "POST",
            world_root + "/save",
            {
                "expected_draft_version": save_preview["draft_version"],
                "expected_initial_world_fingerprint": save_preview[
                    "initial_world_fingerprint"
                ],
            },
        )
        assert status == 201

        ranking_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
        preparation = {
            "command_id": "derive-initial-ranking",
            "audit": {
                "actor_label": "Integration admin",
                "reason": "Derive from owned players",
            },
        }
        status, ranking_preview = _request(
            "POST", ranking_root + "/prepare/initial/derived/preview", preparation
        )
        assert status == 200 and ranking_preview["candidate"]["snapshot"]["rows"] == []

        def ranking_player(player):
            identity = json.dumps(
                {
                    "player_id": player["player_id"],
                    "birth_year": player["birth_year"],
                    "birth_year_week": player["birth_year_week"],
                    "source": player["source_generation_fingerprint"],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            return {
                "player_id": player["player_id"],
                "tie_break_token": hashlib.sha256(identity.encode()).hexdigest(),
                "tour_entry_week": {"season_index": 0, "week": 1},
                "retired": False,
            }

        derived_players = [
            ranking_player(player) for player in original_owned["players"]
        ]
        forged_base = {
            "kind": "initial_ranking.v1",
            "command_id": "forged",
            "run_id": run_id,
            "branch_id": branch_id,
            "target_week": {"season_index": 0, "week": 1},
            "policy": original_owned["policies"][0],
            "players": derived_players,
            "discipline": "none",
            "initial_world_fingerprint": preview["fingerprint"],
            "audit": preparation["audit"],
        }
        for index, mutation in enumerate(
            (
                {"players": []},
                {
                    "policy": {
                        "policy_id": "forged",
                        "best_n": 1,
                        "tie_break_version": "result_profile_age_previous_token.v1",
                    }
                },
                {
                    "players": [
                        derived_players[0] | {"tie_break_token": "forged"},
                        *derived_players[1:],
                    ]
                },
            )
        ):
            forged = forged_base | mutation | {"command_id": f"forged-{index}"}
            # All three produce the same empty Week-1 ordering, but provenance
            # claims are rejected before any candidate or receipt can persist.
            assert _request("POST", ranking_root + "/prepare/initial", forged)[0] == 409
            assert _ranking_row_count(db) == 0
        direct_forgery = RankingBootstrapCommand.model_validate(
            forged_base | {"command_id": "direct-runner-forgery", "players": ()}
        )
        runner = RankingWeekCommandRunner(
            server.app.state.runtime.repository._session_factory
        )
        with pytest.raises(ValueError, match="differ from the owned initial world"):
            runner.execute(direct_forgery)
        assert _ranking_row_count(db) == 0
        status, candidate = _post_headers(
            ranking_root + "/prepare/initial/derived",
            preparation,
            {
                "X-Ranking-Preview-Fingerprint": ranking_preview["candidate"][
                    "fingerprint"
                ],
                "X-Ranking-Preview-Request": ranking_preview["request_fingerprint"],
            },
        )
        assert status == 201 and candidate == ranking_preview["candidate"]
        status, ranking_save = _request("GET", ranking_root + "/save/preview")
        status, ranked_saved = _request(
            "POST",
            ranking_root + "/save",
            {
                "expected_draft_version": ranking_save["draft_version"],
                "expected_ranking_fingerprint": ranking_save["ranking_fingerprint"],
            },
        )
        assert status == 201
        ranked_revision = ranked_saved["saved_revision"]["revision_id"]
        world_revision = world_saved["saved_revision"]["revision_id"]
        _, immutable_legacy = _make_legacy_revision_without_sporting(db, world_revision)
        restore_legacy = (
            f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}"
            f"/saved-revisions/{world_revision}/restore"
        )
        status, restored = _request(
            "POST",
            restore_legacy,
            {
                "expected_head_saved_revision_id": ranked_revision,
                "expected_draft_version": ranked_saved["working_draft"][
                    "draft_version"
                ],
                "expected_current_viewer_branch_id": branch_id,
                "explicit_confirmation": True,
            },
        )
        assert status == 201, restored
        compatibility_revision = restored["saved_revision"]
        with sqlite3.connect(db) as connection:
            compatibility_payload = json.loads(
                connection.execute(
                    "SELECT payload_json FROM branch_saved_revisions WHERE revision_id=?",
                    (compatibility_revision["revision_id"],),
                ).fetchone()[0]
            )
            live_row = connection.execute(
                "SELECT fingerprint,payload_json FROM player_lifecycle_week_states WHERE week_ordinal=0"
            ).fetchone()
            live = json.loads(live_row[1])
            sporting_live_row = connection.execute(
                "SELECT fingerprint,payload_json FROM player_sporting_week_states WHERE week_ordinal=0"
            ).fetchone()
            sporting_live = json.loads(sporting_live_row[1])
            stored_legacy = json.loads(
                connection.execute(
                    "SELECT payload_json FROM branch_saved_revisions WHERE revision_id=?",
                    (world_revision,),
                ).fetchone()[0]
            )
        component = compatibility_payload["content"]["player_lifecycle"]
        assert component["states"] == [live]
        assert component["states"][0] == live and live_row[0]
        assert stored_legacy == immutable_legacy
        assert "player_lifecycle" in stored_legacy["content"]
        assert "player_sporting_state" not in stored_legacy["content"]
        assert compatibility_payload["content"]["player_sporting_state"]["states"] == [
            sporting_live
        ]
        assert sporting_live_row[0]
        restore_ranked = (
            f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}"
            f"/saved-revisions/{ranked_revision}/restore"
        )
        status, restored_again = _request(
            "POST",
            restore_ranked,
            {
                "expected_head_saved_revision_id": restored["saved_revision"][
                    "revision_id"
                ],
                "expected_draft_version": restored["working_draft"]["draft_version"],
                "expected_current_viewer_branch_id": branch_id,
                "explicit_confirmation": True,
            },
        )
        assert status == 201 and _request("GET", world_root)[1] == original_owned
        assert _request("GET", ranking_root + "/0/1")[1] == candidate
        restore_compatibility = (
            f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}"
            f"/saved-revisions/{compatibility_revision['revision_id']}/restore"
        )
        status, compatibility_again = _request(
            "POST",
            restore_compatibility,
            {
                "expected_head_saved_revision_id": restored_again["saved_revision"][
                    "revision_id"
                ],
                "expected_draft_version": restored_again["working_draft"][
                    "draft_version"
                ],
                "expected_current_viewer_branch_id": branch_id,
                "explicit_confirmation": True,
            },
        )
        assert status == 201
        with sqlite3.connect(db) as connection:
            assert (
                json.loads(
                    connection.execute(
                        "SELECT payload_json FROM player_lifecycle_week_states WHERE week_ordinal=0"
                    ).fetchone()[0]
                )
                == live
            )

    with ApiServer(database_url=f"sqlite:///{db}") as reopened:
        assert (
            _request(
                "GET",
                f"{reopened.base_url}/admin/players/runs/{run_id}/branches/{branch_id}/initial-world",
            )[1]
            == original_owned
        )
        with sqlite3.connect(db) as connection:
            assert (
                json.loads(
                    connection.execute(
                        "SELECT payload_json FROM player_lifecycle_week_states WHERE week_ordinal=0"
                    ).fetchone()[0]
                )
                == live
            )


def test_first_adoption_rejects_source_change_after_preview(tmp_path):
    db = tmp_path / "stale.db"
    pool = tmp_path / "pool.json"
    with ApiServer(database_url=f"sqlite:///{db}") as server:
        server.app.state.initial_player_pool_config_path = pool
        assert (
            _request(
                "POST",
                server.base_url + "/admin/players/initial-pool/generate",
                {
                    "season": "2000/2001",
                    "seed": 723,
                    "target_pool_size": 12,
                    "dry_run": False,
                },
            )[0]
            == 200
        )
        run_id, branch_id, _ = _create_run(server, display_name="Stale adoption")
        root = f"{server.base_url}/admin/players/runs/{run_id}/branches/{branch_id}/initial-world"
        payload = {
            "command_id": "stale-source",
            "source_season": "2000/2001",
            "bootstrap_seed": 44,
            "audit_label": "Admin",
            "audit_reason": "Verify stale source",
            "best_n": 9,
        }
        preview = _request("POST", root + "/preview", payload)[1]
        assert (
            _request(
                "POST",
                server.base_url + "/admin/players/initial-pool/generate",
                {
                    "season": "2000/2001",
                    "seed": 999,
                    "target_pool_size": 5,
                    "dry_run": False,
                },
            )[0]
            == 200
        )
        assert (
            _post_headers_result(
                root,
                payload,
                {"X-Initial-World-Preview-Fingerprint": preview["fingerprint"]},
            )[0]
            == 409
        )
        assert _request("GET", root)[0] == 404
        with sqlite3.connect(db) as connection:
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM initial_world_states"
                ).fetchone()[0]
                == 0
            )

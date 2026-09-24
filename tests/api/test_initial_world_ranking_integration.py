"""Real HTTP/SQLite integration for initial world ownership and ranking derivation."""

import json
import hashlib
import sqlite3
from urllib import error, request

import pytest
from sqlalchemy import event, text

from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner
from beta_engine.infrastructure.db.ranking_revision_state import (
    capture_ranking_revision_state,
)
from beta_engine.infrastructure.db.saved_revision_rankings import (
    load_saved_ranking_component,
)
from beta_engine.infrastructure.db.player_lifecycle_state import load_saved_lifecycle
from beta_engine.infrastructure.db.player_sporting_state import (
    load_saved_sporting_bundle,
)
from beta_engine.application.run_branch_creation_service import RunBranchCreationService
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    BranchStateModel,
    BranchWorkingDraftModel,
    InitialWorldStateModel,
    RunBranchModel,
)
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


def _create_saved_world(server, tmp_path, *, suffix, with_ranking):
    pool = tmp_path / f"pool-{suffix}.json"
    server.app.state.initial_player_pool_config_path = pool
    assert (
        _request(
            "POST",
            server.base_url + "/admin/players/initial-pool/generate",
            {
                "season": "2000/2001",
                "seed": 810,
                "target_pool_size": 4,
                "dry_run": False,
            },
        )[0]
        == 200
    )
    run_id, branch_id, _ = _create_run(server, display_name=f"Fork {suffix}")
    world_root = f"{server.base_url}/admin/players/runs/{run_id}/branches/{branch_id}/initial-world"
    adoption = {
        "command_id": f"adopt-{suffix}",
        "source_season": "2000/2001",
        "bootstrap_seed": 17,
        "audit_label": "Fork test",
        "audit_reason": "Create owned fork fixture",
        "official_run": False,
        "best_n": 4,
    }
    preview = _request("POST", world_root + "/preview", adoption)[1]
    assert (
        _post_headers(
            world_root,
            adoption,
            {"X-Initial-World-Preview-Fingerprint": preview["fingerprint"]},
        )[0]
        == 201
    )
    save_preview = _request("GET", world_root + "/save/preview")[1]
    saved = _request(
        "POST",
        world_root + "/save",
        {
            "expected_draft_version": save_preview["draft_version"],
            "expected_initial_world_fingerprint": save_preview[
                "initial_world_fingerprint"
            ],
        },
    )[1]
    pool.unlink()
    if not with_ranking:
        return run_id, branch_id, saved["saved_revision"]["revision_id"], adoption
    ranking_root = (
        f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
    )
    intent = {
        "command_id": f"ranking-{suffix}",
        "audit": {"actor_label": "Fork test", "reason": "Derived bootstrap"},
    }
    ranking_preview = _request(
        "POST", ranking_root + "/prepare/initial/derived/preview", intent
    )[1]
    assert (
        _post_headers(
            ranking_root + "/prepare/initial/derived",
            intent,
            {
                "X-Ranking-Preview-Fingerprint": ranking_preview["candidate"][
                    "fingerprint"
                ],
                "X-Ranking-Preview-Request": ranking_preview["request_fingerprint"],
            },
        )[0]
        == 201
    )
    ranking_save = _request("GET", ranking_root + "/save/preview")[1]
    saved = _request(
        "POST",
        ranking_root + "/save",
        {
            "expected_draft_version": ranking_save["draft_version"],
            "expected_ranking_fingerprint": ranking_save["ranking_fingerprint"],
        },
    )[1]
    return run_id, branch_id, saved["saved_revision"]["revision_id"], adoption


@pytest.mark.pr_critical
def test_initial_world_only_fork_nested_reopen_and_adoption_is_not_target_retry(
    tmp_path,
):
    db = tmp_path / "world-only-fork.db"
    with ApiServer(database_url=f"sqlite:///{db}") as server:
        run_id, source_id, source_revision, adoption = _create_saved_world(
            server, tmp_path, suffix="world-only", with_ranking=False
        )
        root = f"{server.base_url}/run-containers/{run_id}/branches"
        status, target = _request(
            "POST",
            root,
            {
                "source_branch_id": source_id,
                "source_saved_revision_id": source_revision,
            },
        )
        assert status == 201
        status, nested = _request(
            "POST",
            root,
            {
                "source_branch_id": target["branch_id"],
                "source_saved_revision_id": target["saved_head_revision_id"],
            },
        )
        assert status == 201
        repo = server.app.state.runtime.repository
        source_world = repo.get_initial_world(run_id=run_id, branch_id=source_id)
        target_world = repo.get_initial_world(
            run_id=run_id, branch_id=target["branch_id"]
        )
        nested_world = repo.get_initial_world(
            run_id=run_id, branch_id=nested["branch_id"]
        )
        before_rows = _initial_world_row_count(db)
        target_root = (
            f"{server.base_url}/admin/players/runs/{run_id}/branches/"
            f"{target['branch_id']}/initial-world"
        )
        # Historical source adoption identity is provenance, not a target retry.
        assert (
            _post_headers_result(
                target_root,
                adoption,
                {"X-Initial-World-Preview-Fingerprint": source_world.fingerprint},
            )[0]
            == 409
        )
        assert _initial_world_row_count(db) == before_rows
        assert (
            repo.get_initial_world(run_id=run_id, branch_id=target["branch_id"])
            == target_world
        )
        expected = {
            source_id: source_world.fingerprint,
            target["branch_id"]: target_world.fingerprint,
            nested["branch_id"]: nested_world.fingerprint,
        }

    with ApiServer(database_url=f"sqlite:///{db}") as reopened:
        repo = reopened.app.state.runtime.repository
        for branch_id, world_fingerprint in expected.items():
            world = repo.get_initial_world(run_id=run_id, branch_id=branch_id)
            assert world.branch_id == branch_id
            assert world.fingerprint == world_fingerprint


@pytest.mark.pr_critical
def test_initial_world_ranking_fork_diverges_saves_restores_and_reopens(tmp_path):
    db = tmp_path / "world-ranking-fork.db"
    with ApiServer(database_url=f"sqlite:///{db}") as server:
        run_id, source_id, source_revision, _ = _create_saved_world(
            server, tmp_path, suffix="ranked", with_ranking=True
        )
        repo = server.app.state.runtime.repository
        source_head_before = repo.get_branch_revision_state(branch_id=source_id)
        source_payload_before = repo.get_branch_saved_revision(
            revision_id=source_revision
        ).payload
        status, target = _request(
            "POST",
            f"{server.base_url}/run-containers/{run_id}/branches",
            {
                "source_branch_id": source_id,
                "source_saved_revision_id": source_revision,
            },
        )
        assert status == 201, target
        target_id = target["branch_id"]
        fork_root_id = target["saved_head_revision_id"]
        fork_root = repo.get_branch_saved_revision(revision_id=fork_root_id)
        target_world = repo.get_initial_world(run_id=run_id, branch_id=target_id)
        target_ranking = load_saved_ranking_component(
            fork_root.payload, run_id=run_id, branch_id=target_id
        )
        target_lifecycle = load_saved_lifecycle(
            fork_root.payload, run_id=run_id, branch_id=target_id
        )
        target_sporting = load_saved_sporting_bundle(
            fork_root.payload, run_id=run_id, branch_id=target_id
        )
        bootstrap = RankingBootstrapCommand.model_validate_json(
            target_ranking.entries[0].receipts[0].request_payload_json
        )
        assert bootstrap.initial_world_fingerprint == target_world.fingerprint

        RankingWeekCommandRunner(repo._session_factory).execute(
            RankingWeekCommand(
                command_id="target-week-two",
                tournaments=(),
                context=RankingTransitionContext(
                    run_id=run_id,
                    branch_id=target_id,
                    completed_week=RankingWeek(season_index=0, week=1),
                    target_week=RankingWeek(season_index=0, week=2),
                    policy=bootstrap.policy,
                    players=bootstrap.players,
                    discipline="none",
                ),
            )
        )
        ranking_root = f"{server.base_url}/admin/runs/{run_id}/branches/{target_id}/ranking-candidates"
        save_preview = _request("GET", ranking_root + "/save/preview")[1]
        divergent_ranking_fingerprint = save_preview["ranking_fingerprint"]
        status, target_saved = _request(
            "POST",
            ranking_root + "/save",
            {
                "expected_draft_version": save_preview["draft_version"],
                "expected_ranking_fingerprint": save_preview["ranking_fingerprint"],
            },
        )
        assert status == 201
        divergent_id = target_saved["saved_revision"]["revision_id"]
        assert divergent_id != fork_root_id
        assert repo.get_branch_revision_state(branch_id=source_id) == source_head_before
        assert (
            repo.get_branch_saved_revision(revision_id=source_revision).payload
            == source_payload_before
        )

        target_state = repo.get_branch_revision_state(branch_id=target_id)
        restore_url = (
            f"{server.base_url}/run-containers/{run_id}/branches/{target_id}/"
            f"saved-revisions/{fork_root_id}/restore"
        )
        status, restored = _request(
            "POST",
            restore_url,
            {
                "expected_head_saved_revision_id": divergent_id,
                "expected_draft_version": target_state.working_draft.draft_version,
                "expected_current_viewer_branch_id": source_id,
                "explicit_confirmation": True,
            },
        )
        assert status == 201, restored
        restored_head = restored["saved_revision"]["revision_id"]
        restored_ranking = load_saved_ranking_component(
            repo.get_branch_saved_revision(revision_id=restored_head).payload,
            run_id=run_id,
            branch_id=target_id,
        )
        restored_payload = repo.get_branch_saved_revision(
            revision_id=restored_head
        ).payload
        assert restored_ranking.fingerprint == target_ranking.fingerprint
        assert len(restored_ranking.entries) == 1
        assert (
            load_saved_lifecycle(restored_payload, run_id=run_id, branch_id=target_id)
            == target_lifecycle
        )
        assert (
            load_saved_sporting_bundle(
                restored_payload, run_id=run_id, branch_id=target_id
            )
            == target_sporting
        )
        target_world_fingerprint = target_world.fingerprint

    with ApiServer(database_url=f"sqlite:///{db}") as reopened:
        repo = reopened.app.state.runtime.repository
        world = repo.get_initial_world(run_id=run_id, branch_id=target_id)
        assert world.branch_id == target_id
        assert world.fingerprint == target_world_fingerprint
        state = repo.get_branch_revision_state(branch_id=target_id)
        assert state.saved_head_revision_id == restored_head
        assert state.working_draft.base_revision_id == restored_head
        assert state.working_draft.status == "clean"
        assert repo.get_branch_revision_state(branch_id=source_id) == source_head_before
        RankingWeekCommandRunner(repo._session_factory).execute(
            RankingWeekCommand(
                command_id="target-week-two",
                tournaments=(),
                context=RankingTransitionContext(
                    run_id=run_id,
                    branch_id=target_id,
                    completed_week=RankingWeek(season_index=0, week=1),
                    target_week=RankingWeek(season_index=0, week=2),
                    policy=bootstrap.policy,
                    players=bootstrap.players,
                    discipline="none",
                ),
            )
        )
        assert (
            repo.preview_ranking_save(run_id=run_id, branch_id=target_id)[
                "ranking_fingerprint"
            ]
            == divergent_ranking_fingerprint
        )


@pytest.mark.pr_critical
def test_initial_world_fork_corruption_and_late_failure_roll_back(tmp_path):
    db = tmp_path / "world-fork-fail-closed.db"
    with ApiServer(database_url=f"sqlite:///{db}") as server:
        run_id, source_id, source_revision, _ = _create_saved_world(
            server, tmp_path, suffix="corrupt", with_ranking=False
        )
        repo = server.app.state.runtime.repository
        with repo._session_factory.begin() as session:
            model = session.get(BranchSavedRevisionModel, source_revision)
            payload = json.loads(model.payload_json)
            payload["content"]["initial_world"]["fingerprint"] = "0" * 64
            summary = json.loads(model.change_summary_json)
            model.payload_json = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            )
            model.content_hash = saved_revision_content_hash(
                revision_id=model.revision_id,
                run_id=model.run_id,
                branch_id=model.branch_id,
                sequence=model.sequence,
                parent_revision_id=model.parent_revision_id,
                kind=model.kind,
                payload_schema_version=model.payload_schema_version,
                payload=payload,
                change_summary=summary,
            )
        before = _initial_world_row_count(db)
        status, _ = _request(
            "POST",
            f"{server.base_url}/run-containers/{run_id}/branches",
            {
                "source_branch_id": source_id,
                "source_saved_revision_id": source_revision,
            },
        )
        assert status == 409
        assert _initial_world_row_count(db) == before

        # Restore the valid immutable fixture solely to exercise a failure after
        # target InitialWorld installation but before the fork revision is written.
        with repo._session_factory.begin() as session:
            model = session.get(BranchSavedRevisionModel, source_revision)
            payload = json.loads(model.payload_json)
            state = payload["content"]["initial_world"]["state"]
            world = repo.get_initial_world(run_id=run_id, branch_id=source_id)
            payload["content"]["initial_world"] = {
                "fingerprint": world.fingerprint,
                "state": state,
            }
            summary = json.loads(model.change_summary_json)
            model.payload_json = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            )
            model.content_hash = saved_revision_content_hash(
                revision_id=model.revision_id,
                run_id=model.run_id,
                branch_id=model.branch_id,
                sequence=model.sequence,
                parent_revision_id=model.parent_revision_id,
                kind=model.kind,
                payload_schema_version=model.payload_schema_version,
                payload=payload,
                change_summary=summary,
            )

        identities = iter(("rollback-branch", "rollback-draft", "rollback-revision"))
        service = RunBranchCreationService(repo, lambda _kind: next(identities))

        def fail_revision_insert(*_args):
            raise RuntimeError("injected late fork failure")

        event.listen(BranchSavedRevisionModel, "before_insert", fail_revision_insert)
        try:
            with pytest.raises(RuntimeError, match="injected late fork failure"):
                service.create_from_saved_revision(
                    run_id=run_id,
                    source_branch_id=source_id,
                    source_saved_revision_id=source_revision,
                )
        finally:
            event.remove(
                BranchSavedRevisionModel, "before_insert", fail_revision_insert
            )
        with repo._session_factory() as session:
            assert session.get(RunBranchModel, "rollback-branch") is None
            assert session.get(BranchStateModel, "rollback-branch") is None
            assert (
                session.scalar(
                    text(
                        "SELECT COUNT(*) FROM branch_working_drafts WHERE branch_id='rollback-branch'"
                    )
                )
                == 0
            )
            assert (
                session.get(InitialWorldStateModel, (run_id, "rollback-branch")) is None
            )
            assert session.get(BranchSavedRevisionModel, "rollback-revision") is None
            for table in (
                "official_ranking_candidates",
                "official_ranking_commands",
                "player_lifecycle_week_states",
                "player_sporting_week_states",
            ):
                assert session.scalar(
                    text(
                        f"SELECT COUNT(*) FROM {table} WHERE run_id=:run_id "
                        "AND branch_id='rollback-branch'"
                    ),
                    {"run_id": run_id},
                ) == 0

        linked_run, linked_branch, linked_revision, _ = _create_saved_world(
            server, tmp_path, suffix="bad-link", with_ranking=True
        )
        with repo._session_factory.begin() as session:
            model = session.get(BranchSavedRevisionModel, linked_revision)
            payload = json.loads(model.payload_json)
            ranking = load_saved_ranking_component(
                payload, run_id=linked_run, branch_id=linked_branch
            )
            entry = ranking.entries[0]
            original = RankingBootstrapCommand.model_validate_json(
                entry.receipts[0].request_payload_json
            )
            corrupted = original.model_copy(
                update={"initial_world_fingerprint": "f" * 64}
            )
            receipt = entry.receipts[0].model_copy(
                update={
                    "request_fingerprint": corrupted.fingerprint,
                    "request_payload_json": corrupted.canonical_request_json,
                }
            )
            inputs = entry.inputs.model_copy(
                update={"command_request_fingerprint": corrupted.fingerprint}
            )
            ranking = ranking.model_copy(
                update={
                    "entries": (
                        entry.model_copy(
                            update={"inputs": inputs, "receipts": (receipt,)}
                        ),
                    )
                }
            )
            payload["content"]["ranking_preparation"] = {
                "fingerprint": ranking.fingerprint,
                "state": ranking.model_dump(mode="json"),
            }
            summary = json.loads(model.change_summary_json)
            model.payload_json = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            )
            model.content_hash = saved_revision_content_hash(
                revision_id=model.revision_id,
                run_id=model.run_id,
                branch_id=model.branch_id,
                sequence=model.sequence,
                parent_revision_id=model.parent_revision_id,
                kind=model.kind,
                payload_schema_version=model.payload_schema_version,
                payload=payload,
                change_summary=summary,
            )
        status, _ = _request(
            "POST",
            f"{server.base_url}/run-containers/{linked_run}/branches",
            {
                "source_branch_id": linked_branch,
                "source_saved_revision_id": linked_revision,
            },
        )
        assert status == 409


@pytest.mark.pr_critical
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

        # InitialWorld alone is enough to require a target-owned materialized root.
        status, world_fork = _request(
            "POST",
            f"{server.base_url}/run-containers/{run_id}/branches",
            {
                "source_branch_id": branch_id,
                "source_saved_revision_id": world_saved["saved_revision"][
                    "revision_id"
                ],
            },
        )
        assert status == 201, world_fork
        world_fork_id = world_fork["branch_id"]
        assert (
            world_fork["saved_head_revision_id"]
            != world_saved["saved_revision"]["revision_id"]
        )
        fork_world_root = (
            f"{server.base_url}/admin/players/runs/{run_id}/branches/"
            f"{world_fork_id}/initial-world"
        )
        status, fork_owned = _request("GET", fork_world_root)
        assert status == 200
        assert fork_owned["branch_id"] == world_fork_id
        source_world_state = server.app.state.runtime.repository.get_initial_world(
            run_id=run_id, branch_id=branch_id
        )
        fork_world_state = server.app.state.runtime.repository.get_initial_world(
            run_id=run_id, branch_id=world_fork_id
        )
        assert fork_world_state.fingerprint != source_world_state.fingerprint
        for provenance_field in (
            "source_kind",
            "source_season",
            "source_fingerprint",
            "bootstrap_seed",
            "bootstrap_fingerprint",
            "adopted_by_command_id",
            "adoption_request_fingerprint",
        ):
            assert fork_owned[provenance_field] == original_owned[provenance_field]
        assert fork_owned["players"] == original_owned["players"]
        assert fork_owned["policies"] == original_owned["policies"]
        assert _request("GET", world_root)[1] == original_owned
        assert world_fork["is_viewer_branch"] is False

        # A nested fork rematerializes again rather than inheriting its parent's
        # Branch-scoped world identity.
        status, nested_fork = _request(
            "POST",
            f"{server.base_url}/run-containers/{run_id}/branches",
            {
                "source_branch_id": world_fork_id,
                "source_saved_revision_id": world_fork["saved_head_revision_id"],
            },
        )
        assert status == 201, nested_fork
        nested_world = _request(
            "GET",
            f"{server.base_url}/admin/players/runs/{run_id}/branches/"
            f"{nested_fork['branch_id']}/initial-world",
        )[1]
        assert nested_world["branch_id"] == nested_fork["branch_id"]
        nested_world_state = server.app.state.runtime.repository.get_initial_world(
            run_id=run_id, branch_id=nested_fork["branch_id"]
        )
        assert nested_world_state.fingerprint not in {
            source_world_state.fingerprint,
            fork_world_state.fingerprint,
        }

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

        # The linked bootstrap is rebuilt against the target-owned InitialWorld;
        # neither the source command nor stable player identities are rewritten.
        repository = server.app.state.runtime.repository
        with repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            source_ranking_before = capture_ranking_revision_state(
                session, run_id=run_id, branch_id=branch_id
            )
        status, ranking_fork = _request(
            "POST",
            f"{server.base_url}/run-containers/{run_id}/branches",
            {
                "source_branch_id": branch_id,
                "source_saved_revision_id": ranked_revision,
            },
        )
        assert status == 201, ranking_fork
        ranking_fork_id = ranking_fork["branch_id"]
        assert (
            _request(
                "GET",
                f"{server.base_url}/admin/players/runs/{run_id}/branches/"
                f"{ranking_fork_id}/initial-world",
            )[0]
            == 200
        )
        with repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            target_ranking = capture_ranking_revision_state(
                session, run_id=run_id, branch_id=ranking_fork_id
            )
        target_command = RankingBootstrapCommand.model_validate_json(
            target_ranking.entries[0].receipts[0].request_payload_json
        )
        source_command = RankingBootstrapCommand.model_validate_json(
            source_ranking_before.entries[0].receipts[0].request_payload_json
        )
        assert target_command.branch_id == ranking_fork_id
        target_world_state = server.app.state.runtime.repository.get_initial_world(
            run_id=run_id, branch_id=ranking_fork_id
        )
        assert (
            target_command.initial_world_fingerprint == target_world_state.fingerprint
        )
        assert target_command.fingerprint != source_command.fingerprint
        assert target_command.players == source_command.players
        assert target_ranking.fingerprint != source_ranking_before.fingerprint
        with repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            assert (
                capture_ranking_revision_state(
                    session, run_id=run_id, branch_id=branch_id
                )
                == source_ranking_before
            )
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
                "SELECT fingerprint,payload_json FROM player_lifecycle_week_states "
                "WHERE run_id=? AND branch_id=? AND week_ordinal=0",
                (run_id, branch_id),
            ).fetchone()
            live = json.loads(live_row[1])
            sporting_live_row = connection.execute(
                "SELECT fingerprint,payload_json FROM player_sporting_week_states "
                "WHERE run_id=? AND branch_id=? AND week_ordinal=0",
                (run_id, branch_id),
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
                        "SELECT payload_json FROM player_lifecycle_week_states "
                        "WHERE run_id=? AND branch_id=? AND week_ordinal=0",
                        (run_id, branch_id),
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
                        "SELECT payload_json FROM player_lifecycle_week_states "
                        "WHERE run_id=? AND branch_id=? AND week_ordinal=0",
                        (run_id, branch_id),
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

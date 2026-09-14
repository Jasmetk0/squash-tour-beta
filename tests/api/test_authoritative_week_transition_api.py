"""Real HTTP/file-backed SQLite acceptance tests for atomic Week Transition."""

import sqlite3
import json
from urllib import error, request

import pytest
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority

from test_admin_ranking_preparation_api import initial
from test_ranking_preparation_preview_api import dump
from test_saved_revision_history_api import ApiServer, _create_run, _request
import beta_engine.infrastructure.db.authoritative_week_transition as transition_module


def confirm(url, command, preview):
    req = request.Request(
        url, data=json.dumps(command).encode(), method="POST",
        headers={"Content-Type": "application/json",
                 "X-Week-Transition-Request-Fingerprint": preview["request_fingerprint"],
                 "X-Week-Transition-Ranking-Fingerprint":
                     preview["result"]["official_ranking_fingerprint"]},
    )
    try:
        with request.urlopen(req) as response:
            return response.status, json.loads(response.read())
    except error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def counts(path):
    with sqlite3.connect(path) as connection:
        return tuple(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in (
            "published_official_rankings", "authoritative_world_states",
            "authoritative_world_events", "authoritative_week_transition_receipts"))


def prepared_transition(server, name):
    run_id, branch_id, empty_revision = _create_run(server, display_name=name)
    ranking = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
    bootstrap = initial() | {"run_id": run_id, "branch_id": branch_id}
    assert _request("POST", ranking + "/prepare/initial", bootstrap)[0] == 201
    authority = {"run_id": run_id, "branch_id": branch_id, "base_revision_id": empty_revision,
        "completed_week": {"season_index": 0, "week": 1}, "target_week": {"season_index": 0, "week": 2},
        "players": bootstrap["players"], "policy": bootstrap["policy"], "provenance": "Frozen boundary",
        "adopted_by_command_id": "authority", "audit": bootstrap["audit"]}
    adopted = _request("POST", ranking + "/transition-authorities", authority)[1]
    review = _request("GET", ranking + "/save/preview")[1]
    saved = _request("POST", ranking + "/save", {"expected_draft_version": review["draft_version"],
        "expected_ranking_fingerprint": review["ranking_fingerprint"]})[1]
    command = {"command_id": "transition", "run_id": run_id, "branch_id": branch_id,
        "base_revision_id": saved["saved_revision"]["revision_id"], "completed_week": authority["completed_week"],
        "target_week": authority["target_week"], "authority_fingerprint": RankingTransitionAuthority.model_validate_json(json.dumps(adopted)).fingerprint,
        "tournaments": [], "audit": bootstrap["audit"]}
    return run_id, branch_id, command


@pytest.mark.parametrize("failure_point", ["after_ranking_staging", "before_publication", "after_publication"])
def test_failure_at_each_write_boundary_rolls_back_everything(tmp_path, monkeypatch, failure_point):
    path = tmp_path / f"rollback-{failure_point}.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(server, failure_point)
        before = dump(path)
        def fail(name):
            if name == failure_point:
                raise RuntimeError("forced transition failure")
        monkeypatch.setattr(transition_module, "_fault_injection_point", fail)
        # Unhandled fault is deliberately asserted at the transaction owner level.
        runner = transition_module.AuthoritativeWeekTransitionRunner(
            server.app.state.runtime.repository._session_factory)
        with pytest.raises(RuntimeError, match="forced"):
            runner.execute(transition_module.AuthoritativeWeekTransitionCommand.model_validate_json(json.dumps(command)))
        assert dump(path) == before and counts(path) == (0, 0, 0, 0)


@pytest.mark.smoke
def test_atomic_publication_retry_save_reopen_and_bidirectional_restore(tmp_path):
    path = tmp_path / "week-transition.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, empty_revision = _create_run(server, display_name="Atomic week")
        ranking = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
        bootstrap = initial() | {"run_id": run_id, "branch_id": branch_id}
        assert _request("POST", ranking + "/prepare/initial", bootstrap)[0] == 201
        authority = {
            "run_id": run_id, "branch_id": branch_id, "base_revision_id": empty_revision,
            "completed_week": {"season_index": 0, "week": 1},
            "target_week": {"season_index": 0, "week": 2},
            "players": bootstrap["players"], "policy": bootstrap["policy"],
            "provenance": "Frozen supported boundary", "adopted_by_command_id": "authority-2",
            "audit": bootstrap["audit"],
        }
        status, adopted = _request("POST", ranking + "/transition-authorities", authority)
        assert status == 201
        review = _request("GET", ranking + "/save/preview")[1]
        status, saved_base = _request("POST", ranking + "/save", {
            "expected_draft_version": review["draft_version"],
            "expected_ranking_fingerprint": review["ranking_fingerprint"],
        })
        assert status == 201
        base_revision = saved_base["saved_revision"]["revision_id"]
        command = {
            "command_id": "transition-week-2", "run_id": run_id, "branch_id": branch_id,
            "base_revision_id": base_revision,
            "completed_week": authority["completed_week"], "target_week": authority["target_week"],
            "authority_fingerprint": RankingTransitionAuthority.model_validate_json(json.dumps(adopted)).fingerprint,
            "tournaments": [],
            "audit": bootstrap["audit"],
        }
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        before = dump(path)
        status, preview = _request("POST", root + "/preview", command)
        assert status == 200 and dump(path) == before and counts(path) == (0, 0, 0, 0)
        assert confirm(root, command | {"base_revision_id": empty_revision}, preview)[0] == 409
        assert confirm(root, command | {"branch_id": "other"}, preview)[0] == 409
        changed = command | {"audit": bootstrap["audit"] | {"reason": "different review"}}
        assert confirm(root, changed, preview)[0] == 409
        assert dump(path) == before and counts(path) == (0, 0, 0, 0)
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE ranking_transition_authorities SET fingerprint = ?", ("0" * 64,))
        corrupted = dump(path)
        assert confirm(root, command, preview)[0] == 409
        assert dump(path) == corrupted and counts(path) == (0, 0, 0, 0)
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE ranking_transition_authorities SET fingerprint = ?", (command["authority_fingerprint"],))
        status, confirmed = confirm(root, command, preview)
        assert status == 201 and confirmed == preview
        assert counts(path) == (2, 1, 1, 1)
        after = dump(path)
        assert confirm(root, command, preview) == (201, confirmed)
        assert dump(path) == after
        assert confirm(root, command | {"audit": bootstrap["audit"] | {"reason": "different"}}, preview)[0] == 409
        assert dump(path) == after

        review = _request("GET", ranking + "/save/preview")[1]
        status, transitioned_save = _request("POST", ranking + "/save", {
            "expected_draft_version": review["draft_version"],
            "expected_ranking_fingerprint": review["ranking_fingerprint"],
        })
        assert status == 201
        transition_revision = transitioned_save["saved_revision"]["revision_id"]
        status, restored = _request("POST", f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}/saved-revisions/{base_revision}/restore", {
            "expected_head_saved_revision_id": transition_revision,
            "expected_draft_version": transitioned_save["working_draft"]["draft_version"],
            "expected_current_viewer_branch_id": branch_id, "explicit_confirmation": True,
        })
        assert status == 201 and counts(path) == (0, 0, 0, 0)
        status, forward = _request("POST", f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}/saved-revisions/{transition_revision}/restore", {
            "expected_head_saved_revision_id": restored["saved_revision"]["revision_id"],
            "expected_draft_version": restored["working_draft"]["draft_version"],
            "expected_current_viewer_branch_id": branch_id, "explicit_confirmation": True,
        })
        assert status == 201 and counts(path) == (2, 1, 1, 1)
    with ApiServer(database_url=f"sqlite:///{path}"):
        assert counts(path) == (2, 1, 1, 1)


def test_normal_boundary_accepts_week_60_to_61_and_rejects_season_rollover_without_mutation(tmp_path):
    from beta_engine.application.authoritative_week_transition import AuthoritativeWeekTransitionCommand

    base = {"command_id": "boundary", "run_id": "run", "branch_id": "branch",
        "base_revision_id": "revision", "authority_fingerprint": "a" * 64,
        "tournaments": [], "audit": {"actor_label": "Admin", "reason": "Boundary review"}}
    valid = base | {"completed_week": {"season_index": 0, "week": 60},
                    "target_week": {"season_index": 0, "week": 61}}
    assert AuthoritativeWeekTransitionCommand.model_validate_json(json.dumps(valid))
    rollover = base | {"completed_week": {"season_index": 0, "week": 61},
                       "target_week": {"season_index": 1, "week": 1}}
    with pytest.raises(ValueError, match="Season Transition"):
        AuthoritativeWeekTransitionCommand.model_validate_json(json.dumps(rollover))

    path = tmp_path / "season-boundary.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(server, "Season boundary")
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        before = dump(path)
        invalid = command | {"completed_week": rollover["completed_week"],
                             "target_week": rollover["target_week"]}
        assert _request("POST", root + "/preview", invalid)[0] == 422
        assert dump(path) == before and counts(path) == (0, 0, 0, 0)


def test_exact_retry_survives_a_valid_later_published_world_head(tmp_path):
    from sqlalchemy import text
    from beta_engine.domain.rankings.official import (
        OfficialRankingPlayer, RankingWeek, calculate_official_ranking,
    )
    from beta_engine.infrastructure.db.models import (
        AuthoritativeWorldStateModel, PublishedOfficialRankingModel,
    )
    from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore

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
                run_id=run_id, branch_id=branch_id)[-1]
            third = calculate_official_ranking(
                run_id=run_id, branch_id=branch_id,
                week=RankingWeek(season_index=0, week=3), policy=second.policy,
                players=tuple(OfficialRankingPlayer.model_validate(player)
                              for player in initial()["players"]),
                results=(), previous=second,
            )
            session.add(PublishedOfficialRankingModel(
                run_id=run_id, branch_id=branch_id, week_ordinal=third.week.ordinal,
                snapshot_fingerprint=third.fingerprint, payload_json=third.model_dump_json()))
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

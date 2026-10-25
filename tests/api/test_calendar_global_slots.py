"""Production HTTP/SQLite overlapping native Editions; no fabricated match results."""

import json
import sqlite3
import time
from copy import deepcopy

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_tour_flow import (
    command,
    execute,
    inspect,
    save_tour,
    setup,
    tour_url,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def ready(server, width=52, *, seasons=2):
    offset = 37 if width == 61 else 80 if width == 80 else 1
    repo, _ = setup(server, RunCalendar(width, offset, 2030, seasons), 8)
    for eid in ("parallel-a", "parallel-b"):
        view = inspect(server)
        week = view["state"]["week"]
        execute(
            server,
            command(
                view,
                "create-edition",
                name=eid + ":create",
                data={
                    "schema_version": "calendar_tournament_edition.v2",
                    "simulation_seed": 891,
                    "edition_id": eid,
                    "name": eid,
                    "week": {**week, "week": 4},
                    "announcement_week": {**week, "week": 3},
                    "start_slot": 1,
                    "main_entrant_count": 4,
                    "ranked": True,
                    "validity_weeks": width,
                    "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
                },
            ),
        )
        save_tour(server)
    for target in (3, 4):
        execute(server, command(inspect(server), "transition", name=f"week-{target}"))
        save_tour(server)
    players = [p["player_id"] for p in inspect(server)["players"]]
    for i, eid in enumerate(("parallel-a", "parallel-b")):
        execute(
            server,
            command(
                inspect(server),
                "submit",
                name=eid + ":submit",
                edition_id=eid,
                data={"player_ids": players[i * 4 : i * 4 + 4]},
            ),
        )
        for action in ("approve", "draw"):
            execute(
                server,
                command(
                    inspect(server), action, name=eid + ":" + action, edition_id=eid
                ),
            )
        save_tour(server)
    return repo


def copy_database(source, target):
    with sqlite3.connect(source) as source_db, sqlite3.connect(target) as target_db:
        source_db.backup(target_db)


def test_metadata_only_global_history_keeps_payload_until_physical_gates_finish(
    tmp_path, prepared_slots, monkeypatch
):
    from sqlalchemy import text

    from beta_engine.infrastructure.db import calendar_terminal_results
    from beta_engine.infrastructure.db.models import BranchSavedRevisionModel, RunBranchModel

    path = tmp_path / "metadata-source-gates.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo = server.app.state.runtime.repository
        verify = calendar_terminal_results.verify_saved_terminal_results
        checked = []

        def complete_payload(repository, session, revision, **kwargs):
            physical = session.get(BranchSavedRevisionModel, revision.revision_id)
            raw = json.loads(physical.payload_json)
            if raw.get("content", {}).get("calendar_tour_authority", {}).get("state", {}).get("schema_version") == "calendar_tour_authority.v5":
                assert revision.payload == raw
                checked.append(revision.revision_id)
            return verify(repository, session, revision, **kwargs)

        monkeypatch.setattr(calendar_terminal_results, "verify_saved_terminal_results", complete_payload)
        with repo._session_factory() as session:
            session.execute(text("BEGIN"))
            lineage = repo._validated_branch_revision_lineage_in_session(
                session=session, branch=session.get(RunBranchModel, "branch"),
                payload_revision_ids=frozenset(),
            )
        assert checked
        assert all(not revision.payload for revision in lineage)
        ancestor_id = checked[0]
        checked.clear()
        with repo._session_factory() as session:
            session.execute(text("BEGIN"))
            warm = repo._validated_branch_revision_lineage_in_session(
                session=session, branch=session.get(RunBranchModel, "branch"),
                payload_revision_ids=frozenset(),
            )
        assert warm == lineage
        assert not checked, "unchanged complete graph and absent closure need only metadata"

        # A newly inserted, rehashed marker must invalidate that absence proof,
        # even though every sporting/Tour component remains byte-for-byte equal.
        from beta_engine.domain.run_revisions import saved_revision_content_hash

        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, ancestor_id)
            original_bytes = row.payload_json, row.content_hash
            body = json.loads(row.payload_json)
            body["run"]["native_branch_closures"] = "not a closure history"
            row.payload_json = json.dumps(body)
            row.content_hash = saved_revision_content_hash(
                revision_id=row.revision_id, run_id=row.run_id, branch_id=row.branch_id,
                sequence=row.sequence, parent_revision_id=row.parent_revision_id,
                kind=row.kind, payload_schema_version=row.payload_schema_version,
                payload=body, change_summary=json.loads(row.change_summary_json),
            )
        with repo._session_factory() as session, pytest.raises(ValueError, match="[Cc]losure"):
            session.execute(text("BEGIN"))
            repo._validated_branch_revision_lineage_in_session(
                session=session, branch=session.get(RunBranchModel, "branch"),
                payload_revision_ids=frozenset(),
            )
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, ancestor_id)
            row.payload_json, row.content_hash = original_bytes
        with repo._session_factory() as session:
            session.execute(text("BEGIN"))
            assert repo._validated_branch_revision_lineage_in_session(
                session=session, branch=session.get(RunBranchModel, "branch"),
                payload_revision_ids=frozenset(),
            ) == lineage


def test_first_global_edition_after_birth_keeps_the_actual_native_root(tmp_path):
    from tests.api.test_calendar_native_birth_week_execution import sign_prospects

    database = f"sqlite:///{tmp_path / 'birth-global-upgrade.db'}"
    with ApiServer(database_url=database) as server:
        clock = RunCalendar(52, 1, 2030, 3)
        repo, _ = setup(server, clock, 4)
        sign_prospects(server, repo, clock)
        execute(server, command(inspect(server), "transition", name="global-admit"))
        saved = save_tour(server)
        born = inspect(server)
        assert born["state"]["schema_version"] == "calendar_tour_authority.v3"
        week = born["state"]["week"]
        execute(server, command(born, "create-edition", name="first-global-after-birth", data={
            "schema_version": "calendar_tournament_edition.v2",
            "simulation_seed": 891, "edition_id": "born-global", "name": "Born global",
            "week": {**week, "week": 5}, "announcement_week": {**week, "week": 4},
            "start_slot": 1, "main_entrant_count": 4, "ranked": True,
            "validity_weeks": 52,
            "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
        }))
        upgraded = inspect(server)
        assert upgraded["state"]["competition_root_tour"] == born["state"]
        assert upgraded["state"]["competition_root_saved_head"] == saved["revision_id"]
        save_tour(server)
        expected = inspect(server)["state"]
    with ApiServer(database_url=database) as reopened:
        assert inspect(reopened)["state"] == expected


def test_real_overlapping_slots_save_restart_and_points(tmp_path, prepared_slots):
    path = tmp_path / "slots.db"
    copy_database(prepared_slots, path)
    db = f"sqlite:///{path}"
    with ApiServer(database_url=db) as server:
        view = inspect(server)
        assert view["next_slot"]["number"] == 4
        assert view["next_slot"]["remaining"] == 4
        result, request = execute(
            server, command(view, "next-match", name="first-match")
        )
        assert result["completed"] == 1 and result["remaining"] == 3
        assert _request("POST", tour_url(server) + "/execute", request) == (201, result)
        save_tour(server)
        snapshot = inspect(server)["next_slot"]["snapshot_fingerprint"]
    with ApiServer(database_url=db) as server:
        view = inspect(server)
        assert view["next_slot"]["snapshot_fingerprint"] == snapshot
        assert view["next_slot"]["remaining"] == 3
        execute(server, command(view, "next-slot", name="complete-first-slot"))
        save_tour(server)
        assert inspect(server)["next_slot"]["number"] == 5
        execute(server, command(inspect(server), "next-slot", name="finals-slot"))
        save_tour(server)
        view = inspect(server)
        assert view["next_slot"] is None
        for eid in ("parallel-a", "parallel-b"):
            assert len(view["edition_evidence"][eid]["matches"]) == 3
            execute(
                server,
                command(
                    inspect(server),
                    "confirm-result",
                    name=eid + ":confirm",
                    edition_id=eid,
                ),
            )
            save_tour(server)
        execute(server, command(inspect(server), "transition", name="publish-points"))
        save_tour(server)
        rows = inspect(server)["state"]["rankings"][-1]["rows"]
        assert sorted(r["points"] for r in rows) == [30, 30, 30, 30, 60, 60, 100, 100]


def sporting(server):
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
        load_checkpoint,
    )

    with server.app.state.runtime.repository._session_factory() as session:
        return load_checkpoint(session, run_id="run", branch_id="branch")


def test_batch_matches_reverse_order_save_and_engine_free_reads(
    tmp_path, prepared_slots, monkeypatch
):
    from beta_engine.domain.matches.match_engine import MatchEngine

    outcomes = []
    elapsed = []
    for mode in ("batch", "reverse"):
        path = tmp_path / f"{mode}.db"
        copy_database(prepared_slots, path)
        started = time.monotonic()
        with ApiServer(database_url=f"sqlite:///{path}") as server:
            view = inspect(server)
            if mode == "batch":
                execute(server, command(view, "next-slot", name="whole-slot"))
            else:
                for i, mid in enumerate(
                    reversed([m["match_id"] for m in view["next_slot"]["matches"]])
                ):
                    execute(
                        server,
                        command(
                            inspect(server),
                            "next-match",
                            name=f"match-{i}",
                            data={"match_id": mid},
                        ),
                    )
                    if i == 1:
                        save_tour(server)
            # Repeated identical reads use byte-bound completed proofs.
            inspect(server)
            with monkeypatch.context() as patch:
                patch.setattr(
                    MatchEngine,
                    "simulate",
                    lambda *args, **kwargs: pytest.fail("GET recalculated a match"),
                )
                for _ in range(3):
                    assert inspect(server)["next_slot"]["number"] == 5
            save_tour(server)
            execute(server, command(inspect(server), "next-slot", name="final-slot"))
            save_tour(server)
            outcomes.append(sporting(server))
        elapsed.append(time.monotonic() - started)
    assert outcomes[0] == outcomes[1]
    assert len(outcomes[0].tournaments[-2:]) == 2
    print({"actual_batch_and_reverse_seconds": elapsed}, flush=True)


def test_partial_source_public_fork_is_independent(tmp_path, prepared_slots):
    from tests.api.test_native_fork_public_continuation import Tour, fork

    path = tmp_path / "partial-fork.db"
    copy_database(prepared_slots, path)
    db = f"sqlite:///{path}"
    with ApiServer(database_url=db) as server:
        execute(server, command(inspect(server), "next-match", name="source-partial"))
        saved = save_tour(server)
        source = sporting(server)
        created = fork(server, saved["revision_id"], name="Independent partial slot")
        target = Tour(server, created["branch_id"])
        assert target.view()["next_slot"]["remaining"] == 3
        target.execute("next-match", "target-second-match")
        target_partial = target.save()
        nested_created = fork(
            server,
            target_partial["revision_id"],
            branch=created["branch_id"],
            name="Nested independent partial slot",
        )
        nested = Tour(server, nested_created["branch_id"])
        assert nested.view()["next_slot"]["remaining"] == 2
        assert nested.view()["next_slot"]["completed"] == 2
        nested.execute("next-slot", "nested-rest-of-slot")
        nested.save()
        assert nested.view()["next_slot"]["number"] == 5
        nested.execute("next-slot", "nested-finals")
        nested.save()
        for eid in ("parallel-a", "parallel-b"):
            nested.execute("confirm-result", eid + ":nested-confirm", edition_id=eid)
            nested.save()
        nested.advance("nested-points")
        assert sorted(
            r["points"] for r in nested.view()["state"]["rankings"][-1]["rows"]
        ) == [30, 30, 30, 30, 60, 60, 100, 100]
        assert target.view()["next_slot"]["remaining"] == 2
        target.execute("next-slot", "target-rest-of-slot")
        target.save()
        assert target.view()["next_slot"]["number"] == 5
        target.execute("next-slot", "target-finals")
        target.save()
        assert sporting(server) == source
        for eid in ("parallel-a", "parallel-b"):
            target.execute("confirm-result", eid + ":target-confirm", edition_id=eid)
            target.save()
        target.advance("target-points")
        assert sorted(
            r["points"] for r in target.view()["state"]["rankings"][-1]["rows"]
        ) == [30, 30, 30, 30, 60, 60, 100, 100]
        assert inspect(server)["next_slot"]["remaining"] == 3


def test_full_simulation_uses_slot_children_and_frozen_target(tmp_path, prepared_slots):
    from tests.api.test_native_full_simulation_tasks import resume, reviewed, start

    path = tmp_path / "slot-worker.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        original = reviewed(
            server, {"season_index": 0, "week": 5}, name="global-slot-worker"
        )
        task = start(server, original)
        assert task["checkpoint"] == "native_manual_save_required", task
        assert inspect(server)["next_slot"]["number"] == 5
        save_tour(server)
        task = resume(server, task, "saved-first-slot")
        assert task["checkpoint"] == "native_manual_save_required", task
        assert inspect(server)["next_slot"] is None
        save_tour(server)
        task = resume(server, task, "saved-finals-slot")
        assert task["checkpoint"] == "native_result_review_required", task
        for eid in ("parallel-a", "parallel-b"):
            execute(
                server,
                command(
                    inspect(server),
                    "confirm-result",
                    name=eid + ":worker-confirm",
                    edition_id=eid,
                ),
            )
            save_tour(server)
        task = resume(server, task, "confirmed-both-results")
        assert task["checkpoint"] == "native_manual_save_required", task
        save_tour(server)
        task = resume(server, task, "saved-next-week")
        assert task["state"] == "target_reached", task
        state = inspect(server)["state"]
        child_actions = [
            r["request"]["command"]["action"]
            for r in state["receipts"]
            if r["command_id"].startswith("nfs-")
        ]
        assert child_actions == ["next-slot", "next-slot", "transition"]
        assert state["week"]["week"] == 5


def test_retry_concurrent_stale_rollback_and_rehashed_slot(
    tmp_path, prepared_slots, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor

    from beta_engine.application import calendar_tour_service
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.models import (
        CalendarPlayerSportingCheckpointModel,
        CalendarTourAuthorityModel,
    )
    from tests.api.test_player_generation_calendar_gate import _dump

    path = tmp_path / "negative.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo = server.app.state.runtime.repository
        view = inspect(server)
        viewer_url = server.base_url + "/viewer/runs/run/calendar-tour"
        code, public = _request("GET", viewer_url)
        assert code == 200, public
        # Warm publication reauthenticates actual Saved bytes and sources, but
        # cannot run the MatchEngine again just to project that same history.
        from beta_engine.domain.matches.match_engine import MatchEngine

        def unexpected_replay(*_args, **_kwargs):
            raise AssertionError("Authenticated publication replayed accepted matches")

        with monkeypatch.context() as patch:
            patch.setattr(MatchEngine, "simulate", unexpected_replay)
            assert _request("GET", viewer_url) == (200, public)
        first = command(view, "next-match", name="concurrent-exact")
        stale = command(view, "next-match", name="concurrent-other")
        requests = []
        for cmd in (first, stale):
            code, preview = _request("POST", tour_url(server) + "/preview", cmd)
            assert code == 200, preview
            requests.append(
                {
                    "command": cmd,
                    "expected_preview_fingerprint": preview["preview_fingerprint"],
                    "explicit_confirmation": True,
                }
            )
        before = _dump(path)

        def fail(point):
            if point == "after_global_slot_matches_write":
                raise ValueError("Injected late global-slot rollback")

        with monkeypatch.context() as patch:
            patch.setattr(calendar_tour_service, "_fault_injection_point", fail)
            assert (
                _request("POST", tour_url(server) + "/execute", requests[0])[0] == 409
            )
        assert _dump(path) == before
        with ThreadPoolExecutor(max_workers=2) as pool:
            attempts = list(
                pool.map(
                    lambda _: _request(
                        "POST", tour_url(server) + "/execute", requests[0]
                    ),
                    range(2),
                )
            )
        assert attempts[0] == attempts[1] and attempts[0][0] == 201
        assert _request("POST", tour_url(server) + "/execute", requests[1])[0] == 409
        forged_request = deepcopy(requests[0])
        forged_request["command"]["seed"] += 1
        assert _request("POST", tour_url(server) + "/execute", forged_request)[0] == 409
        assert inspect(server)["next_slot"]["completed"] == 1
        # A self-consistent rehash of unused frozen inputs is not source proof.
        with repo._session_factory.begin() as session:
            row = session.get(CalendarPlayerSportingCheckpointModel, ("run", "branch"))
            tour = session.get(CalendarTourAuthorityModel, ("run", "branch"))
            originals = (
                row.payload_json,
                row.fingerprint,
                tour.payload_json,
                tour.fingerprint,
            )
            body = json.loads(row.payload_json)
            body["events"][-1]["scheduled"][-1]["seed"] += 1
            row.payload_json, row.fingerprint = json.dumps(body), canonical_hash(body)
            state = json.loads(tour.payload_json)
            state["checkpoint_fingerprint"] = row.fingerprint
            tour.payload_json, tour.fingerprint = (
                json.dumps(state),
                canonical_hash(state),
            )
        assert _request("GET", tour_url(server))[0] == 409
        with repo._session_factory.begin() as session:
            row = session.get(CalendarPlayerSportingCheckpointModel, ("run", "branch"))
            tour = session.get(CalendarTourAuthorityModel, ("run", "branch"))
            row.payload_json, row.fingerprint, tour.payload_json, tour.fingerprint = (
                originals
            )
        assert inspect(server)["next_slot"]["completed"] == 1

        from beta_engine.domain.run_revisions import saved_revision_content_hash
        from beta_engine.infrastructure.db.models import BranchSavedRevisionModel

        source_id = next(
            a["played_saved_head"]
            for a in inspect(server)["state"]["editions"]
            if a["played_saved_head"]
        )
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, source_id)
            original_source = row.payload_json, row.content_hash
            body = json.loads(row.payload_json)
            component = body["content"]["calendar_tour_authority"]
            component["state"]["editions"][0]["edition"]["point_table"]["champion"] += 1
            component["fingerprint"] = canonical_hash(component["state"])
            row.payload_json = json.dumps(body)
            row.content_hash = saved_revision_content_hash(
                revision_id=row.revision_id,
                run_id=row.run_id,
                branch_id=row.branch_id,
                sequence=row.sequence,
                parent_revision_id=row.parent_revision_id,
                kind=row.kind,
                payload_schema_version=row.payload_schema_version,
                payload=body,
                change_summary=json.loads(row.change_summary_json),
            )
        assert _request("GET", tour_url(server))[0] == 409
        assert _request("GET", viewer_url)[0] == 409
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, source_id)
            row.payload_json, row.content_hash = original_source
        assert inspect(server)["next_slot"]["completed"] == 1
        assert _request("GET", viewer_url) == (200, public)


def test_restore_partial_slot_retains_accepted_result_and_exact_retry(
    tmp_path, prepared_slots
):
    from tests.api.test_calendar_population_sporting_checkpoint import restore

    path = tmp_path / "restore-partial.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        first, request = execute(
            server, command(inspect(server), "next-match", name="restore-first")
        )
        saved = save_tour(server)
        accepted = sporting(server)
        execute(server, command(inspect(server), "next-match", name="restore-second"))
        save_tour(server)
        restore(server, saved["revision_id"])
        assert sporting(server) == accepted
        assert inspect(server)["next_slot"]["remaining"] == 3
        assert _request("POST", tour_url(server) + "/execute", request) == (201, first)
        execute(server, command(inspect(server), "next-slot", name="restore-rest"))
        save_tour(server)
        assert inspect(server)["next_slot"]["number"] == 5


def test_same_player_collision_blocks_only_affected_matches(tmp_path, prepared_slots):
    from tests.api.test_calendar_population_sporting_checkpoint import restore

    path = tmp_path / "conflict.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo = server.app.state.runtime.repository
        # Select an actual Saved revision before B's applications; no positive
        # authority or MatchEngine evidence is inserted or fabricated.
        with repo._session_factory() as session:
            from sqlalchemy import select

            from beta_engine.infrastructure.db.models import BranchSavedRevisionModel

            source = None
            for row in session.scalars(
                select(BranchSavedRevisionModel).order_by(
                    BranchSavedRevisionModel.sequence.desc()
                )
            ):
                raw = (
                    json.loads(row.payload_json)
                    .get("content", {})
                    .get("calendar_tour_authority", {})
                    .get("state", {})
                )
                editions = {
                    a["edition"]["edition_id"]: a for a in raw.get("editions", [])
                }
                if (
                    set(editions) == {"parallel-a", "parallel-b"}
                    and editions["parallel-a"]["draw"]
                    and not editions["parallel-b"]["submissions"]
                ):
                    source = row.revision_id
                    break
        assert source
        restore(server, source)
        view = inspect(server)
        a = next(
            a
            for a in view["state"]["editions"]
            if a["edition"]["edition_id"] == "parallel-a"
        )
        shared = a["field"]["direct_main_player_ids"][0]
        selected = [shared] + [
            p["player_id"]
            for p in view["players"]
            if p["player_id"] not in a["field"]["direct_main_player_ids"]
        ][:3]
        execute(
            server,
            command(
                view,
                "submit",
                name="conflict-applications",
                edition_id="parallel-b",
                data={"player_ids": selected},
            ),
        )
        for action in ("approve", "draw"):
            execute(
                server,
                command(
                    inspect(server),
                    action,
                    name="conflict-" + action,
                    edition_id="parallel-b",
                ),
            )
        save_tour(server)
        view = inspect(server)
        assert view["next_slot"]["conflicts"][0]["player_id"] == shared
        code, blocked = _request(
            "POST",
            tour_url(server) + "/preview",
            command(view, "next-slot", name="blocked-conflict-slot"),
        )
        assert code == 409 and shared in blocked["detail"]["message"], blocked
        independent = next(
            m
            for m in view["next_slot"]["matches"]
            if shared not in (m["player_a_id"], m["player_b_id"])
        )
        before = next(p for p in sporting(server).players if p.player_id == shared)
        execute(
            server,
            command(
                view,
                "next-match",
                name="independent-with-conflict",
                data={"match_id": independent["match_id"]},
            ),
        )
        assert (
            next(p for p in sporting(server).players if p.player_id == shared) == before
        )
        assert len(sporting(server).players) == 8
        save_tour(server)
        assert (
            _request(
                "POST",
                tour_url(server) + "/preview",
                command(inspect(server), "transition", name="cannot-skip-conflict"),
            )[0]
            == 409
        )

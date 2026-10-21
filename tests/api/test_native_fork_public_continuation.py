"""Actual public HTTP/SQLite native fork, not staged private ownership or mocks."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest
from sqlalchemy import event

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_revisions import canonical_json
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from beta_engine.infrastructure.db.repositories import (
    _saved_revision_record_content_hash,
)
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_tour_flow import command, setup
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_branch_review_api import confirmed, preview
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


class Tour:
    def __init__(self, server, branch):
        self.server, self.branch = server, branch
        self.url = server.base_url + f"/admin/runs/run/branches/{branch}/calendar-tour"

    def view(self):
        code, body = _request("GET", self.url)
        assert code == 200, body
        return body

    def prepare(self, action, name, *, edition_id=None, data=None):
        cmd = command(self.view(), action, name=name, edition_id=edition_id, data=data)
        code, body = _request("POST", self.url + "/preview", cmd)
        assert code == 200, body
        return {
            "command": cmd,
            "expected_preview_fingerprint": body["preview_fingerprint"],
            "explicit_confirmation": True,
        }

    def execute(self, action, name, *, edition_id=None, data=None):
        request = self.prepare(action, name, edition_id=edition_id, data=data)
        code, result = _request("POST", self.url + "/execute", request)
        assert code == 201, result
        return result, request

    def save(self):
        view = self.view()
        code, result = _request(
            "POST",
            self.url + "/save",
            {
                "expected_draft_version": view["draft_version"],
                "expected_calendar_tour_fingerprint": view["tour_fingerprint"],
            },
        )
        assert code == 201, result
        return result["saved_revision"]

    def advance(self, name):
        action = (
            "season-transition"
            if self.view()["state"]["week"]["week"] == 7
            else "transition"
        )
        self.execute(action, name)
        return self.save()

    def configure(self, name):
        week = self.view()["state"]["week"]
        clock = RunCalendar.from_metadata(week["calendar"])
        now = clock.ordinal(week["season_index"], week["week"])

        def date(n):
            p = clock.position_at_ordinal(now + n)
            return {
                "calendar": week["calendar"],
                "season_index": p.season_index,
                "week": p.season_week,
            }

        self.execute(
            "create-edition",
            name + ":create",
            data={
                "edition_id": name,
                "name": name,
                "week": date(2),
                "announcement_week": date(1),
                "start_slot": 1,
                "main_entrant_count": 4,
                "ranked": True,
                "validity_weeks": clock.weeks_per_year,
                "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
            },
        )
        self.save()
        self.advance(name + ":announce")
        self.advance(name + ":open")
        ids = [
            p["player_id"] for p in self.view()["players"] if p["status"] == "active"
        ][-4:]
        for action in ("submit", "approve", "draw"):
            self.execute(
                action,
                name + ":" + action,
                edition_id=name,
                data={"player_ids": ids} if action == "submit" else None,
            )
        self.save()
        return ids


def fork(server, source_id, *, branch="branch", name="native-fork"):
    source, review = preview(server, "run", branch, source_id)
    assert review["can_create"], review["blockers"]
    request = confirmed(source, review, name)
    code, result = _request(
        "POST", server.base_url + "/run-containers/run/branches", request
    )
    assert code == 201, result
    assert not result["read_only"] and result["status"] == "active"
    assert _request(
        "POST", server.base_url + "/run-containers/run/branches", request
    ) == (201, result)
    return result


def test_public_native_fork_birth_matches_save_restore_restart_and_independence(
    tmp_path,
):
    path = tmp_path / "public-native.db"
    db = f"sqlite:///{path}"
    clock = RunCalendar(7, 1, 2030, 3)
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, clock, 4)
        source = sign_prospects(server, repo, clock)
        original = Tour(server, "branch")
        original_saved = original.view()
        before = _dump(path)
        created = fork(server, source["revision_id"])
        target_id, root_id = created["branch_id"], created["saved_head_revision_id"]
        # Existing rows are byte-for-byte untouched by creation; only new rows.
        assert set(before) <= set(_dump(path))
        target = Tour(server, target_id)
        assert target.view()["players"] == original_saved["players"]
        request = target.prepare("transition", "fork-birthday")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda _: _request("POST", target.url + "/execute", request),
                    range(2),
                )
            )
        assert results[0] == results[1] and results[0][0] == 201
        born = target.view()
        assert not born["saved"] and len(born["players"]) == 5
        assert any(
            p["player_id"] == "born-native-15" and p["age"] == 15
            for p in born["players"]
        )
        assert original.view() == original_saved
        # A late audit insertion fault rolls back Saved/head/draft/Viewer together.
        failed_before = _dump(path)

        def fail_audit(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith("INSERT INTO branch_revision_audit_events"):
                raise RuntimeError("late fork Save audit fault")

        event.listen(repo._engine, "before_cursor_execute", fail_audit)
        try:
            with pytest.raises(RuntimeError, match="late fork Save"):
                repo.save_viewer_branch_selection_atomically(
                    run_id="run",
                    branch_id=target_id,
                    expected_draft_version=born["draft_version"],
                    expected_calendar_tour_fingerprint=born["tour_fingerprint"],
                    revision_id="failed-save",
                    audit_event_id="failed-audit",
                )
        finally:
            event.remove(repo._engine, "before_cursor_execute", fail_audit)
        assert _dump(path) == failed_before
        saved_birth = target.save()
        original.advance("original-birth")
        original.advance("original-week4")
        assert target.view()["state"]["week"]["week"] == 3
        # Reload/restore target's own Saved root; preserve linear recovery history.
        restore_url = (
            server.base_url
            + f"/run-containers/run/branches/{target_id}/saved-revisions/{root_id}"
        )
        code, review = _request("GET", restore_url + "/restore-preflight")
        assert code == 200 and review["can_restore"], review
        code, restored = _request(
            "POST",
            restore_url + "/restore",
            {
                "expected_head_saved_revision_id": review["saved_head_revision_id"],
                "expected_draft_version": review["draft_version"],
                "expected_current_viewer_branch_id": review["current_viewer_branch_id"],
                "explicit_confirmation": True,
            },
        )
        assert code == 201, restored
        assert (
            restored["safety_checkpoint"]["saved_revision_id"]
            == saved_birth["revision_id"]
        )
        assert target.view()["state"]["week"]["week"] == 2
        target.advance("fork-birthday-again")
        # Actual complete Ranked Tour field + three real rally-level MatchEngine games.
        entrants = target.configure("fork-cup")
        played, played_request = target.execute(
            "play", "fork-cup:play", edition_id="fork-cup"
        )
        assert len(played["played"]["match_ids"]) == 3
        assert "born-native-15" in entrants
        target.save()
        assert _request("POST", target.url + "/execute", played_request) == (
            201,
            played,
        )
        match = target.view()["edition_evidence"]["fork-cup"]["matches"][0]
        code, replay = _request(
            "GET",
            server.base_url
            + f"/admin/runs/run/branches/{target_id}/authoritative-simulation/calendar-continuation/{match['match_id']}/replay",
        )
        assert code == 200 and replay["exact_replay"], replay
        target.execute("confirm-result", "fork-cup:confirm", edition_id="fork-cup")
        target.save()
        target.advance("fork-publish")
        ranked = target.view()
        assert sorted(r["points"] for r in ranked["state"]["rankings"][-1]["rows"]) == [
            30,
            30,
            60,
            100,
        ]
        assert original.view()["state"]["week"]["week"] == 4
        target.advance("fork-week7")
        target.advance("fork-season1")
        assert target.view()["state"]["week"]["season_index"] == 1
        final = target.view()
        original_final = original.view()
        code, report = _request("GET", target.url + "/records")
        assert code == 200, report
        # A fork of a fork binds the actual saved target and unchanged original past.
        nested = fork(
            server,
            final["saved_head_revision_id"],
            branch=target_id,
            name="nested-native",
        )
        assert Tour(server, nested["branch_id"]).view()["players"] == final["players"]
        raw_before = repo.get_branch_saved_revision(
            revision_id=final["saved_head_revision_id"]
        )
        # Fully rehashed altered current facts still fail actual source + command replay.
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, raw_before.revision_id)
            payload = deepcopy(raw_before.payload)
            from beta_engine.application.native_fork_runtime_reducer import cohere
            from beta_engine.infrastructure.db.native_fork_runtime_state import (
                component,
                load_runtime,
            )

            runtime = load_runtime(payload)
            altered = cohere(
                runtime,
                players=(
                    runtime.players[0].model_copy(
                        update={"current_form": runtime.players[0].current_form + 1}
                    ),
                    *runtime.players[1:],
                ),
            )
            payload["content"]["native_fork_runtime"] = component(altered)
            row.payload_json = canonical_json(payload)
            from dataclasses import replace

            row.content_hash = _saved_revision_record_content_hash(
                replace(raw_before, payload=payload)
            )
        code, _ = _request("GET", target.url)
        assert code == 409
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, raw_before.revision_id)
            row.payload_json, row.content_hash = (
                canonical_json(raw_before.payload),
                raw_before.content_hash,
            )
        assert target.view() == final
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, source["revision_id"])
            old_summary = row.change_summary_json
            row.change_summary_json = canonical_json({"corrupt_actual_source": True})
        assert _request("GET", target.url)[0] == 409
        with repo._session_factory.begin() as session:
            session.get(
                BranchSavedRevisionModel, source["revision_id"]
            ).change_summary_json = old_summary
        assert target.view() == final
    with ApiServer(database_url=db) as server:
        assert Tour(server, target_id).view() == final
        assert Tour(server, "branch").view() == original_final
        # Viewer changes are an independent reviewed draft and become public only
        # with its explicit Save; the Viewer reads signed facts, including history.
        target = Tour(server, target_id)
        draft_url = (
            server.base_url + f"/run-containers/run/branches/{target_id}/working-draft"
        )
        code, draft = _request("GET", draft_url)
        assert code == 200, draft
        code, staged = _request(
            "PUT",
            draft_url + "/viewer-branch",
            {
                "viewer_branch_id": target_id,
                "expected_draft_version": draft["draft_version"],
            },
        )
        assert code == 200, staged
        assert (
            _request("GET", server.base_url + "/run-containers/run")[1][
                "viewer_branch_id"
            ]
            == "branch"
        )
        code, saved_viewer = _request(
            "POST",
            draft_url + "/save",
            {"expected_draft_version": staged["draft_version"]},
        )
        assert code == 201, saved_viewer
        code, publication = _request(
            "GET", server.base_url + "/viewer/runs/run/calendar-tour"
        )
        assert code == 200 and publication["branch_id"] == target_id, publication
        assert sorted(r["points"] for r in publication["official_ranking"]["rows"]) == [
            30,
            30,
            60,
            100,
        ]
        # A strict Run-wide horizon extension retains all original runtime bytes;
        # the next explicit transition consumes its actual extended Saved envelope.
        from tests.api.test_run_calendar_extension_commit_api import _review, _save

        code, review = _review(server, "run", 4)
        assert code == 200 and review["can_save"], review
        code, extended = _save(server, "run", review, "native-all-branch-extension")
        assert code == 201, extended
        assert target.view()["run_calendar"]["season_count"] == 4
        target.advance("fork-after-extension")
        extended_view = target.view()
        assert extended_view["state"]["week"]["calendar"]["season_count"] == 4
        assert extended_view["state"]["week"]["week"] == 2

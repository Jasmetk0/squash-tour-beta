"""Production HTTP + SQLite review/confirmation/retry, without mocked services."""

import json

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request

pytestmark = pytest.mark.pr_critical


def preview(server, run_id, branch_id, revision_id, **extra):
    source = dict(
        source_branch_id=branch_id, source_saved_revision_id=revision_id, **extra
    )
    code, result = _request(
        "POST", f"{server.base_url}/run-containers/{run_id}/branches/preview", source
    )
    assert code == 200, result
    return source, result


def confirmed(source, review, command_id="reviewed-create"):
    return {
        **source,
        "review": {
            "command_id": command_id,
            "expected_preview_fingerprint": review["preview_fingerprint"],
            "explicit_confirmation": True,
        },
    }


def test_reviewed_create_is_atomic_stale_safe_and_durable(tmp_path):
    path = tmp_path / "review.db"
    database = f"sqlite:///{path}"
    with ApiServer(database_url=database) as server:
        run, branch, revision = _create_run(server, display_name="Reviewed branches")
        url = f"{server.base_url}/run-containers/{run}/branches"
        before = _dump(path)
        source, review = preview(server, run, branch, revision)
        assert review["can_create"] and review["target_display_name"] == "Timeline 2"
        assert _dump(path) == before
        request = confirmed(source, review)
        # Bypassing the confirmation checkbox cannot execute the reviewed path.
        unconfirmed = {
            **request,
            "review": {**request["review"], "explicit_confirmation": False},
        }
        assert _request("POST", url, unconfirmed)[0] == 422
        assert _dump(path) == before
        # Late receipt failure must roll back Branch, draft and retry record together.
        repo = server.app.state.runtime.repository

        def reject_receipt(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith("INSERT INTO saved_revision_branch_commands"):
                raise IntegrityError(
                    statement, parameters, RuntimeError("controlled receipt failure")
                )

        event.listen(repo._engine, "before_cursor_execute", reject_receipt)
        try:
            assert _request("POST", url, request)[0] == 409
        finally:
            event.remove(repo._engine, "before_cursor_execute", reject_receipt)
        assert _dump(path) == before
        status, created = _request("POST", url, request)
        assert status == 201, created
        after = _dump(path)
        assert _request("POST", url, request) == (201, created)
        assert _dump(path) == after
        # Reuse with different input is not a new Branch command.
        assert (
            _request("POST", url, {**request, "display_name": "Conflicting retry"})[0]
            == 409
        )
        assert _dump(path) == after
        # A sibling creation invalidates a still-open naming/inventory review.
        assert (
            _request("POST", url, confirmed(source, review, "stale-command"))[0] == 409
        )
        assert _dump(path) == after
        assert created["saved_head_revision_id"] == revision
        assert not created["is_viewer_branch"]
        branch_id = created["branch_id"]
        draft_url = f"{url}/{branch_id}/working-draft"
        status, draft = _request("GET", draft_url)
        assert status == 200 and draft["status"] == "clean", draft
        status, staged = _request(
            "PUT",
            draft_url + "/viewer-branch",
            {
                "viewer_branch_id": branch_id,
                "expected_draft_version": draft["draft_version"],
            },
        )
        assert status == 200, staged
        status, saved = _request(
            "POST",
            draft_url + "/save",
            {
                "expected_draft_version": staged["draft_version"],
            },
        )
        assert status == 201, saved
        # Exact retry must still return the original receipt after later Branch Save.
        assert _request("POST", url, request) == (201, created)
    with ApiServer(database_url=database) as restarted:
        url = f"{restarted.base_url}/run-containers/{run}/branches"
        before = _dump(path)
        assert _request("POST", url, request) == (201, created)
        assert _dump(path) == before
        original = _request("GET", f"{restarted.base_url}/run-branches/{branch}")[1]
        assert original["saved_head_revision_id"] == revision
        reopened = _request("GET", f"{restarted.base_url}/run-branches/{branch_id}")[1]
        assert (
            reopened["saved_head_revision_id"] == saved["saved_revision"]["revision_id"]
        )


def test_review_rejects_foreign_unreachable_and_corrupt_saved_sources(tmp_path):
    path = tmp_path / "invalid.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run, branch, revision = _create_run(server, display_name="First")
        _other_run, other_branch, other_revision = _create_run(
            server, display_name="Second"
        )
        url = f"{server.base_url}/run-containers/{run}/branches/preview"
        before = _dump(path)
        for bad_branch, bad_revision in (
            (other_branch, revision),
            (branch, other_revision),
            (branch, "missing"),
        ):
            assert _request(
                "POST",
                url,
                {
                    "source_branch_id": bad_branch,
                    "source_saved_revision_id": bad_revision,
                },
            )[0] in (404, 409)
        assert _dump(path) == before
        create_url = url.removesuffix("/preview")
        code, fork = _request(
            "POST",
            create_url,
            {
                "source_branch_id": branch,
                "source_saved_revision_id": revision,
            },
        )
        assert code == 201, fork
        draft_url = f"{create_url}/{fork['branch_id']}/working-draft"
        code, staged = _request(
            "PUT",
            draft_url + "/viewer-branch",
            {
                "viewer_branch_id": fork["branch_id"],
                "expected_draft_version": 0,
            },
        )
        assert code == 200, staged
        code, sibling_save = _request(
            "POST",
            draft_url + "/save",
            {
                "expected_draft_version": staged["draft_version"],
            },
        )
        assert code == 201, sibling_save
        before = _dump(path)
        assert (
            _request(
                "POST",
                url,
                {
                    "source_branch_id": branch,
                    "source_saved_revision_id": sibling_save["saved_revision"][
                        "revision_id"
                    ],
                },
            )[0]
            == 409
        )
        assert _dump(path) == before
        from beta_engine.infrastructure.db.models import BranchSavedRevisionModel

        repo = server.app.state.runtime.repository
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, revision)
            raw = json.loads(row.payload_json)
            raw["run"]["display_name"] = "Damaged immutable payload"
            row.payload_json = json.dumps(raw)
        damaged = _dump(path)
        assert (
            _request(
                "POST",
                url,
                {"source_branch_id": branch, "source_saved_revision_id": revision},
            )[0]
            == 409
        )
        assert _dump(path) == damaged


def test_concurrent_exact_confirmations_create_only_one_branch(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "concurrent.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run, branch, revision = _create_run(server, display_name="Concurrent")
        source, review = preview(server, run, branch, revision)
        body = confirmed(source, review)
        url = f"{server.base_url}/run-containers/{run}/branches"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: _request("POST", url, body), range(2)))
        assert results[0][0] == 201 and results[0] == results[1], results
        rows = _request("GET", f"{server.base_url}/run-branches?run_id={run}")[1][
            "run_branches"
        ]
        assert len(rows) == 2


@pytest.mark.parametrize(
    "change", ["head", "viewer", "hash", "name", "metadata", "read_only"]
)
def test_server_rejects_changed_review_even_when_client_forces_confirmation(
    tmp_path, change
):
    from beta_engine.infrastructure.db.models import RunContainerModel

    path = tmp_path / f"{change}.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run, branch, revision = _create_run(server, display_name="Stale")
        url = f"{server.base_url}/run-containers/{run}/branches"
        assert (
            _request(
                "POST",
                url,
                {"source_branch_id": branch, "source_saved_revision_id": revision},
            )[0]
            == 201
        )
        rows = _request("GET", f"{server.base_url}/run-branches?run_id={run}")[1][
            "run_branches"
        ]
        other = next(b["branch_id"] for b in rows if b["branch_id"] != branch)
        source, review = preview(
            server, run, branch, revision, display_name="Reviewed name"
        )
        body = confirmed(source, review)
        if change in ("head", "viewer"):
            # Isolate Viewer change from source-head change. A sibling Save can
            # switch Viewer without moving the reviewed source's head.
            draft_url = f"{url}/{other if change == 'viewer' else branch}/working-draft"
            code, staged = _request(
                "PUT",
                draft_url + "/viewer-branch",
                {
                    "viewer_branch_id": other,
                    "expected_draft_version": 0,
                },
            )
            assert code == 200, staged
            code, saved = _request(
                "POST",
                draft_url + "/save",
                {"expected_draft_version": staged["draft_version"]},
            )
            assert code == 201, saved
            if change == "head":
                # Restore the reviewed Viewer selection while leaving a newer
                # source head, so this case tests head staleness independently.
                code, staged = _request(
                    "PUT",
                    draft_url + "/viewer-branch",
                    {
                        "viewer_branch_id": branch,
                        "expected_draft_version": saved["working_draft"][
                            "draft_version"
                        ],
                    },
                )
                assert code == 200, staged
                code, saved = _request(
                    "POST",
                    draft_url + "/save",
                    {
                        "expected_draft_version": staged["draft_version"],
                    },
                )
                assert code == 201, saved
        elif change == "hash":
            body["review"]["expected_preview_fingerprint"] = "f" * 64
        elif change == "name":
            body["display_name"] = "Changed after review"
        else:
            with (
                server.app.state.runtime.repository._session_factory.begin() as session
            ):
                row = session.get(RunContainerModel, run)
                if change == "metadata":
                    row.metadata_json = json.dumps(
                        {**json.loads(row.metadata_json), "review_note": "changed"}
                    )
                else:
                    row.read_only = 1
        before = _dump(path)
        assert _request("POST", url, body)[0] == 409
        assert _dump(path) == before

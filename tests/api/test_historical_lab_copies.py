"""Actual historical native source, all Lab APIs, replay, isolation and restart."""

import json
import os
import sqlite3

import pytest

from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.support.historical_lab import cached_history, non_lab_rows

pytestmark = pytest.mark.smoke


@pytest.fixture(scope="module")
def source_fixture(tmp_path_factory):
    return cached_history(
        os.environ.get("SQUASH_LAB_FIXTURE_ROOT")
        or tmp_path_factory.mktemp("historical-source")
    )


def _copy_db(source, target):
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)


def test_historical_lab_native_copies_replay_isolation_and_restart(
    tmp_path, source_fixture
):
    source, meta = source_fixture
    path = tmp_path / "lab.sqlite"
    _copy_db(source, path)
    db = f"sqlite:///{path}"
    request = {
        "product_run_id": meta["run"],
        "branch_id": meta["branch"],
        "saved_revision_id": meta["born"],
        "player_id": meta["player"],
        "duration_weeks": 2,
    }
    with ApiServer(database_url=db) as server:
        base = server.base_url + "/admin/labs/"
        before = non_lab_rows(path)
        code, scenario = _request(
            "POST", base + "player/import-saved-revision-player", request
        )
        assert code == 200, scenario
        snap = scenario["source_snapshot"]
        assert snap["owner_branch_id"] == meta["branch"] and snap["week"]["week"] == 3
        assert (
            snap["biography"]["age"] == 15 and len(snap["player"]["attributes"]) == 57
        )
        assert snap["biography"]["hidden_career_traits"] is None
        assert scenario["start_week"]["calendar"]["weeks_per_year"] == 52
        code, latest = _request(
            "POST",
            base + "player/import-saved-revision-player",
            {**request, "saved_revision_id": meta["latest"]},
        )
        assert code == 200, latest
        assert latest["player"] != scenario["player"]
        # Born presence is sporting/lifecycle membership, never future prospect visibility.
        for change in (
            {"saved_revision_id": meta["prebirth"]},
            {"product_run_id": "foreign"},
            {"branch_id": "foreign"},
            {"saved_revision_id": "foreign"},
            {"branch_id": "branch"},
        ):
            code, error = _request(
                "POST",
                base + "player/import-saved-revision-player",
                {**request, **change},
            )
            assert code in (404, 409), error
        # The fork can reach a shared original ancestor, retaining its real owner.
        code, shared = _request(
            "POST",
            base + "player/import-saved-revision-player",
            {
                **request,
                "saved_revision_id": meta["prebirth"],
                "player_id": meta["opponent"],
            },
        )
        assert code == 200, shared
        assert shared["source_snapshot"]["owner_branch_id"] == "branch"
        code, saved = _request(
            "POST",
            base + "player/sessions",
            {"display_name": "Historical experiment", "scenario": scenario},
        )
        assert code == 201, saved
        run_request = {"expected_session_fingerprint": saved["session_fingerprint"]}
        code, result = _request(
            "POST", base + f"player/sessions/{saved['session_id']}/run", run_request
        )
        assert code == 200, result
        assert _request(
            "POST", base + f"player/sessions/{saved['session_id']}/run", run_request
        ) == (200, result)
        assert (
            _request(
                "PUT",
                base + f"player/sessions/{saved['session_id']}",
                {
                    "display_name": "stale",
                    "scenario": scenario,
                    "expected_session_fingerprint": "0" * 64,
                },
            )[0]
            == 409
        )
        assert (
            _request(
                "POST",
                base + f"player/sessions/{saved['session_id']}/run",
                {"expected_session_fingerprint": "0" * 64},
            )[0]
            == 409
        )
        code, match = _request(
            "POST",
            base + "match/sessions",
            {
                "display_name": "Historical match",
                "built_in_scenario_id": "standard-even-match",
            },
        )
        assert code == 201, match
        for side, player in (
            ("player_a", meta["player"]),
            ("player_b", meta["opponent"]),
        ):
            code, match = _request(
                "POST",
                base
                + f"match/sessions/{match['session_id']}/import-saved-revision-player",
                {k: v for k, v in request.items() if k != "duration_weeks"}
                | {
                    "player_id": player,
                    "side": side,
                    "expected_session_fingerprint": match["session_fingerprint"],
                },
            )
            assert code == 200, match
        assert len(match["participant_imports"]) == 2
        assert (
            _request(
                "POST",
                base + f"match/sessions/{match['session_id']}/run",
                {"expected_session_fingerprint": match["session_fingerprint"]},
            )[0]
            == 200
        )
        code, tournament = _request(
            "POST",
            base + "tournament/sessions/copy-saved-revision",
            {
                "display_name": "Historical edition",
                "product_run_id": meta["run"],
                "branch_id": meta["branch"],
                "saved_revision_id": meta["drawn"],
                "event_id": meta["event"],
            },
        )
        assert code == 201, tournament
        assert len(tournament["scenario"]["source_snapshot"]["historical_players"]) == 4
        assert (
            _request(
                "POST",
                base + f"tournament/sessions/{tournament['session_id']}/run",
                {"expected_session_fingerprint": tournament["session_fingerprint"]},
            )[0]
            == 200
        )
        assert non_lab_rows(path) == before
    with ApiServer(database_url=db) as server:
        base = server.base_url + "/admin/labs/"
        assert saved in _request("GET", base + "player/sessions")[1]
        assert _request(
            "POST", base + f"player/sessions/{saved['session_id']}/run", run_request
        ) == (200, result)
        assert non_lab_rows(path) == before
        # Warm proof caches must still detect missing/changed physical source dependencies.
        assert (
            _request("POST", base + "player/import-saved-revision-player", request)[0]
            == 200
        )
        with sqlite3.connect(path) as connection:
            raw = connection.execute(
                "SELECT payload_json FROM branch_saved_revisions WHERE revision_id=?",
                (meta["prebirth"],),
            ).fetchone()[0]
            changed = json.loads(raw)
            changed["content"]["initial_world"]["fingerprint"] = "0" * 64
            connection.execute(
                "UPDATE branch_saved_revisions SET payload_json=? WHERE revision_id=?",
                (json.dumps(changed), meta["prebirth"]),
            )
        assert (
            _request("POST", base + "player/import-saved-revision-player", request)[0]
            == 409
        )
        # Already copied Session remains independent even when the source is damaged.
        assert _request(
            "POST", base + f"player/sessions/{saved['session_id']}/run", run_request
        ) == (200, result)


def test_historical_import_rejects_rehashed_provenance_and_missing_dependency(
    tmp_path, source_fixture
):
    from copy import deepcopy
    from dataclasses import replace

    from beta_engine.infrastructure.db.repositories import (
        _saved_revision_record_content_hash,
    )

    source, meta = source_fixture
    path = tmp_path / "dependency.sqlite"
    _copy_db(source, path)
    request = {
        "product_run_id": meta["run"],
        "branch_id": meta["branch"],
        "saved_revision_id": meta["born"],
        "player_id": meta["player"],
        "duration_weeks": 1,
    }
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        url = server.base_url + "/admin/labs/player/import-saved-revision-player"
        assert _request("POST", url, request)[0] == 200

        repo = server.app.state.runtime.repository
        original = repo.get_branch_saved_revision(revision_id=meta["prebirth"])
        changed = deepcopy(original.payload)
        del changed["content"]["run_prospect_source"]
        digest = _saved_revision_record_content_hash(replace(original, payload=changed))
        with sqlite3.connect(path) as connection:
            raw = connection.execute(
                "SELECT * FROM branch_saved_revisions WHERE revision_id=?",
                (meta["prebirth"],),
            ).fetchone()
            connection.execute(
                "UPDATE branch_saved_revisions SET payload_json=?, content_hash=? WHERE revision_id=?",
                (json.dumps(changed), digest, meta["prebirth"]),
            )
        assert _request("POST", url, request)[0] == 409
        with sqlite3.connect(path) as connection:
            connection.execute(
                "DELETE FROM branch_saved_revisions WHERE revision_id=?",
                (meta["prebirth"],),
            )
        assert _request("POST", url, request)[0] == 409
        with sqlite3.connect(path) as connection:
            connection.execute(
                "INSERT INTO branch_saved_revisions VALUES ("
                + ",".join("?" for _ in raw)
                + ")",
                raw,
            )
        assert _request("POST", url, request)[0] == 200


def test_nested_native_copy_retains_inherited_edition_authority(
    tmp_path, source_fixture
):
    from tests.api.test_native_fork_public_continuation import fork

    source, meta = source_fixture
    path = tmp_path / "nested.sqlite"
    _copy_db(source, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        created = fork(
            server, meta["latest"], name="Nested historical Lab", branch=meta["branch"]
        )
        before = non_lab_rows(path)
        code, copied = _request(
            "POST",
            server.base_url + "/admin/labs/tournament/sessions/copy-saved-revision",
            {
                "display_name": "Inherited Edition",
                "product_run_id": meta["run"],
                "branch_id": created["branch_id"],
                "saved_revision_id": created["saved_head_revision_id"],
                "event_id": meta["event"],
            },
        )
        assert code == 201, copied
        players = copied["scenario"]["source_snapshot"]["historical_players"]
        assert any(p["player"]["player_id"] == meta["player"] for p in players)
        assert all(p["owner_branch_id"] == created["branch_id"] for p in players)
        assert non_lab_rows(path) == before

"""Real HTTP/SQLite portable archives; target never opens source SQLite files."""

from __future__ import annotations

import json
from pathlib import Path
from urllib import error, parse, request

import pytest

from beta_engine.domain.run_branch_archive import Archive
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.application.test_standalone_match_acceptance import _player
from tests.support.run_branch_archive_http import ColdApiServer

pytestmark = pytest.mark.pr_critical


def raw_request(url, raw=None):
    req = request.Request(url, data=raw, method="POST")
    req.add_header("Content-Type", "application/vnd.squash.saved-branch+json")
    try:
        with request.urlopen(req, timeout=120) as response:
            return response.status, response.read()
    except error.HTTPError as exc:
        return exc.code, exc.read()


def archive_root(server):
    return server.base_url + "/admin/run-archives"


def upload_preview(server, raw):
    code, body = raw_request(archive_root(server) + "/import/preview", raw)
    result = json.loads(body)
    assert code == 200, result
    return result


def confirm(server, raw, preview, *, command_id="cold-restore", explicit=True):
    query = parse.urlencode(
        {
            "command_id": command_id,
            "expected_preview_fingerprint": preview["preview_fingerprint"],
            "explicit_confirmation": str(explicit).lower(),
            "operator_label": "Archive acceptance",
            "audit_reason": "Reviewed cold restore",
        }
    )
    code, body = raw_request(archive_root(server) + "/import/confirm?" + query, raw)
    return code, json.loads(body)


def export(server, run_id, branch_id):
    selection = {"run_id": run_id, "branch_id": branch_id}
    code, preview = _request(
        "POST", archive_root(server) + "/export/preview", selection
    )
    assert code == 200, preview
    command = {
        **selection,
        "expected_head_revision_id": preview["selected_head_revision_id"],
        "expected_archive_digest": preview["archive_digest"],
    }
    code, raw = raw_request(
        archive_root(server) + "/export", json.dumps(command).encode()
    )
    assert code == 200, raw.decode()[:3000]
    assert Archive(raw).raw_digest == preview["archive_digest"]
    return raw, preview


def manual_match(server):
    code, run = _request(
        "POST",
        server.base_url + "/run-containers",
        {"display_name": "Portable two manual players"},
    )
    assert code == 201, run
    rid, bid = run["run_id"], run["viewer_branch_id"]
    root = (
        server.base_url + f"/admin/runs/{rid}/branches/{bid}/authoritative-simulation"
    )
    one = _request(
        "POST",
        root + "/standalone-match/players",
        {"player": _player("P-A", "Player A", technique=82).model_dump(mode="json")},
    )
    assert one[0] == 200, one
    code, two = _request(
        "POST",
        root + "/standalone-match/players",
        {
            "player": _player("P-B", "Player B", technique=78).model_dump(mode="json"),
            "expected_workspace_fingerprint": one[1]["workspace"].get("fingerprint"),
        },
    )
    # The workspace fingerprint is a computed property exposed by the service
    # serializer only when requested; the supported add command permits None.
    assert code == 200, two
    from beta_engine.application.standalone_match_service import (
        StandaloneMatchWorkspace,
    )

    workspace = StandaloneMatchWorkspace.model_validate_json(
        json.dumps(two["workspace"])
    )
    code, played = _request(
        "POST",
        root + "/standalone-match/simulate",
        {
            "command_id": "play-manual",
            "expected_workspace_fingerprint": workspace.fingerprint,
            "seed": 777,
            "operator_label": "Admin",
            "audit_reason": "Real manual pair portability",
        },
    )
    assert code == 200, played
    code, preview = _request("GET", root + "/save/preview")
    assert code == 200 and preview["can_save"], preview
    code, saved = _request(
        "POST",
        root + "/save",
        {
            "expected_draft_version": preview["draft_version"],
            "expected_simulation_fingerprint": preview["simulation_fingerprint"],
        },
    )
    assert code == 201, saved
    replay = _request("GET", root + "/match-replay?group_id=standalone-match-group-1")
    assert replay[0] == 200, replay
    played["stored_replay"] = replay[1]
    return rid, bid, played, saved


def test_real_manual_pair_cold_roundtrip_restart_exact_retry_and_replay(
    tmp_path, monkeypatch
):
    source, target = tmp_path / "A.db", tmp_path / "B.db"
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        rid, bid, played, saved = manual_match(server)
        before = _dump(source)
        raw, exported = export(server, rid, bid)
        assert _dump(source) == before
        assert len(exported["history"]) == 2
    server.app.state.runtime.repository._engine.dispose()
    # Close ALL source handles and physically remove the source installation.
    source.unlink()
    for suffix in ("-wal", "-shm"):
        Path(str(source) + suffix).unlink(missing_ok=True)
    assert not source.exists()
    empty_installation = tmp_path / "B-installation"
    empty_installation.mkdir()
    monkeypatch.chdir(empty_installation)
    assert not Path("config").exists()
    with ColdApiServer(
        database_url=f"sqlite:///{target}", directory=empty_installation
    ) as server:
        _request(
            "POST",
            server.base_url + "/run-containers",
            {"display_name": "Unrelated target Run"},
        )
        before = _dump(target)
        preview = upload_preview(server, raw)
        assert preview["can_restore"], preview
        assert _dump(target) == before
        assert confirm(server, raw, preview, explicit=False)[0] == 409
        assert _dump(target) == before
        code, receipt = confirm(server, raw, preview)
        assert code == 201, receipt
        assert set(before) <= set(_dump(target))
        assert confirm(server, raw, preview) == (201, receipt)
        assert (
            receipt["saved_head_revision_id"] == saved["saved_revision"]["revision_id"]
        )
        assert (
            len(
                _request("GET", server.base_url + "/run-containers")[1][
                    "run_containers"
                ]
            )
            == 2
        )
    with ColdApiServer(
        database_url=f"sqlite:///{target}", directory=empty_installation
    ) as server:
        assert confirm(server, raw, preview) == (201, receipt)
        root = (
            server.base_url
            + f"/admin/runs/{rid}/branches/{bid}/authoritative-simulation"
        )
        code, state = _request("GET", root + "/standalone-match")
        assert code == 200 and state["result"] == played["result"], state
        code, replay = _request(
            "GET", root + "/match-replay?group_id=standalone-match-group-1"
        )
        assert code == 200, replay
        assert replay == played["stored_replay"]
        assert len(replay["final_result"]["rally_log"]["events"]) > 20
        assert replay["replay_source"] == "stored_authoritative_events"
        context = _request(
            "GET", server.base_url + f"/viewer/runs/{rid}/official-context"
        )
        assert (
            context[0] == 200
            and context[1]["saved_head_revision_id"]
            == receipt["saved_head_revision_id"]
        ), context
        history = _request(
            "GET",
            server.base_url + f"/run-containers/{rid}/branches/{bid}/saved-revisions",
        )
        assert history[0] == 200 and len(history[1]["saved_revisions"]) == 2, history
        detail = _request(
            "GET",
            server.base_url
            + f"/run-containers/{rid}/branches/{bid}/saved-revisions/{receipt['saved_head_revision_id']}",
        )
        assert (
            detail[0] == 200
            and detail[1]["payload"] == saved["saved_revision"]["payload"]
        ), detail
        before = _dump(target)
        conflict = upload_preview(server, raw)
        assert not conflict["can_restore"]
        assert confirm(server, raw, conflict, command_id="second-import")[0] == 409
        assert _dump(target) == before

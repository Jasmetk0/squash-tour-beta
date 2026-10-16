"""Real HTTP/SQLite calendar Health edits and immutable Save recovery."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest
from sqlalchemy import select

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.models import BranchWorkingDraftModel
from tests.api.test_admin_player_health_api import _request
from tests.api.test_calendar_initial_health import (
    health_root,
    setup,
)
from tests.api.test_calendar_initial_health import (
    preview as initial_preview,
)
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer

pytestmark = pytest.mark.pr_critical


def baseline(server, clock):
    repo, _, request = setup(server, clock)
    code, installed = _request(
        "POST",
        health_root(server) + "/calendar-initial",
        initial_preview(server, request),
    )
    assert code == 201, installed
    saved = save(server)
    player = installed["state"]["players"][0]["player_id"]
    url = server.base_url + f"/admin/runs/run/branches/branch/players/{player}/health"
    code, view = _request("GET", url)
    assert code == 200, view
    return repo, url, view, saved


def save(server, branch="branch"):
    code, proof = _request("GET", health_root(server, branch) + "/save/preview")
    assert code == 200 and proof["can_save"], proof
    code, result = _request(
        "POST",
        health_root(server, branch) + "/save",
        {
            "expected_draft_version": proof["draft_version"],
            "expected_player_health_fingerprint": proof["health_component_fingerprint"],
        },
    )
    assert code == 201, result
    return result


def record(**changes):
    return dict(
        record_id="old-ankle",
        kind="Injury",
        condition_key="ankle",
        lifecycle="Active",
        severity=25,
        affected_domains=["movement"],
        onset_week=None,
        recovered_week=None,
        started_before_run=True,
        recurrence_of_record_id=None,
        recovery_window_min_weeks=2,
        recovery_window_max_weeks=6,
        provenance="Explicit known pre-Run medical history",
        **changes,
    )


def edit_request(view):
    return dict(
        schema_version="admin_health_edit_request.v2",
        command_id="health-edit",
        player_id=view["player"]["player_id"],
        mode="pre_start_input",
        expected_draft_version=view["draft_version"],
        expected_saved_head=view["saved_head_revision_id"],
        expected_state_fingerprint=view["state_fingerprint"],
        records=[record()],
        permanent_consequences=[],
        audit_label="Admin",
        audit_reason="Reviewed known health facts",
    )


def review(url, payload):
    code, result = _request("POST", url + "/preview", payload)
    assert code == 200, result
    return result


def commit(url, payload, reviewed):
    return _request(
        "POST",
        url,
        payload,
        headers={
            "X-Player-Health-Preview-Fingerprint": reviewed["preview_fingerprint"],
        },
    )


@pytest.mark.parametrize(
    "clock",
    [
        RunCalendar(52, 35, 2030, 3),
        RunCalendar(80, 80, 2100, 300),
        RunCalendar(1, 1, 0, 1),
    ],
)
def test_edit_review_save_restart_fork_restore_exact(tmp_path, clock):
    from beta_engine.application.run_saved_revision_restore_service import (
        RunSavedRevisionRestoreService,
    )
    from tests.application.test_run_package_review_acceptance import _ids

    path = tmp_path / "edit.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, url, view, baseline_save = baseline(server, clock)
        old_revision = baseline_save["saved_revision"]
        old_payload = deepcopy(old_revision["payload"])
        payload = edit_request(view)
        # Both types, recovered history, recurrence and permanent limitation are independent facts.
        payload["records"][0].update(lifecycle="Recovered", severity=0)
        payload["records"] += [
            {
                **record(),
                "record_id": "recurrence",
                "recurrence_of_record_id": "old-ankle",
            },
            {
                **record(),
                "record_id": "illness",
                "kind": "Illness",
                "affected_domains": ["stamina"],
            },
        ]
        payload["permanent_consequences"] = [
            dict(
                consequence_id="limitation",
                source_record_id="old-ankle",
                affected_domains=["movement"],
                limitation_severity=3,
                provenance="Explicit lasting limitation",
            )
        ]
        before = _dump(path)
        reviewed = review(url, payload)
        assert _dump(path) == before
        code, result = commit(url, payload, reviewed)
        assert code == 200, result
        assert result["draft_version"] == view["draft_version"] + 1
        assert (
            repo.get_branch_revision_state(
                branch_id="branch"
            ).saved_revision.revision_id
            == old_revision["revision_id"]
        )
        after = _dump(path)
        code, retry = commit(url, payload, reviewed)
        assert code == 200 and retry["already_applied"]
        assert _dump(path) == after
        assert commit(url, {**payload, "audit_reason": "changed"}, reviewed)[0] == 409
        assert _dump(path) == after
        edited_save = save(server)
        edited_state = edited_save["saved_revision"]["payload"]["content"][
            "player_health_state"
        ]["states"][0]
        assert edited_state["schema_version"] == "player_health_calendar_state.v2"
        assert (
            edited_state["origin"]["baseline_fingerprint"] == view["state_fingerprint"]
        )
        assert edited_state["week"]["calendar"] == clock.to_metadata()
        assert (
            edited_state["players"][0]["records"][0]["recovery_window_max_weeks"] == 6
        )
        assert (
            repo.get_branch_saved_revision(
                revision_id=old_revision["revision_id"]
            ).payload
            == old_payload
        )
        assert repo.verify_branch_saved_revision_hash(
            revision_id=old_revision["revision_id"]
        )
        assert commit(url, payload, reviewed)[1]["already_applied"]
        code, fork = _request(
            "POST",
            server.base_url + "/run-containers/run/branches",
            {
                "source_branch_id": "branch",
                "source_saved_revision_id": edited_save["saved_revision"][
                    "revision_id"
                ],
            },
        )
        assert code == 201, fork
        fork_url = url.replace(
            "/branches/branch/", "/branches/" + fork["branch_id"] + "/"
        )
        code, copied = _request("GET", fork_url)
        assert code == 200 and copied["player"] == _request("GET", url)[1]["player"], (
            copied
        )
        fork_state = repo.get_branch_revision_state(
            branch_id=fork["branch_id"]
        ).saved_revision.payload["content"]["player_health_state"]["states"][0]
        assert (
            fork_state["origin"] == edited_state["origin"]
            and fork_state["admin_edits"] == edited_state["admin_edits"]
        )
        fork_request = edit_request(copied)
        fork_request["records"][0]["severity"] = 31
        fork_review = review(fork_url, fork_request)
        # Same command string is branch scoped; source-branch proofs never work here.
        assert commit(fork_url, payload, reviewed)[0] == 409
        assert commit(fork_url, fork_request, fork_review)[0] == 200
        save(server, fork["branch_id"])
        saved = edited_save
        for n, target in enumerate(
            [old_revision["revision_id"], edited_save["saved_revision"]["revision_id"]]
        ):
            saved = RunSavedRevisionRestoreService(
                repo,
                _ids(
                    f"health-checkpoint-{n}", f"health-restore-{n}", f"health-audit-{n}"
                ),
            ).restore_current_branch(
                run_id="run",
                branch_id="branch",
                target_saved_revision_id=target,
                expected_head_saved_revision_id=saved["saved_revision"]["revision_id"]
                if isinstance(saved, dict)
                else saved.saved_revision.revision_id,
                expected_draft_version=saved["working_draft"]["draft_version"]
                if isinstance(saved, dict)
                else saved.working_draft.draft_version,
                expected_current_viewer_branch_id="branch",
                explicit_confirmation=True,
            )
            state = saved.saved_revision.payload["content"]["player_health_state"][
                "states"
            ][0]
            assert state == (
                old_payload["content"]["player_health_state"]["states"][0]
                if n == 0
                else edited_state
            )
            assert repo.verify_branch_saved_revision_hash(
                revision_id=saved.saved_revision.revision_id
            )
            if n == 0:
                before = _dump(path)
                assert commit(url, payload, reviewed)[0] == 409
                assert _dump(path) == before
        final = _request("GET", url)[1]
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        restarted_url = server.base_url + url[url.index("/admin/") :]
        assert _request("GET", restarted_url) == (200, final)
        assert commit(restarted_url, payload, reviewed)[1]["already_applied"]


def test_reject_invalid_scope_time_and_stale_proofs_without_writes(tmp_path):
    path = tmp_path / "invalid.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, url, view, _ = baseline(server, RunCalendar(80, 80, 0, 3))
        payload = edit_request(view)
        reviewed = review(url, payload)
        before = _dump(path)
        clock = view["week"]["calendar"]
        bad_records = [
            {
                **record(),
                "started_before_run": False,
                "onset_week": {"calendar": clock, "season_index": 0, "week": 2},
            },
            {
                **record(),
                "started_before_run": False,
                "onset_week": {
                    "calendar": {
                        **clock,
                        "weeks_per_year": 52,
                        "season_start_year_week": 1,
                    },
                    "season_index": 0,
                    "week": 1,
                },
            },
            {
                **record(),
                "started_before_run": False,
                "onset_week": {"season_index": 0, "week": 1},
            },
            {
                **record(),
                "started_before_run": False,
                "onset_week": {"calendar": clock, "season_index": 3, "week": 1},
            },
            {**record(), "lifecycle": "Recovered", "severity": 25},
            {**record(), "recurrence_of_record_id": "unknown"},
            {**record(), "recovery_window_min_weeks": 9},
        ]
        for value in bad_records:
            assert _request(
                "POST",
                url + "/preview",
                {**payload, "records": [value], "mode": "current_state_correction"},
            )[0] in (409, 422)
            assert _dump(path) == before
        for changes in [
            dict(expected_saved_head="other"),
            dict(expected_state_fingerprint="0" * 64),
            dict(expected_draft_version=999),
            dict(player_id="absent"),
        ]:
            assert commit(url, {**payload, **changes}, reviewed)[0] == 409
            assert _dump(path) == before
        assert _request("GET", url.replace("/runs/run/", "/runs/foreign/"))[0] == 409
        legacy = {
            k: v
            for k, v in payload.items()
            if k not in {"expected_saved_head", "expected_state_fingerprint"}
        }
        legacy["schema_version"] = "admin_health_edit_request.v1"
        assert _request("POST", url + "/preview", legacy)[0] == 409
        assert _dump(path) == before
        with repo._session_factory.begin() as session:
            draft = session.scalar(
                select(BranchWorkingDraftModel).where(
                    BranchWorkingDraftModel.branch_id == "branch"
                )
            )
            draft.draft_version += 1
        changed = _dump(path)
        assert commit(url, payload, reviewed)[0] == 409
        assert _dump(path) == changed


def test_concurrent_commit_once_and_rollback_after_receipt_flush(tmp_path, monkeypatch):
    from sqlalchemy.orm import Session

    from beta_engine.infrastructure.db.models import PlayerHealthAdminEditReceiptModel

    path = tmp_path / "race.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _, url, view, _ = baseline(server, RunCalendar.earth_default())
        payload = edit_request(view)
        reviewed = review(url, payload)
        original = Session.flush

        def fail_receipt(session, *args, **kwargs):
            has_receipt = any(
                isinstance(x, PlayerHealthAdminEditReceiptModel) for x in session.new
            )
            result = original(session, *args, **kwargs)
            if has_receipt:
                raise ValueError(
                    "Injected failure after health, draft and receipt writes"
                )
            return result

        before = _dump(path)
        monkeypatch.setattr(Session, "flush", fail_receipt)
        assert commit(url, payload, reviewed)[0] == 409
        assert _dump(path) == before
        monkeypatch.setattr(Session, "flush", original)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: commit(url, payload, reviewed), range(2)))
        assert [x[0] for x in results] == [200, 200], results
        assert sorted(x[1]["already_applied"] for x in results) == [False, True]
        assert _request("GET", url)[1]["draft_version"] == view["draft_version"] + 1


def test_snapshot_integrity_old_writers_and_corrupt_receipt_fail_closed(tmp_path):
    import json

    from beta_engine.domain.players.health import bootstrap_health_state
    from beta_engine.domain.rankings.official import RankingWeek
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.models import PlayerHealthAdminEditReceiptModel
    from beta_engine.infrastructure.db.player_health_state import (
        get_health,
        load_saved_health,
        put_health,
        replace_health_head,
    )

    path = tmp_path / "integrity.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, url, view, _ = baseline(server, RunCalendar(80, 80, 0, 3))
        payload = edit_request(view)
        reviewed = review(url, payload)
        assert commit(url, payload, reviewed)[0] == 200
        saved = save(server)
        snapshot = saved["saved_revision"]["payload"]
        old_state = bootstrap_health_state(
            run_id="run",
            branch_id="branch",
            source_initial_world_fingerprint="old",
            player_ids=(view["player"]["player_id"],),
        )
        before = _dump(path)
        for writer in [
            lambda s: get_health(
                s,
                run_id="run",
                branch_id="branch",
                week=RankingWeek(season_index=0, week=1),
            ),
            lambda s: put_health(s, old_state),
            lambda s: replace_health_head(s, old_state, expected_fingerprint="a" * 64),
        ]:
            with pytest.raises(ValueError), repo._session_factory.begin() as session:
                writer(session)
            assert _dump(path) == before
        for mutate in [
            lambda st: st["week"]["calendar"].update(
                weeks_per_year=52, season_start_year_week=1
            ),
            lambda st: st.update(source_initial_world_fingerprint="f" * 64),
            lambda st: st["players"].pop(),
            lambda st: st["admin_edits"][0].update(source_run_id="foreign"),
            lambda st: st.update(schema_version="player_health_unknown.v99"),
        ]:
            damaged = deepcopy(snapshot)
            component = damaged["content"]["player_health_state"]
            mutate(component["states"][0])
            component["fingerprint"] = canonical_hash(component["states"])
            with pytest.raises(ValueError):
                load_saved_health(damaged, run_id="run", branch_id="branch")
            assert _dump(path) == before
        with repo._session_factory.begin() as session:
            receipt = session.get(
                PlayerHealthAdminEditReceiptModel,
                ("run", "branch", payload["command_id"]),
            )
            value = json.loads(receipt.payload_json)
            value["result"]["player_id"] = "foreign"
            receipt.payload_json = json.dumps(value)
        damaged = _dump(path)
        assert commit(url, payload, reviewed)[0] == 409
        assert _dump(path) == damaged


def test_competing_reviews_and_save_between_review_and_confirm(tmp_path):
    path = tmp_path / "competing.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        _, url, view, _ = baseline(server, RunCalendar.earth_default())
        first = edit_request(view)
        second = deepcopy(first)
        second["command_id"] = "other-edit"
        second["records"][0]["severity"] = 36
        reviews = [review(url, first), review(url, second)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(
                pool.map(lambda pair: commit(url, *pair), zip([first, second], reviews))
            )
        assert sorted(x[0] for x in outcomes) == [200, 409], outcomes
        current = _request("GET", url)[1]
        correction = edit_request(current)
        correction["command_id"] = "after-review"
        correction["records"][0]["severity"] = 49
        correction_review = review(url, correction)
        save(server)
        before = _dump(path)
        assert commit(url, correction, correction_review)[0] == 409
        assert _dump(path) == before

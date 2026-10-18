"""Real HTTP/SQLite configured Edition -> Entry -> matches -> Official week."""

import hashlib
import json
import sqlite3

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_continuation_flow import root, save_continuation
from tests.api.test_calendar_health_edit import save as health_save
from tests.api.test_calendar_initial_health import (
    health_root,
)
from tests.api.test_calendar_initial_health import (
    preview as health_preview,
)
from tests.api.test_calendar_population_sporting_checkpoint import (
    play,
    prepare,
    restore,
    save,
)
from tests.api.test_calendar_sporting_week_flow import advance, weekly_command
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def tour_url(server):
    return server.base_url + "/admin/runs/run/branches/branch/calendar-tour"


def inspect(server):
    code, view = _request("GET", tour_url(server))
    assert code == 200, view
    return view


def command(view, action, *, name=None, edition_id=None, data=None):
    return {
        "action": action,
        "command_id": name or action,
        "edition_id": edition_id,
        "expected_saved_head": view["saved_head_revision_id"],
        "expected_checkpoint_fingerprint": view["checkpoint_fingerprint"],
        "expected_tour_fingerprint": view["tour_fingerprint"],
        "seed": 231,
        "operator_label": "Admin",
        "audit_reason": "Reviewed actual configured native Tour operation",
        "data": data or {},
    }


def execute(server, cmd):
    code, preview = _request("POST", tour_url(server) + "/preview", cmd)
    assert code == 200, preview
    request = {
        "command": cmd,
        "expected_preview_fingerprint": preview["preview_fingerprint"],
        "explicit_confirmation": True,
    }
    code, result = _request("POST", tour_url(server) + "/execute", request)
    assert code == 201, result
    if cmd["action"] in {"play", "transition"}:
        assert _request("POST", tour_url(server) + "/execute", request) == (201, result)
    return result, request


def save_tour(server):
    view = inspect(server)
    assert not view["saved"]
    code, result = _request(
        "POST",
        tour_url(server) + "/save",
        {
            "expected_draft_version": view["draft_version"],
            "expected_calendar_tour_fingerprint": view["tour_fingerprint"],
        },
    )
    assert code == 201, result
    assert result["schema_version"] == "calendar_tour_save_receipt.v1"
    assert "payload" not in result["saved_revision"]
    assert len(json.dumps(result)) < 16000
    assert inspect(server)["saved"]
    return result["saved_revision"]


def setup(server, clock, count=8, *, initialize=True):
    repo, head = prepare(server, clock, count)
    rev = repo.get_branch_saved_revision(revision_id=head)
    health = {
        "command_id": "fresh-health",
        "expected_saved_head": head,
        "expected_draft_version": repo.get_viewer_branch_working_draft(
            run_id="run", branch_id="branch"
        ).draft_version,
        "expected_population_fingerprint": rev.payload["content"]["initial_world"][
            "fingerprint"
        ],
        "audit_label": "Admin",
        "audit_reason": "Explicit fresh health baseline",
    }
    code, response = _request(
        "POST",
        health_root(server) + "/calendar-initial",
        health_preview(server, health),
    )
    assert code == 201, response
    saved_health = health_save(server)
    opening, _ = play(server, saved_health["saved_revision"]["revision_id"])
    save(server, opening)
    view = _request("GET", root(server))[1]
    prepared, _ = advance(server, weekly_command(view))
    sporting_saved = save_continuation(server, prepared)
    if not initialize:
        return repo, sporting_saved
    execute(server, command(inspect(server), "initialize"))
    initial = save_tour(server)
    return repo, initial


def create_edition(server, name, size=8, offset=2, factor=1):
    view = inspect(server)
    week = view["state"]["week"]
    data = {
        "edition_id": name,
        "name": "Configured Tour " + name,
        "week": {**week, "week": week["week"] + offset},
        "announcement_week": {**week, "week": week["week"] + 1},
        "start_slot": 1,
        "main_entrant_count": size,
        "ranked": True,
        "validity_weeks": week["calendar"]["weeks_per_year"],
        "point_table": dict(
            champion=100 * factor,
            finalist=60 * factor,
            semifinal=30 * factor,
            **({"quarterfinal": 15 * factor} if size == 8 else {}),
        ),
    }
    execute(server, command(view, "create-edition", name=name + ":create", data=data))
    save_tour(server)


def edition(server, name, size=8):
    view = inspect(server)
    execute(
        server,
        command(
            view,
            "submit",
            name=name + ":applications",
            edition_id=name,
            data={"player_ids": [p["player_id"] for p in view["players"][:size]]},
        ),
    )
    save_tour(server)
    for action in ("approve", "draw", "play", "confirm-result"):
        execute(
            server,
            command(inspect(server), action, name=name + ":" + action, edition_id=name),
        )
        save_tour(server)


@pytest.mark.parametrize("width", [52])
def test_configured_tour_two_weeks_real_matches_rankings_and_restart(
    tmp_path, width, monkeypatch
):
    db = f"sqlite:///{tmp_path / 'tour.db'}"
    with ApiServer(database_url=db) as server:
        _repo, initial = setup(server, RunCalendar(width, 35, 2030, 3))
        view = inspect(server)
        future = {**view["state"]["week"], "week": 5}
        stale = command(
            view,
            "policy",
            name="stale-review",
            data={
                "effective_week": future,
                "ranking": {"policy_id": "obsolete-review", "best_n": 2},
            },
        )
        status, stale_review = _request("POST", tour_url(server) + "/preview", stale)
        assert status == 200, stale_review
        execute(
            server,
            command(
                view,
                "policy",
                name="effective-week5",
                data={
                    "effective_week": future,
                    "ranking": {"policy_id": "Best1fromW5", "best_n": 1},
                    "development": {
                        "annual_change_basis_points": 0,
                        "annual_form_influence_basis_points": 0,
                    },
                },
            ),
        )
        save_tour(server)
        assert (
            _request(
                "POST",
                tour_url(server) + "/execute",
                {
                    "command": stale,
                    "expected_preview_fingerprint": stale_review["preview_fingerprint"],
                    "explicit_confirmation": True,
                },
            )[0]
            == 409
        )
        assert (
            _request(
                "GET",
                tour_url(server).replace("/branches/branch/", "/branches/foreign/"),
            )[0]
            == 409
        )
        assert (
            _request("GET", tour_url(server).replace("/runs/run/", "/runs/foreign/"))[0]
            == 409
        )
        create_edition(server, "first", 8)
        create_edition(server, "second", 8, offset=3, factor=2)
        assert not _request("GET", server.base_url + "/viewer/runs/run/calendar-tour")[
            1
        ]["editions"]
        for name in ("open-announcements", "open-first-play-week"):
            execute(server, command(inspect(server), "transition", name=name))
            save_tour(server)
        edition(server, "first", 8)
        view = inspect(server)
        assert view["transition_blockers"] == []
        cmd = command(view, "transition", name="week4-to5")
        code, review = _request("POST", tour_url(server) + "/preview", cmd)
        assert code == 200, review
        approval = {
            "command": cmd,
            "expected_preview_fingerprint": review["preview_fingerprint"],
            "explicit_confirmation": True,
        }

        def digest():
            h = hashlib.sha256()
            with sqlite3.connect(tmp_path / "tour.db") as c:
                for line in c.iterdump():
                    h.update(line.encode())
            return h.hexdigest()

        before = digest()
        from beta_engine.application import calendar_tour_service as service

        def fail(name):
            if name == "after_tour_write":
                raise ValueError("Controlled late transition failure")

        with monkeypatch.context() as patch:
            patch.setattr(service, "_fault_injection_point", fail)
            assert _request("POST", tour_url(server) + "/execute", approval)[0] == 409
        assert digest() == before
        assert (
            _request(
                "POST",
                tour_url(server) + "/execute",
                {**approval, "expected_preview_fingerprint": "f" * 64},
            )[0]
            == 409
        )
        transition, request = execute(
            server, command(view, "transition", name="week4-to5")
        )
        assert (
            transition["impact"]["development_policy"]["annual_change_basis_points"]
            == 1098
        )
        assert transition["impact"]["target_ranking_policy"]["best_n"] == 1
        before_save = _request(
            "GET", server.base_url + "/viewer/runs/run/calendar-tour"
        )[1]
        assert before_save["official_ranking"]["week"]["week"] == 4
        assert sorted(r["points"] for r in transition["impact"]["ranking"]["rows"]) == [
            15,
            15,
            15,
            15,
            30,
            30,
            60,
            100,
        ]
        save_tour(server)
        assert (
            sum(
                n
                for _, n in transition["impact"]["sporting"]["advance"]["played_counts"]
            )
            == 14
        )
        assert (
            _request(
                "POST",
                tour_url(server) + "/execute",
                {**request, "command": {**request["command"], "seed": 232}},
            )[0]
            == 409
        )
        public = _request("GET", server.base_url + "/viewer/runs/run/calendar-tour")[1]
        assert public["official_ranking"]["week"]["week"] == 5
        assert (
            _request(
                "GET", server.base_url + "/viewer/runs/run/calendar-tour?week_ordinal=5"
            )[0]
            == 409
        )
        assert inspect(server)["state"]["week"]["week"] == 5
        from tests.api.test_calendar_sporting_horizon_extension import extend, extension

        code, review = extension(server, 4)
        assert code == 200 and review["can_save"], review
        assert extend(server, review)[0] == 200
        edition(server, "second", 8)
        second_transition, _ = execute(
            server, command(inspect(server), "transition", name="week5-to6")
        )
        assert (
            second_transition["impact"]["development_policy"][
                "annual_change_basis_points"
            ]
            == 0
        )
        assert second_transition["impact"]["sporting"]["attribute_change_count"] == 0
        assert all(
            len(row["counted_results"]) == 1
            for row in second_transition["impact"]["ranking"]["rows"]
        )
        final = save_tour(server)
        assert len(inspect(server)["state"]["rankings"]) == 5
        assert sorted(
            r["main_points"]
            for r in inspect(server)["edition_evidence"]["first"]["results"]
        ) == [15, 15, 15, 15, 30, 30, 60, 100]
        code, replay = _request("GET", root(server) + "/second:final/replay")
        assert code == 200 and replay["exact_replay"], replay
        # Controlled negative injection touches only the disposable live row.
        # Saved revisions/hashes are never rewritten, including during recovery.
        from beta_engine.domain.run_packages import canonical_hash
        from beta_engine.infrastructure.db.models import CalendarTourAuthorityModel

        for damage in ("point_table", "receipt"):
            with _repo._session_factory.begin() as session:
                row = session.get(CalendarTourAuthorityModel, ("run", "branch"))
                original = (row.payload_json, row.fingerprint)
                corrupt = json.loads(row.payload_json)
                if damage == "point_table":
                    corrupt["editions"][0]["edition"]["point_table"]["champion"] = 999
                else:
                    receipt = next(
                        r
                        for r in corrupt["receipts"]
                        if r["result"]["action"] == "transition"
                    )
                    receipt["result"]["impact"] = None
                row.payload_json = json.dumps(corrupt)
                row.fingerprint = canonical_hash(corrupt)
            try:
                assert _request("GET", tour_url(server))[0] == 409
            finally:
                with _repo._session_factory.begin() as session:
                    row = session.get(CalendarTourAuthorityModel, ("run", "branch"))
                    row.payload_json, row.fingerprint = original
    with ApiServer(database_url=db) as restarted:
        assert inspect(restarted)["saved"]
        assert inspect(restarted)["state"]["week"]["week"] == 6
        code, replayed = _request("GET", root(restarted) + "/first:final/replay")
        assert code == 200 and replayed["exact_replay"], replayed
        assert _request("POST", tour_url(restarted) + "/execute", request) == (
            201,
            transition,
        )
        restore(restarted, initial["revision_id"])
        assert not inspect(restarted)["state"]["editions"]
        restore(restarted, final["revision_id"])
        assert inspect(restarted)["state"]["week"]["week"] == 6
        for edition_id in ("first", "second"):
            code, replayed = _request(
                "GET", root(restarted) + f"/{edition_id}:final/replay"
            )
            assert code == 200 and replayed["exact_replay"], replayed

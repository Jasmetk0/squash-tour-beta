"""Real production HTTP/SQLite post-admission Edition and actual MatchEngine."""

import json
from collections import Counter
from copy import deepcopy
from dataclasses import replace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.models import (
    CalendarPlayerSportingCheckpointModel,
    CalendarTourAuthorityModel,
)
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_population_sporting_checkpoint import restore
from tests.api.test_calendar_tour_flow import (
    command,
    execute,
    inspect,
    save_tour,
    setup,
    tour_url,
)
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def replay_url(server):
    return tour_url(server).replace(
        "/calendar-tour",
        "/authoritative-simulation/calendar-continuation/after-intake:final/replay",
    )


@pytest.mark.parametrize(
    "width,offset", [(52, 1), (61, 37), (80, 80)], ids=["earth", "fax", "extended"]
)
def test_admitted_player_plays_real_edition_and_saved_history(
    tmp_path, monkeypatch, width, offset
):
    path = tmp_path / "post-intake.db"
    database_url = f"sqlite:///{path}"
    clock = RunCalendar(width, offset, 2030, 3)
    with ApiServer(database_url=database_url) as server:
        repo, initial = setup(server, clock, 4)
        immutable_initial = repo.get_branch_saved_revision(
            revision_id=initial["revision_id"]
        )
        sign_prospects(server, repo, clock)
        from beta_engine.domain.calendar.run_week_position import RunWeekPosition
        from tests.application.test_calendar_native_prospect_intake import source_at

        future = source_at(
            clock,
            RunWeekPosition(calendar=clock, season_index=0, week=8),
            pid="future-prospect",
        )
        original = repo.list_run_prospects(run_id="run")[0]
        repo.upsert_run_prospects(
            [
                replace(
                    original,
                    prospect_id="future-prospect",
                    display_name="Future Athlete",
                    season_start_year=future["season_start_year"],
                    season_week=future["season_week"],
                    calendar_year=future["calendar_year"],
                    year_week=future["year_week"],
                    birth_year=future["birth_year"],
                    birth_year_week=future["birth_year_week"],
                    profile_json=future["profile"],
                    development_json=future["development"],
                    potential_json=future["potential"],
                )
            ]
        )
        sign_prospects(server, repo, clock)
        born, _ = execute(server, command(inspect(server), "transition", name="admit"))
        assert "born-native-15" not in {
            r["player_id"] for r in born["impact"]["ranking"]["rows"]
        }
        assert "future-prospect" not in {
            p["player_id"] for p in inspect(server)["players"]
        }
        birth_save = save_tour(server)
        immutable_birth = repo.get_branch_saved_revision(
            revision_id=birth_save["revision_id"]
        )
        if width == 80:
            from tests.api.test_calendar_sporting_horizon_extension import (
                extend,
                extension,
            )

            code, review = extension(server, 5)
            assert code == 200 and review["can_save"], review
            assert extend(server, review)[0] == 200
        view = inspect(server)
        week = {**view["state"]["week"], "calendar": view["run_calendar"]}
        execute(
            server,
            command(
                view,
                "create-edition",
                name="after-intake:create",
                data={
                    "edition_id": "after-intake",
                    "name": "Post-admission Tour",
                    "week": {**week, "week": 5},
                    "announcement_week": {**week, "week": 4},
                    "start_slot": 1,
                    "main_entrant_count": 4,
                    "ranked": True,
                    "validity_weeks": width,
                    "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
                },
            ),
        )
        save_tour(server)
        for week in (4, 5):
            execute(
                server,
                command(inspect(server), "transition", name=f"native-week-{week}"),
            )
            save_tour(server)
        view = inspect(server)
        assert (
            _request(
                "POST",
                tour_url(server) + "/preview",
                command(
                    view,
                    "submit",
                    name="not-admitted",
                    edition_id="after-intake",
                    data={"player_ids": ["future-prospect"]},
                ),
            )[0]
            == 409
        )
        entrants = ["born-native-15"] + [
            p["player_id"]
            for p in view["players"]
            if p["player_id"] != "born-native-15"
        ][:3]
        execute(
            server,
            command(
                view,
                "submit",
                name="applications",
                edition_id="after-intake",
                data={"player_ids": entrants},
            ),
        )
        for action in ("approve", "draw"):
            execute(
                server,
                command(
                    inspect(server), action, name=action, edition_id="after-intake"
                ),
            )
        assert (
            _request(
                "POST",
                tour_url(server) + "/preview",
                command(
                    inspect(server),
                    "play",
                    name="unsaved-play",
                    edition_id="after-intake",
                ),
            )[0]
            == 409
        )
        before_play = save_tour(server)
        prior_payload = repo.get_branch_saved_revision(
            revision_id=before_play["revision_id"]
        ).payload
        from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
            parse_checkpoint_json,
        )

        prior = parse_checkpoint_json(
            json.dumps(
                prior_payload["content"]["calendar_player_sporting_checkpoint"]["state"]
            )
        )
        prior_records = {p.player_id: p for p in prior.players}
        cmd = command(
            inspect(server), "play", name="native-play", edition_id="after-intake"
        )
        code, preview = _request("POST", tour_url(server) + "/preview", cmd)
        assert code == 200, preview
        request = {
            "command": cmd,
            "expected_preview_fingerprint": preview["preview_fingerprint"],
            "explicit_confirmation": True,
        }
        viewer_url = server.base_url + "/viewer/runs/run/calendar-tour"
        public_before = _request("GET", viewer_url)
        if width == 61:
            from beta_engine.application import calendar_tour_service

            for seam in (
                "after_native_matches_write",
                "after_tour_write",
                "after_native_replay",
            ):
                before = _dump(path)

                def fail(name, seam=seam):
                    if name == seam:
                        raise ValueError("Injected native competition fault")

                with monkeypatch.context() as patch:
                    patch.setattr(calendar_tour_service, "_fault_injection_point", fail)
                    assert (
                        _request("POST", tour_url(server) + "/execute", request)[0]
                        == 409
                    )
                assert _dump(path) == before
        code, played = _request("POST", tour_url(server) + "/execute", request)
        assert code == 201, played
        assert _request("POST", tour_url(server) + "/execute", request) == (201, played)
        assert _request("GET", viewer_url) == public_before
        played_slots = inspect(server)["edition_evidence"]["after-intake"]["matches"]
        assert played_slots[0]["slot"] == played_slots[1]["slot"]
        assert played_slots[-1]["slot"] > played_slots[0]["slot"]
        played_save = save_tour(server)
        raw = repo.get_branch_saved_revision(
            revision_id=played_save["revision_id"]
        ).payload
        cp = raw["content"]["calendar_player_sporting_checkpoint"]["state"]
        assert cp["schema_version"] == "calendar_sporting_checkpoint.v12"
        event = cp["events"][-1]
        assert event["schema_version"] == "calendar_followup_knockout.v6"
        assert "born-native-15" in event["entrant_ids"] and len(event["matches"]) == 3
        first, second, final = event["matches"]
        assert (
            first["source_checkpoint_fingerprint"]
            == second["source_checkpoint_fingerprint"]
        )
        assert (
            final["source_checkpoint_fingerprint"]
            != first["source_checkpoint_fingerprint"]
        )
        for match in (first, second):
            for projection in match["canonical_projections"]:
                record = prior_records[projection["player_id"]]
                assert projection["canonical_attributes"] == [
                    list(a) for a in record.attributes
                ]
                assert (
                    projection["current_form"],
                    projection["long_term_fatigue"],
                ) == (record.current_form, record.long_term_fatigue)
            from beta_engine.infrastructure.db.player_health_state import (
                _parse_health_json,
            )

            source_health = _parse_health_json(
                json.dumps(
                    prior_payload["content"]["player_health_state"]["states"][-1]
                )
            )
            assert match["source_health_fingerprint"] == source_health.fingerprint
            assert [
                p["player_id"] for p in match["effective_health"]["player_profiles"]
            ] == [p["player_id"] for p in match["canonical_projections"]]
        effects = {e["player_id"]: e for m in (first, second) for e in m["effects"]}
        assert {p["player_id"] for p in final["canonical_projections"]} == {
            first["result"]["winner_player_id"],
            second["result"]["winner_player_id"],
        }
        for p in final["canonical_projections"]:
            assert (
                p["current_form"],
                p["match_sharpness"],
                p["long_term_fatigue"],
            ) == (
                effects[p["player_id"]]["form_after"],
                effects[p["player_id"]]["sharpness_after"],
                effects[p["player_id"]]["fatigue_after"],
            )
        assert _request("GET", replay_url(server))[0] == 200
        execute(
            server,
            command(
                inspect(server),
                "confirm-result",
                name="confirm",
                edition_id="after-intake",
            ),
        )
        save_tour(server)
        result, _ = execute(
            server, command(inspect(server), "transition", name="after-play")
        )
        rows = result["impact"]["ranking"]["rows"]
        assert "born-native-15" in {r["player_id"] for r in rows}
        assert sorted(r["points"] for r in rows) == [30, 30, 60, 100]
        after = save_tour(server)
        final_revision = repo.get_branch_saved_revision(
            revision_id=after["revision_id"]
        )
        advanced = final_revision.payload["content"][
            "calendar_player_sporting_checkpoint"
        ]["state"]["events"][-1]["advance"]
        counts = Counter(
            pid
            for m in event["matches"]
            for pid in (m["result"]["player_a_id"], m["result"]["player_b_id"])
        )
        assert dict(advanced["played_counts"]) == {
            pid: counts[pid] for pid in prior_records
        }
        assert sum(dict(advanced["played_counts"]).values()) == 6
        assert _request("POST", tour_url(server) + "/execute", request) == (201, played)
        changed = deepcopy(request)
        changed["command"]["seed"] += 1
        assert _request("POST", tour_url(server) + "/execute", changed)[0] == 409
        assert (
            _request(
                "POST",
                tour_url(server).replace("branches/branch/", "branches/foreign/")
                + "/execute",
                request,
            )[0]
            == 409
        )
        assert (
            _request(
                "POST",
                tour_url(server).replace("runs/run/", "runs/foreign/") + "/execute",
                request,
            )[0]
            == 409
        )
        assert (
            repo.get_branch_saved_revision(revision_id=initial["revision_id"])
            == immutable_initial
        )
        assert (
            repo.get_branch_saved_revision(revision_id=birth_save["revision_id"])
            == immutable_birth
        )
        expected = inspect(server)
        expected_replay = _request("GET", replay_url(server))
        assert expected_replay[0] == 200 and expected_replay[1]["exact_replay"], (
            expected_replay
        )
        if width == 52:
            for model, attack in (
                (CalendarTourAuthorityModel, "receipt"),
                (CalendarTourAuthorityModel, "saved_origin"),
                (CalendarPlayerSportingCheckpointModel, "played_counts"),
            ):
                with repo._session_factory.begin() as session:
                    row = session.get(model, ("run", "branch"))
                    original = row.payload_json, row.fingerprint
                    body = json.loads(row.payload_json)
                    if attack == "receipt":
                        body["receipts"][-1]["result"]["impact"][
                            "ranking_fingerprint"
                        ] = "0" * 64
                    elif attack == "saved_origin":
                        body["competition_root_saved_head"] = initial["revision_id"]
                    else:
                        body["events"][-1]["advance"]["played_counts"][0][1] += 1
                    row.payload_json = json.dumps(body)
                    row.fingerprint = canonical_hash(body)
                try:
                    assert _request("GET", tour_url(server))[0] == 409, attack
                finally:
                    with repo._session_factory.begin() as session:
                        row = session.get(model, ("run", "branch"))
                        row.payload_json, row.fingerprint = original
    with ApiServer(database_url=database_url) as restarted:
        assert inspect(restarted) == expected
        assert _request("GET", replay_url(restarted)) == expected_replay
        restore(restarted, before_play["revision_id"])
        assert not inspect(restarted)["state"]["editions"][-1]["tournament_fingerprint"]
        restore(restarted, after["revision_id"])
        assert inspect(restarted)["state"] == expected["state"]
        restore(restarted, birth_save["revision_id"])
        assert (
            inspect(restarted)["state"]["schema_version"]
            == "calendar_tour_authority.v3"
        )
        restore(restarted, after["revision_id"])
        assert _request("GET", replay_url(restarted)) == expected_replay

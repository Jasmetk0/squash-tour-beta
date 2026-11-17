"""Two real closed seasons on fixed Run clocks: archive, both-direction comparison, extension.

Reuses the global-slot preparation (two overlapping Editions in each season, every actual
week and both Season Transitions executed over HTTP/SQLite, real MatchEngine matches,
confirmed results and an explicit Save after every operation). Each Run keeps one fixed
clock: W6, Earth W52, FAX W61 (Season Week 1 = Year Week 37) and W80. Season 2 uses
another point table, so the comparison must show different awards and explicitly flag
the changed point tables. The Saved clock is recorded after every week executed by this
module; the test fails unless both complete seasons and both Season Transitions ran.

W6 is the fast scenario. The W52/W61/W80 variants are long (``long_season`` marker);
CI runs each in its own job by exact node id, never through a ``-k`` substring.
"""

import pytest

from tests.api.test_calendar_global_slots import ready
from tests.api.test_calendar_sporting_horizon_extension import extend, extension
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, tour_url
from tests.api.test_saved_revision_history_api import ApiServer

pytestmark = pytest.mark.smoke

TABLES = {0: {"champion": 100, "finalist": 60, "semifinal": 30},
          1: {"champion": 200, "finalist": 120, "semifinal": 60}}


def visit(server, visited):
    """Record the actual Saved clock position after an explicit Save."""
    if visited is None:
        return
    view = inspect(server)
    assert view["saved"], "every step must end in an explicit Save"
    week = view["state"]["week"]
    visited.append((week["season_index"], week["week"]))


def play_season_editions(server, ids):
    """Two global slots, then confirm both Editions (real matches, explicit Saves)."""
    for index in (1, 2):
        execute(server, command(inspect(server), "next-slot", name=f"{ids[0]}-slot-{index}"))
        save_tour(server)
    for eid in ids:
        execute(server, command(inspect(server), "confirm-result", name=eid + ":confirm", edition_id=eid))
        save_tour(server)


def run_to_season_end(server, width, visited=None):
    for week in range(5, width + 1):
        execute(server, command(inspect(server), "transition", name=f"s-{inspect(server)['state']['week']['season_index']}-w{week}"))
        save_tour(server)
        visit(server, visited)
    name = f"season-end-{inspect(server)['state']['week']['season_index']}"
    execute(server, command(inspect(server), "season-transition", name=name))
    save_tour(server)
    visit(server, visited)


def plan_second_season(server, width, visited=None):
    ids = ("s2-a", "s2-b")
    for eid in ids:
        view = inspect(server)
        week = view["state"]["week"]
        assert (week["season_index"], week["week"]) == (1, 1)
        execute(server, command(view, "create-edition", name=eid + ":create", data={
            "schema_version": "calendar_tournament_edition.v2", "simulation_seed": 905,
            "edition_id": eid, "name": eid,
            "week": {**week, "week": 4}, "announcement_week": {**week, "week": 3},
            "start_slot": 1, "main_entrant_count": 4, "ranked": True, "validity_weeks": width,
            "point_table": TABLES[1],
        }))
        save_tour(server)
    for target in (2, 3, 4):
        execute(server, command(inspect(server), "transition", name=f"s2-week-{target}"))
        save_tour(server)
        visit(server, visited)
    players = [p["player_id"] for p in inspect(server)["players"]]
    for i, eid in enumerate(ids):
        execute(server, command(inspect(server), "submit", name=eid + ":submit", edition_id=eid,
                                data={"player_ids": players[i * 4:i * 4 + 4]}))
        for action in ("approve", "draw"):
            execute(server, command(inspect(server), action, name=eid + ":" + action, edition_id=eid))
        save_tour(server)
    return ids


def raw(server, path):
    """GET with the shared acceptance timeout; slow reads must remain visible."""
    import json
    from urllib import error, request

    try:
        with request.urlopen(tour_url(server) + path, timeout=120) as response:
            return response.status, json.loads(response.read().decode() or "{}")
    except error.HTTPError as exc:
        return int(exc.code), json.loads(exc.read().decode() or "{}")


def get(server, path):
    code, body = raw(server, path)
    assert code == 200, body
    return body


def without_head(value):
    """The Saved HEAD identifier legitimately changes with each new Save."""
    return {k: v for k, v in value.items() if k != "saved_head_revision_id"}


def closed_season_reads(server):
    return {
        "s0": get(server, "/seasons/0")["selected"],
        "s1": get(server, "/seasons/1")["selected"],
        "s1_vs_0": without_head(get(server, "/seasons/1?compare_to=0")),
        "s0_vs_1": without_head(get(server, "/seasons/0?compare_to=1")),
    }


def tour_fingerprint_free(value):
    """An explicit extension re-signs the Tour clock; sporting values must stay equal."""
    if isinstance(value, dict):
        return {k: tour_fingerprint_free(v) for k, v in value.items() if k != "source_tour_fingerprint"}
    if isinstance(value, list):
        return [tour_fingerprint_free(v) for v in value]
    return value


@pytest.mark.parametrize("width", [
    pytest.param(6, id="w6"),
    pytest.param(52, id="w52", marks=pytest.mark.long_season),
    pytest.param(61, id="w61", marks=pytest.mark.long_season),
    pytest.param(80, id="w80", marks=pytest.mark.long_season),
])
def test_two_closed_seasons_archive_compare_extend_and_restart(tmp_path, width):
    db = f"sqlite:///{tmp_path / 'wide-archive.sqlite'}"
    with ApiServer(database_url=db) as server:
        ready(server, width, seasons=3)
        # ready() plays the opening Week 1 knockout, the Week 2 sporting command,
        # then executes and Saves Week Transitions to Weeks 3 and 4.
        view = inspect(server)
        assert view["saved"] and view["run_calendar"]["weeks_per_year"] == width
        assert (view["state"]["week"]["season_index"], view["state"]["week"]["week"]) == (0, 4)
        visited = [(0, 1), (0, 2), (0, 3), (0, 4)]
        play_season_editions(server, ("parallel-a", "parallel-b"))
        run_to_season_end(server, width, visited)
        plan_second_season(server, width, visited)
        play_season_editions(server, ("s2-a", "s2-b"))
        run_to_season_end(server, width, visited)
        # Every week of both seasons in order, both W -> Week 1 Season Transitions.
        assert visited == [(s, w) for s in (0, 1) for w in range(1, width + 1)] + [(2, 1)]
        assert inspect(server)["saved_completed_seasons"] == [0, 1]
        run_clock = inspect(server)["run_calendar"]
        assert run_clock["weeks_per_year"] == width

        archive = get(server, "/seasons")
        assert [s["season_index"] for s in archive["seasons"]] == [0, 1]
        first, second = archive["seasons"]
        assert first["rules"]["weeks_per_season"] == second["rules"]["weeks_per_season"] == width
        assert first["overview"]["completed_edition_count"] == second["overview"]["completed_edition_count"] == 2
        for season in (first, second):
            rankings = season["overview"]["rankings"]
            assert rankings["next_season_week_1_fingerprint"] not in (
                None, rankings["week_w_published_fingerprint"])
        # Season 2 awards are exactly double (same field, doubled point table).
        s0, s1 = get(server, "/seasons/0")["selected"], get(server, "/seasons/1")["selected"]
        assert sum(p["awarded_points"] for p in s0["players"]) > 0
        assert sum(p["awarded_points"] for p in s1["players"]) == 2 * sum(p["awarded_points"] for p in s0["players"])

        forward = get(server, "/seasons/1?compare_to=0")["detail"]
        backward = get(server, "/seasons/0?compare_to=1")["detail"]
        assert forward["comparability"]["comparable"] is False and backward["comparability"]["comparable"] is False
        assert "edition_point_tables_fingerprint" in {d["field"] for d in forward["comparability"]["differences"]}
        fw = {r["country_code"]: r for r in forward["countries"]}
        for row in backward["countries"]:
            assert row["presence"] == fw[row["country_code"]]["presence"].replace("selected", "X").replace("comparison", "selected").replace("X", "comparison")
            if row["delta"] is not None:
                assert row["delta"] == {k: -v for k, v in fw[row["country_code"]]["delta"].items()}
        assert any(r["delta"] and r["delta"]["awarded_points"] > 0 for r in forward["countries"])
        before = closed_season_reads(server)
        assert before["s0"] == s0 and before["s1"] == s1

        # Continuing (explicit extension) leaves both closed seasons untouched.
        status, review = extension(server, 4)
        assert status == 200 and review["can_save"], review
        status, receipt = extend(server, review, "extend-wide-archive")
        assert status == 200 and receipt["simulation_started"] is False, receipt
        extended = closed_season_reads(server)
        assert tour_fingerprint_free(extended) == tour_fingerprint_free(before)
        extended_archive = get(server, "/seasons")
        assert [s["season_index"] for s in extended_archive["seasons"]] == [0, 1]

    with ApiServer(database_url=db) as restarted:
        assert inspect(restarted)["saved_completed_seasons"] == [0, 1]
        again = get(restarted, "/seasons")
        for old, new in zip(archive["seasons"], again["seasons"], strict=True):
            for key in ("rules", "leading_player", "leading_country", "boundary_command_id"):
                assert old[key] == new[key]
        # A cold process reads exactly the same Saved history as before the restart.
        assert again == extended_archive
        assert closed_season_reads(restarted) == extended
        assert raw(restarted, "/seasons/2")[0] == 409

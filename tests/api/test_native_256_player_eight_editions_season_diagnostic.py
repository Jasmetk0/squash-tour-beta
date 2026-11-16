"""Diagnostic only: a genuinely populated, PLAYED native squash season.

This deliberately tests a 12-week *configured* season, not a full W52 FAX or
ATP season. 256 actual generated players occupy one Saved Run; 16 distinct
players play four 4-player Editions in week 4 and another four in week 5.
Every one of the 24 matches uses the real global-slot MatchEngine, followed by
reviewed result confirmation, manual Saves and Ranking week publication.
The remaining weeks and Season Transition use ordinary production commands.
No fabricated outcomes, inserted SQLite rows, bypassed Entry or implicit Save.
"""
from __future__ import annotations

import json
import resource
import sqlite3
import time

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_tour_flow import (
    command, execute, inspect, save_tour, setup,
)
from tests.api.test_saved_revision_history_api import ApiServer

pytestmark = pytest.mark.smoke

POPULATION = 256
WEEKS = 12
EVENTS_PER_WEEK = 4
ENTRANTS_PER_EVENT = 4
FIRST_WEEK = tuple(f"load-w4-{i}" for i in range(EVENTS_PER_WEEK))
SECOND_WEEK = tuple(f"load-w5-{i}" for i in range(EVENTS_PER_WEEK))
ALL_EVENTS = FIRST_WEEK + SECOND_WEEK


def _evidence(label, **values):
    print("POPULATED_SEASON_DIAGNOSTIC " + json.dumps(
        {"phase": label, **values}, sort_keys=True
    ), flush=True)


def _save_after(server, label):
    signed = save_tour(server)
    _evidence(label, revision_id=signed["revision_id"])
    return signed


def _advance(server, week):
    before = inspect(server)
    assert before["saved"], "Week Transition requires explicit previous Save"
    _, _ = execute(server, command(
        before, "transition", name=f"load-transition-{week}"
    ))
    _save_after(server, f"transition-to-week-{week}")
    assert inspect(server)["state"]["week"]["week"] == week


def _schedule(server):
    for index, edition_id in enumerate(ALL_EVENTS):
        view = inspect(server)
        assert view["state"]["week"]["week"] == 2
        source_week = view["state"]["week"]
        target_week = 4 if index < EVENTS_PER_WEEK else 5
        result, _ = execute(server, command(
            view, "create-edition", name=f"{edition_id}-create",
            data={
                "schema_version": "calendar_tournament_edition.v2",
                "simulation_seed": 12000 + index,
                "edition_id": edition_id,
                "name": edition_id,
                "week": {**source_week, "week": target_week},
                "announcement_week": {**source_week, "week": 3},
                "start_slot": 1,
                "main_entrant_count": ENTRANTS_PER_EVENT,
                "ranked": True,
                "validity_weeks": WEEKS,
                "point_table": {
                    "champion": 100, "finalist": 60, "semifinal": 30,
                },
            },
        ))
        assert result["manual_save_required"]
        _save_after(server, f"create-{edition_id}")
    assert len(inspect(server)["state"]["editions"]) == len(ALL_EVENTS)


def _entry_and_draw(server, ids, players):
    for index, edition_id in enumerate(ids):
        entrants = players[index * ENTRANTS_PER_EVENT:(index + 1) * ENTRANTS_PER_EVENT]
        assert len(entrants) == ENTRANTS_PER_EVENT
        execute(server, command(
            inspect(server), "submit", name=f"{edition_id}-submit",
            edition_id=edition_id, data={"player_ids": entrants},
        ))
        for action in ("approve", "draw"):
            execute(server, command(
                inspect(server), action, name=f"{edition_id}-{action}",
                edition_id=edition_id,
            ))
        _save_after(server, f"draw-{edition_id}")
    assert inspect(server)["next_slot"] is not None


def _play_actual_matches(server, ids, week):
    matches_in_slots = 0
    slots = 0
    for index in range(10):
        before = inspect(server)
        assert before["state"]["week"]["week"] == week
        slot = before["next_slot"]
        if slot is None:
            break
        assert slot["matches"] and not slot["conflicts"]
        count = len(slot["matches"])
        result, _ = execute(server, command(
            before, "next-slot", name=f"load-w{week}-slot-{index}",
        ))
        assert result["manual_save_required"]
        _save_after(server, f"w{week}-global-slot-{index}")
        matches_in_slots += count
        slots += 1
    else:
        raise AssertionError("Global-slot progression did not terminate within ten slots")

    assert inspect(server)["next_slot"] is None
    assert slots >= 2
    assert matches_in_slots == 3 * len(ids), (slots, matches_in_slots)
    for edition_id in ids:
        evidence = inspect(server)["edition_evidence"][edition_id]
        assert len(evidence["matches"]) == 3
        assert all(match["rally_count"] > 0 for match in evidence["matches"])
        assert not next(e for e in inspect(server)["state"]["editions"]
                        if e["edition"]["edition_id"] == edition_id)["result_confirmed"]
        result, _ = execute(server, command(
            inspect(server), "confirm-result", name=f"{edition_id}-confirm",
            edition_id=edition_id,
        ))
        assert result["manual_save_required"]
        _save_after(server, f"confirm-{edition_id}")
        verified = inspect(server)["edition_evidence"][edition_id]
        assert sorted(p["main_points"] for p in verified["results"]) == [
            30, 30, 60, 100,
        ]
    _evidence(f"played-week-{week}", real_matches=matches_in_slots,
              confirmed_editions=len(ids), slots=slots)
    return matches_in_slots


def _check_published(server, expected_events, expected_points):
    view = inspect(server)
    ranking = view["state"]["rankings"][-1]
    rows = ranking["rows"]
    assert len(view["players"]) == POPULATION
    actual = {entry["edition_id"] for row in rows
              for entry in row["counted_results"]}
    assert actual == set(expected_events), (actual, expected_events)
    assert sum(row["points"] for row in rows) == expected_points
    assert len([row for row in rows if row["counted_results"]]) == 16
    return ranking


def _db_measure(path):
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        row = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(payload_json AS BLOB))), 0) "
            "FROM branch_saved_revisions"
        ).fetchone()
        return {
            "sqlite_bytes": path.stat().st_size,
            "saved_revision_count": row[0],
            "saved_payload_bytes": row[1],
        }


def test_native_w12_256_players_eight_real_editions_cold_reopen(tmp_path):
    started = time.perf_counter()
    process_started = time.process_time()
    path = tmp_path / "populated-w12-256.db"
    url = f"sqlite:///{path}"
    total_matches = 0

    with ApiServer(database_url=url) as server:
        repository, saved_initial = setup(
            server, RunCalendar(WEEKS, 1, 2030, 2), count=POPULATION
        )
        initial = inspect(server)
        players = [p["player_id"] for p in initial["players"]]
        assert len(players) == len(set(players)) == POPULATION
        assert initial["state"]["week"]["week"] == 2
        _evidence("initialized", players=len(players), week=2,
                  initial_saved_revision=saved_initial["revision_id"],
                  wall_s=round(time.perf_counter() - started, 3))

        _schedule(server)
        _advance(server, 3)
        _advance(server, 4)
        announced = inspect(server)["state"]["editions"]
        assert len(announced) == len(ALL_EVENTS)
        _entry_and_draw(server, FIRST_WEEK, players)
        total_matches += _play_actual_matches(server, FIRST_WEEK, 4)
        _advance(server, 5)
        _check_published(server, FIRST_WEEK, 4 * 220)

        _entry_and_draw(server, SECOND_WEEK, players)
        total_matches += _play_actual_matches(server, SECOND_WEEK, 5)
        _advance(server, 6)
        published = _check_published(server, ALL_EVENTS, 8 * 220)
        assert total_matches == 24
        assert len([a for a in inspect(server)["state"]["editions"]
                    if a["result_confirmed"]]) == len(ALL_EVENTS)
        _evidence("sporting-complete", world_players=POPULATION,
                  distinct_match_participants=16, tournament_entries=32,
                  matches=total_matches, tournaments=len(ALL_EVENTS),
                  points=8 * 220, week=6,
                  wall_s=round(time.perf_counter() - started, 3))

        # Complete every remaining week of the *configured* W12 season.
        for week in range(7, WEEKS + 1):
            _advance(server, week)
        before_close = inspect(server)
        assert before_close["state"]["week"]["week"] == WEEKS
        result, _ = execute(server, command(
            before_close, "season-transition", name="load-season-1-close",
        ))
        assert result["manual_save_required"]
        _save_after(server, "season-one-closed")
        final = inspect(server)
        assert final["saved"]
        assert final["state"]["week"]["season_index"] == 1
        assert final["state"]["week"]["week"] == 1
        assert final["saved_head_revision_id"] != saved_initial["revision_id"]
        final_head = final["saved_head_revision_id"]
        # Authentic original ranking must still be backed by the same results.
        assert published["rows"]

    _evidence("before-cold-reopen", **_db_measure(path),
              wall_s=round(time.perf_counter() - started, 3))
    with ApiServer(database_url=url) as restarted:
        view = inspect(restarted)
        assert view["saved"]
        assert view["saved_head_revision_id"] == final_head
        assert view["state"]["week"]["season_index"] == 1
        assert view["state"]["week"]["week"] == 1
        evidence = view["edition_evidence"]
        for edition_id in ALL_EVENTS:
            assert len(evidence[edition_id]["matches"]) == 3
            assert all(row["rally_count"] > 0 for row in evidence[edition_id]["matches"])
            assert next(a for a in view["state"]["editions"]
                        if a["edition"]["edition_id"] == edition_id)["result_confirmed"]
        assert len(view["players"]) == POPULATION

    _evidence(
        "pass-cold-reopen", **_db_measure(path),
        population=POPULATION,
        distinct_match_participants=16,
        tournament_entries=32,
        played_tournaments=8,
        authentic_matches=total_matches,
        weeks_per_season=WEEKS,
        seasons_completed=1,
        wall_s=round(time.perf_counter() - started, 3),
        process_cpu_s=round(time.process_time() - process_started, 3),
        process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        full_reference_w52_season=False,
    )

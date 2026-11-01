"""Four actual native Tour Editions in two consecutive overlapping weeks.

Production HTTP/SQLite, reviewed Entry/Draw, real global-slot MatchEngine,
four independently confirmed results, manual Save, two Official publications,
cold restart and original-command idempotence. No fabricated match scores,
direct writes, automatic eligibility or 80-played-Edition claim.
"""
import json

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_tour_flow import (
    command, execute, inspect, save_tour, setup, tour_url,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke

FIRST_WEEK = ("week4-alpha", "week4-beta")
SECOND_WEEK = ("week5-gamma", "week5-delta")
EDITION_FACTORS = {
    "week4-alpha": 1, "week4-beta": 2,
    "week5-gamma": 3, "week5-delta": 4,
}


def _fixture_schedule():
    """Only scheduling inputs; sporting results always come from MatchEngine."""
    return tuple(
        (edition_id, 4 if index < 2 else 5, index + 1)
        for index, edition_id in enumerate((*FIRST_WEEK, *SECOND_WEEK))
    )


@pytest.mark.pr_critical
def test_four_edition_reference_schedule_has_two_distinct_same_week_fields():
    schedule = _fixture_schedule()
    assert len(schedule) == 4
    assert [week for _, week, _ in schedule] == [4, 4, 5, 5]
    assert len({edition_id for edition_id, _, _ in schedule}) == 4
    assert set(EDITION_FACTORS) == {item[0] for item in schedule}
    for edition_id, week, factor in schedule:
        assert factor > 0 and 3 < week < 52
        assert len(edition_id) <= 128


def _plan(server):
    """Create and Saved-sign four independent events *before* announcement."""
    for edition_id, target_week, factor in _fixture_schedule():
        view = inspect(server)
        week = view["state"]["week"]
        assert week["week"] == 2
        result, _ = execute(server, command(
            view, "create-edition", name=edition_id + ":create",
            data={
                "schema_version": "calendar_tournament_edition.v2",
                "simulation_seed": 890 + factor,
                "edition_id": edition_id,
                "name": edition_id,
                "week": {**week, "week": target_week},
                "announcement_week": {**week, "week": 3},
                "start_slot": 1,
                "main_entrant_count": 4,
                "ranked": True,
                "validity_weeks": 52,
                "point_table": {
                    "champion": factor * 100,
                    "finalist": factor * 60,
                    "semifinal": factor * 30,
                },
            },
        ))
        assert result["manual_save_required"]
        save_tour(server)
    view = inspect(server)
    assert len(view["state"]["editions"]) == 4
    assert all(not event["result_confirmed"] for event in view["state"]["editions"])


def _advance(server, label, week):
    result, request = execute(
        server, command(inspect(server), "transition", name=label)
    )
    before = inspect(server)
    assert not before["saved"]
    assert before["state"]["week"]["week"] == week
    signed = save_tour(server)
    assert inspect(server)["saved_head_revision_id"] == signed["revision_id"]
    return result, request


def _prepare_fields(server, edition_ids):
    """One group of four real players per overlapping slot, no collision."""
    players = [p["player_id"] for p in inspect(server)["players"]]
    assert len(players) == len(set(players)) == 8
    for index, edition_id in enumerate(edition_ids):
        ids = players[index * 4:(index + 1) * 4]
        assert len(ids) == 4
        result, _ = execute(
            server, command(inspect(server), "submit",
                name=edition_id + ":submit", edition_id=edition_id,
                data={"player_ids": ids}),
        )
        assert result["manual_save_required"]
        for action in ("approve", "draw"):
            execute(server, command(
                inspect(server), action,
                name=edition_id + ":" + action, edition_id=edition_id,
            ))
        assert not inspect(server)["saved"]
        save_tour(server)
    ready = inspect(server)
    assert ready["next_slot"] is not None
    assert len(ready["next_slot"]["matches"]) > 0
    assert not ready["next_slot"]["conflicts"]
    return players


def _play_week(server, edition_ids, week, *, max_slots=8):
    """Real global-slot children, never direct play() or inserted outcomes."""
    observed = []
    original_requests = []
    for i in range(max_slots):
        before = inspect(server)
        assert before["state"]["week"]["week"] == week
        if before["next_slot"] is None:
            break
        slot = before["next_slot"]
        assert slot["number"] > 0
        assert slot["matches"]
        assert slot["remaining"] > 0
        assert not slot["conflicts"]
        result, request = execute(
            server, command(
                before, "next-slot", name=f"global-week-{week}-slot-{i}",
            ),
        )
        assert result["manual_save_required"]
        assert not inspect(server)["saved"]
        saved = save_tour(server)
        observed.append({
            "slot_number": slot["number"],
            "match_count": len(slot["matches"]),
            "saved_revision_id": saved["revision_id"],
        })
        original_requests.append((request, result))
    else:
        raise AssertionError("Global slot progression exceeded the bounded week")
    assert inspect(server)["next_slot"] is None
    assert len(observed) >= 2, observed
    assert sum(s["match_count"] for s in observed) == 6

    for edition_id in edition_ids:
        evidence = inspect(server)["edition_evidence"][edition_id]
        matches = evidence["matches"]
        assert len(matches) == 3
        assert all(m["rally_count"] > 0 for m in matches)
        # Actual outcomes cannot be inferred from the draw or the Fixture.
        assert not next(e for e in inspect(server)["state"]["editions"]
                        if e["edition"]["edition_id"] == edition_id)["result_confirmed"]

        result, request = execute(
            server, command(inspect(server), "confirm-result",
                name=edition_id + ":confirm", edition_id=edition_id),
        )
        assert result["manual_save_required"]
        saved = save_tour(server)
        assert saved["revision_id"] == inspect(server)["saved_head_revision_id"]
        original_requests.append((request, result))

    evidence = inspect(server)["edition_evidence"]
    confirmed = {
        eid: {
            "matches": evidence[eid]["matches"],
            "results": evidence[eid]["results"],
        } for eid in edition_ids
    }
    for edition_id, item in confirmed.items():
        assert len(item["matches"]) == 3
        assert len(item["results"]) == 4
        factor = EDITION_FACTORS[edition_id]
        assert sorted(x["main_points"] for x in item["results"]) == [
            factor * 30, factor * 30, factor * 60, factor * 100,
        ]
        assert next(e for e in inspect(server)["state"]["editions"]
                    if e["edition"]["edition_id"] == edition_id)["result_confirmed"]
    return confirmed, original_requests, observed


def _ranking(server, week, expected_ids, total_points):
    view = inspect(server)
    ranking = view["state"]["rankings"][-1]
    assert ranking["week"]["week"] == week
    rows = ranking["rows"]
    assert len(rows) == 8
    assert sum(r["points"] for r in rows) == total_points
    # Each simultaneous tournament has its own disjoint four-player field.
    # Thus EACH player has one of two W4 Edition results, not both. Only
    # after W5 should each player carry one W4 and one W5 source.
    assert set(expected_ids) == set(FIRST_WEEK) or set(expected_ids) == set(EDITION_FACTORS)
    from collections import Counter

    occurrences = Counter(
        entry["edition_id"] for row in rows for entry in row["counted_results"]
    )
    assert occurrences == Counter({eid: 4 for eid in expected_ids})
    for row in rows:
        sources = [entry["edition_id"] for entry in row["counted_results"]]
        assert len(sources) == (1 if len(expected_ids) == 2 else 2)
        assert sum(eid in FIRST_WEEK for eid in sources) == 1
        assert sum(eid in SECOND_WEEK for eid in sources) == (1 if len(expected_ids) == 4 else 0)
        assert row["points"] == sum(entry["points"] for entry in row["counted_results"])
    return ranking


def test_four_actual_overlapping_editions_across_two_weeks_and_sqlite_restarts(tmp_path):
    """One Run, four actual MatchEngine tournaments, two publication boundaries."""
    db = f"sqlite:///{tmp_path / 'four-actual-editions.sqlite'}"
    with ApiServer(database_url=db) as server:
        repo, initial = setup(server, RunCalendar(52, 1, 2030, 3), count=8)
        original_saved = repo.get_branch_saved_revision(
            revision_id=initial["revision_id"]
        )
        _plan(server)
        for target_week in (3, 4):
            _advance(server, f"opening-w{target_week}", target_week)
        view = inspect(server)
        assert view["state"]["week"]["week"] == 4
        assert set(view["state"]["transitions"][-2]["public_event"][
            "announced_edition_ids"]) == set(EDITION_FACTORS)
        assert all(not view["edition_evidence"].get(eid, {}).get("matches")
                   for eid in EDITION_FACTORS)

        players = _prepare_fields(server, FIRST_WEEK)
        first, first_requests, first_slots = _play_week(
            server, FIRST_WEEK, week=4
        )
        assert all(not inspect(server)["edition_evidence"].get(eid, {}).get("matches")
                   for eid in SECOND_WEEK)
        assert inspect(server)["state"]["rankings"][-1]["week"]["week"] == 4
        before_week5_public = _request(
            "GET", server.base_url + "/viewer/runs/run/calendar-tour"
        )
        assert before_week5_public[0] == 200
        _advance(server, "publish-two-from-w4", 5)
        first_ranking = _ranking(server, 5, FIRST_WEEK, 660)
        assert all(
            r["counted_results"][0]["first_publication_week"]
                == {"season_index": 0, "week": 5}
            for r in first_ranking["rows"]
        )
        source_before_restart = inspect(server)["saved_head_revision_id"]
        saved_viewer = _request(
            "GET", server.base_url + "/viewer/runs/run/calendar-tour"
        )[1]
        assert saved_viewer != before_week5_public[1]
        assert repo.get_branch_saved_revision(
            revision_id=initial["revision_id"]) == original_saved
        print("Actual week 4 complete: two Editions, six real Matches, 660 awards",
              json.dumps(first_slots), flush=True)

    # Reopening the real database between the two overlapping weeks also
    # invalidates any ephemeral Python/SQLAlchemy caches.
    with ApiServer(database_url=db) as server:
        reopened = inspect(server)
        assert reopened["saved"]
        assert reopened["saved_head_revision_id"] == source_before_restart
        assert _request(
            "GET", server.base_url + "/viewer/runs/run/calendar-tour"
        ) == (200, saved_viewer)
        assert _ranking(server, 5, FIRST_WEEK, 660) == first_ranking
        for eid, item in first.items():
            assert reopened["edition_evidence"][eid]["matches"] == item["matches"]
            assert reopened["edition_evidence"][eid]["results"] == item["results"]

        assert _prepare_fields(server, SECOND_WEEK) == players
        second, second_requests, second_slots = _play_week(
            server, SECOND_WEEK, week=5
        )
        unpublished = inspect(server)
        assert unpublished["saved"]
        assert unpublished["state"]["rankings"][-1] == first_ranking
        assert _ranking(server, 5, FIRST_WEEK, 660) == first_ranking
        assert _request(
            "GET", server.base_url + "/viewer/runs/run/calendar-tour"
        ) == (200, saved_viewer) or (
            # Viewer may now show the newly Saved published match results;
            # Official Ranking still cannot advance until an explicit week.
            _request("GET", server.base_url + "/viewer/runs/run/calendar-tour")[1]
                ["official_ranking"] == saved_viewer["official_ranking"]
        )

        second_transition, second_pub_request = _advance(
            server, "publish-two-from-w5", 6
        )
        final_ranking = _ranking(
            server, 6, (*FIRST_WEEK, *SECOND_WEEK), 2200
        )
        assert all(
            {r["first_publication_week"]["week"] for r in row["counted_results"]}
                == {5, 6}
            for row in final_ranking["rows"]
        )
        all_results = {**first, **second}
        all_requests = [*first_requests, *second_requests,
                        (second_pub_request, second_transition)]
        last_head = inspect(server)["saved_head_revision_id"]
        viewer = _request(
            "GET", server.base_url + "/viewer/runs/run/calendar-tour"
        )[1]
        print("Actual week 5 complete: four Editions, twelve real Matches, "
              "2,200 original points", json.dumps(second_slots), flush=True)

    with ApiServer(database_url=db) as server:
        final = inspect(server)
        assert final["saved"] and final["saved_head_revision_id"] == last_head
        assert final["state"]["week"]["week"] == 6
        assert final["state"]["rankings"][-1] == final_ranking
        assert len(final["edition_evidence"]) >= 4
        for eid, original in all_results.items():
            assert final["edition_evidence"][eid]["matches"] == original["matches"]
            assert final["edition_evidence"][eid]["results"] == original["results"]
        assert _request(
            "GET", server.base_url + "/viewer/runs/run/calendar-tour"
        ) == (200, viewer)

        # Every actual completed slot and result command must be idempotent
        # even after later weekly publications and a cold SQLite restart.
        for request, expected in all_requests:
            assert _request(
                "POST", tour_url(server) + "/execute", request
            ) == (201, expected)
        stable = inspect(server)
        assert stable["saved_head_revision_id"] == last_head
        assert stable["state"]["rankings"][-1] == final_ranking
        assert all(
            stable["edition_evidence"][eid]["matches"] == info["matches"]
            for eid, info in all_results.items()
        )

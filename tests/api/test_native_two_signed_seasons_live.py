"""Two genuinely played native knockouts straddling two *signed* season closures.

Actual production HTTP, real MatchEngine rallies, independent manual Saves,
Official Ranking at the exact publication week, cold SQLite restart, and
authenticated Signed Season/Records read models. Never fabricated results.
A narrow W4 calendar bounds runtime; this is NOT 80 Editions or 50 seasons.
"""
import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_tour_flow import (
    command, edition, execute, inspect, save_tour, setup, tour_url,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke

FIRST = "season-one-terminal-cup"
SECOND = "season-two-opening-cup"


@pytest.mark.pr_critical
def test_two_distinct_season_edition_intents_have_independent_reviewed_authority():
    scope = {"saved_head_revision_id": "source-head",
             "checkpoint_fingerprint": "a" * 64, "tour_fingerprint": "b" * 64}
    for edition_id in (FIRST, SECOND):
        cmd = command(scope, "confirm-result",
                      name=edition_id + ":confirm", edition_id=edition_id)
        assert cmd["expected_saved_head"] == "source-head"
        assert cmd["expected_tour_fingerprint"] == "b" * 64
        assert cmd["edition_id"] == edition_id
        assert cmd["action"] == "confirm-result"
        assert "expected_preview_fingerprint" not in cmd
        assert "explicit_confirmation" not in cmd
    assert FIRST != SECOND


def _date(state, season, week):
    return {**state["week"], "season_index": season, "week": week}


def _plan(server, edition_id, season, week, announced_season, announced_week, factor):
    view = inspect(server)
    result, _ = execute(server, command(
        view, "create-edition", name=edition_id + ":plan",
        data={
            "edition_id": edition_id,
            "name": edition_id,
            "week": _date(view["state"], season, week),
            "announcement_week": _date(view["state"], announced_season, announced_week),
            "start_slot": 1,
            "main_entrant_count": 4,
            "ranked": True,
            "validity_weeks": view["run_calendar"]["weeks_per_year"],
            "point_table": {
                "champion": 100 * factor,
                "finalist": 60 * factor,
                "semifinal": 30 * factor,
            },
        },
    ))
    assert result["manual_save_required"]
    signed = save_tour(server)
    assert inspect(server)["saved_head_revision_id"] == signed["revision_id"]
    return signed


def _advance(server, action, label, expected_season, expected_week):
    result, request = execute(server, command(inspect(server), action, name=label))
    assert result["manual_save_required"]
    draft = inspect(server)
    assert not draft["saved"]
    assert (draft["state"]["week"]["season_index"],
            draft["state"]["week"]["week"]) == (expected_season, expected_week)
    saved = save_tour(server)
    assert inspect(server)["saved_head_revision_id"] == saved["revision_id"]
    return result, request, saved


def _published(server):
    code, value = _request("GET", server.base_url + "/viewer/runs/run/calendar-tour")
    assert code == 200, value
    return value


def _signed_season(server, season_index):
    code, body = _request("GET", tour_url(server) + f"/seasons/{season_index}")
    assert code == 200, body
    assert body["saved_head_revision_id"] == inspect(server)["saved_head_revision_id"]
    return body["selected"]


def _signed_records(server):
    code, body = _request("GET", tour_url(server) + "/records")
    assert code == 200, body
    assert body["saved_head_revision_id"] == inspect(server)["saved_head_revision_id"]
    return body


def _assert_played(server, edition_id, factor):
    authority = next(e for e in inspect(server)["state"]["editions"]
                     if e["edition"]["edition_id"] == edition_id)
    assert authority["result_confirmed"]
    evidence = inspect(server)["edition_evidence"][edition_id]
    assert len(evidence["matches"]) == 3
    assert len(evidence["results"]) == 4
    assert all(m["rally_count"] > 0 for m in evidence["matches"])
    assert sorted(r["main_points"] for r in evidence["results"]) == [
        30 * factor, 30 * factor, 60 * factor, 100 * factor,
    ]
    return {
        "matches": evidence["matches"],
        "results": evidence["results"],
    }


def test_two_real_tournaments_and_two_signed_seasons_after_cold_restarts(tmp_path):
    database = f"sqlite:///{tmp_path / 'two-signed-seasons.sqlite'}"
    with ApiServer(database_url=database) as server:
        repo, initial = setup(server, RunCalendar(4, 2, 2030, 3), count=4)
        assert inspect(server)["state"]["week"]["week"] == 2
        initial_rev = repo.get_branch_saved_revision(revision_id=initial["revision_id"])

        # S1 W4 is planned at W2 (published announcement in W3).
        _plan(server, FIRST, 0, 4, 0, 3, factor=1)
        _advance(server, "transition", "open-first-announcement", 0, 3)

        # The next season W1 is prospectively announced in S1 W4.
        _plan(server, SECOND, 1, 1, 0, 4, factor=2)
        before_announcement = inspect(server)
        premature = command(before_announcement, "submit",
            name="premature-s2", edition_id=SECOND,
            data={"player_ids": [p["player_id"] for p in before_announcement["players"][:4]]})
        assert _request("POST", tour_url(server) + "/preview", premature)[0] == 409

        _, _, before_last_week = _advance(
            server, "transition", "announce-second-at-last-week", 0, 4)
        at_last_week = inspect(server)
        assert SECOND in at_last_week["state"]["transitions"][-1]["public_event"]["announced_edition_ids"]
        assert (at_last_week["state"]["week"]["season_index"],
                at_last_week["state"]["week"]["week"]) == (0, 4)
        assert _request("GET", tour_url(server) + "/seasons/0")[0] == 409
        assert not at_last_week["edition_evidence"].get(SECOND, {}).get("matches")

        # Genuine final-week tournament; confirmed data does not retroactively
        # change Official Ranking publication at S1 W4.
        original_published = _published(server)
        edition(server, FIRST, size=4)
        first = _assert_played(server, FIRST, factor=1)
        assert _published(server)["official_ranking"] == original_published["official_ranking"]
        assert _request("GET", tour_url(server) + "/seasons/0")[0] == 409

        first_saved_head = inspect(server)["saved_head_revision_id"]
        transition, season_request, signed_s1 = _advance(
            server, "season-transition", "signed-s1-to-s2", 1, 1)
        assert transition["impact"]["target_week"]["season_index"] == 1
        at_s2 = inspect(server)
        assert at_s2["saved_completed_seasons"] == [0]
        assert sorted(r["points"] for r in at_s2["state"]["rankings"][-1]["rows"]) == [
            30, 30, 60, 100,
        ]
        assert all(len(r["counted_results"]) == 1
                   and r["counted_results"][0]["edition_id"] == FIRST
                   and r["counted_results"][0]["first_publication_week"]
                       == {"season_index": 1, "week": 1}
                   for r in at_s2["state"]["rankings"][-1]["rows"])
        signed_s1_summary = _signed_season(server, 0)
        assert signed_s1_summary["completed_edition_count"] == 1
        assert signed_s1_summary["editions"][0]["edition_id"] == FIRST
        assert sum(c["awarded_points"] for c in signed_s1_summary["countries"]) == 220
        assert _request("GET", tour_url(server) + "/seasons/1")[0] == 409
        assert _signed_records(server)["completed_edition_count"] == 1
        assert repo.get_branch_saved_revision(revision_id=initial_rev.revision_id) == initial_rev
        published_s2 = _published(server)

    # Close the production API and SQLite connection before playing S2 W1.
    with ApiServer(database_url=database) as restarted:
        ready = inspect(restarted)
        assert ready["saved"] and ready["saved_head_revision_id"] == signed_s1["revision_id"]
        assert ready["edition_evidence"][FIRST] == inspect(restarted)["edition_evidence"][FIRST]
        assert ready["edition_evidence"][FIRST]["matches"] == first["matches"]
        assert ready["edition_evidence"][FIRST]["results"] == first["results"]
        assert not ready["edition_evidence"].get(SECOND, {}).get("matches")
        assert _published(restarted) == published_s2
        assert _signed_season(restarted, 0) == signed_s1_summary

        # The second tournament is played in S2 W1, never attributed to S1.
        edition(restarted, SECOND, size=4)
        second = _assert_played(restarted, SECOND, factor=2)
        assert inspect(restarted)["edition_evidence"][FIRST]["matches"] == first["matches"]
        assert _signed_season(restarted, 0) == signed_s1_summary
        assert _request("GET", tour_url(restarted) + "/seasons/1")[0] == 409
        assert _published(restarted)["official_ranking"] == published_s2["official_ranking"]

        after_second, second_request, _ = _advance(
            restarted, "transition", "publish-second-in-s2-w2", 1, 2)
        rows = inspect(restarted)["state"]["rankings"][-1]["rows"]
        assert len(rows) == 4
        assert sum(r["points"] for r in rows) == 660
        assert all(len(r["counted_results"]) == 2
                   and {x["edition_id"] for x in r["counted_results"]} == {FIRST, SECOND}
                   for r in rows)
        assert all(any(x["edition_id"] == SECOND
                       and x["first_publication_week"] == {"season_index": 1, "week": 2}
                       for x in r["counted_results"]) for r in rows)
        assert after_second["impact"]["ranking"]["rows"] == rows

        _advance(restarted, "transition", "s2-w2-to-w3", 1, 3)
        _advance(restarted, "transition", "s2-w3-to-w4", 1, 4)
        _advance(restarted, "season-transition", "signed-s2-to-s3", 2, 1)

        final = inspect(restarted)
        assert final["saved_completed_seasons"] == [0, 1]
        s1 = _signed_season(restarted, 0)
        s2 = _signed_season(restarted, 1)
        assert s1["editions"] == signed_s1_summary["editions"]
        assert s1["completed_edition_count"] == 1
        assert s2["completed_edition_count"] == 1
        assert s2["editions"][0]["edition_id"] == SECOND
        assert sum(c["awarded_points"] for c in s2["countries"]) == 440
        assert sum(c["titles"] for c in s1["countries"]) == 1
        assert sum(c["titles"] for c in s2["countries"]) == 1
        assert _request("GET", tour_url(restarted) + "/seasons/2")[0] == 409
        records = _signed_records(restarted)
        assert records["completed_seasons"] == [0, 1]
        assert records["completed_edition_count"] == 2
        awarded = next(r for r in records["records"]
                       if r["record_id"] == "native_tour.country.awarded_points.v1")
        assert awarded["value"] == 660
        signed_last_head = final["saved_head_revision_id"]
        signed_public = _published(restarted)

    # A second physical SQL reopen must keep both signed season sources.
    with ApiServer(database_url=database) as final_server:
        final = inspect(final_server)
        assert final["saved"] and final["saved_head_revision_id"] == signed_last_head
        assert final["state"]["week"]["season_index"] == 2
        assert final["state"]["week"]["week"] == 1
        assert final["edition_evidence"][FIRST]["matches"] == first["matches"]
        assert final["edition_evidence"][SECOND]["matches"] == second["matches"]
        assert _signed_season(final_server, 0) == s1
        assert _signed_season(final_server, 1) == s2
        assert _signed_records(final_server) == records
        assert _published(final_server) == signed_public
        for request, receipt in ((season_request, transition),
                                 (second_request, after_second)):
            status, replay = _request(
                "POST", tour_url(final_server) + "/execute", request)
            assert (status, replay) == (201, receipt)
        stable = inspect(final_server)
        assert stable["saved"] and stable["saved_head_revision_id"] == signed_last_head
        assert stable["edition_evidence"][FIRST]["results"] == first["results"]
        assert stable["edition_evidence"][SECOND]["results"] == second["results"]

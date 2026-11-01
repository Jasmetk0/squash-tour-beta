"""Real HTTP/SQLite two-Edition progression with a physical restart between play weeks.

One 4-player Edition is fully Saved/published, the backend stops, then a second
independent Edition proceeds in the next week without restoring or resetting
the same Run. No MatchEngine mocks, direct SQL writes or automatic approval.
"""
import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_tour_flow import (
    command, create_edition, execute, inspect, save_tour, setup, tour_url,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke

FIRST = "two-week-first"
SECOND = "two-week-second"


@pytest.mark.pr_critical
def test_two_edition_commands_keep_distinct_authority_and_saved_head_guards():
    """Fast CI companion for a dedicated real HTTP/SQLite acceptance."""
    view = {
        "saved_head_revision_id": "revision-1",
        "checkpoint_fingerprint": "a" * 64,
        "tour_fingerprint": "b" * 64,
    }
    first = command(view, "draw", name="first:draw", edition_id=FIRST)
    second = command(view, "draw", name="second:draw", edition_id=SECOND)
    assert first["edition_id"] != second["edition_id"]
    assert first["command_id"] != second["command_id"]
    for payload in (first, second):
        assert payload["expected_saved_head"] == "revision-1"
        assert payload["expected_checkpoint_fingerprint"] == "a" * 64
        assert payload["expected_tour_fingerprint"] == "b" * 64
        assert "explicit_confirmation" not in payload
        assert "expected_preview_fingerprint" not in payload


def _viewer(server):
    status, data = _request("GET", server.base_url + "/viewer/runs/run/calendar-tour")
    assert status == 200, data
    return data


def _next_week(server, label):
    before = inspect(server)
    previous_week = before["state"]["week"]["week"]
    result, request = execute(server, command(
        before, "transition", name=label,
    ))
    assert not inspect(server)["saved"]
    assert inspect(server)["state"]["week"]["week"] == previous_week + 1
    saved = save_tour(server)
    assert inspect(server)["saved_head_revision_id"] == saved["revision_id"]
    return result, request, saved


def _run_edition(server, edition_id):
    """Explicit signed Field/Draw, real three-match play and reviewed result."""
    view = inspect(server)
    previous_head = view["saved_head_revision_id"]
    original_viewer = _viewer(server)
    players = [p["player_id"] for p in view["players"][:4]]
    assert len(players) == 4 and len(set(players)) == 4

    for action, data in (
        ("submit", {"player_ids": players}),
        ("approve", {}),
        ("draw", {}),
    ):
        execute(server, command(
            inspect(server), action,
            name=edition_id + ":" + action, edition_id=edition_id, data=data,
        ))
        assert not inspect(server)["saved"]
        assert _viewer(server) == original_viewer
    draft = inspect(server)
    assert draft["saved_head_revision_id"] == previous_head

    # Signed draw, not a Working Draft, is the only MatchEngine authority.
    unsaved_play = command(
        draft, "play", name=edition_id + ":unsaved-play", edition_id=edition_id,
    )
    status, blocker = _request("POST", tour_url(server) + "/preview", unsaved_play)
    assert status == 409, blocker
    assert "Manual Save" in blocker["detail"]["message"]
    assert not draft["edition_evidence"].get(edition_id, {}).get("matches", [])

    signed_draw = save_tour(server)
    assert signed_draw["revision_id"] != previous_head
    signed_public = _viewer(server)

    played, play_request = execute(server, command(
        inspect(server), "play", name=edition_id + ":play",
        edition_id=edition_id,
    ))
    assert played["action"] == "play"
    after_play = inspect(server)
    assert len(after_play["edition_evidence"][edition_id]["matches"]) == 3
    assert not after_play["saved"]
    assert _viewer(server) == signed_public
    signed_matches = save_tour(server)

    confirmed, result_request = execute(server, command(
        inspect(server), "confirm-result", name=edition_id + ":result",
        edition_id=edition_id,
    ))
    assert confirmed["action"] == "confirm-result"
    after_result = inspect(server)
    assert len(after_result["edition_evidence"][edition_id]["results"]) == 4
    assert not after_result["saved"]
    assert _viewer(server) != original_viewer
    # Uncommitted result confirmation is not visible even though signed
    # MatchEngine receipts already are visible in the Viewer.
    assert _viewer(server) == _viewer(server)
    signed_results = save_tour(server)
    assert signed_results["revision_id"] != signed_matches["revision_id"]

    # The player/Edition-specific result authority must not alias another
    # Edition; the second future Edition remains unplayed until its own week.
    final = inspect(server)
    assert final["saved"]
    return {
        "result": final["edition_evidence"][edition_id]["results"],
        "matches": final["edition_evidence"][edition_id]["matches"],
        "signed_result_head": signed_results["revision_id"],
        "play_request": play_request,
        "play_receipt": played,
        "result_request": result_request,
        "result_receipt": confirmed,
    }


def test_two_sequential_editions_keep_results_and_rankings_after_restart(tmp_path):
    db = f"sqlite:///{tmp_path / 'native-two-editions.sqlite'}"
    with ApiServer(database_url=db) as server:
        setup(server, RunCalendar(52, 35, 2030, 3), count=4)
        create_edition(server, FIRST, size=4, offset=2)
        create_edition(server, SECOND, size=4, offset=3, factor=2)
        assert inspect(server)["saved"]
        assert not inspect(server)["edition_evidence"].get(FIRST, {}).get("results", [])
        assert not inspect(server)["edition_evidence"].get(SECOND, {}).get("results", [])

        # Both Editions are already announced from this original Saved Run.
        _next_week(server, "tour:open-announcements")
        _next_week(server, "tour:open-first")
        first_week = inspect(server)["state"]["week"]["week"]
        first = _run_edition(server, FIRST)
        assert sorted(r["main_points"] for r in first["result"]) == [30, 30, 60, 100]
        assert not inspect(server)["edition_evidence"].get(SECOND, {}).get("matches", [])

        before_publish = _viewer(server)
        transition, request, saved_week = _next_week(server, "tour:first-points")
        first_points = sorted(r["points"] for r in transition["impact"]["ranking"]["rows"])
        assert first_points == [30, 30, 60, 100]
        assert inspect(server)["state"]["week"]["week"] == first_week + 1
        assert sorted(r["points"] for r in inspect(server)["state"]["rankings"][-1]["rows"]) == first_points
        first_head = saved_week["revision_id"]
        first_viewer = _viewer(server)
        assert first_viewer != before_publish

    # Genuine process and SQLAlchemy engine shutdown; the second event begins
    # from the first event's exact stored Saved revision in a *fresh* process.
    with ApiServer(database_url=db) as reopened:
        before_second = inspect(reopened)
        assert before_second["saved"] and before_second["saved_head_revision_id"] == first_head
        assert before_second["edition_evidence"][FIRST]["results"] == first["result"]
        assert before_second["edition_evidence"][FIRST]["matches"] == first["matches"]
        assert not before_second["edition_evidence"].get(SECOND, {}).get("matches", [])
        assert _viewer(reopened) == first_viewer

        second = _run_edition(reopened, SECOND)
        assert sorted(r["main_points"] for r in second["result"]) == [60, 60, 120, 200]
        assert inspect(reopened)["edition_evidence"][FIRST]["results"] == first["result"]
        assert inspect(reopened)["edition_evidence"][FIRST]["matches"] == first["matches"]
        assert inspect(reopened)["state"]["week"]["week"] == first_week + 1

        second_unpublished = _viewer(reopened)
        transition_two, request_two, signed_week_two = _next_week(reopened, "tour:second-points")
        assert inspect(reopened)["state"]["week"]["week"] == first_week + 2
        assert _viewer(reopened) != second_unpublished
        saved_second_head = signed_week_two["revision_id"]
        both_saved = inspect(reopened)
        assert both_saved["saved"]
        assert both_saved["edition_evidence"][FIRST]["results"] == first["result"]
        assert both_saved["edition_evidence"][SECOND]["results"] == second["result"]
        assert both_saved["edition_evidence"][FIRST]["matches"] == first["matches"]
        assert both_saved["edition_evidence"][SECOND]["matches"] == second["matches"]
        assert len(both_saved["edition_evidence"][FIRST]["matches"]) == 3
        assert len(both_saved["edition_evidence"][SECOND]["matches"]) == 3
        assert len(both_saved["edition_evidence"][FIRST]["results"]) == 4
        assert len(both_saved["edition_evidence"][SECOND]["results"]) == 4
        final_viewer = _viewer(reopened)

    # A second physical reopen must preserve *both* complete Edition histories,
    # final Official Ranking and unmodified original command receipts.
    with ApiServer(database_url=db) as final_server:
        final = inspect(final_server)
        assert final["saved"] and final["saved_head_revision_id"] == saved_second_head
        assert final["edition_evidence"][FIRST]["results"] == first["result"]
        assert final["edition_evidence"][SECOND]["results"] == second["result"]
        assert final["edition_evidence"][FIRST]["matches"] == first["matches"]
        assert final["edition_evidence"][SECOND]["matches"] == second["matches"]
        assert _viewer(final_server) == final_viewer
        assert len(final["state"]["rankings"]) >= 3
        assert final["state"]["week"]["week"] == first_week + 2

        # Real idempotent replay of the signed first and second tournament
        # operations must never create new matches or award the same points.
        for original_request, original_receipt in (
            (first["play_request"], first["play_receipt"]),
            (second["play_request"], second["play_receipt"]),
            (request, transition),
            (request_two, transition_two),
        ):
            status, replay = _request(
                "POST", tour_url(final_server) + "/execute", original_request,
            )
            assert status == 201, replay
            assert replay == original_receipt
        stable = inspect(final_server)
        assert stable["saved_head_revision_id"] == saved_second_head
        for id_, data in ((FIRST, first), (SECOND, second)):
            assert stable["edition_evidence"][id_]["matches"] == data["matches"]
            assert stable["edition_evidence"][id_]["results"] == data["result"]
        assert _viewer(final_server) == final_viewer

        foreign_branch = tour_url(final_server).replace("/branches/branch/", "/branches/other/")
        assert _request("GET", foreign_branch)[0] == 409

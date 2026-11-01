"""Focused REAL HTTP/SQLite operator journey: Entry -> field -> draw -> play -> points -> Save.

Unlike broad reference/FAX probes this intentionally uses a four-player native
Tour Edition; the full 80-Edition/1,000-player/50-season release proof remains
separate. No mocked MatchEngine, arbitrary SQL repair or policy decisions.
"""
import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_tour_flow import (
    command, create_edition, execute, inspect, save_tour, setup, tour_url,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def _viewer(server):
    status, view = _request("GET", server.base_url + "/viewer/runs/run/calendar-tour")
    assert status == 200, view
    return view


def _transition(server, name):
    execute(server, command(inspect(server), "transition", name=name))
    return save_tour(server)


def test_single_edition_real_operator_save_chain_and_physical_restart(tmp_path):
    """A real saved draw is required before MatchEngine can consume a field."""
    db = f"sqlite:///{tmp_path / 'one-native-edition.sqlite'}"
    edition_id = "operator-cup"
    with ApiServer(database_url=db) as server:
        setup(server, RunCalendar(52, 35, 2030, 3), count=4)
        create_edition(server, edition_id, size=4)
        assert inspect(server)["saved"]

        # The announced Edition is scheduled two weeks after the current week.
        for index in range(2):
            _transition(server, f"operator:approach:{index}")

        initial = inspect(server)
        original_saved_head = initial["saved_head_revision_id"]
        public_before_draft = _viewer(server)
        assert initial["saved"]
        assert not initial["edition_evidence"][edition_id]["matches"]

        # Exactly four real players apply; approval/draw are explicit reviewed
        # commands staged in the same Working Draft, not an implicit Save.
        entrants = [p["player_id"] for p in initial["players"][:4]]
        assert len(entrants) == 4 and len(set(entrants)) == 4
        for action, data in (
            ("submit", {"player_ids": entrants}),
            ("approve", {}),
            ("draw", {}),
        ):
            execute(server, command(
                inspect(server), action, name=f"operator:{action}",
                edition_id=edition_id, data=data,
            ))
            assert not inspect(server)["saved"]
            assert _viewer(server) == public_before_draft

        draft = inspect(server)
        assert draft["saved_head_revision_id"] == original_saved_head
        # A successful Preview or a drafted draw cannot authorize actual play:
        # a separate immutable manual Save of the field/draw is mandatory.
        preview_play = command(
            draft, "play", name="operator:unsaved-play", edition_id=edition_id,
        )
        status, blocked = _request("POST", tour_url(server) + "/preview", preview_play)
        assert status == 409, blocked
        assert "Manual Save" in blocked["detail"]["message"]
        assert not inspect(server)["edition_evidence"][edition_id]["matches"]
        assert _viewer(server) == public_before_draft

        signed_draw = save_tour(server)
        assert signed_draw["revision_id"] != original_saved_head
        public_after_draw = _viewer(server)
        assert public_after_draw != public_before_draft

        # The production rally-by-rally MatchEngine plays two semifinals and
        # the final. Points/results still require a separately reviewed close.
        play, original_play_request = execute(server, command(
            inspect(server), "play", name="operator:play", edition_id=edition_id,
        ))
        assert play["action"] == "play"
        played = inspect(server)
        assert len(played["edition_evidence"][edition_id]["matches"]) == 3
        assert not played["saved"]
        assert _viewer(server) == public_after_draw
        match_save = save_tour(server)

        confirmed, _ = execute(server, command(
            inspect(server), "confirm-result", name="operator:result",
            edition_id=edition_id,
        ))
        assert confirmed["action"] == "confirm-result"
        closed = inspect(server)
        assert len(closed["edition_evidence"][edition_id]["results"]) == 4
        assert not closed["saved"]
        assert _viewer(server) != public_after_draw or not closed["saved"]
        result_save = save_tour(server)
        assert result_save["revision_id"] != match_save["revision_id"]

        # Only the next Official Week transition publishes points. Confirm
        # actual FAX-style authored 4-player table, not a synthetic ranking.
        week_before = inspect(server)["state"]["week"]["week"]
        transition, transition_request = execute(server, command(
            inspect(server), "transition", name="operator:points-week",
        ))
        points = sorted(row["points"] for row in transition["impact"]["ranking"]["rows"])
        assert points == [30, 30, 60, 100]
        assert not inspect(server)["saved"]
        last_saved = save_tour(server)
        verified = inspect(server)
        assert verified["state"]["week"]["week"] == week_before + 1
        assert verified["saved_head_revision_id"] == last_saved["revision_id"]
        assert verified["saved"]
        assert sorted(row["points"] for row in verified["state"]["rankings"][-1]["rows"]) == points
        assert len(verified["edition_evidence"][edition_id]["matches"]) == 3
        assert len(verified["edition_evidence"][edition_id]["results"]) == 4
        public_final = _viewer(server)
        assert public_final != public_after_draw

    # A physically reopened app + SQLite connection must still preserve the
    # same exact Saved revision, authentic result evidence and published points.
    with ApiServer(database_url=db) as reopened:
        actual = inspect(reopened)
        assert actual["saved"]
        assert actual["saved_head_revision_id"] == last_saved["revision_id"]
        assert actual["edition_evidence"][edition_id]["matches"] == verified["edition_evidence"][edition_id]["matches"]
        assert actual["edition_evidence"][edition_id]["results"] == verified["edition_evidence"][edition_id]["results"]
        assert sorted(row["points"] for row in actual["state"]["rankings"][-1]["rows"]) == [30, 30, 60, 100]
        assert _viewer(reopened) == public_final

        # An original reviewed play/transition must remain exactly replayable,
        # never produce a duplicate match, award or Saved revision on restart.
        for original, receipt in (
            (original_play_request, play),
            (transition_request, transition),
        ):
            status, replayed = _request(
                "POST", tour_url(reopened) + "/execute", original,
            )
            assert status == 201, replayed
            assert replayed == receipt
        stable = inspect(reopened)
        assert stable["saved_head_revision_id"] == last_saved["revision_id"]
        assert stable["edition_evidence"][edition_id]["matches"] == actual["edition_evidence"][edition_id]["matches"]
        assert stable["edition_evidence"][edition_id]["results"] == actual["edition_evidence"][edition_id]["results"]
        assert _viewer(reopened) == public_final

        assert _request(
            "GET", tour_url(reopened).replace("/branches/branch/", "/branches/foreign/"),
        )[0] == 409

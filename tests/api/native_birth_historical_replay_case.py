"""Actual HTTP checks for the old frozen final after native birthday admission."""

from beta_engine.domain.players.calendar_native_sporting_checkpoint import (
    CalendarNativeSportingCheckpoint,
)
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint
from beta_engine.infrastructure.db.models import (
    CalendarPlayerSportingCheckpointModel,
    PlayerHealthWeekStateModel,
)
from tests.api.test_calendar_tour_flow import inspect, tour_url
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import _request


def replay_url(server):
    return tour_url(server).replace(
        "/calendar-tour",
        "/authoritative-simulation/calendar-continuation/before-birthday:final/replay",
    )


def exercise_historical_replay(server, repo, path):
    before = _dump(path)
    code, expected = _request("GET", replay_url(server))
    assert code == 200, expected
    assert expected["exact_replay"]
    assert expected["historical_owner_scope"] == "pre_native_birth_checkpoint"
    assert len(expected["historical_root_checkpoint_fingerprint"]) == 64
    assert len(expected["match_source_checkpoint_fingerprint"]) == 64
    assert _dump(path) == before
    with repo._session_factory() as session:
        state = load_checkpoint(session, run_id="run", branch_id="branch")
        assert isinstance(state, CalendarNativeSportingCheckpoint)
    with repo._session_factory.begin() as session:
        row = session.get(
            PlayerHealthWeekStateModel, ("run", "branch", state.week.ordinal)
        )
        health_original = (row.payload_json, row.fingerprint)
        row.fingerprint = "0" * 64
    try:
        before = _dump(path)
        assert _request("GET", replay_url(server)) == (200, expected)
        # Replaying a frozen match does NOT grant today's corrupt owner any
        # readiness or permission to mutate the Tour.
        assert _request("GET", tour_url(server))[0] == 409
        assert _dump(path) == before
    finally:
        with repo._session_factory.begin() as session:
            row = session.get(
                PlayerHealthWeekStateModel, ("run", "branch", state.week.ordinal)
            )
            row.payload_json, row.fingerprint = health_original

    root = state.source_checkpoint.model_copy(
        update={"source_saved_head": "forged-historical-origin"}
    )
    entry = state.native_weeks[0]
    changed = entry.model_copy(
        update={
            "advance": entry.advance.model_copy(
                update={"source_checkpoint_fingerprint": root.fingerprint}
            )
        }
    )
    forged = state.model_copy(
        update={"source_checkpoint": root, "native_weeks": (changed,)}
    )
    # All changed outer hashes and structural links agree. Only actual Signed
    # ownership may authorize the selected historical root.
    forged = CalendarNativeSportingCheckpoint.model_validate_json(
        forged.model_dump_json()
    )
    with repo._session_factory.begin() as session:
        row = session.get(CalendarPlayerSportingCheckpointModel, ("run", "branch"))
        original = (row.payload_json, row.fingerprint)
        row.payload_json, row.fingerprint = forged.model_dump_json(), forged.fingerprint
    try:
        before = _dump(path)
        code, rejected = _request("GET", replay_url(server))
        assert code == 409, rejected
        assert "actual Signed owner" in str(rejected)
        assert _dump(path) == before
    finally:
        with repo._session_factory.begin() as session:
            row = session.get(CalendarPlayerSportingCheckpointModel, ("run", "branch"))
            row.payload_json, row.fingerprint = original
    assert _request("GET", replay_url(server)) == (200, expected)
    assert inspect(server)["saved"]
    return expected

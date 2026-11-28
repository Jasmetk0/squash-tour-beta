"""Real HTTP/SQLite: the Tour read decodes its Saved checkpoint without a JSON round trip.

Every case runs the production FastAPI/SQLite stack on a copy of the genuinely
produced Saved v2 ``prepared_slots_v2`` Run (real MatchEngine slots, Saved
revisions, Tour transitions). The bounded value caches are shrunk so that every
warm read decodes, as on the nightly 1,000-player W9-W15 snapshots whose
110-200 MB checkpoints always exceed the 64 MiB budget. Each state's complete
inspection is compared with the original ``json.dumps`` round trip, forced on
the same server and the same SQLite snapshot.
"""

import copy
import json

import pytest

from tests.api.test_calendar_global_slots import copy_database
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, tour_url
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


@pytest.fixture
def oversize(monkeypatch):
    """Emulate the long-history regime: no checkpoint fits the value caches."""
    from beta_engine.infrastructure.db import native_fork_source_projection as projection

    monkeypatch.setattr(projection, "MAX_GLOBAL_TOUR_BYTES", 4096)
    monkeypatch.setattr(projection, "MAX_LIVE_COMPONENT_BYTES", 4096)


@pytest.fixture
def decoded(monkeypatch):
    """Count decodes that started from the decoded body; allow forcing the original."""
    from beta_engine.infrastructure.db import calendar_sporting_checkpoint as sporting

    seen = {"decoded": 0, "raw": 0, "round_trip_forced": False}
    parse, guard = sporting.parse_checkpoint_json, sporting.decoded_checkpoint_body

    def counted(raw, **kwargs):
        seen["decoded" if kwargs.get("_decoded") is not None else "raw"] += 1
        return parse(raw, **kwargs)

    def maybe_forced(body):
        return False if seen["round_trip_forced"] else guard(body)

    monkeypatch.setattr(sporting, "parse_checkpoint_json", counted)
    monkeypatch.setattr(sporting, "decoded_checkpoint_body", maybe_forced)
    return seen


def _both(server, seen):
    """Optimized and original inspection of the same unchanged snapshot."""
    before = seen["decoded"]
    optimized = inspect(server)
    used = seen["decoded"] - before
    seen["round_trip_forced"] = True
    try:
        original = inspect(server)
    finally:
        seen["round_trip_forced"] = False
    assert seen["decoded"] - before == used, "the forced read must not use the new path"
    assert json.dumps(optimized, sort_keys=False) == json.dumps(original, sort_keys=False)
    return optimized, used


def _rows(path):
    import sqlite3

    with sqlite3.connect(path) as db:
        return {table: db.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall()
                for table in ("calendar_player_sporting_checkpoints", "calendar_tour_authorities",
                              "player_lifecycle_week_states", "branch_saved_revisions",
                              "branch_working_drafts", "branch_revision_audit_events")}


def test_every_read_state_matches_the_original_round_trip(tmp_path, prepared_slots_v2, oversize, decoded):
    path = tmp_path / "decode.db"
    copy_database(prepared_slots_v2, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        uses = []
        inspect(server)  # the cold read reuses its own lineage replay instead
        saved, used = _both(server, decoded)
        uses.append(used)
        assert saved["saved"]
        rows = _rows(path)
        _both(server, decoded)  # the identical repeated read
        assert _rows(path) == rows, "a read must not write"
        # Working Draft change that keeps the sporting owner (Tour only).
        week = saved["state"]["week"]
        execute(server, command(saved, "create-edition", name="decode:create", data={
            "schema_version": "calendar_tournament_edition.v2", "simulation_seed": 17,
            "edition_id": "decode-late", "name": "decode-late",
            "week": {**week, "week": week["week"] + 2},
            "announcement_week": {**week, "week": week["week"] + 1},
            "start_slot": 1, "main_entrant_count": 4, "ranked": True, "validity_weeks": 52,
            "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
        }))
        draft, used = _both(server, decoded)
        uses.append(used)
        assert not draft["saved"] and draft["sporting_saved"]
        save_tour(server)
        _, used = _both(server, decoded)
        uses.append(used)
        # Week boundary: the live sporting owner now differs from Saved.
        execute(server, command(inspect(server), "transition", name="decode:transition"))
        moved, used = _both(server, decoded)
        uses.append(used)
        assert not moved["sporting_saved"]
        assert moved["state"]["week"]["week"] == week["week"] + 1
        save_tour(server)
        final, used = _both(server, decoded)
        uses.append(used)
        assert final["saved"]
    # Every warm read above decoded the Saved checkpoint from its body.
    assert all(count >= 1 for count in uses), uses
    with ApiServer(database_url=f"sqlite:///{path}") as restarted:
        after, _ = _both(restarted, decoded)
    assert after == final


def test_a_changed_decoded_body_still_fails_the_unchanged_hash_check(tmp_path, prepared_slots_v2, oversize, decoded):
    from beta_engine.infrastructure.db.calendar_standalone_match_state import (
        decode_prevalidated_calendar_sources,
    )

    path = tmp_path / "reject.db"
    copy_database(prepared_slots_v2, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        view = inspect(server)
        repo = server.app.state.runtime.repository
        payload = repo.get_branch_saved_revision(revision_id=view["saved_head_revision_id"]).payload
        args = {"run_id": "run", "branch_id": "branch", "_global_value_proofs": {}, "_repository": repo}
        before = decoded["decoded"]
        _, checkpoint, _ = decode_prevalidated_calendar_sources(copy.deepcopy(payload), **args)
        assert decoded["decoded"] == before + 1
        assert checkpoint.fingerprint == view["checkpoint_fingerprint"]

        def changed(mutate):
            body = copy.deepcopy(payload)
            mutate(body["content"]["calendar_player_sporting_checkpoint"]["state"])
            return body

        def form(state):
            # One real numeric sporting value inside the stored competition root.
            players = state["competition_root"]["players"]
            players[0]["current_form"] = players[0]["current_form"] - 1

        # A value every validator accepts: only the unchanged hash check sees it.
        with pytest.raises(ValueError, match="scope/hash"):
            decode_prevalidated_calendar_sources(changed(form), **args)
        with pytest.raises(ValueError, match="foreign historical root"):
            decode_prevalidated_calendar_sources(
                changed(lambda state: state.update(run_id="other-run")), **args)
        # A real Saved row cannot be swapped under the GET either: the
        # physical lineage gate rejects it before any decode.
        assert _request("GET", tour_url(server))[0] == 200


def test_an_unusual_top_level_body_keeps_the_original_round_trip(tmp_path, prepared_slots_v2, oversize, decoded):
    from beta_engine.infrastructure.db.calendar_standalone_match_state import (
        decode_prevalidated_calendar_sources,
    )

    path = tmp_path / "unusual.db"
    copy_database(prepared_slots_v2, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        view = inspect(server)
        repo = server.app.state.runtime.repository
        payload = copy.deepcopy(repo.get_branch_saved_revision(revision_id=view["saved_head_revision_id"]).payload)
        state = payload["content"]["calendar_player_sporting_checkpoint"]["state"]
        state["events"] = tuple(state["events"])  # a tuple only a round trip turns into a list
        before, raw = decoded["decoded"], decoded["raw"]
        _, checkpoint, _ = decode_prevalidated_calendar_sources(
            payload, run_id="run", branch_id="branch", _global_value_proofs={}, _repository=repo)
        assert decoded["decoded"] == before and decoded["raw"] > raw
        assert checkpoint.fingerprint == view["checkpoint_fingerprint"]

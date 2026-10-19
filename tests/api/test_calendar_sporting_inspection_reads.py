"""Real HTTP/SQLite: authenticated read reuse does not trust damaged live rows."""
import json
from collections import Counter

import pytest
from sqlalchemy import select

from beta_engine.application import calendar_opening_knockout_service as opening
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db import calendar_sporting_checkpoint as checkpoint
from beta_engine.infrastructure.db.models import CalendarStandaloneMatchModel
from tests.api.test_calendar_opening_knockout_flow import base
from tests.api.test_calendar_population_sporting_checkpoint import prepare, play, save
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("width", [52, 80])
def test_signed_read_sources_are_loaded_once_but_tampered_actual_bytes_still_fail(tmp_path, monkeypatch, width):
    path = tmp_path / "read-reuse.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo, head = prepare(server, RunCalendar(width, width, 2030, 3), count=8)
        counts = Counter()
        for module, name in ((opening, "load_match_rows"), (checkpoint, "load_checkpoint")):
            original = getattr(module, name)

            def counted(*args, _name=name, _original=original, **kwargs):
                counts[_name] += 1
                return _original(*args, **kwargs)

            monkeypatch.setattr(module, name, counted)

        def read(url, *, status=200):
            counts.clear()
            code, response = _request("GET", url)
            assert code == status, response
            if status == 200:
                assert counts == {"load_match_rows": 1, "load_checkpoint": 1}
            return response

        first = read(base(server))
        assert first["knockout"] is None and first["population_sporting_checkpoint"] is None
        counts.clear()
        code, preview = _request("POST", base(server) + "/canonical-preview", {
            "expected_saved_head": head,
            "expected_initial_world_fingerprint": first["initial_world_fingerprint"],
            "entrant_ids": first["player_ids"][:4],
        })
        assert code == 200, preview
        assert counts == {"load_match_rows": 1, "load_checkpoint": 1}

        receipt, _ = play(server, head)
        unsaved = read(base(server))
        assert unsaved["knockout"] == receipt["knockout"] and not unsaved["saved"]
        stored = save(server, receipt)
        signed = read(base(server))
        assert signed["saved"] and signed["knockout"] == receipt["knockout"]
        fp = signed["population_sporting_checkpoint"]["fingerprint"]
        player_id = signed["player_ids"][0]
        player_url = (base(server) + "/sporting-checkpoint/players/" + player_id
            + "?expected_saved_head=" + stored["revision_id"]
            + "&expected_checkpoint_fingerprint=" + fp)
        player = read(player_url)
        assert player["player"]["player_id"] == player_id
        before = _dump(path)
        assert read(base(server)) == signed
        assert _dump(path) == before, "GET must not write or backfill state"
        assert _request("GET", player_url.replace(fp, "f" * 64))[0] == 409

        with repo._session_factory() as session:
            row = session.scalar(select(CalendarStandaloneMatchModel))
            original_json, original_fp = row.payload_json, row.fingerprint
            match_id = row.match_id
        for rehash in (False, True):
            with repo._session_factory.begin() as session:
                row = session.scalar(select(CalendarStandaloneMatchModel))
                damaged = json.loads(original_json)
                damaged["audit_reason"] += " damaged live bytes"
                row.payload_json = json.dumps(damaged)
                row.fingerprint = canonical_hash(damaged) if rehash else original_fp
            damaged_db = _dump(path)
            read(base(server), status=409)
            read(player_url, status=409)
            assert _dump(path) == damaged_db, "Rejected reads must not repair tampered data"
            with repo._session_factory.begin() as session:
                row = session.scalar(select(CalendarStandaloneMatchModel).where(
                    CalendarStandaloneMatchModel.match_id == match_id))
                row.payload_json, row.fingerprint = original_json, original_fp
            assert read(base(server)) == signed
        assert repo.verify_branch_saved_revision_hash(revision_id=stored["revision_id"])

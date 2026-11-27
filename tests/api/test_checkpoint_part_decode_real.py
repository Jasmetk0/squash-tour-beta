"""Real played v13 checkpoints: part reuse is the original strict decode, bit for bit.

``prepared_slots_v2`` is a genuinely produced Saved v2 Run whose live and Saved
checkpoints hold played global slots (complete MatchResults with rally,
timeline and stamina logs). The part cache must return values equal to the
original strict decode, primed fingerprints equal to the full canonical hash,
and the same HTTP/SQLite outcome as with the cache bypassed.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments import calendar_global_slots as slots
from beta_engine.infrastructure.db import checkpoint_part_decode as parts
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import parse_checkpoint_json
from tests.api.test_calendar_global_slots import copy_database
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour
from tests.api.test_saved_revision_history_api import ApiServer

pytestmark = pytest.mark.smoke


def _live_row(path):
    with sqlite3.connect(path) as db:
        return db.execute("SELECT payload_json, fingerprint FROM calendar_player_sporting_checkpoints "
                          "WHERE run_id='run' AND branch_id='branch'").fetchone()


def _bypass(monkeypatch):
    def original(text, parse):
        return parse(text), None
    monkeypatch.setattr(parts, "decode", original)


@pytest.fixture(autouse=True)
def empty_cache():
    parts.clear()
    with slots._CONTENT_CHAINS_LOCK:
        slots._CONTENT_CHAINS.clear()
    yield
    parts.clear()


def test_reused_parts_equal_the_original_strict_decode_and_full_hash(prepared_slots_v2, monkeypatch):
    raw, declared = _live_row(prepared_slots_v2)
    body = json.loads(raw)
    assert body["schema_version"] == "calendar_sporting_checkpoint.v13" and len(body["events"]) >= 4
    with monkeypatch.context() as patch:
        _bypass(patch)
        original = parse_checkpoint_json(raw)
    expected_bytes = original.model_dump_json()
    expected_hash = canonical_hash(original.model_dump(mode="json"))
    assert expected_hash == declared
    with slots.global_replay_projection_scope():
        cold = parse_checkpoint_json(raw)
        warm = parse_checkpoint_json(None, _body=body)
        primed = (cold.fingerprint, warm.fingerprint)
    assert parts.stats()["hits"] == parts.stats()["misses"] == 1 + len(body["events"])
    for value in (cold, warm):
        assert value.model_dump_json() == expected_bytes and value == original
    assert primed == (expected_hash, expected_hash)
    assert warm is not cold and all(a is not b for a, b in zip(warm.events, cold.events))
    # Outside a private replay scope nothing is primed: the property computes.
    assert parse_checkpoint_json(raw).fingerprint == expected_hash


def test_appended_and_changed_histories_reuse_only_identical_parts(prepared_slots_v2):
    raw, _ = _live_row(prepared_slots_v2)
    body = json.loads(raw)
    shorter = {**body, "events": body["events"][:-1]}
    with slots.global_replay_projection_scope():
        base = parse_checkpoint_json(None, _body=shorter)
        base_hash = base.fingerprint
        full = parse_checkpoint_json(None, _body=body)       # one appended event
        full_hash = full.fingerprint
    assert base_hash == canonical_hash(base.model_dump(mode="json"))
    assert full_hash == canonical_hash(full.model_dump(mode="json"))
    assert parts.stats()["misses"] == 1 + len(body["events"])   # only the new event was parsed
    # A changed byte anywhere in one historical event is that event's own parse.
    changed = json.loads(raw)
    target = next(i for i, e in enumerate(changed["events"]) if "GlobalSlot" in str(type(full.events[i])))
    text = json.dumps(changed["events"][target])
    for old, new in (('"rally_number": 1,', '"rally_number": 2,'), ('"winner_games": 11', '"winner_games": 12'),
                     ('"rally_number": 1}', '"rally_number": 2}')):
        if old in text:
            tampered = text.replace(old, new, 1)
            break
    else:
        pytest.fail("no played rally to tamper with")
    assert tampered != text
    changed["events"][target] = json.loads(tampered)
    misses = parts.stats()["misses"]
    with pytest.raises(ValueError):
        parse_checkpoint_json(None, _body=changed)
    assert parts.stats()["misses"] == misses       # rejected, never retained
    with slots.global_replay_projection_scope():
        again = parse_checkpoint_json(raw)
        assert again.fingerprint == full_hash


def _play_and_save(tmp_path, source, label, monkeypatch, *, bypass):
    path = tmp_path / f"{label}.db"
    copy_database(source, path)
    with monkeypatch.context() as patch:
        if bypass:
            _bypass(patch)
        from beta_engine.api import deps
        import itertools
        import uuid
        sequence = itertools.count()
        patch.setattr(deps, "uuid4", lambda: uuid.uuid5(uuid.NAMESPACE_URL, f"part-decode:{next(sequence)}"))
        with ApiServer(database_url=f"sqlite:///{path}") as server:
            views = [inspect(server)]
            view = views[-1]
            if view["next_slot"] is not None:
                execute(server, command(view, "next-slot", name="part-decode-slot"))
            else:
                execute(server, command(view, "transition", name="part-decode-transition"))
            views.append(inspect(server))
            save_tour(server)
            views.extend([inspect(server), inspect(server)])
        with ApiServer(database_url=f"sqlite:///{path}") as server:
            views.append(inspect(server))
    with sqlite3.connect(path) as db:
        rows = {
            "checkpoint": db.execute("SELECT * FROM calendar_player_sporting_checkpoints ORDER BY 1, 2").fetchall(),
            "revisions": db.execute("SELECT revision_id, sequence, content_hash, payload_json "
                                    "FROM branch_saved_revisions ORDER BY sequence").fetchall(),
            "audit": db.execute("SELECT audit_event_id, event_kind, payload_json "
                                "FROM branch_revision_audit_events ORDER BY rowid").fetchall(),
        }
    return views, rows


def test_http_sqlite_outcome_is_identical_with_and_without_part_reuse(tmp_path, prepared_slots_v2, monkeypatch):
    expected = _play_and_save(tmp_path, prepared_slots_v2, "bypassed", monkeypatch, bypass=True)
    parts.clear()
    actual = _play_and_save(tmp_path, prepared_slots_v2, "reused", monkeypatch, bypass=False)
    # This small Run fits the existing whole-value caches, so parts are
    # decoded (misses) rather than reused; the outcome must be identical.
    assert parts.stats()["misses"] > 0
    assert actual[0] == expected[0]
    assert actual[1] == expected[1]

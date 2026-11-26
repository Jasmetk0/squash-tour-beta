"""Week Transition performance changes keep the exact canonical values.

Component tests on a genuinely produced v13 checkpoint (real HTTP/SQLite
global slots and MatchEngine via ``prepared_slots``); they compare with the
ordinary full canonical hash computed outside any private scope.
"""

import pytest

from tests.api.test_calendar_global_slots import copy_database
from tests.api.test_calendar_tour_flow import command, execute, inspect
from tests.api.test_saved_revision_history_api import ApiServer

pytestmark = pytest.mark.smoke


@pytest.fixture
def actual_checkpoint(tmp_path, prepared_slots):
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import parse_checkpoint_json
    from beta_engine.infrastructure.db.models import CalendarPlayerSportingCheckpointModel

    path = tmp_path / "appended-checkpoint-hash.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        execute(server, command(inspect(server), "next-match", name="appended-first-result"))
        with server.app.state.runtime.repository._session_factory() as session:
            raw = session.get(CalendarPlayerSportingCheckpointModel, ("run", "branch")).payload_json
    actual = parse_checkpoint_json(raw)
    assert len(actual.events) >= 2
    return actual


def _full(value):
    from beta_engine.domain.run_packages import canonical_hash

    return canonical_hash(value.model_dump(mode="json"))


def _clear():
    from beta_engine.domain.tournaments import calendar_global_slots as slots

    with slots._APPENDABLE_CHECKPOINTS_LOCK:
        slots._APPENDABLE_CHECKPOINTS.clear()


def _count_body_encodings(monkeypatch, slots):
    calls = []
    original = slots._canonical_bytes

    def counted(body):
        if isinstance(body, dict):
            calls.append(body)
        return original(body)

    monkeypatch.setattr(slots, "_canonical_bytes", counted)
    return calls


def test_appended_checkpoint_hash_is_the_full_canonical_hash(actual_checkpoint, monkeypatch):
    from beta_engine.domain.tournaments import calendar_global_slots as slots

    actual = actual_checkpoint
    previous = actual.model_copy(update={"events": actual.events[:-1]})
    expected = _full(actual)
    for run_id, branch_id in (("run", "branch"), ("běh/漢", 'větev "🟢"')):
        prior = previous.model_copy(update={"run_id": run_id, "branch_id": branch_id})
        successor = prior.model_copy(update={"events": prior.events + (actual.events[-1],)})
        wanted = expected if run_id == "run" else _full(successor)
        _clear()
        # Cold: the prefix is encoded once and checked against its own digest;
        # warm (a new private scope, e.g. the next request): only the new event.
        calls = _count_body_encodings(monkeypatch, slots)
        for warm in (False, True):
            calls.clear()
            with slots.global_replay_projection_scope():
                assert slots.appended_checkpoint_fingerprint(prior, successor) == wanted
                assert successor.fingerprint == wanted
            if warm:
                # Only the appended event is encoded; the history is not.
                assert len(calls) == 1
        monkeypatch.undo()
        assert slots._APPENDABLE_CHECKPOINTS[_full(prior)][2] == len(prior.events)
        assert slots._APPENDABLE_CHECKPOINTS[wanted][2] == len(successor.events)
    # A chain built by the ordinary incremental fingerprint also seeds it.
    _clear()
    with slots.global_replay_projection_scope():
        assert previous.fingerprint == _full(previous)
    calls = _count_body_encodings(monkeypatch, slots)
    with slots.global_replay_projection_scope():
        assert slots.appended_checkpoint_fingerprint(previous, actual) == expected
    assert len(calls) == 1


def test_appended_checkpoint_hash_never_extends_an_unproven_digest(actual_checkpoint):
    from beta_engine.domain.tournaments import calendar_global_slots as slots

    actual = actual_checkpoint
    previous = actual.model_copy(update={"events": actual.events[:-1]})
    expected = _full(actual)
    _clear()
    with slots.global_replay_projection_scope():
        # A primed predecessor digest that its content does not have is never
        # extended or recorded; the ordinary full hash is returned instead.
        slots._prime_private_fingerprint(previous, "0" * 64)
        assert slots.appended_checkpoint_fingerprint(previous, actual) == expected
    assert "0" * 64 not in slots._APPENDABLE_CHECKPOINTS
    # A recorded state for another event count/suffix is not reused.
    with slots._APPENDABLE_CHECKPOINTS_LOCK:
        state, suffix, count = slots._APPENDABLE_CHECKPOINTS[expected]
    assert slots._appendable_state(expected, count + 1, suffix) is None
    assert slots._appendable_state(expected, count, suffix + b" ") is None


def test_appended_checkpoint_hash_falls_back_outside_its_exact_relation(actual_checkpoint):
    from beta_engine.domain.tournaments import calendar_global_slots as slots

    actual = actual_checkpoint
    first, *rest = actual.events
    previous = actual.model_copy(update={"events": actual.events[:-1]})
    cases = {
        # Two appended events, a replaced (equal but distinct) prefix event,
        # a different root object and a changed Branch identity.
        "two": (actual.model_copy(update={"events": actual.events[:-2]}), actual),
        "replaced": (previous, actual.model_copy(update={"events": (first.model_copy(), *rest)})),
        "root": (previous, actual.model_copy(update={
            "competition_root": actual.competition_root.model_copy()})),
        "branch": (previous, actual.model_copy(update={"branch_id": "other"})),
    }
    for name, (prior, successor) in cases.items():
        _clear()
        with slots.global_replay_projection_scope():
            assert slots.appended_checkpoint_fingerprint(prior, successor) == _full(successor), name
        assert _full(prior) not in slots._APPENDABLE_CHECKPOINTS, name
    # Outside a private scope, and while value hashes are being collected,
    # the ordinary property is used unchanged.
    _clear()
    assert slots.appended_checkpoint_fingerprint(previous, actual) == _full(actual)
    assert not slots._APPENDABLE_CHECKPOINTS
    with slots.global_replay_projection_scope():
        slots._replay_projections.get()["collect_checkpoint_value_hashes"] = True
        assert slots.appended_checkpoint_fingerprint(previous, actual) == _full(actual)

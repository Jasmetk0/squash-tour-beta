"""The v13 checkpoint parser may start from a decoded body only when that is exact.

Pure parser contract (no database): ``parse_checkpoint_json(None, _decoded=body)``
must equal ``parse_checkpoint_json(json.dumps(body))`` whenever
``decoded_checkpoint_body(body)`` accepts it, and every body it rejects keeps
the original JSON round trip in the Tour context decoder.
"""

import json

import pytest

from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
    decoded_checkpoint_body,
    parse_checkpoint_json,
)

pytestmark = pytest.mark.pr_critical

V13 = "calendar_sporting_checkpoint.v13"


def _body(**top):
    return {"schema_version": V13, "run_id": "run", "branch_id": "branch",
            "competition_root": {"schema_version": "x"}, "events": [], **top}


def test_accepts_only_bodies_whose_top_level_survives_a_json_round_trip():
    assert decoded_checkpoint_body(_body())
    for value in ((), ({"schema_version": "x"},)):
        assert not decoded_checkpoint_body(_body(events=value))
    assert not decoded_checkpoint_body({**_body(), 1: "non-string key"})
    assert not decoded_checkpoint_body(_body(run_id=("run",)))
    assert not decoded_checkpoint_body(_body(run_id=["run"]))
    assert not decoded_checkpoint_body(_body(extra={"nested": True}))
    assert not decoded_checkpoint_body(_body(schema_version="calendar_sporting_checkpoint.v12"))
    assert not decoded_checkpoint_body([_body()])

    class Key(str):
        pass

    assert not decoded_checkpoint_body({**_body(), Key("subclass"): 1})


def test_a_round_trip_would_change_exactly_what_the_guard_rejects():
    # Regression for the equivalence argument itself: the rejected top-level
    # shapes are precisely those json.loads(json.dumps(body)) changes.
    for body in (_body(events=()), {**_body(), 1: "x"}, _body(run_id=("run",))):
        assert json.loads(json.dumps(body)) != body
    accepted = _body(note=None, count=3, ratio=-0.0, flag=True)
    assert decoded_checkpoint_body(accepted)
    assert json.loads(json.dumps(accepted)) == accepted


def test_decoded_body_is_refused_with_raw_text_or_an_unsupported_body():
    with pytest.raises(TypeError):
        parse_checkpoint_json(json.dumps(_body()), _decoded=_body())
    with pytest.raises(TypeError):
        parse_checkpoint_json(None, _decoded=_body(events=()))
    with pytest.raises(TypeError):
        parse_checkpoint_json(None, _decoded={"schema_version": "calendar_sporting_checkpoint.v12"})


@pytest.mark.parametrize("body", [
    _body(competition_root=[]),                     # root must be an object
    _body(events=[["not", "an", "event"]]),         # every event must be an object
    _body(competition_root={"schema_version": "unknown"}),
])
def test_invalid_bodies_fail_identically_on_both_paths(body):
    with pytest.raises((TypeError, ValueError)) as original:
        parse_checkpoint_json(json.dumps(body))
    with pytest.raises((TypeError, ValueError)) as decoded:
        parse_checkpoint_json(None, _decoded=body)
    assert type(decoded.value) is type(original.value)

"""The Saved InitialWorld parse scope of one transition preparation (#1925)."""

import pytest

from beta_engine.infrastructure.db import initial_world_state as iws


class _World:
    schema_version = "initial_world_state.v1"

    def __init__(self, run_id, branch_id, fingerprint):
        self.run_id, self.branch_id, self.fingerprint = run_id, branch_id, fingerprint


def _payload(state):
    return {"content": {iws.INITIAL_WORLD_COMPONENT_KEY: {"fingerprint": "f", "state": state}}}


@pytest.fixture
def parses(monkeypatch):
    seen = []

    def parse(raw):
        seen.append(raw)
        if '"broken"' in raw:
            raise ValueError("corrupt InitialWorld")
        return _World("run", "branch", "f")

    monkeypatch.setattr(iws, "parse_initial_world_json", parse)
    return seen


def test_outside_the_scope_every_load_parses(parses):
    payload = _payload({"x": 1})
    first = iws.load_saved_initial_world(payload, run_id="run", branch_id="branch")
    second = iws.load_saved_initial_world(payload, run_id="run", branch_id="branch")
    assert len(parses) == 2 and first is not second


def test_inside_the_scope_identical_text_is_parsed_once_and_checks_still_run(parses):
    payload = _payload({"x": 1})
    with iws.saved_initial_world_parse_scope():
        first = iws.load_saved_initial_world(payload, run_id="run", branch_id="branch")
        again = iws.load_saved_initial_world(_payload({"x": 1}), run_id="run", branch_id="branch")
        assert first is again and len(parses) == 1
        # The reused parse is still checked against THIS call's identity/fingerprint.
        with pytest.raises(ValueError, match="identity or fingerprint"):
            iws.load_saved_initial_world(payload, run_id="run", branch_id="other")
        wrong = _payload({"x": 1})
        wrong["content"][iws.INITIAL_WORLD_COMPONENT_KEY]["fingerprint"] = "g"
        with pytest.raises(ValueError, match="identity or fingerprint"):
            iws.load_saved_initial_world(wrong, run_id="run", branch_id="branch")
        # Different bytes are a different input.
        iws.load_saved_initial_world(_payload({"x": 2}), run_id="run", branch_id="branch")
        assert len(parses) == 2
    # Nothing survives the scope.
    iws.load_saved_initial_world(payload, run_id="run", branch_id="branch")
    assert len(parses) == 3


def test_a_failed_parse_is_never_remembered_and_nested_scopes_share(parses):
    broken = _payload({"broken": True})
    with iws.saved_initial_world_parse_scope():
        for _ in range(2):
            with pytest.raises(ValueError, match="corrupt"):
                iws.load_saved_initial_world(broken, run_id="run", branch_id="branch")
        assert len(parses) == 2
        iws.load_saved_initial_world(_payload({"x": 1}), run_id="run", branch_id="branch")
        with iws.saved_initial_world_parse_scope():
            iws.load_saved_initial_world(_payload({"x": 1}), run_id="run", branch_id="branch")
        iws.load_saved_initial_world(_payload({"x": 1}), run_id="run", branch_id="branch")
        assert len(parses) == 3

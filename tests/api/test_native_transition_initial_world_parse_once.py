"""Real HTTP/SQLite: a native transition parses its Saved InitialWorld once (#1925).

The Week/Season Transition candidate loads Saved lifecycle and Health, and each
loader authenticated the same Saved InitialWorld again (under Master v87 every
parse recomputes the whole opening Turn Pro evidence). This compares the actual
production Preview with the original three parses against the scoped single
parse, byte for byte, and Executes the ORIGINAL Preview fingerprint with the new
path: a birth week, a following week without births and a Season Transition,
under the historical policy and under v87 with real Turn Pro decisions. Retries,
explicit Save, physical restart and continued Signed replay are included.
"""

import contextlib
import json

import pytest

from beta_engine.application import calendar_initial_world
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db import initial_world_state
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_native_turn_pro_v87_birth import _eager
from tests.api.test_calendar_tour_flow import command, inspect, save_tour, setup, tour_url
from tests.api.test_calendar_tour_turn_pro_v87_flow import _v87_population
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def _counted(monkeypatch):
    counts = {"parse": 0, "opening": 0}
    parse = initial_world_state.parse_initial_world_json
    opening = calendar_initial_world.initial_turn_pro_evidence

    def counted_parse(raw):
        counts["parse"] += 1
        return parse(raw)

    def counted_opening(**kwargs):
        counts["opening"] += 1
        return opening(**kwargs)

    monkeypatch.setattr(initial_world_state, "parse_initial_world_json", counted_parse)
    monkeypatch.setattr(calendar_initial_world, "initial_turn_pro_evidence", counted_opening)
    return counts


def _preview(server, cmd, counts):
    before = dict(counts)
    code, body = _request("POST", tour_url(server) + "/preview", cmd)
    assert code == 200, body
    return body, {k: counts[k] - before[k] for k in counts}


def _transition(server, monkeypatch, counts, action, name, *, v87):
    view = inspect(server)
    cmd = command(view, action, name=name)
    # The original path: every loader parses (and v87 re-derives) on its own.
    with monkeypatch.context() as original:
        original.setattr(
            initial_world_state, "saved_initial_world_parse_scope", contextlib.nullcontext
        )
        reference, old = _preview(server, cmd, counts)
    preview, new = _preview(server, cmd, counts)
    assert json.dumps(preview, sort_keys=True) == json.dumps(reference, sort_keys=True)
    impact = preview["impact"]
    assert impact["native_transition"]
    # Exactly the two repeated parses of the one preparation disappear.
    assert old["parse"] - new["parse"] == 2, (old, new)
    assert old["opening"] - new["opening"] == (2 if v87 else 0), (old, new)
    assert ("turn_pro_model" in impact) is v87
    request = {
        "command": cmd,
        "expected_preview_fingerprint": reference["preview_fingerprint"],
        "explicit_confirmation": True,
    }
    code, result = _request("POST", tour_url(server) + "/execute", request)
    assert code == 201, result
    assert json.dumps(result["impact"], sort_keys=True) == json.dumps(impact, sort_keys=True)
    # The same confirmed command again returns its recorded result unchanged.
    assert _request("POST", tour_url(server) + "/execute", request) == (201, result)
    save_tour(server)
    return impact


@pytest.mark.parametrize("v87", [False, True], ids=["historical-policy", "v87"])
def test_native_transitions_parse_saved_initial_world_once_byte_identically(
    tmp_path, monkeypatch, v87
):
    if v87:
        _v87_population(monkeypatch)
    path = tmp_path / "parse-once.db"
    db = f"sqlite:///{path}"
    clock = RunCalendar(4, 1, 2030, 2)
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, clock, 12)
        assert inspect(server)["state"]["week"]["week"] == 2
        sign_prospects(server, repo, clock, target_week=3)
        counts = _counted(monkeypatch)
        decided = []
        with monkeypatch.context() as patch:
            if v87:
                # Test calibration so real decisions (with evidence) are compared.
                _eager(patch)
            birth = _transition(server, monkeypatch, counts, "transition", "parse-once-birth", v87=v87)
            assert birth["admitted_player_ids"] == ["born-native-15"]
            quiet = _transition(server, monkeypatch, counts, "transition", "parse-once-quiet", v87=v87)
            assert quiet["admitted_player_ids"] == []
            season = _transition(
                server, monkeypatch, counts, "season-transition", "parse-once-season", v87=v87
            )
            assert season["target_week"]["season_index"] == 1
            assert season["target_week"]["week"] == 1
            for impact in (birth, quiet, season):
                decided += [d["player_id"] for d in impact.get("turn_pro_decisions", ())]
        if v87:
            # The newborn cannot turn pro in its birth week, only afterwards.
            assert decided and "born-native-15" in decided, decided
            assert "born-native-15" not in {
                d["player_id"] for d in birth["turn_pro_decisions"]
            }
        saved_view = inspect(server)
        assert saved_view["saved"]
        assert repo.verify_branch_saved_revision_hash(
            revision_id=saved_view["saved_head_revision_id"]
        )
    with ApiServer(database_url=db) as restarted:
        # Physical restart: the complete Signed history replays identically.
        assert inspect(restarted) == saved_view
        nxt = command(saved_view, "transition", name="parse-once-after-restart")
        code, body = _request("POST", tour_url(restarted) + "/preview", nxt)
        assert code == 200, body

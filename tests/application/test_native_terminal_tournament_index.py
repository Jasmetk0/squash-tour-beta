"""Terminal tournament summary equivalence and actual native worker acceptance.

The terminal index is *only* a projection after existing Signed/receipt proof;
these tests do not bypass or mock any authoritative production Save/worker path.
"""

import json
from time import perf_counter
from types import SimpleNamespace

import pytest

from beta_engine.application.native_full_simulation import (
    NativeFullSimulationDriver,
    completed_tournament_ids,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api import test_native_full_simulation_tasks as full_tasks

pytestmark = pytest.mark.pr_critical


def _legacy_completed(state, children):
    """Unmodified buuk terminal expression, retained for differential testing."""
    return [
        a.edition.edition_id
        for a in state.editions
        if a.result_confirmed
        and any(
            (
                c["request"]["command"]["action"] == "play"
                and c["request"]["command"]["edition_id"] == a.edition.edition_id
            )
            or (
                c["request"]["command"]["action"] in {"next-slot", "next-match"}
                and any(
                    mid.startswith(a.edition.edition_id + ":")
                    for r in state.receipts
                    if r.command_id == c["request"]["command"]["command_id"]
                    for mid in r.result.get("match_ids", [])
                )
            )
            for c in children
        )
    ]


def _command(action, command_id, edition_id=None):
    return {
        "request": {
            "command": {
                "action": action,
                "command_id": command_id,
                "edition_id": edition_id,
            }
        }
    }


def _source(n):
    ids = [
        "s1",
        "s1:edition",
        "s1:edition:sub",
        "řetězec:β",
        "nonparticipant",
    ] + [f"year:{i // 8}:edition:{i}" for i in range(n)]
    editions = [
        SimpleNamespace(
            edition=SimpleNamespace(edition_id=edition_id),
            result_confirmed=(i % 7 != 0),
        )
        for i, edition_id in enumerate(ids)
    ]
    children = []
    receipts = []
    for i, edition_id in enumerate(ids):
        if i % 3 == 0:
            children.append(_command("play", "play-" + str(i), edition_id))
        elif i % 3 == 1:
            action = "next-slot" if i % 2 else "next-match"
            children.append(_command(action, "slot-" + str(i)))
            receipts.append(
                SimpleNamespace(
                    command_id="slot-" + str(i),
                    result={
                        "match_ids": [
                            edition_id + ":match:1",
                            "not-a-" + edition_id + ":match",
                        ]
                    },
                )
            )
        else:
            children.append(_command("transition", "transition-" + str(i)))
    # A decoy receipt cannot authorize an unreferenced terminal match.
    receipts.append(
        SimpleNamespace(
            command_id="unrelated",
            result={"match_ids": ["nonparticipant:match:1"]},
        )
    )
    return SimpleNamespace(editions=editions, receipts=receipts), children


@pytest.mark.parametrize("edition_count", [0, 1, 8, 32, 128, 320])
def test_terminal_index_matches_original_output_with_colons_and_false_positives(edition_count):
    state, children = _source(edition_count)
    assert completed_tournament_ids(state, children) == _legacy_completed(state, children)
    # The terminal summary contains the original Edition order only.
    assert len(completed_tournament_ids(state, children)) == len(
        set(completed_tournament_ids(state, children))
    )


def test_terminal_index_handles_all_play_no_confirmed_and_child_order():
    state, children = _source(35)
    state.editions = [
        SimpleNamespace(edition=a.edition, result_confirmed=False)
        for a in state.editions
    ]
    assert completed_tournament_ids(state, children) == []
    assert completed_tournament_ids(state, children) == _legacy_completed(state, children)
    state.editions = [
        SimpleNamespace(edition=a.edition, result_confirmed=True)
        for a in state.editions
    ]
    play = [_command("play", "play-" + str(i), a.edition.edition_id) for i, a in enumerate(state.editions)]
    assert completed_tournament_ids(state, play) == _legacy_completed(state, play)
    assert completed_tournament_ids(state, list(reversed(children))) == (
        _legacy_completed(state, list(reversed(children)))
    )


def test_large_histories_have_identical_terminal_projection(capsys):
    # Structural scale test, NOT a real 50-season worker benchmark. No brittle
    # millisecond-based CI assertion, only the exact equality requirement.
    state, children = _source(480)
    start = perf_counter()
    baseline = _legacy_completed(state, children)
    baseline_seconds = perf_counter() - start
    start = perf_counter()
    candidate = completed_tournament_ids(state, children)
    candidate_seconds = perf_counter() - start
    assert baseline == candidate
    with capsys.disabled():
        print(
            "NATIVE_TERMINAL_SCALED_AB " + json.dumps({
                "edition_count": len(state.editions),
                "child_count": len(children),
                "receipt_count": len(state.receipts),
                "baseline_projection_ms": round(1000 * baseline_seconds, 3),
                "candidate_projection_ms": round(1000 * candidate_seconds, 3),
                "output_identical": True,
                "scope": "synthetic_terminal_projection_only; not complete simulation",
            }, sort_keys=True),
            flush=True,
        )


def test_actual_seven_week_worker_real_match_save_season_restart_unchanged(
    tmp_path, monkeypatch, capsys
):
    # Reuses the unchanged production HTTP/SQLite integration scenario:
    # actual server-task dispatcher, weekly Saves, real MatchEngine tournament,
    # 100/60/30 points, Season Transition and cold SQLite restart.
    original = NativeFullSimulationDriver._terminal
    observed = []

    def checked(self, row, payload, command, ctx, status):
        state, children = ctx["state"], payload["children"]
        start = perf_counter()
        old = _legacy_completed(state, children)
        old_seconds = perf_counter() - start
        start = perf_counter()
        new = completed_tournament_ids(state, children)
        new_seconds = perf_counter() - start
        assert old == new
        observed.append((old, old_seconds, new_seconds))
        return original(self, row, payload, command, ctx, status)

    monkeypatch.setattr(NativeFullSimulationDriver, "_terminal", checked)
    full_tasks.test_native_task_actual_match_points_all_weeks_and_real_season_rollover(
        tmp_path, RunCalendar(7, 5, 2030, 2)
    )
    assert observed, "Real worker did not reach its target/terminal projection"
    assert any("worker-cup" in ids for ids, _, _ in observed)
    with capsys.disabled():
        print(
            "NATIVE_TERMINAL_REAL_W7 " + json.dumps({
                "projections_checked": len(observed),
                "legacy_total_ms": round(1000 * sum(x[1] for x in observed), 3),
                "candidate_total_ms": round(1000 * sum(x[2] for x in observed), 3),
                "full_run_ab": False,
                "real_http_sqlite_matchengine_save_season_restart": True,
                "sporting_projection_identical": True,
            }, sort_keys=True),
            flush=True,
        )

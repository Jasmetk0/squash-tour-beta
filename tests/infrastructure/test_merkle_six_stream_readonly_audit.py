"""Check six-stream W52 prototype reader against synthetic SQLite revisions.

This does not exercise the sporting server. It guards the offline audit against
silently accepting corrected historical lists and verifies the six supported
paths. Actual 55-revision W52 evidence lives in docs/evidence.
"""
import json
import sqlite3

import pytest

from scripts.benchmark_merkle_append_w52 import HISTORICAL_PATHS, run

pytestmark = pytest.mark.pr_critical


def _state(week, *, corrupt_rankings=False):
    rows = list(range(week + 1))
    rankings = [{"n": i} for i in rows]
    if corrupt_rankings and rankings:
        rankings[0]["n"] = 999
    return {
        "journal": [{"n": i} for i in rows],
        "advances": [{"n": i} for i in rows],
        "tournaments": [{"n": i} for i in rows],
        "tour": {
            "receipts": [{"n": i} for i in rows],
            "transitions": [{"n": i} for i in rows],
            "rankings": rankings,
            "editions": [{"edited": week}],  # deliberately mutable, excluded
        },
    }


def _write_rows(tmp_path, states):
    path = tmp_path / "saved-for-audit.db"
    with sqlite3.connect(path) as session:
        session.execute(
            "CREATE TABLE branch_saved_revisions "
            "(sequence INTEGER, payload_schema_version TEXT, payload_json TEXT)"
        )
        for i, state in enumerate(states):
            session.execute(
                "INSERT INTO branch_saved_revisions VALUES(?, ?, ?)",
                (i + 1, "native_fork_saved_root.v2",
                 json.dumps({"content": {"native_fork_runtime": {"state": state}}})),
            )
    return path


def test_six_native_history_paths_are_reconstructed_exactly(tmp_path):
    states = [_state(0), _state(1), _state(1)]
    db = _write_rows(tmp_path, states)
    actual = run(db)
    assert len(HISTORICAL_PATHS) == 6
    assert actual["snapshots"] == 3
    assert actual["exact_reconstructions"] == 18
    assert actual["physical_corruption_rejected"]
    assert actual["unique_merkle_node_bytes"] > 0
    assert actual["new_events_by_field"]["journal"] == 2
    assert actual["new_events_by_field"]["tour.rankings"] == 2
    assert actual["new_events_by_field"]["tournaments"] == 2


def test_corrected_rankings_are_not_misrepresented_as_appends(tmp_path):
    db = _write_rows(tmp_path, [_state(0), _state(1, corrupt_rankings=True)])
    with pytest.raises(AssertionError, match="NOT APPEND ONLY"):
        run(db)


def test_missing_history_authority_is_rejected_instead_of_defaulting_empty(tmp_path):
    state = _state(0)
    del state["tour"]["transitions"]
    db = _write_rows(tmp_path, [state])
    with pytest.raises(AssertionError, match="missing field"):
        run(db)

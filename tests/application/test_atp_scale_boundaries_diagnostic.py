"""Diagnostic only: two REAL ATP-capable boundaries, not a full ATP season.

The checked-in ATP historical calendar is currently reference-only; this test
does not invent missing native tournament imports or mark empty weeks as games.

Boundary A: production ATP Earth World Package -> 250 countries -> 1000-player
InitialWorld -> official Run Save/Rankings -> one ACTUAL empty-week transition ->
SQLite restart and fork. Original existing server acceptance is called unchanged.

Boundary B: Saved ATP 2025 Finals -> playable *squash* group profile -> 15 real
MatchEngine BO5 matches + explicit Save, ranking, cold SQLite reopen.

Independent databases by design. The 1000-player Run and the 15-match tournament
are NOT combined into one Run, and neither represents a full ATP season.
"""
from __future__ import annotations

import json
import resource
import signal
import sqlite3
import time

import pytest

from tests.application import test_earth_world_package_run_integration as earth
from tests.api import test_atp_next_gen_edition as atp

pytestmark = pytest.mark.pr_critical


def _db_metrics(path):
    if not path.is_file():
        return {"sqlite_found": False}
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
        revisions = conn.execute(
            "SELECT COUNT(*) FROM branch_saved_revisions"
        ).fetchone()[0]
        revisions_bytes = conn.execute(
            "SELECT COALESCE(SUM(LENGTH(CAST(payload_json AS BLOB))),0) "
            "FROM branch_saved_revisions"
        ).fetchone()[0]
    return {
        "sqlite_found": True,
        "sqlite_file_bytes": path.stat().st_size,
        "saved_revisions": revisions,
        "saved_payload_bytes": revisions_bytes,
    }


def _measure(label, sqlite_path, fn):
    t0 = time.perf_counter()
    c0 = time.process_time()
    try:
        fn()
    finally:
        evidence = {
            "label": label,
            "description": (
                "ATPEarth World1000 + one EMPTY official week, restart/fork"
                if label == "atp_earth_1000_players_one_empty_week"
                else "ATP Finals 2025, eight entrants, 15 real squash BO5 matches, cold reopen"
            ),
            "wall_s": round(time.perf_counter() - t0, 3),
            "process_cpu_s": round(time.process_time() - c0, 3),
            "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "db": _db_metrics(sqlite_path),
            "full_atp_season": False,
            "squash_rules_not_real_tennis": True,
        }
        print("ATP_REAL_BOUNDARY_MEASUREMENT " + json.dumps(evidence, sort_keys=True), flush=True)


def _limited(seconds, fn):
    """Avoid an unlimited hosted bill if 1000-player legacy world proves very slow."""
    def on_alarm(_signum, _frame):
        raise TimeoutError(
            f"ATP Earth 1000-player diagnostic exceeded {seconds}s budget; "
            "not evidence of completed week"
        )
    old_handler = signal.signal(signal.SIGALRM, on_alarm)
    previous = signal.alarm(seconds)
    try:
        fn()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        if previous:
            signal.alarm(previous)


def test_real_saved_atp_finals_2025_play_fifteen_matches(tmp_path):
    """Existing production acceptance, unchanged, with SQLite timing evidence."""
    def scenario():
        atp.test_saved_atp_import_plays_fifteen_squash_matches_and_reopens(
            tmp_path, "atp_2025_atp_finals", True, 43
        )
    _measure("atp_finals_2025_real_15_matches",
             tmp_path / "atp-next-gen.db", scenario)


def test_real_atp_earth_1000_players_one_event_free_week(tmp_path):
    """Existing real 250-country production Run acceptance, one empty week."""
    def scenario():
        earth._verify_earth_post_transition_fork(
            tmp_path, "atp_earth", 1000, 1, continue_fork=False
        )
    _measure("atp_earth_1000_players_one_empty_week",
             tmp_path / "atp_earth" / "api.sqlite",
             lambda: _limited(900, scenario))

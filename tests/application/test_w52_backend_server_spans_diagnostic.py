"""W52 *diagnostic only*: exact #1803 production flow, backend-thread spans.

Run through Fast CI with pytest.mark.pr_critical on a child branch of the
specific PR #1803 head. No production file, Signed verification, writer, clock,
Saved content, simulation command or fixture scenario is modified.

The probes wrap the actual methods invoked by Uvicorn and the server task's
worker thread. There is deliberately NO cProfile tracing on the 52-week timing
sample, and SQL timings cover cursor.execute only, not result fetching.

Each span stores inclusive and EXCLUSIVE wall/thread-CPU time. Exclusive subtracts
nested instrumented spans on the SAME thread, so overlapping instrumented calls
are never double counted in the ranked CPU table. Unwrapped calls still contribute
to the closest tracked span's exclusive time. SQL metrics are attributed only to
the innermost active span.

Weeks are segmented by the existing test's observed task position after wait():
work between observed Wn and Wn+1 is assigned to Wn. This is cycle attribution,
not proof that each individual DB operation belongs to that sporting week.
"""

from __future__ import annotations

import functools
import json
import statistics
import threading
import time
from collections import defaultdict
from contextlib import contextmanager

import pytest
from sqlalchemy import Engine, event

from beta_engine.application import (
    calendar_tour_service as tour_service,
    full_simulation_tasks as task_service,
    native_fork_runtime_reducer as reducer,
    native_fork_runtime_service as fork_service,
    native_full_simulation as simulation,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db import (
    native_fork_runtime_state as runtime_state,
    repositories,
)
from tests.api import test_native_full_simulation_tasks as flow


class BackendSpans:
    """Request/worker thread-local call tree with a global, synchronized collector."""

    def __init__(self):
        self.tls = threading.local()
        self.lock = threading.Lock()
        self.enabled = False
        self.phase = "setup"
        self.calls = defaultdict(lambda: {
            "calls": 0,
            "cpu_ns": 0,
            "self_cpu_ns": 0,
            "wall_ns": 0,
            "self_wall_ns": 0,
            "sql_calls": 0,
            "sql_driver_ns": 0,
            "sql_selects": 0,
            "sql_writes": 0,
        })
        self.unattributed_sql = 0
        self.phase_marks = []

    def mark(self, task):
        week = task.get("current_week")
        if not isinstance(week, dict):
            return
        season = week.get("season_index")
        index = week.get("week")
        if type(season) is not int or type(index) is not int:
            return
        if season != 0:
            label = "season2"
        elif 3 <= index <= 12:
            label = "W03-12"
        elif 20 <= index <= 30:
            label = "W20-30"
        elif 40 <= index <= 50:
            label = "W40-50"
        else:
            label = "other_week"
        with self.lock:
            self.phase = label
            self.phase_marks.append((season, index, time.perf_counter_ns()))

    def wrap(self, name, original):
        @functools.wraps(original)
        def traced(*args, **kwargs):
            if not self.enabled:
                return original(*args, **kwargs)
            stack = getattr(self.tls, "stack", None)
            if stack is None:
                stack = []
                self.tls.stack = stack
            start_wall = time.perf_counter_ns()
            start_cpu = time.thread_time_ns()
            phase = self.phase
            frame = {"child_cpu": 0, "child_wall": 0, "label": name, "phase": phase}
            stack.append(frame)
            try:
                return original(*args, **kwargs)
            finally:
                elapsed_cpu = max(0, time.thread_time_ns() - start_cpu)
                elapsed_wall = max(0, time.perf_counter_ns() - start_wall)
                popped = stack.pop()
                assert popped is frame
                self_cpu = max(0, elapsed_cpu - frame["child_cpu"])
                self_wall = max(0, elapsed_wall - frame["child_wall"])
                if stack:
                    stack[-1]["child_cpu"] += elapsed_cpu
                    stack[-1]["child_wall"] += elapsed_wall
                with self.lock:
                    item = self.calls[(phase, name)]
                    item["calls"] += 1
                    item["cpu_ns"] += elapsed_cpu
                    item["self_cpu_ns"] += self_cpu
                    item["wall_ns"] += elapsed_wall
                    item["self_wall_ns"] += self_wall

        return traced

    def sql_start(self, conn, cursor, statement, parameters, context, executemany):
        if self.enabled:
            context._w52_probe_start = time.perf_counter_ns()

    def sql_end(self, conn, cursor, statement, parameters, context, executemany):
        start = getattr(context, "_w52_probe_start", None)
        if start is None:
            return
        elapsed = max(0, time.perf_counter_ns() - start)
        stack = getattr(self.tls, "stack", [])
        if not stack:
            with self.lock:
                self.unattributed_sql += 1
            return
        # The containing method's full duration already includes this SQL call.
        # Counting SQL on the innermost span preserves exclusive attribution.
        # The top-of-stack entry includes the exact originating label and phase.
        label, phase = stack[-1]["label"], stack[-1]["phase"]
        kind = statement.lstrip().split(maxsplit=1)[0].upper() if statement.strip() else ""
        with self.lock:
            entry = self.calls[(phase, label)]
            entry["sql_calls"] += 1
            entry["sql_driver_ns"] += elapsed
            if kind in {"SELECT", "WITH", "PRAGMA"}:
                entry["sql_selects"] += 1
            elif kind in {"INSERT", "UPDATE", "DELETE", "REPLACE"}:
                entry["sql_writes"] += 1

    def summarize(self, total_wall_ns, total_process_cpu_ns):
        out = defaultdict(lambda: defaultdict(int))
        per_phase = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        with self.lock:
            for (phase, label), stats in self.calls.items():
                for key, value in stats.items():
                    out[label][key] += value
                    per_phase[phase][label][key] += value
            outside = self.unattributed_sql
            marks = list(self.phase_marks)

        cpu_covered = sum(a["self_cpu_ns"] for a in out.values())
        def row(label, x):
            return {
                "name": label,
                "calls": x["calls"],
                "cpu_ms": round(x["cpu_ns"] / 1e6, 3),
                "exclusive_cpu_ms": round(x["self_cpu_ns"] / 1e6, 3),
                "inclusive_wall_ms": round(x["wall_ns"] / 1e6, 3),
                "exclusive_wall_ms": round(x["self_wall_ns"] / 1e6, 3),
                "share_of_instrumented_cpu_pct": round(
                    100 * x["self_cpu_ns"] / cpu_covered, 2
                ) if cpu_covered else 0,
                "sql": x["sql_calls"],
                "sql_selects": x["sql_selects"],
                "sql_writes": x["sql_writes"],
                "sql_cursor_execute_ms": round(x["sql_driver_ns"] / 1e6, 3),
            }

        all_rows = sorted(
            [row(k, v) for k, v in out.items()],
            key=lambda x: -x["exclusive_cpu_ms"],
        )
        groups = {}
        for phase in ("W03-12", "W20-30", "W40-50"):
            records = per_phase[phase]
            groups[phase] = {
                "calls": sum(v["calls"] for v in records.values()),
                "exclusive_cpu_ms": round(sum(v["self_cpu_ns"] for v in records.values()) / 1e6, 3),
                "sql_queries": sum(v["sql_calls"] for v in records.values()),
                "top": sorted([row(k, v) for k, v in records.items()],
                              key=lambda x: -x["exclusive_cpu_ms"])[:14],
            }
        return {
            "schema": "w52_backend_exact_1803_span_diagnostic.v1",
            "baseline_sha": "136b277a6b246da8bd01bca7b2e1668f35983fad",
            "scenario": "original production W52 HTTP+SQLite+MatchEngine+Save+SeasonTransition+cold_restart",
            "whole_test_wall_s": round(total_wall_ns / 1e9, 3),
            "whole_test_process_cpu_s": round(total_process_cpu_ns / 1e9, 3),
            "sum_instrumented_exclusive_cpu_s": round(cpu_covered / 1e9, 3),
            "instrumented_cpu_vs_process_cpu_pct": round(
                cpu_covered / total_process_cpu_ns * 100, 2
            ) if total_process_cpu_ns else None,
            "sql_outside_wrapped_spans": outside,
            "observed_week_marks": len(marks),
            "top_30_exclusive_cpu": all_rows[:30],
            "periods": groups,
            "methodology": (
                "Exclusive subtracts only nested measured spans on one thread; "
                "thread CPU sums may cover several concurrent threads. SQL driver "
                "time excludes fetching/row decoding and is already inside span "
                "wall duration. Periods label observed task cycles, not exact "
                "sporting event timestamps. No full A/B end-to-end speedup claimed."
            ),
        }


def _install_spans(monkeypatch, spans):
    def instrument(obj, attr, label):
        old = getattr(obj, attr)
        wrapped = spans.wrap(label, old)
        # Attach metadata via closure stack, not a new argument to production.
        # Uses a new span identity per method invocation.
        # A wrapper can appear on the same object's method and in a module alias.
        monkeypatch.setattr(obj, attr, wrapped)

    # API requests, task worker and task status, in *server* execution threads.
    instrument(simulation.NativeFullSimulationDriver, "simulate_full_simulation", "driver.simulate")
    instrument(simulation.NativeFullSimulationDriver, "plan", "driver.plan")
    instrument(simulation.NativeFullSimulationDriver, "_parent", "driver._parent")
    instrument(simulation.NativeFullSimulationDriver, "_terminal", "driver._terminal")
    instrument(simulation, "native_context", "native_context")
    instrument(simulation, "validate_native_parent", "parent_validation")
    instrument(simulation, "authenticate_children", "child_receipts_validation")
    instrument(simulation, "read_native_task_progress", "task_progress_read")
    instrument(task_service, "_project", "task_status_project")
    instrument(task_service, "_parent", "task_status_parent")
    instrument(task_service, "_progress_evidence", "task_progress_evidence")
    instrument(task_service, "inspect_tasks", "task_status_inspect")
    instrument(task_service, "validate_native_parent", "task_parent_validation")
    instrument(tour_service.CalendarTourService, "preview", "tour.preview")
    instrument(tour_service.CalendarTourService, "execute", "tour.execute")
    instrument(tour_service.CalendarTourService, "_context", "tour._context")

    # The W52 original test forks into native-v2; the actual worker dispatches
    # through this service, rather than the legacy calendar service directly.
    service = fork_service.NativeForkRuntimeService
    for attr in ("inspect", "_inspection", "_context", "preview", "execute",
                 "save", "_append"):
        instrument(service, attr, "native_v2." + attr)

    instrument(fork_service, "load_runtime", "native_v2.runtime_decode")
    instrument(fork_service, "component", "native_v2.runtime_component")
    instrument(fork_service, "prepare_command", "native_v2.prepare_command")
    instrument(fork_service, "commit_prepared", "native_v2.commit_prepared")
    instrument(fork_service, "source_inputs", "native_v2.source_inputs")
    instrument(reducer, "_advance", "sporting_week_advance")
    instrument(reducer, "cohere", "sporting_cohere_validate")
    instrument(reducer, "calculate_calendar_official_ranking", "sporting_ranking")
    instrument(reducer, "project_native_sporting_birth_advance", "sporting_development")
    instrument(runtime_state, "actual_dependency_signature", "saved_dependency_graph")

    repository = repositories.SimulationPersistenceRepository
    instrument(repository, "_validated_saved_revision_in_session", "saved_revision_validate")
    instrument(repository, "_validated_saved_revision_core_in_session", "saved_revision_core")
    instrument(repository, "_validated_branch_revision_lineage_in_session", "saved_lineage_walk")
    event.listen(Engine, "before_cursor_execute", spans.sql_start)
    event.listen(Engine, "after_cursor_execute", spans.sql_end)


@pytest.mark.pr_critical
def test_instrumented_original_w52_worker_without_changes(tmp_path, monkeypatch, capsys):
    spans = BackendSpans()
    _install_spans(monkeypatch, spans)

    original_wait = flow.wait
    def observed_wait(*args, **kwargs):
        result = original_wait(*args, **kwargs)
        spans.mark(result)
        return result
    monkeypatch.setattr(flow, "wait", observed_wait)

    start = time.perf_counter_ns()
    start_cpu = time.process_time_ns()
    spans.enabled = True
    try:
        # This is the *unchanged* existing acceptance function, called directly.
        # Its assertions cover real MatchEngine matches, point accounting, exact
        # Saved source, Week-by-Week transitions, Season Transition and cold reopen.
        flow.test_native_task_actual_match_points_all_weeks_and_real_season_rollover(
            tmp_path,
            RunCalendar(52, 51, 2030, 2),
        )
    finally:
        spans.enabled = False
        event.remove(Engine, "before_cursor_execute", spans.sql_start)
        event.remove(Engine, "after_cursor_execute", spans.sql_end)

    result = spans.summarize(time.perf_counter_ns() - start,
                             time.process_time_ns() - start_cpu)
    assert len(spans.phase_marks) >= 50, "Missing most actual W52 boundaries"
    assert result["top_30_exclusive_cpu"], "No backend instrumentation was observed"
    assert result["sum_instrumented_exclusive_cpu_s"] > 0
    with capsys.disabled():
        print("W52_EXACT_1803_SERVER_PROFILE " + json.dumps(result, sort_keys=True), flush=True)

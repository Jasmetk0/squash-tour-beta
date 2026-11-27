"""Whole-operation A/B of sequential vs. spawn-worker slot matches (HTTP/SQLite).

Production path only: a real uvicorn server on a disposable copy of one
pinned SQLite fixture runs ``next-slot`` (preview + execute), the following
inspection, one explicit Tour Save and a cold restart inspection. Every run is
a fresh process; ``ab`` orders samples A B B A per round. The driver checkout
is held constant; A and B are detached worktrees of two exact commits.

    # 32 + 16 + 8 simultaneous matches (8 parallel 8-player Editions, 64 players)
    python scripts/profile_slot_match_workers.py prepare --editions 8 --database work/e8x8.db
    sha=$(sha256sum work/e8x8.db | cut -d' ' -f1)
    python scripts/profile_slot_match_workers.py ab --a "$base" --b "$candidate" \
        --input work/e8x8.db --sha256 "$sha" --steps 3 --b-workers 0,2,3 --rounds 2 --out work/ab
    # separate instrumented run (exclusive handler-thread CPU per phase)
    python scripts/profile_slot_match_workers.py run --root . --input work/e8x8.db \
        --sha256 "$sha" --workers 3 --phases --out work/phases-w3.json

Measured per step: wall, parent process CPU, CPU of every descendant process
(workers and the spawn resource tracker, from ``/proc``), peak RSS of the whole
process group (parent + descendants, sampled every 20 ms and at each step
boundary), SQLite+WAL bytes, played matches and rallies. Linux only for the
process-group counters; elsewhere they are null. Output equality (execute
results, the saved inspection and the restarted inspection, each without the
random Saved revision id) is required between every sample of one ``ab``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

DRIVER = Path(__file__).resolve()
CLK = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
PAGE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ----------------------------------------------------------------- process group
def _children(pid):
    out = []
    try:
        tasks = os.listdir(f"/proc/{pid}/task")
    except OSError:
        return out
    for task in tasks:
        try:
            out += [int(c) for c in open(f"/proc/{pid}/task/{task}/children").read().split()]
        except OSError:
            pass
    return out


def _proc(pid):
    try:
        stat = open(f"/proc/{pid}/stat").read()
        fields = stat[stat.rindex(")") + 2:].split()
        rss = int(open(f"/proc/{pid}/statm").read().split()[1]) * PAGE
        return (int(fields[11]) + int(fields[12])) / CLK, rss
    except (OSError, ValueError, IndexError):
        return None


class GroupSampler:
    """Peak RSS of parent + descendants; last CPU seen per descendant."""

    def __init__(self, interval=0.02):
        self.supported = sys.platform.startswith("linux")
        self.interval = interval
        self.peak = 0
        self.child_cpu = {}
        self.child_peak = {}
        self.child_cmd = {}
        try:
            self.own_cmd = open(f"/proc/{os.getpid()}/cmdline", "rb").read()
        except OSError:
            self.own_cmd = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def sample(self):
        if not self.supported:
            return
        me = os.getpid()
        seen, stack, total = set(), [me], 0
        while stack:
            pid = stack.pop()
            if pid in seen:
                continue
            seen.add(pid)
            info = _proc(pid)
            if info is None:
                continue
            total += info[1]
            if pid != me:
                try:
                    cmd = open(f"/proc/{pid}/cmdline", "rb").read()
                except OSError:
                    total -= info[1]
                    continue
                if cmd == self.own_cmd:
                    # fork before exec: the parent's shared pages, not new memory
                    total -= info[1]
                    continue
                self.child_cmd[pid] = cmd.replace(b"\0", b" ").decode(errors="replace")[-100:]
                with self._lock:
                    self.child_cpu[pid] = max(self.child_cpu.get(pid, 0.0), info[0])
                    self.child_peak[pid] = max(self.child_peak.get(pid, 0), info[1])
            stack += _children(pid)
        with self._lock:
            self.peak = max(self.peak, total)

    def _loop(self):
        while not self._stop.wait(self.interval):
            self.sample()

    def start(self):
        if self.supported:
            self.thread.start()

    def stop(self):
        self._stop.set()
        if self.thread.is_alive():
            self.thread.join()

    def window(self):
        self.sample()
        with self._lock:
            peak, self.peak = self.peak, 0
            return peak, sum(self.child_cpu.values()), len(self.child_cpu)


# ----------------------------------------------------------------- engine imports
def target_imports(root):
    root = Path(root).resolve()
    sys.path[:0] = [str(root / "src"), str(root)]
    import beta_engine
    if not Path(beta_engine.__file__).resolve().is_relative_to(root / "src"):
        raise SystemExit("Imported engine does not come from the requested checkout")
    from tests.api import test_calendar_tour_flow as flow
    from tests.api.test_saved_revision_history_api import ApiServer, _request
    return flow, ApiServer, _request


def prepare(args):
    target = Path(args.database)
    if target.exists():
        raise SystemExit(f"{target} exists; prepare never overwrites")
    flow, ApiServer, _ = target_imports(args.root)
    from beta_engine.domain.calendar.run_calendar import RunCalendar
    import sqlite3

    entrants = args.entrants
    with tempfile.TemporaryDirectory() as tmp:
        build = Path(tmp) / "build.db"
        with ApiServer(database_url=f"sqlite:///{build}") as server:
            flow.setup(server, RunCalendar(52, 1, 2030, 2), args.editions * entrants)
            for k in range(args.editions):
                eid = f"parallel-{k:02d}"
                view = flow.inspect(server)
                week = view["state"]["week"]
                flow.execute(server, flow.command(view, "create-edition", name=eid + ":create", data={
                    "schema_version": "calendar_tournament_edition.v2", "simulation_seed": 891 + k,
                    "edition_id": eid, "name": eid, "week": {**week, "week": 4},
                    "announcement_week": {**week, "week": 3}, "start_slot": 1,
                    "main_entrant_count": entrants, "ranked": True, "validity_weeks": 52,
                    "point_table": {"champion": 100, "finalist": 60, "semifinal": 30,
                                    **({"quarterfinal": 15} if entrants == 8 else {})}}))
                flow.save_tour(server)
            for week_number in (3, 4):
                flow.execute(server, flow.command(flow.inspect(server), "transition", name=f"week-{week_number}"))
                flow.save_tour(server)
            players = [p["player_id"] for p in flow.inspect(server)["players"]]
            for k in range(args.editions):
                eid = f"parallel-{k:02d}"
                flow.execute(server, flow.command(flow.inspect(server), "submit", name=eid + ":submit",
                             edition_id=eid, data={"player_ids": players[k * entrants:(k + 1) * entrants]}))
                for action in ("approve", "draw"):
                    flow.execute(server, flow.command(flow.inspect(server), action, name=f"{eid}:{action}",
                                                      edition_id=eid))
            flow.save_tour(server)
        # One self-contained file (no WAL sidecar) is the pinned fixture.
        with sqlite3.connect(build) as source, sqlite3.connect(target) as copy:
            source.backup(copy)
    print(json.dumps({"database": str(target), "sha256": sha256(target), "editions": args.editions,
                      "entrants": entrants, "bytes": target.stat().st_size}))


# ----------------------------------------------------------------- phases (separate runs)
_PHASES = threading.local()


def _wrap(owner, name, label, totals):
    original = getattr(owner, name, None)
    if original is None:
        return
    if isinstance(original, staticmethod):
        original = original.__func__

    def wrapper(*a, **k):
        stack = getattr(_PHASES, "stack", None)
        if stack is None:
            stack = _PHASES.stack = []
        start = time.thread_time()
        stack.append(0.0)
        try:
            return original(*a, **k)
        finally:
            elapsed = time.thread_time() - start
            nested = stack.pop()
            entry = totals.setdefault(label, [0, 0.0, 0.0])
            entry[0] += 1
            entry[1] += elapsed - nested
            entry[2] += elapsed
            if stack:
                stack[-1] += elapsed
    setattr(owner, name, wrapper)


def install_phases(totals):
    from beta_engine.application import calendar_global_slot_service as service_mod
    from beta_engine.application.calendar_tour_service import CalendarTourService
    from beta_engine.application.run_working_draft_service import RunWorkingDraftService
    from beta_engine.domain.tournaments import calendar_global_slots as slots
    from beta_engine.infrastructure.db import calendar_sporting_checkpoint as sporting

    _wrap(CalendarTourService, "execute", "execute: other", totals)
    _wrap(CalendarTourService, "_verify_installed", "post-write verification: other", totals)
    _wrap(CalendarTourService, "inspect", "inspection", totals)
    _wrap(RunWorkingDraftService, "save_calendar_tour", "explicit Save", totals)
    _wrap(service_mod, "prepare_global_slot", "freeze + prepare inputs", totals)
    _wrap(sporting, "replace_checkpoint", "checkpoint write", totals)
    _wrap(slots, "accept_slot", "accept slot: other", totals)
    _wrap(slots, "_match_inputs", "match inputs + anchor", totals)
    _wrap(slots, "continuation_effects", "state effects", totals)
    _wrap(slots, "_simulate_slot_matches", "replay memo + batch: other", totals)
    try:
        from beta_engine.domain.matches import slot_batch
        from beta_engine.infrastructure.match_workers import ProcessMatchExecutor
    except ImportError:
        slots_engine = getattr(slots, "MatchEngine", None)
        if slots_engine is not None:
            _wrap(slots_engine, "simulate", "MatchEngine in parent", totals)
        return
    _wrap(slot_batch, "_sequential", "MatchEngine in parent", totals)
    _wrap(slot_batch, "encode_request", "encode requests", totals)
    _wrap(slot_batch, "bind_response", "bind + full decode of worker results", totals)
    _wrap(ProcessMatchExecutor, "run", "wait for workers", totals)


# ----------------------------------------------------------------- one fresh run
def run(args):
    os.environ["BETA_ENGINE_MATCH_WORKERS"] = str(args.workers)
    flow, ApiServer, request = target_imports(args.root)
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint

    totals = {}
    if args.phases:
        install_phases(totals)
    if sha256(args.input) != args.sha256:
        raise SystemExit("Input fixture SHA-256 differs")
    sampler = GroupSampler()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work.db"
        shutil.copyfile(args.input, work)
        if sha256(work) != args.sha256:
            raise SystemExit("Copied fixture differs")

        def db_bytes():
            return sum(p.stat().st_size for p in (work, Path(str(work) + "-wal")) if p.exists())

        steps, results = [], []
        sampler.start()
        sampler.window()

        def timed(label, fn):
            w, c = time.perf_counter(), time.process_time()
            out = fn()
            wall, cpu = time.perf_counter() - w, time.process_time() - c
            peak, child_cpu, children = sampler.window()
            steps.append({"step": label, "wall": round(wall, 4), "cpu": round(cpu, 4),
                          "children_cpu_total": round(child_cpu, 3), "descendants_seen": children,
                          "group_peak_rss_mib": round(peak / 2 ** 20, 1) if sampler.supported else None,
                          "db_wal_bytes": db_bytes()})
            return out

        with ApiServer(database_url=f"sqlite:///{work}") as server:
            pool = getattr(server.app.state, "match_workers", None)
            if args.prestart and pool is not None:
                timed("pool prestart", pool.start)
            view = timed("inspect before", lambda: flow.inspect(server))
            for n in range(args.steps):
                cmd = flow.command(view, "next-slot", name=f"slot-step-{n}")
                code, preview = timed(f"slot {n + 1}: preview",
                                      lambda: request("POST", flow.tour_url(server) + "/preview", cmd))
                assert code == 200, preview
                body = {"command": cmd, "expected_preview_fingerprint": preview["preview_fingerprint"],
                        "explicit_confirmation": True}
                code, result = timed(f"slot {n + 1}: execute",
                                     lambda: request("POST", flow.tour_url(server) + "/execute", body))
                assert code == 201, result
                results.append(result)
                steps[-1]["matches"] = len(result["match_ids"])
                view = timed(f"slot {n + 1}: inspect", lambda: flow.inspect(server))
            timed("explicit Save", lambda: flow.save_tour(server))
            saved = flow.inspect(server)
            shutdown_started = time.perf_counter()
        steps.append({"step": "server shutdown (pool close)", "wall": round(time.perf_counter() - shutdown_started, 4)})
        with ApiServer(database_url=f"sqlite:///{work}") as server:
            restarted = timed("restart: first inspect", lambda: flow.inspect(server))
            timed("restart: warm inspect", lambda: flow.inspect(server))
            with server.app.state.runtime.repository._session_factory() as session:
                cp = load_checkpoint(session, run_id="run", branch_id="branch")
        sampler.stop()
        played = [m for m in cp.played_continuations if m.match_id.startswith("parallel-")]
        evidence = {
            "execute_results": digest(results),
            "saved_inspection": digest({k: v for k, v in saved.items() if k != "saved_head_revision_id"}),
            "restart_inspection": digest({k: v for k, v in restarted.items() if k != "saved_head_revision_id"}),
            "restart_equals_saved": restarted == saved,
            "checkpoint_fingerprint": restarted["checkpoint_fingerprint"],
            "matches": digest([m.model_dump(mode="json") for m in played]),
        }
    try:
        from beta_engine.domain.matches import slot_batch
        counters = slot_batch.batch_counters()
    except ImportError:
        counters = None
    import resource
    report = {
        "schema_version": "slot_match_workers_run.v1",
        "root": str(Path(args.root).resolve()), "commit": _git(args.root, "rev-parse", "HEAD"),
        "workers": args.workers, "prestart": args.prestart, "phases": args.phases,
        "input_sha256": args.sha256, "python": sys.version.split()[0], "platform": platform.platform(),
        "cpu_count": os.cpu_count(), "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "played_matches": len(played), "rallies": sum(m.result.rally_log.total_rallies for m in played),
        "steps": steps, "evidence": evidence, "batch_counters": counters,
        "parent_ru_maxrss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "reaped_children_cpu": round(sum(resource.getrusage(resource.RUSAGE_CHILDREN)[:2]), 3),
        "descendant_peak_rss_mib": round(sum(sampler.child_peak.values()) / 2 ** 20, 1),
        "descendants": [{"pid": pid, "peak_rss_mib": round(sampler.child_peak.get(pid, 0) / 2 ** 20, 1),
                         "cpu": round(cpu, 3), "cmd": sampler.child_cmd.get(pid)}
                        for pid, cpu in sorted(sampler.child_cpu.items())],
        "phase_thread_cpu": {k: {"calls": v[0], "exclusive": round(v[1], 3), "inclusive": round(v[2], 3)}
                             for k, v in sorted(totals.items())} if args.phases else None,
    }
    text = json.dumps(report, indent=1)
    if args.out:
        Path(args.out).write_text(text)
    print(text)


def _git(root, *cmd):
    try:
        return subprocess.run(["git", "-C", str(root), *cmd], check=True, capture_output=True,
                              text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


# ----------------------------------------------------------------- A B B A
def _sample(root, args, workers, out):
    cmd = [sys.executable, str(DRIVER), "run", "--root", str(root), "--input", str(args.input),
           "--sha256", args.sha256, "--workers", str(workers), "--steps", str(args.steps), "--out", str(out)]
    if args.prestart:
        cmd.append("--prestart")
    subprocess.run(cmd, check=True, cwd=root, env={**os.environ, "PYTHONHASHSEED": "0"},
                   stdout=subprocess.DEVNULL)
    return json.loads(Path(out).read_text())


def _whole(report):
    rows = [s for s in report["steps"] if "cpu" in s]
    slot = [s for s in rows if s["step"].startswith("slot ")]
    return {
        "slot_wall": sum(s["wall"] for s in slot),
        "slot_parent_cpu": sum(s["cpu"] for s in slot),
        "first_execute_wall": next(s["wall"] for s in slot if s["step"] == "slot 1: execute"),
        "save_wall": next(s["wall"] for s in rows if s["step"] == "explicit Save"),
        "restart_first_inspect_wall": next(s["wall"] for s in rows if s["step"] == "restart: first inspect"),
        "operation_wall": sum(s["wall"] for s in rows if s["step"] != "pool prestart"),
        "operation_parent_cpu": sum(s["cpu"] for s in rows if s["step"] != "pool prestart"),
        "children_cpu": rows[-1]["children_cpu_total"],
        "group_peak_rss_mib": max((s["group_peak_rss_mib"] or 0) for s in rows),
        "db_wal_bytes_max": max(s["db_wal_bytes"] for s in rows),
    }


def ab(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    trees = {}
    for side, commit in (("A", args.a), ("B", args.b)):
        tree = out / f"tree-{side}"
        subprocess.run(["git", "worktree", "add", "--detach", str(tree), commit], check=True,
                       capture_output=True)
        trees[side] = tree
    variants = [("A", 0)] + [("B", int(w)) for w in args.b_workers.split(",")]
    samples = {f"{s}-w{w}": [] for s, w in variants}
    try:
        for r in range(args.rounds):
            for b_workers in [int(w) for w in args.b_workers.split(",")]:
                for side in ("A", "B", "B", "A"):
                    workers = 0 if side == "A" else b_workers
                    key = f"{side}-w{workers}"
                    path = out / f"{key}-r{r}-{len(samples[key])}.json"
                    samples[key].append(_sample(trees[side], args, workers, path))
                    print(f"{key} sample {len(samples[key])}: {_whole(samples[key][-1])['operation_wall']:.2f}s",
                          flush=True)
    finally:
        for tree in trees.values():
            subprocess.run(["git", "worktree", "remove", "--force", str(tree)], capture_output=True)
    evidence = {json.dumps(s["evidence"], sort_keys=True) for v in samples.values() for s in v}
    summary = {"schema_version": "slot_match_workers_ab.v1", "a": args.a, "b": args.b,
               "input_sha256": args.sha256, "steps": args.steps, "prestart": args.prestart,
               "equal_outputs": len(evidence) == 1, "evidence": json.loads(sorted(evidence)[0]),
               "played_matches": samples["A-w0"][0]["played_matches"],
               "rallies": samples["A-w0"][0]["rallies"], "variants": {}}
    for key, values in samples.items():
        metrics = [_whole(v) for v in values]
        summary["variants"][key] = {
            "n": len(values),
            **{m: {"median": round(statistics.median(x[m] for x in metrics), 3),
                   "values": [round(x[m], 3) for x in metrics]} for m in metrics[0]},
        }
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    if not summary["equal_outputs"]:
        raise SystemExit("A and B outputs differ")


# ----------------------------------------------------------------- isolated (Lab)
def _isolated_items(root, corpus, count):
    sys.path[:0] = [str(Path(root).resolve() / "scripts")]
    import benchmark_match_engine as bench
    from beta_engine.domain.matches import MatchContext, MatchParticipantContext
    from beta_engine.domain.matches.health import EffectiveMatchHealthSnapshot
    from beta_engine.domain.players.health import PlayerHealthProfile

    def healthy(context):
        return EffectiveMatchHealthSnapshot.from_profiles(
            player_a=PlayerHealthProfile(player_id=context.player_a.player.player_id),
            player_b=PlayerHealthProfile(player_id=context.player_b.player.player_id))

    items = []
    if corpus == "ko128":
        # First round of the ko128 Lab scenario: 64 independent matches, 1 v 128 ...
        players = [bench._player(f"P{i:03d}", 95 - (i * 50) // 128, style=bench.STYLES[i % 5],
                                 archetype=bench.ARCHETYPES[(i * 3) % 5], spread=i % 6)
                   for i in range(1, 129)]
        for k in range(64):
            context = MatchContext(match_id=f"ko128-r1-m{k + 1:02d}",
                                   player_a=MatchParticipantContext(player=players[k]),
                                   player_b=MatchParticipantContext(player=players[127 - k]))
            items.append((context, 2701 + k * 7919, f"{k + 1:064x}", healthy(context)))
    else:
        for label, context, seed, health, _ in bench.edge_cases():
            if label.startswith(("lab-", "step-")):
                continue
            snapshot = (bench._health(context.player_a.player.player_id, context.player_b.player.player_id)
                        if health == "injured" else healthy(context))
            items.append((context, seed, f"{len(items) + 1:064x}", snapshot))
    return [items[i % len(items)] for i in range(count)] if count else items


def isolated(args):
    target_imports(args.root)
    from beta_engine.domain.matches import slot_batch
    from beta_engine.infrastructure.match_workers import ProcessMatchExecutor

    items = _isolated_items(args.root, args.corpus, args.matches)
    sampler = GroupSampler()
    sampler.start()
    sampler.window()
    executor = ProcessMatchExecutor(args.workers) if args.workers else None
    rows = []
    try:
        for label in ("first batch (cold pool)", "warm batch"):
            w, c = time.perf_counter(), time.process_time()
            results = slot_batch.simulate_batch(items, executor=executor)
            wall, cpu = time.perf_counter() - w, time.process_time() - c
            peak, child_cpu, _ = sampler.window()
            rows.append({"step": label, "wall": round(wall, 4), "parent_cpu": round(cpu, 4),
                         "children_cpu_total": round(child_cpu, 3),
                         "group_peak_rss_mib": round(peak / 2 ** 20, 1) if sampler.supported else None,
                         "digest": digest([r.model_dump(mode="json") for r in results])})
    finally:
        if executor is not None:
            executor.close()
        sampler.stop()
    report = {"schema_version": "slot_match_workers_isolated.v1", "corpus": args.corpus,
              "matches": len(items), "workers": args.workers, "commit": _git(args.root, "rev-parse", "HEAD"),
              "python": sys.version.split()[0], "cpu_count": os.cpu_count(),
              "rallies": sum(r.rally_log.total_rallies for r in results),
              "counters": slot_batch.batch_counters(), "rows": rows}
    print(json.dumps(report))


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--database", required=True)
    p.add_argument("--editions", type=int, required=True)
    p.add_argument("--entrants", type=int, default=8, choices=(4, 8))
    p.add_argument("--root", default=str(DRIVER.parents[1]))
    r = sub.add_parser("run")
    for q in (r,):
        q.add_argument("--root", required=True)
        q.add_argument("--workers", type=int, default=0)
        q.add_argument("--phases", action="store_true")
        q.add_argument("--out")
    a = sub.add_parser("ab")
    a.add_argument("--a", required=True)
    a.add_argument("--b", required=True)
    a.add_argument("--b-workers", default="0,3")
    a.add_argument("--rounds", type=int, default=1)
    a.add_argument("--out", required=True)
    for q in (r, a):
        q.add_argument("--input", required=True)
        q.add_argument("--sha256", required=True)
        q.add_argument("--steps", type=int, default=1)
        q.add_argument("--prestart", action="store_true")
    i = sub.add_parser("isolated", help="Lab/isolated batch: no HTTP, SQLite or Run state")
    i.add_argument("--root", default=str(DRIVER.parents[1]))
    i.add_argument("--corpus", choices=("ko128", "cases"), default="ko128")
    i.add_argument("--matches", type=int, default=0, help="first N items (cycled); 0 = all")
    i.add_argument("--workers", type=int, default=0)
    args = parser.parse_args(argv)
    {"prepare": prepare, "run": run, "ab": ab, "isolated": isolated}[args.command](args)


if __name__ == "__main__":
    main()

"""Real HTTP/SQLite native Week Transition A/B: fixture, measurement, phases.

``prepare`` builds one immutable native birth Run through the production API:
an initial world of N players, a signed 15-year-old prospect source with
arrivals in chosen weeks, one real ranked Edition played by MatchEngine, and
explicitly Saved Week Transitions. A SQLite backup of every Saved week is kept
(``week-SS-WW.db``) so a short, a longer-history and a season-boundary
transition are all measured from the same verified chain.

``measure`` copies one fixture (never opening the input for writing), then runs
cold GET, Preview, Execute, explicit Save and the first Saved GET over HTTP,
and finally reopens the database in a fresh process, compares the complete
inspection and previews the next command to prove continuation.

Timing mode installs nothing. ``--phases`` wraps the named transition stages
with per-thread CPU accounting (inclusive and self = inclusive minus wrapped
children) and is reported separately; ``--profile`` adds cProfile.
"""

import argparse
import cProfile
import hashlib
import json
import marshal
import multiprocessing
import os
import platform
import pstats
import resource
import sqlite3
import subprocess
import sys
import threading
import time
from itertools import count
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ.setdefault("BETA_ENGINE_NEW_RUN_SAVED_STORAGE", "saved_v2")

# (module, attribute, phase label). Labels group the Master/Task phases.
PHASES = (
    ("beta_engine.application.calendar_tour_service", "CalendarTourService._transition_candidate", "transition.candidate"),
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "prepare_native_tour_week", "transition.native_week"),
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "_native_turn_pro", "lifecycle.turn_pro"),
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "build_calendar_prospect_birth_event", "lifecycle.incoming_births"),
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "advance_calendar_lifecycle_with_prospects", "lifecycle.advance"),
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "advance_calendar_lifecycle", "lifecycle.advance"),
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "prepare_native_health_history", "health.regeneration"),
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "played_counts", "development.played_counts"),
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "project_native_sporting_birth_advance", "development.form_recovery"),
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "append_native_sporting_week", "checkpoint.build"),
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "published_edition_results", "ranking.results"),
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "calculate_native_ranking_from_signed_lifecycle", "ranking.calculate"),
    ("beta_engine.infrastructure.db.player_lifecycle_state", "load_saved_lifecycle", "inputs.saved_lifecycle"),
    ("beta_engine.infrastructure.db.player_health_state", "load_saved_health", "inputs.saved_health"),
    ("beta_engine.domain.players.calendar_native_sporting_intake", "develop_and_recover", "development.kernel"),
    ("beta_engine.application.calendar_tour_service", "CalendarTourService._apply", "execute.apply"),
    ("beta_engine.application.calendar_tour_service", "CalendarTourService.preview", "http.preview"),
    ("beta_engine.application.calendar_tour_service", "CalendarTourService.execute", "http.execute"),
    ("beta_engine.application.calendar_tour_service", "CalendarTourService.inspect", "http.inspect"),
)

_LOCAL = threading.local()
_TOTALS = {}
_TOTALS_LOCK = threading.Lock()


def _wrap(label, original):
    def measured(*args, **kwargs):
        stack = getattr(_LOCAL, "stack", None)
        if stack is None:
            stack = _LOCAL.stack = []
        stack.append(0.0)
        cpu, wall = time.thread_time(), time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            inclusive = time.thread_time() - cpu
            elapsed = time.perf_counter() - wall
            children = stack.pop()
            if stack:
                stack[-1] += inclusive
            with _TOTALS_LOCK:
                row = _TOTALS.setdefault(label, {"calls": 0, "cpu_inclusive": 0.0, "cpu_self": 0.0, "wall_inclusive": 0.0})
                row["calls"] += 1
                row["cpu_inclusive"] += inclusive
                row["cpu_self"] += inclusive - children
                row["wall_inclusive"] += elapsed

    measured.__wrapped__ = original
    return measured


def install_phases():
    import importlib

    for module_name, attribute, label in PHASES:
        module = importlib.import_module(module_name)
        owner, name = module, attribute
        if "." in attribute:
            cls, name = attribute.split(".")
            owner = getattr(module, cls)
        setattr(owner, name, _wrap(label, getattr(owner, name)))


def take_phases():
    with _TOTALS_LOCK:
        rows = {k: {f: round(v, 4) if isinstance(v, float) else v for f, v in row.items()} for k, row in _TOTALS.items()}
        _TOTALS.clear()
    return rows


def backup(source, destination):
    with sqlite3.connect(Path(source).as_uri() + "?mode=ro", uri=True) as s, sqlite3.connect(destination) as d:
        s.backup(d)


def database_bytes(path):
    path = Path(path)
    return {suffix or "db": (path.with_name(path.name + suffix).stat().st_size
                             if path.with_name(path.name + suffix).exists() else 0)
            for suffix in ("", "-wal")}


def peak_rss_mib():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def machine():
    model = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                  if line.startswith("model name")), platform.processor())
    memory = next((line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines()
                   if line.startswith("MemTotal")), "0")
    return {"cpu": model, "logical_cpus": os.cpu_count(), "mem_mib": int(memory) // 1024,
            "python": sys.version.split()[0], "platform": platform.platform()}


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


# --------------------------------------------------------------------- prepare

def _sign_prospects(server, repo, clock, targets):
    from beta_engine.infrastructure.db.repositories import RunProspectRecord
    from tests.api.test_saved_revision_history_api import _request
    from tests.application.test_calendar_native_prospect_intake import source_at
    from tests.application.test_prospect_persistence import _record

    world = repo.get_initial_world(run_id="run", branch_id="branch")
    records = []
    for index, target in enumerate(targets):
        pid = f"wt-born-s{target.season_index:02d}-w{target.week:02d}-{index:03d}"
        src = source_at(clock, target, pid=pid)
        records.append(RunProspectRecord(**(_record().__dict__ | {
            "prospect_id": pid, "run_id": "run", "world_id": world.world_package_id,
            "season_start_year": src["season_start_year"], "season_label": str(src["season_start_year"]),
            "season_week": src["season_week"], "calendar_year": src["calendar_year"],
            "year_week": src["year_week"], "birth_year": src["birth_year"],
            "birth_year_week": src["birth_year_week"], "age": 15, "country_code": src["country_code"],
            "status": "prospect", "display_name": f"Week transition arrival {index + 1}",
            "source_type": "native_calendar_15yo_cohort",
            "cohort_policy_version": "native_calendar_15yo_cohort_v1",
            "profile_version": "prospect_profile_v1", "profile_seed": "profile",
            "development_seed": "development", "potential_seed": "potential",
            "profile_json": src["profile"], "development_json": src["development"],
            "potential_json": src["potential"],
        })))
    repo.upsert_run_prospects(records)
    url = server.base_url + "/admin/runs/run/branches/branch/authoritative-simulation/prospect-source/save"
    code, review = _request("GET", url + "/preview")
    assert code == 200 and review["can_save"], review
    code, saved = _request("POST", url, {
        "expected_draft_version": review["draft_version"],
        "expected_run_prospect_source_fingerprint": review["run_prospect_source_fingerprint"],
    })
    assert code == 201, saved


def _plan(server, edition_ids, week, size):
    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour

    for number, edition_id in enumerate(edition_ids):
        view = inspect(server)
        current = view["state"]["week"]
        execute(server, command(view, "create-edition", name=edition_id + ":plan", data={
            "schema_version": "calendar_tournament_edition.v2", "edition_id": edition_id,
            "name": "Week transition load " + edition_id,
            "week": {**current, "week": week}, "announcement_week": {**current, "week": week - 1},
            "start_slot": 1, "simulation_seed": 9301 + number, "main_entrant_count": size,
            "ranked": True, "validity_weeks": current["calendar"]["weeks_per_year"],
            "point_table": dict((("champion", 1000), ("finalist", 600), ("semifinal", 360),
                                 ("quarterfinal", 216))[:size.bit_length()]),
        }))
        save_tour(server)


def _play(server, fields):
    """Disjoint simultaneous fields; shared real global slots; actual MatchEngine."""
    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour

    for edition_id, players in fields.items():
        execute(server, command(inspect(server), "submit", name=edition_id + ":submit",
                                edition_id=edition_id, data={"player_ids": list(players)}))
        for action in ("approve", "draw"):
            execute(server, command(inspect(server), action, name=edition_id + ":" + action,
                                    edition_id=edition_id))
        save_tour(server)
    slots = 0
    while (view := inspect(server))["next_slot"] is not None:
        slots += 1
        execute(server, command(view, "next-slot", name=f"wt-slot-{slots}"))
        save_tour(server)
    for edition_id in fields:
        execute(server, command(inspect(server), "confirm-result", name=edition_id + ":confirm",
                                edition_id=edition_id))
        save_tour(server)
    return slots


def prepare(args):
    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from beta_engine.domain.calendar.run_week_position import RunWeekPosition
    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup
    from tests.api.test_saved_revision_history_api import ApiServer

    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    database = out / "build.db"
    width = args.width
    clock = RunCalendar(width, 1, 2030, args.seasons)
    log = []

    def note(**row):
        row["elapsed_s"] = round(time.perf_counter() - started, 2)
        log.append(row)
        print(json.dumps(row), flush=True)

    started = time.perf_counter()
    with ApiServer(database_url=f"sqlite:///{database}") as server:
        repo, _ = setup(server, clock, count=args.players)
        note(step="setup", players=args.players)
        world = repo.get_initial_world(run_id="run", branch_id="branch")
        pros = tuple(sorted(world.initial_turn_pro.professional_player_ids)
                     if world.lifecycle_policy.requires_turn_pro else sorted(p.player_id for p in world.players))
        # Arrivals in every later week of season 1 and in Week 1 of season 2.
        targets = [RunWeekPosition(calendar=clock, season_index=0, week=w)
                   for w in range(3, width + 1) for _ in range(args.born_per_week)]
        if args.seasons > 1:
            targets += [RunWeekPosition(calendar=clock, season_index=1, week=1)] * args.born_per_week
        _sign_prospects(server, repo, clock, targets)
        note(step="prospects", arrivals=len(targets))
        play_week = min(4, width)
        size = args.edition_size
        fields = {f"wt-ranked-{n + 1}": pros[n * size:(n + 1) * size] for n in range(args.editions)}
        _plan(server, tuple(fields), play_week, size)
        note(step="planned", editions=len(fields), week=play_week)
        while True:
            view = inspect(server)
            week = view["state"]["week"]
            if week["week"] == play_week and week["season_index"] == 0 and not view["state"]["editions"][0]["result_confirmed"]:
                slots = _play(server, fields)
                note(step="played", editions=len(fields), slots=slots)
                view = inspect(server)
            snapshot = out / f"week-{week['season_index']:02d}-{week['week']:02d}.db"
            with sqlite3.connect(database) as live:
                live.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            backup(database, snapshot)
            note(step="snapshot", file=snapshot.name, players=len(view["players"]),
                 saved_head=view["saved_head_revision_id"])
            if week["season_index"] == args.stop_season and week["week"] == args.stop_week:
                break
            action = "season-transition" if week["week"] == width else "transition"
            if view["season_transition_blockers" if action == "season-transition" else "transition_blockers"]:
                raise RuntimeError(view)
            execute(server, command(view, action, name=f"wt-s{week['season_index']}-w{week['week']}-{action}"))
            save_tour(server)
            note(step=action, season=week["season_index"], week=week["week"])
    meta = {"git_sha": git("rev-parse", "HEAD"), "source_tree": git("rev-parse", "HEAD:src"),
            "args": {k: str(v) for k, v in vars(args).items()}, "machine": machine(),
            "steps": log, "snapshots": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in sorted(out.glob("week-*.db"))}}
    (out / "fixture.json").write_text(json.dumps(meta, indent=1))
    database.unlink()
    for suffix in ("-wal", "-shm"):
        Path(str(database) + suffix).unlink(missing_ok=True)


# --------------------------------------------------------------------- measure

class _Sampler(threading.Thread):
    def __init__(self, database):
        super().__init__(daemon=True)
        self.database, self.stop, self.peak_db_wal = database, threading.Event(), 0

    def run(self):
        while not self.stop.wait(0.05):
            self.peak_db_wal = max(self.peak_db_wal, sum(database_bytes(self.database).values()))


def measure(args):
    from beta_engine.api import deps
    from tests.api.test_calendar_tour_flow import command, tour_url
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    if subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "src"], check=False).returncode:
        raise ValueError("Commit production source before measuring")
    root = args.root
    root.mkdir(parents=True, exist_ok=args.restart_child)
    database = root / "run.db"
    if not args.restart_child:
        input_sha = hashlib.sha256(args.input.read_bytes()).hexdigest()
        if args.sha256 and input_sha != args.sha256:
            raise ValueError("Input SHA-256 mismatch")
        backup(args.input, database)
    else:
        input_sha = json.loads((root / "timings.json").read_text())["metadata"]["input_sha256"]
    ids = count()
    deps.uuid4 = lambda: uuid5(NAMESPACE_URL, f"week-transition-ab:{input_sha}:{args.restart_child}:{next(ids)}")
    if args.phases:
        install_phases()
    profiler = [None]
    if args.profile:
        # The endpoint runs in a server worker thread: profile there, not the client.
        import importlib

        for module_name, attribute in (
            ("beta_engine.application.calendar_tour_service", "CalendarTourService.inspect"),
            ("beta_engine.application.calendar_tour_service", "CalendarTourService.preview"),
            ("beta_engine.application.calendar_tour_service", "CalendarTourService.execute"),
            ("beta_engine.application.run_working_draft_service", "RunWorkingDraftService.save_calendar_tour"),
        ):
            cls_name, name = attribute.split(".")
            owner = getattr(importlib.import_module(module_name), cls_name)

            def profiled(*a, _original=getattr(owner, name), **k):
                return profiler[0].runcall(_original, *a, **k) if profiler[0] else _original(*a, **k)

            setattr(owner, name, profiled)
    rows = []
    sampler = _Sampler(database)
    sampler.start()
    with ApiServer(database_url=f"sqlite:///{database}") as server:
        url = tour_url(server)

        def phase(label, method, path="", body=None, expect=200):
            take_phases()
            if args.profile:
                profiler[0] = cProfile.Profile()
            cpu = resource.getrusage(resource.RUSAGE_SELF)
            started = time.perf_counter()
            status, value = _request(method, url + path, body)
            seconds = time.perf_counter() - started
            after = resource.getrusage(resource.RUSAGE_SELF)
            assert status == expect, (label, status, value)
            row = {"phase": label, "seconds": round(seconds, 3),
                   "process_cpu_s": round(after.ru_utime + after.ru_stime - cpu.ru_utime - cpu.ru_stime, 3),
                   "peak_rss_mib": peak_rss_mib(), **{f"bytes_{k}": v for k, v in database_bytes(database).items()}}
            if args.phases:
                row["stages"] = take_phases()
            if args.profile:
                prof, profiler[0] = profiler[0], None
                prof.create_stats()
                prefix = "restart-" if args.restart_child else ""
                with open(root / f"{prefix}{label}.pstats", "wb") as stream:
                    marshal.dump(prof.stats, stream)
                with open(root / f"{prefix}{label}.txt", "w") as stream:
                    pstats.Stats(prof, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(120)
            rows.append(row)
            print(json.dumps({k: v for k, v in row.items() if k != "stages"}), flush=True)
            return value

        view = phase("restart_cold_get" if args.restart_child else "cold_get", "GET")
        if args.restart_child:
            expected = json.loads((root / "expected.json").read_text())
            assert view == expected, "Complete inspection differs after physical restart"
            week = view["state"]["week"]
            action = "season-transition" if week["week"] == week["calendar"]["weeks_per_year"] else "transition"
            if view["season_transition_blockers" if action == "season-transition" else "transition_blockers"]:
                # The next boundary is legitimately blocked (an Edition is due);
                # continue with a real reviewed planning command instead.
                current = {**week, "calendar": view["run_calendar"]}
                target = min(week["week"] + 2, week["calendar"]["weeks_per_year"])
                nxt = command(view, "create-edition", name="wt-ab-continuation", data={
                    "schema_version": "calendar_tournament_edition.v2", "edition_id": "wt-ab-continuation",
                    "name": "Continuation after restart", "week": {**current, "week": target},
                    "announcement_week": {**current, "week": target - 1}, "start_slot": 1,
                    "simulation_seed": 9401, "main_entrant_count": 4, "ranked": True,
                    "validity_weeks": week["calendar"]["weeks_per_year"],
                    "point_table": {"champion": 100, "finalist": 60, "semifinal": 30}})
            else:
                nxt = command(view, action, name="wt-ab-continuation")
            phase("restart_continuation_preview", "POST", "/preview", nxt)
        else:
            cmd = command(view, args.action, name="wt-ab-measured")
            review = phase("preview", "POST", "/preview", cmd)
            request = {"command": cmd, "expected_preview_fingerprint": review["preview_fingerprint"],
                       "explicit_confirmation": True}
            result = phase("execute", "POST", "/execute", request, expect=201)
            view = phase("draft_get", "GET")
            assert not view["saved"]
            receipt = phase("save", "POST", "/save", {
                "expected_draft_version": view["draft_version"],
                "expected_calendar_tour_fingerprint": view["tour_fingerprint"]}, expect=201)
            view = phase("first_saved_get", "GET")
            assert view["saved"]
            evidence = {
                "preview": review, "execute": result,
                "receipt_hash": receipt["saved_revision"].get("content_hash"),
                "players": view["players"], "ranking": view["state"]["rankings"][-1],
                "week": view["state"]["week"], "checkpoint_fingerprint": view["checkpoint_fingerprint"],
                "tour_fingerprint": view["tour_fingerprint"],
            }
            (root / "evidence.json").write_text(json.dumps(evidence, sort_keys=True))
            (root / "expected.json").write_text(json.dumps(view, sort_keys=True))
    sampler.stop.set()
    sampler.join()
    with sqlite3.connect(database) as db:
        integrity = db.execute("PRAGMA quick_check").fetchone()[0]
        revisions = db.execute("SELECT count(*) FROM branch_saved_revisions").fetchone()[0]
    metadata = {"git_sha": git("rev-parse", "HEAD"), "source_tree": git("rev-parse", "HEAD:src"),
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "input": str(args.input), "input_sha256": input_sha, "machine": machine(),
                "phases_instrumented": args.phases, "profiled": args.profile,
                "peak_rss_mib": peak_rss_mib(), "peak_db_plus_wal_bytes": sampler.peak_db_wal,
                "sqlite_quick_check": integrity, "saved_revisions": revisions}
    name = "restart.json" if args.restart_child else "timings.json"
    (root / name).write_text(json.dumps({"metadata": metadata, "phases": rows}, indent=1))
    if not args.restart_child:
        child = multiprocessing.get_context("spawn").Process(target=main, args=([
            "measure", f"--root={root}", f"--input={args.input}", "--restart-child",
        ],))
        child.start()
        child.join()
        if child.exitcode != 0:
            raise RuntimeError(f"Fresh-process restart failed: {child.exitcode}")


def stage(args):
    """In-process: the exact production transition candidate, repeated.

    Loads the real authenticated context once (same code as Preview), then
    times ``_prepare`` (blockers + candidate) and reports a digest of the
    complete preview body and successor checkpoint for exact A/B equality.
    """
    from sqlalchemy import text

    from beta_engine.api.deps import build_runtime
    from beta_engine.application.calendar_tour_service import CalendarTourService, CalendarTourCommand
    from beta_engine.domain.run_packages import canonical_hash
    from tests.api.test_calendar_tour_flow import command

    root = args.root
    root.mkdir(parents=True, exist_ok=False)
    database = root / "run.db"
    backup(args.input, database)
    if args.phases:
        install_phases()
    repository = build_runtime(database_url=f"sqlite:///{database}").repository
    service = CalendarTourService(repository)
    view = service.inspect(run_id="run", branch_id="branch")
    view = json.loads(json.dumps(view))
    week = view["state"]["week"]
    action = "season-transition" if week["week"] == week["calendar"]["weeks_per_year"] else "transition"
    cmd = CalendarTourCommand.model_validate(command(view, action, name="wt-ab-measured"))
    rows, digests = [], set()
    profile = cProfile.Profile() if args.profile else None
    from beta_engine.infrastructure.db.cyclic_gc import paused_cyclic_gc

    # Production Preview/Execute run with the cyclic collector paused.
    with paused_cyclic_gc(), repository._session_factory() as session:
        session.execute(text("BEGIN"))
        from beta_engine.domain.tournaments.calendar_global_slots import (
            _prime_private_fingerprint, global_replay_projection_scope,
        )

        fingerprints = {}
        loaded = service._context(session, "run", "branch", _fingerprints=fingerprints)
        for _ in range(args.repeat):
            take_phases()
            cpu, wall = time.thread_time(), time.perf_counter()
            if profile:
                profile.enable()
            # Exactly as Execute: a fresh private scope primed only with the
            # context's own canonical hashes, then the shared preparation.
            with global_replay_projection_scope():
                for value, fingerprint in fingerprints.values():
                    _prime_private_fingerprint(value, fingerprint)
                preview, ctx, state, authority, successor = service._prepare_from_context(
                    session, "run", "branch", cmd, *loaded)
            if profile:
                profile.disable()
            rows.append({"cpu_s": round(time.thread_time() - cpu, 4), "wall_s": round(time.perf_counter() - wall, 4),
                         **({"stages": take_phases()} if args.phases else {})})
            digests.add((preview["preview_fingerprint"], canonical_hash(json.loads(json.dumps(preview))),
                         successor.fingerprint))
    assert len(digests) == 1, digests
    preview_fp, body_hash, successor_fp = digests.pop()
    result = {"metadata": {"git_sha": git("rev-parse", "HEAD"), "source_tree": git("rev-parse", "HEAD:src"),
                           "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
                           "machine": machine(), "action": action, "players": len(view["players"]),
                           "week": week, "repeat": args.repeat},
              "preview_fingerprint": preview_fp, "preview_body_sha256": body_hash,
              "successor_checkpoint_fingerprint": successor_fp, "rows": rows}
    (root / "stage.json").write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k != "rows"} | {"cpu_s": [r["cpu_s"] for r in rows]}))
    if profile:
        profile.create_stats()
        with open(root / "stage.pstats", "wb") as stream:
            marshal.dump(profile.stats, stream)
        with open(root / "stage.txt", "w") as stream:
            pstats.Stats(profile, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(120)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--players", type=int, default=1000)
    p.add_argument("--width", type=int, default=8)
    p.add_argument("--seasons", type=int, default=3)
    p.add_argument("--born-per-week", type=int, default=4)
    p.add_argument("--edition-size", type=int, choices=(4, 8), default=8)
    p.add_argument("--editions", type=int, default=4)
    p.add_argument("--stop-season", type=int, default=1)
    p.add_argument("--stop-week", type=int, default=1)
    m = sub.add_parser("measure")
    m.add_argument("--input", type=Path, required=True)
    m.add_argument("--sha256")
    m.add_argument("--root", type=Path, required=True)
    m.add_argument("--action", choices=("transition", "season-transition"), default="transition")
    m.add_argument("--phases", action="store_true")
    m.add_argument("--profile", action="store_true")
    m.add_argument("--restart-child", action="store_true", help=argparse.SUPPRESS)
    t = sub.add_parser("stage")
    t.add_argument("--input", type=Path, required=True)
    t.add_argument("--root", type=Path, required=True)
    t.add_argument("--repeat", type=int, default=5)
    t.add_argument("--phases", action="store_true")
    t.add_argument("--profile", action="store_true")
    args = parser.parse_args(argv)
    {"prepare": prepare, "measure": measure, "stage": stage}[args.mode](args)


if __name__ == "__main__":
    main()

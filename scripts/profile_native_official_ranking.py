"""Real HTTP/SQLite native Official Ranking A/B: long-history fixture and phases.

Diagnostic only; its timings are never a pass criterion.

``prepare`` builds one immutable native birth Run through the production API:
an initial world of N players, signed 15-year-old arrivals, and ranked
Editions played by the actual MatchEngine in MANY weeks (``--edition-weeks``)
across the Season boundary, every week explicitly Saved. Their validity is W,
so results expire after the boundary while their sources remain in the proof.
A SQLite backup of every Saved week is kept (``week-SS-WW.db``).

``measure`` copies one fixture (opening the input read-only), then runs cold
GET, Preview, Execute, the draft GET, explicit Save and the first Saved GET over
HTTP, reopens the copy in a fresh process, compares the complete inspection and
previews the next command. ``--phases`` adds per-thread CPU for the ranking
stages (results, eligibility, Best N calculation, proof) and the number of
results/Editions actually rebuilt; it is reported separately from plain timing.

``stage`` repeats the exact production transition candidate in-process on one
authenticated context and reports per-phase CPU, the counts and the digests of
the complete preview body and successor checkpoint.

``report`` compares measure roots: same input/instrumentation, identical
complete evidence (responses, ranking, proof, Saved revision hash).
"""

import argparse
import hashlib
import json
import multiprocessing
import os
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import closing
from itertools import count
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scripts.process_measurement import machine, peak_rss_kib  # noqa: E402

# (module, attribute, phase label). Wrapped only with --phases.
PHASES = (
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "prepare_native_tour_week", "transition.native_week"),
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "native_confirmed_results", "ranking.results"),
    ("beta_engine.domain.tournaments.calendar_native_tour_week", "calculate_native_ranking_from_signed_lifecycle", "ranking.bridge"),
    ("beta_engine.domain.players.calendar_native_ranking_bridge", "verify_calendar_native_birth_history", "ranking.eligibility_lifecycle_replay"),
    ("beta_engine.domain.players.calendar_native_ranking_bridge", "validate_previous_ranking_owner", "ranking.eligibility_previous"),
    ("beta_engine.domain.players.calendar_native_ranking_bridge", "calculate_calendar_official_ranking", "ranking.best_n"),
    ("beta_engine.domain.players.calendar_native_ranking_bridge", "result_source_fingerprints", "ranking.proof_fingerprints"),
    ("beta_engine.domain.tournaments.calendar_tour", "edition_results", "ranking.edition_results_rebuilt"),
    ("beta_engine.domain.tournaments.calendar_global_slots", "completed_tournaments", "played.completed_tournaments"),
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
        cpu = time.thread_time()
        value = None
        try:
            value = original(*args, **kwargs)
            return value
        finally:
            inclusive = time.thread_time() - cpu
            children = stack.pop()
            if stack:
                stack[-1] += inclusive
            with _TOTALS_LOCK:
                row = _TOTALS.setdefault(label, {"calls": 0, "cpu_inclusive": 0.0, "cpu_self": 0.0, "items": 0})
                row["calls"] += 1
                row["cpu_inclusive"] += inclusive
                row["cpu_self"] += inclusive - children
                if isinstance(value, tuple) and label in {"ranking.results", "ranking.edition_results_rebuilt"}:
                    row["items"] += len(value)

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
        if not hasattr(owner, name):
            continue  # the baseline tree lacks a candidate-only seam
        setattr(owner, name, _wrap(label, getattr(owner, name)))


def take_phases():
    with _TOTALS_LOCK:
        rows = {k: {f: round(v, 4) if isinstance(v, float) else v for f, v in row.items()}
                for k, row in sorted(_TOTALS.items())}
        _TOTALS.clear()
    return rows


def backup(source, destination):
    uri = source.resolve(strict=True).as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as reader, closing(sqlite3.connect(destination)) as writer:
        reader.backup(writer)


def file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def peak_rss_mib():
    return round(peak_rss_kib() / 1024, 1)


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
        pid = f"rk-born-s{target.season_index:02d}-w{target.week:02d}-{index:03d}"
        src = source_at(clock, target, pid=pid)
        records.append(RunProspectRecord(**(_record().__dict__ | {
            "prospect_id": pid, "run_id": "run", "world_id": world.world_package_id,
            "season_start_year": src["season_start_year"], "season_label": str(src["season_start_year"]),
            "season_week": src["season_week"], "calendar_year": src["calendar_year"],
            "year_week": src["year_week"], "birth_year": src["birth_year"],
            "birth_year_week": src["birth_year_week"], "age": 15, "country_code": src["country_code"],
            "status": "prospect", "display_name": f"Ranking arrival {index + 1}",
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


def _plan(server, schedule, size):
    """One reviewed create-edition command per (season, week, n); announced a week earlier."""
    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour

    table = dict((("champion", 1000), ("finalist", 600), ("semifinal", 360),
                  ("quarterfinal", 216))[:size.bit_length()])
    for number, (edition_id, season, week) in enumerate(schedule):
        view = inspect(server)
        current = view["state"]["week"]
        width = current["calendar"]["weeks_per_year"]
        announce = (season, week - 1) if week > 1 else (season - 1, width)
        execute(server, command(view, "create-edition", name=edition_id + ":plan", data={
            "schema_version": "calendar_tournament_edition.v2", "edition_id": edition_id,
            "name": "Ranking load " + edition_id,
            "week": {**current, "season_index": season, "week": week},
            "announcement_week": {**current, "season_index": announce[0], "week": announce[1]},
            "start_slot": 1, "simulation_seed": 9501 + number, "main_entrant_count": size,
            "ranked": True, "validity_weeks": width, "point_table": table,
        }))
        save_tour(server)


def _play(server, fields, tag):
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
        execute(server, command(view, "next-slot", name=f"rk-{tag}-slot-{slots}"))
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
    stop = (args.stop_season, args.stop_week)
    width = args.width
    if not (0 <= args.stop_season < args.seasons and 1 <= args.stop_week <= width):
        raise ValueError("Requested stop must be inside the Run calendar")
    out.mkdir(parents=True, exist_ok=False)
    database = out / "build.db"
    clock = RunCalendar(width, 1, 2030, args.seasons)
    log = []
    started = time.perf_counter()

    def note(**row):
        row["elapsed_s"] = round(time.perf_counter() - started, 2)
        log.append(row)
        print(json.dumps(row), flush=True)

    # Edition weeks: every week from 4 in season 0 (announced from W3), then season 1 weeks 1..k.
    weeks = [(0, w) for w in range(4, width + 1)] + [(1, w) for w in range(1, width + 1)]
    weeks = [w for w in weeks if w < stop][: args.edition_weeks]
    with ApiServer(database_url=f"sqlite:///{database}") as server:
        repo, _ = setup(server, clock, count=args.players)
        note(step="setup", players=args.players)
        world = repo.get_initial_world(run_id="run", branch_id="branch")
        pros = tuple(sorted(world.initial_turn_pro.professional_player_ids)
                     if world.lifecycle_policy.requires_turn_pro else sorted(p.player_id for p in world.players))
        targets = [RunWeekPosition(calendar=clock, season_index=0, week=w)
                   for w in range(3, width + 1) for _ in range(args.born_per_week)]
        if args.seasons > 1:
            targets += [RunWeekPosition(calendar=clock, season_index=1, week=1)] * args.born_per_week
        _sign_prospects(server, repo, clock, targets)
        note(step="prospects", arrivals=len(targets))
        size = args.edition_size
        schedule = [(f"rk-s{s}-w{w:02d}-{n + 1}", s, w) for s, w in weeks for n in range(args.editions)]
        _plan(server, schedule, size)
        note(step="planned", editions=len(schedule), weeks=len(weeks))
        while True:
            view = inspect(server)
            week = view["state"]["week"]
            position = (week["season_index"], week["week"])
            if position > stop:
                raise ValueError(f"Fixture opens at {position}, after requested stop {stop}")
            due = [a["edition"]["edition_id"] for a in view["state"]["editions"]
                   if (a["edition"]["week"]["season_index"], a["edition"]["week"]["week"]) == position
                   and not a["result_confirmed"]]
            if due:
                # Rotate overlapping fields so players accumulate several results.
                # Only players still active now: a Season Transition retires some.
                active = {p["player_id"] for p in view["players"] if p["status"] == "active"}
                eligible = tuple(pid for pid in pros if pid in active)
                shift = (len(weeks) and weeks.index(position)) * size // 2
                pool = eligible[shift % len(eligible):] + eligible[:shift % len(eligible)]
                fields = {eid: pool[n * size:(n + 1) * size] for n, eid in enumerate(sorted(due))}
                slots = _play(server, fields, f"s{position[0]}w{position[1]}")
                note(step="played", week=position, editions=len(fields), slots=slots)
                view = inspect(server)
            snapshot = out / f"week-{week['season_index']:02d}-{week['week']:02d}.db"
            with closing(sqlite3.connect(database)) as live:
                live.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            backup(database, snapshot)
            confirmed = sum(a["result_confirmed"] for a in view["state"]["editions"])
            note(step="snapshot", file=snapshot.name, players=len(view["players"]),
                 confirmed_editions=confirmed, saved_head=view["saved_head_revision_id"])
            if position == stop:
                break
            action = "season-transition" if week["week"] == width else "transition"
            if view["season_transition_blockers" if action == "season-transition" else "transition_blockers"]:
                raise RuntimeError(view)
            execute(server, command(view, action, name=f"rk-s{week['season_index']}-w{week['week']}-{action}"))
            save_tour(server)
            note(step=action, season=week["season_index"], week=week["week"])
    meta = {"git_sha": git("rev-parse", "HEAD"), "source_tree": git("rev-parse", "HEAD:src"),
            "args": {k: str(v) for k, v in vars(args).items()}, "machine": machine(),
            "steps": log, "snapshots": {p.name: file_sha(p) for p in sorted(out.glob("week-*.db"))}}
    (out / "fixture.json").write_text(json.dumps(meta, indent=1))
    database.unlink()
    for suffix in ("-wal", "-shm"):
        Path(str(database) + suffix).unlink(missing_ok=True)


# --------------------------------------------------------------------- measure

def _evidence(review, result, receipt, view):
    impact = (result.get("impact") or {})
    return {
        "preview": review, "execute": result,
        "receipt_hash": receipt["saved_revision"].get("content_hash"),
        "saved_revision_id": receipt["saved_revision"].get("revision_id"),
        "ranking": view["state"]["rankings"][-1],
        "ranking_fingerprint": impact.get("ranking_fingerprint"),
        "ranking_adoption_fingerprint": impact.get("ranking_adoption_fingerprint"),
        "players": view["players"], "week": view["state"]["week"],
        "checkpoint_fingerprint": view["checkpoint_fingerprint"],
        "tour_fingerprint": view["tour_fingerprint"],
    }


def _client(timeout):
    """The test helper's HTTP request with an explicit client wait.

    Measurement only. 120 s is the tests' transport bound; a longer wait is
    reported in the metadata, so a read slower than the bound is recorded as
    such rather than hidden. No server or test timeout changes.
    """
    from tests.api import test_saved_revision_history_api as helper

    def call(method, url, payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        http_request = helper.request.Request(url, data=body, method=method)
        http_request.add_header("content-type", "application/json")
        try:
            with helper.request.urlopen(http_request, timeout=timeout) as response:
                raw = response.read().decode()
                return response.status, (json.loads(raw) if raw else {})
        except helper.error.HTTPError as exc:
            raw = exc.read().decode()
            return int(exc.code), (json.loads(raw) if raw else {})

    return call


def measure(args):
    from beta_engine.api import deps
    from tests.api.test_calendar_tour_flow import command, tour_url
    from tests.api.test_saved_revision_history_api import ApiServer

    _request = _client(args.client_timeout)

    if subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "src"], check=False).returncode:
        raise ValueError("Commit production source before measuring")
    root = args.root
    root.mkdir(parents=True, exist_ok=args.restart_child)
    database = root / "run.db"
    if not args.restart_child:
        input_sha = file_sha(args.input)
        if args.sha256 and input_sha != args.sha256:
            raise ValueError("Input SHA-256 mismatch")
        backup(args.input, database)
    else:
        input_sha = json.loads((root / "timings.json").read_text())["metadata"]["input_sha256"]
    ids = count()
    deps.uuid4 = lambda: uuid5(NAMESPACE_URL, f"ranking-ab:{input_sha}:{args.restart_child}:{next(ids)}")
    if args.phases:
        install_phases()
    rows = []
    with ApiServer(database_url=f"sqlite:///{database}") as server:
        url = tour_url(server)

        def phase(label, method, path="", body=None, expect=200):
            take_phases()
            cpu, started = time.process_time(), time.perf_counter()
            status, value = _request(method, url + path, body)
            row = {"phase": label, "seconds": round(time.perf_counter() - started, 3),
                   "over_test_transport_bound": time.perf_counter() - started > 120,
                   "process_cpu_s": round(time.process_time() - cpu, 3), "peak_rss_mib": peak_rss_mib()}
            assert status == expect, (label, status, value)
            if args.phases:
                row["stages"] = take_phases()
            rows.append(row)
            print(json.dumps({k: v for k, v in row.items() if k != "stages"}), flush=True)
            return value

        view = phase("restart_cold_get" if args.restart_child else "cold_get", "GET")
        if args.restart_child:
            expected = json.loads((root / "expected.json").read_text())
            assert view == expected, "Complete inspection differs after physical restart"
            week = view["state"]["week"]
            action = "season-transition" if week["week"] == week["calendar"]["weeks_per_year"] else "transition"
            if not view["season_transition_blockers" if action == "season-transition" else "transition_blockers"]:
                phase("restart_continuation_preview", "POST", "/preview",
                      command(view, action, name="rk-ab-continuation"))
        else:
            week = view["state"]["week"]
            action = "season-transition" if week["week"] == week["calendar"]["weeks_per_year"] else "transition"
            cmd = command(view, action, name="rk-ab-measured")
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
            (root / "evidence.json").write_text(json.dumps(_evidence(review, result, receipt, view), sort_keys=True))
            (root / "expected.json").write_text(json.dumps(view, sort_keys=True))
    with closing(sqlite3.connect(database)) as db:
        integrity = db.execute("PRAGMA quick_check").fetchone()[0]
        revisions = db.execute("SELECT count(*) FROM branch_saved_revisions").fetchone()[0]
    if integrity != "ok":
        raise ValueError(f"Fixture copy failed SQLite quick_check: {integrity}")
    from beta_engine.domain.tournaments import calendar_native_tour_week as native_week

    stats = getattr(native_week, "native_results_cache_stats", None)
    metadata = {"results_cache": stats() if stats else None,
                "git_sha": git("rev-parse", "HEAD"), "source_tree": git("rev-parse", "HEAD:src"),
                "script_sha256": file_sha(Path(__file__)), "input": str(args.input),
                "input_sha256": input_sha, "machine": machine(), "phases_instrumented": args.phases,
                "client_timeout_s": args.client_timeout,
                "peak_rss_mib": peak_rss_mib(), "sqlite_quick_check": integrity, "saved_revisions": revisions}
    name = "restart.json" if args.restart_child else "timings.json"
    (root / name).write_text(json.dumps({"metadata": metadata, "phases": rows}, indent=1))
    if not args.restart_child:
        child = multiprocessing.get_context("spawn").Process(target=main, args=([
            "measure", f"--root={root}", f"--input={args.input}", "--restart-child",
            f"--client-timeout={args.client_timeout}",
            *(["--phases"] if args.phases else []),
        ],))
        child.start()
        child.join()
        if child.exitcode != 0:
            raise RuntimeError(f"Fresh-process restart failed: {child.exitcode}")


def stage(args):
    """In-process: the exact production transition candidate, repeated."""
    from sqlalchemy import text

    from beta_engine.api.deps import build_runtime
    from beta_engine.application.calendar_tour_service import CalendarTourCommand, CalendarTourService
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.domain.tournaments.calendar_global_slots import (
        _prime_private_fingerprint, global_replay_projection_scope,
    )
    from beta_engine.infrastructure.db.cyclic_gc import paused_cyclic_gc
    from tests.api.test_calendar_tour_flow import command

    root = args.root
    root.mkdir(parents=True, exist_ok=False)
    database = root / "run.db"
    backup(args.input, database)
    install_phases()
    repository = build_runtime(database_url=f"sqlite:///{database}").repository
    service = CalendarTourService(repository)
    view = json.loads(json.dumps(service.inspect(run_id="run", branch_id="branch")))
    take_phases()
    week = view["state"]["week"]
    action = "season-transition" if week["week"] == week["calendar"]["weeks_per_year"] else "transition"
    cmd = CalendarTourCommand.model_validate(command(view, action, name="rk-ab-measured"))
    rows, digests = [], set()
    with paused_cyclic_gc(), repository._session_factory() as session:
        session.execute(text("BEGIN"))
        fingerprints = {}
        loaded = service._context(session, "run", "branch", _fingerprints=fingerprints)
        take_phases()
        # --same-scope is the EXPERIMENT: every repeat after the first runs in
        # the first one's private scope, i.e. as if all private values derived
        # from the same verified inputs survived to the next request. That is
        # the upper bound of cross-request reuse; production never does it.
        outer = global_replay_projection_scope() if args.same_scope else None
        if outer is not None:
            outer.__enter__()
        try:
            for _ in range(args.repeat):
                cpu = time.thread_time()
                with global_replay_projection_scope():
                    for value, fingerprint in fingerprints.values():
                        _prime_private_fingerprint(value, fingerprint)
                    preview, _ctx, _state, _authority, successor = service._prepare_from_context(
                        session, "run", "branch", cmd, *loaded)
                rows.append({"cpu_s": round(time.thread_time() - cpu, 4), "stages": take_phases()})
                digests.add((preview["preview_fingerprint"], canonical_hash(json.loads(json.dumps(preview))),
                             successor.fingerprint))
        finally:
            if outer is not None:
                outer.__exit__(None, None, None)
    assert len(digests) == 1, digests
    preview_fp, body_hash, successor_fp = digests.pop()
    confirmed = sum(a["result_confirmed"] for a in view["state"]["editions"])
    result = {"metadata": {"git_sha": git("rev-parse", "HEAD"), "source_tree": git("rev-parse", "HEAD:src"),
                           "input_sha256": file_sha(args.input), "machine": machine(), "action": action,
                           "players": len(view["players"]), "confirmed_editions": confirmed,
                           "week": week, "repeat": args.repeat, "same_scope_experiment": args.same_scope,
                           "peak_rss_mib": peak_rss_mib()},
              "preview_fingerprint": preview_fp, "preview_body_sha256": body_hash,
              "successor_checkpoint_fingerprint": successor_fp, "rows": rows}
    (root / "stage.json").write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k != "rows"} | {"cpu_s": [r["cpu_s"] for r in rows]}))


def report(args):
    """Summarize measure roots: per-phase seconds, peaks and exact equality."""
    rows, digests, comparisons = [], {}, set()
    for root in args.roots:
        timing = json.loads((root / "timings.json").read_text())
        restart = json.loads((root / "restart.json").read_text())
        meta, restarted = timing["metadata"], restart["metadata"]
        if (restarted["input_sha256"] != meta["input_sha256"] or restarted["git_sha"] != meta["git_sha"]
                or "ok" != restarted["sqlite_quick_check"] or "ok" != meta["sqlite_quick_check"]):
            raise ValueError(f"{root}: restart evidence does not match the measured run")
        comparisons.add((meta["input_sha256"], meta["phases_instrumented"]))
        phases = {r["phase"]: r["seconds"] for r in timing["phases"] + restart["phases"]}
        cpu = {r["phase"]: r["process_cpu_s"] for r in timing["phases"] + restart["phases"]}
        digest = tuple(hashlib.sha256((root / name).read_bytes()).hexdigest()
                       for name in ("expected.json", "evidence.json"))
        digests.setdefault(digest, []).append(root.name)
        rows.append({"root": root.name, "git_sha": meta["git_sha"][:9], **phases,
                     "preview_execute_save_s": round(sum(phases[k] for k in ("preview", "execute", "save")), 3),
                     "preview_execute_cpu_s": round(cpu["preview"] + cpu["execute"], 3),
                     "peak_rss_mib": max(meta["peak_rss_mib"], restarted["peak_rss_mib"]),
                     "saved_revisions": restarted["saved_revisions"], "input_sha256": meta["input_sha256"][:12]})
    if len(comparisons) != 1:
        raise ValueError("Compare the same input SHA-256 and instrumentation mode")
    identical = len(digests) == 1
    print(json.dumps({"rows": rows, "identical_groups": list(digests.values()), "identical": identical}, indent=1))
    return 0 if identical else 2


# ------------------------------------------------------------------- synthetic

def _original_owner_check(previous, previous_life):
    """The pre-index per-row linear search, kept verbatim for comparison."""
    if any(row.player_id not in {person.player_id for person in previous_life.players}
           for row in previous.rows):
        raise ValueError("Previous ranking contains an athlete not born at its publication")
    for row in previous.rows:
        prior = next(p for p in previous_life.players if p.player_id == row.player_id)
        if (prior.tour_entry_week is None or prior.tour_entry_week.ordinal >= previous_life.week.ordinal
                or prior.status == "retired"):
            raise ValueError("Previous ranking contains an athlete without prior Tour Entry")


def synthetic(args):
    """SYNTHETIC growth only: pure domain inputs, no MatchEngine, no Saved data.

    P classified players and E ranked Editions (8 results each, validity W)
    spread over the weeks before a target just after the Season boundary, so
    part of the results has expired but stays in the proof. Times the owner
    check (original vs index), Best N calculation and proof fingerprints.
    """
    from types import SimpleNamespace

    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from beta_engine.domain.calendar.run_week_position import RunWeekPosition
    from beta_engine.domain.players.calendar_native_ranking_bridge import (
        result_source_fingerprints, validate_previous_ranking_owner,
    )
    from beta_engine.domain.rankings.calendar_official import (
        CalendarRankingPlayer, CalendarRankingResult, calculate_calendar_official_ranking,
    )
    from beta_engine.domain.rankings.official import OfficialRankingPolicy
    from beta_engine.domain.tournaments.calendar_tour import ranking_week

    width = 8
    clock = RunCalendar(width, 1, 2030, 3)
    policy = OfficialRankingPolicy(policy_id="synthetic", best_n=15)

    def at(ordinal):
        return RunWeekPosition(calendar=clock, season_index=ordinal // width, week=ordinal % width + 1)

    rows = []
    for players in args.players:
        for editions in args.editions:
            target = width + 2  # Season 2 Week 3: results older than W expired
            ids = [f"p{n:05d}" for n in range(players)]
            entrants = tuple(CalendarRankingPlayer(
                player_id=pid, tie_break_token=f"t{n:05d}", tour_entry_week=ranking_week(at(0)),
            ) for n, pid in enumerate(ids))
            results = []
            for e in range(editions):
                week = 1 + e % (target - 2)
                for place, n in enumerate(range(8)):
                    results.append(CalendarRankingResult(
                        edition_id=f"e{e:04d}", player_id=ids[(e * 5 + n) % players],
                        source_fingerprint=f"{e:04d}{n}".ljust(64, "0"),
                        completed_week=ranking_week(at(week)),
                        first_publication_week=ranking_week(at(week + 1)),
                        main_points=1000 >> place, validity_weeks=width))
            results = tuple(results)
            previous = calculate_calendar_official_ranking(
                run_id="r", branch_id="b", run_calendar=clock, week=ranking_week(at(target - 1)),
                policy=policy, players=entrants,
                results=tuple(r for r in results if r.first_publication_week.week + width * r.first_publication_week.season_index <= target - 1))
            life = SimpleNamespace(week=at(target - 1), players=tuple(SimpleNamespace(
                player_id=pid, tour_entry_week=at(0), status="active") for pid in ids))
            timings = {}

            def timed(name, call):
                cpu = time.thread_time()
                value = call()
                timings[name] = round(time.thread_time() - cpu, 4)
                return value

            replay = SimpleNamespace(run_id="r", branch_id="b")
            timed("owner_check_original", lambda: _original_owner_check(previous, life))
            timed("owner_check_index", lambda: validate_previous_ranking_owner(previous, life, replay))
            ranking = timed("best_n_calculation", lambda: calculate_calendar_official_ranking(
                run_id="r", branch_id="b", run_calendar=clock, week=ranking_week(at(target)),
                policy=policy, players=entrants, results=results, previous=previous))
            timed("proof_fingerprints", lambda: result_source_fingerprints(results))
            counted = sum(len(row.counted_results) for row in ranking.rows)
            row = {"synthetic": True, "players": players, "editions": editions, "results": len(results),
                   "counted": counted, "expired_or_uncounted": len(results) - counted, **timings}
            rows.append(row)
            print(json.dumps(row), flush=True)
    if args.out:
        args.out.write_text(json.dumps({"metadata": {"git_sha": git("rev-parse", "HEAD"), "machine": machine(),
                                                     "synthetic": True}, "rows": rows}, indent=1))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--players", type=int, default=1000)
    p.add_argument("--width", type=int, default=8)
    p.add_argument("--seasons", type=int, default=3)
    p.add_argument("--born-per-week", type=int, default=2)
    p.add_argument("--edition-size", type=int, choices=(4, 8), default=8)
    p.add_argument("--editions", type=int, default=2, help="Editions per Edition week")
    p.add_argument("--edition-weeks", type=int, default=8)
    p.add_argument("--stop-season", type=int, default=1)
    p.add_argument("--stop-week", type=int, default=4)
    m = sub.add_parser("measure")
    m.add_argument("--input", type=Path, required=True)
    m.add_argument("--sha256")
    m.add_argument("--root", type=Path, required=True)
    m.add_argument("--phases", action="store_true")
    m.add_argument("--client-timeout", type=float, default=120.0,
                   help="HTTP client wait in seconds (tests use 120)")
    m.add_argument("--restart-child", action="store_true", help=argparse.SUPPRESS)
    t = sub.add_parser("stage")
    t.add_argument("--input", type=Path, required=True)
    t.add_argument("--root", type=Path, required=True)
    t.add_argument("--repeat", type=int, default=3)
    t.add_argument("--same-scope", action="store_true",
                   help="experiment: later repeats reuse the first private scope")
    r = sub.add_parser("report")
    r.add_argument("roots", type=Path, nargs="+")
    y = sub.add_parser("synthetic")
    y.add_argument("--players", type=int, nargs="+", default=[250, 1000, 4000])
    y.add_argument("--editions", type=int, nargs="+", default=[16, 64, 256])
    y.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    os.environ.setdefault("BETA_ENGINE_NEW_RUN_SAVED_STORAGE", "saved_v2")
    return {"prepare": prepare, "measure": measure, "stage": stage, "report": report,
            "synthetic": synthetic}[args.mode](args)


if __name__ == "__main__":
    sys.exit(main())

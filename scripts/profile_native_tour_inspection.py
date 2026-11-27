"""Real HTTP/SQLite measurement of the full native Tour inspection GET.

Measurement only (issue #1918). The immutable input is a Saved v2 backup from
the nightly giant matrix. The script copies it into a fresh, empty ``--root``,
checks the copy's SHA-256 against ``--sha256``, runs SQLite ``quick_check`` and
reads Run/Branch, Saved HEAD, revision count and Tour position from the copy.
The original file is never opened for writing and no database is committed.

Scenarios (one fresh interpreter per invocation):

``states``
    GET after restart, the identical GET again, one real Working Draft change
    (the next real harness command, previewed and confirmed), the first and a
    repeated GET of that changed draft, explicit Save, the first and a repeated
    GET after Save, and finally the first GET after a server restart in a NEW
    process on the same copy.

``week``
    One complete next Tour week of the giant ``compatible`` load profile
    (Edition planning, submit/approve/draw, every real MatchEngine slot,
    result confirmation and the Week Transition), each with Preview, explicit
    confirmation and an explicit Save. ``--variant harness`` issues exactly
    the requests of the unchanged ``tests.api.test_calendar_tour_flow`` helpers
    used by ``giant_native_five_season_load.py`` (including its deliberate
    idempotency retry and the GETs before and after every Save).
    ``--variant minimal`` is the separate diagnostic arm: the same commands,
    Previews, confirmations, idempotency retries and Saves, but each GET only
    once per distinct state, and ``include_inspection`` on Execute where its
    inspection covers exactly the token read the next request needs. Its
    inspection cost is therefore charged to Execute.

Modes: ``timing`` installs nothing. ``phases`` wraps named production
functions with wall/CPU accumulators (no profiler). ``profile`` runs cProfile
around the in-process GET handler thread for CPU attribution. ``alloc`` traces
Python allocations (tracemalloc peak) per request. Use separate runs for CPU
and allocation profiles; their overhead distorts the other measurements.

OS ``rchar`` is NOT reported as physical SQLite I/O. ``db_bytes`` is the size
of the main SQLite file and ``wal_bytes`` the WAL after the scenario.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from process_measurement import machine, memory_kib  # noqa: E402

TOUR = "/admin/runs/{run}/branches/{branch}/calendar-tour"


# --------------------------------------------------------------------------
# Snapshot verification (copy only)
# --------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_copy(path: Path, expected_sha: str, run_id: str, branch_id: str) -> dict:
    actual = sha256_file(path)
    if actual != expected_sha:
        raise SystemExit(f"snapshot copy digest {actual} differs from {expected_sha}")
    # Read-only URI; the copy is opened for writing only by the server later.
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        quick = connection.execute("PRAGMA quick_check").fetchall()
        if quick != [("ok",)]:
            raise SystemExit(f"quick_check failed: {quick[:3]}")
        branch = connection.execute(
            "SELECT saved_head_revision_id FROM run_branches WHERE run_id=? AND branch_id=?",
            (run_id, branch_id)).fetchone()
        if branch is None:
            raise SystemExit("Run/Branch is not present in the snapshot")
        storage = connection.execute(
            "SELECT * FROM run_saved_storage_formats WHERE run_id=?", (run_id,)).fetchall()
        revisions = connection.execute(
            "SELECT COUNT(*) FROM branch_saved_revisions WHERE run_id=? AND branch_id=?",
            (run_id, branch_id)).fetchone()[0]
        tour = connection.execute(
            "SELECT payload_json FROM calendar_tour_authorities WHERE run_id=? AND branch_id=?",
            (run_id, branch_id)).fetchone()
        week = json.loads(tour[0])["week"] if tour else None
        checkpoint_bytes = connection.execute(
            "SELECT length(payload_json) FROM calendar_player_sporting_checkpoints WHERE run_id=? AND branch_id=?",
            (run_id, branch_id)).fetchone()
    return {
        "sha256": actual,
        "quick_check": "ok",
        "storage": storage,
        "saved_head_revision_id": branch[0],
        "saved_revision_count": revisions,
        "tour_week": week and {"season_index": week["season_index"], "week": week["week"]},
        "live_checkpoint_json_bytes": checkpoint_bytes and checkpoint_bytes[0],
        "tour_json_bytes": len(tour[0]) if tour else None,
    }


def history_digest(path: Path, run_id: str, branch_id: str) -> dict:
    """Sporting/revision/audit content with random revision IDs renamed by sequence."""
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        ids = [row[0] for row in connection.execute(
            "SELECT revision_id FROM branch_saved_revisions WHERE run_id=? AND branch_id=? ORDER BY sequence",
            (run_id, branch_id))]
        rename = {value: f"saved-revision#{index}" for index, value in enumerate(ids)}

        def normal(text: str) -> str:
            for value, label in rename.items():
                text = text.replace(value, label)
            return text

        def digest(rows) -> str:
            h = hashlib.sha256()
            for row in rows:
                h.update(normal(json.dumps(row, sort_keys=True, default=str)).encode())
            return h.hexdigest()

        out = {"saved_revisions": len(ids)}
        out["checkpoint"] = digest(connection.execute(
            "SELECT fingerprint, payload_json FROM calendar_player_sporting_checkpoints WHERE run_id=? AND branch_id=?",
            (run_id, branch_id)))
        out["tour"] = digest(connection.execute(
            "SELECT payload_json FROM calendar_tour_authorities WHERE run_id=? AND branch_id=?",
            (run_id, branch_id)))
        out["lifecycle"] = digest(connection.execute(
            "SELECT week_ordinal, fingerprint, payload_json FROM player_lifecycle_week_states WHERE run_id=? AND branch_id=? ORDER BY week_ordinal",
            (run_id, branch_id)))
        out["saved_kinds"] = [row[0] for row in connection.execute(
            "SELECT kind FROM branch_saved_revisions WHERE run_id=? AND branch_id=? ORDER BY sequence",
            (run_id, branch_id))]
        out["audit_events"] = connection.execute(
            "SELECT COUNT(*) FROM branch_revision_audit_events WHERE run_id=? AND branch_id=?",
            (run_id, branch_id)).fetchone()[0]
        out["audit_kinds"] = digest(connection.execute(
            "SELECT event_kind FROM branch_revision_audit_events WHERE run_id=? AND branch_id=? ORDER BY created_at, rowid",
            (run_id, branch_id)))
    return out


def normalized_view_digest(view: dict) -> str:
    """Complete inspection, except per-run random Saved revision IDs."""
    text = json.dumps(view, sort_keys=True)
    head = view.get("saved_head_revision_id")
    if head:
        text = text.replace(head, "saved-head")
    return hashlib.sha256(text.encode()).hexdigest()


# --------------------------------------------------------------------------
# Instrumentation (phases / profile / alloc)
# --------------------------------------------------------------------------

PHASES: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
_PHASE_LOCK = threading.Lock()


def _wrap(owner, name, label):
    raw = owner.__dict__[name] if isinstance(owner, type) else getattr(owner, name)
    static = isinstance(raw, staticmethod)
    function = raw.__func__ if static else raw

    def timed(*args, **kwargs):
        wall, cpu = time.perf_counter(), time.thread_time()
        try:
            return function(*args, **kwargs)
        finally:
            with _PHASE_LOCK:
                entry = PHASES[label]
                entry[0] += time.perf_counter() - wall
                entry[1] += time.thread_time() - cpu
                entry[2] += 1

    timed.__wrapped__ = function
    setattr(owner, name, staticmethod(timed) if static else timed)


def install_phase_timers():
    from beta_engine.application import calendar_tour_service as tour
    from beta_engine.application import calendar_native_tour_context as native_ctx
    from beta_engine.application import calendar_global_slot_service as slots
    from beta_engine.application import calendar_native_groups as groups
    from beta_engine.application import calendar_tour_save_projection as save_projection
    from beta_engine.application.calendar_standalone_match_service import CalendarStandaloneMatchService
    from beta_engine.infrastructure.db import calendar_sporting_checkpoint as checkpoint_db
    from beta_engine.infrastructure.db import calendar_standalone_match_state as match_state
    from beta_engine.infrastructure.db import native_fork_source_projection as projection
    from beta_engine.infrastructure.db import player_lifecycle_state as lifecycle_db
    from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository
    import fastapi.routing as routing

    targets = [
        (tour.CalendarTourService, "inspect", "GET.service"),
        (tour.CalendarTourService, "_context", "ctx"),
        (CalendarStandaloneMatchService, "_context", "ctx.saved_lineage_world"),
        (SimulationPersistenceRepository, "_validated_branch_revision_state_in_session",
         "ctx.saved_lineage_world.lineage_validation"),
        (projection, "decoded_global_tour_source", "ctx.saved_decode"),
        (projection, "decoded_global_checkpoint_component", "ctx.saved_decode.checkpoint"),
        (match_state, "load_match_rows", "ctx.live_match_rows"),
        (checkpoint_db, "load_checkpoint", "ctx.live_checkpoint"),
        (tour, "load_tour", "ctx.live_tour"),
        (native_ctx, "native_working_context", "ctx.native_working_context"),
        (tour, "verify_tour_origins", "ctx.tour_origins"),
        (tour, "decode_prevalidated_lifecycle", "ctx.saved_lifecycle_decode"),
        (tour.CalendarTourService, "_live_lifecycle", "ctx.live_lifecycle"),
        (tour.CalendarTourService, "_verify_lifecycle_and_entry", "ctx.lifecycle_entry_check"),
        (tour.CalendarTourService, "_project_inspection", "proj"),
        (tour.CalendarTourService, "_transition_blockers", "proj.readiness_blockers"),
        (groups, "inspect_groups", "proj.groups"),
        (slots, "slot_inspection", "proj.next_slot"),
        (tour, "edition_results", "proj.edition_results"),
        (tour, "get_lifecycle", "proj.current_lifecycle"),
        (tour, "completed_season_indices", "proj.completed_seasons"),
        (save_projection, "saved_inspection_value_fingerprint", "proj.save_projection_fingerprint"),
        (routing, "serialize_response", "http.serialize_response"),
    ]
    from fastapi.responses import JSONResponse
    targets.append((JSONResponse, "render", "http.json_render"))
    for owner, name, label in targets:
        _wrap(owner, name, label)


def take_phases() -> dict:
    with _PHASE_LOCK:
        out = {k: {"wall": round(v[0], 3), "cpu": round(v[1], 3), "calls": v[2]}
               for k, v in sorted(PHASES.items())}
        PHASES.clear()
    return out


class RequestProfiler:
    """cProfile/tracemalloc around each request handled on the server thread."""

    def __init__(self, mode: str, out_dir: Path):
        self.mode, self.out_dir, self.index = mode, out_dir, 0
        self.result = None

    def install(self):
        from beta_engine.application import calendar_tour_service as tour
        owner = tour.CalendarTourService
        function = owner.__dict__["inspect"]
        profiler = self

        def wrapped(*args, **kwargs):
            return profiler.run(function, *args, **kwargs)

        owner.inspect = wrapped

    def run(self, function, *args, **kwargs):
        if self.mode == "profile":
            import cProfile
            profile = cProfile.Profile()
            profile.enable()
            try:
                return function(*args, **kwargs)
            finally:
                profile.disable()
                path = self.out_dir / f"inspect-{self.index:03d}.prof"
                profile.dump_stats(path)
                self.result = {"profile": str(path)}
                self.index += 1
        import tracemalloc
        tracemalloc.start()
        try:
            return function(*args, **kwargs)
        finally:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            self.result = {"traced_peak_mib": round(peak / 2**20, 1),
                           "traced_retained_mib": round(current / 2**20, 1)}

    def take(self):
        result, self.result = self.result, None
        return result


# --------------------------------------------------------------------------
# HTTP client with per-request accounting
# --------------------------------------------------------------------------

@dataclass
class Client:
    base: str
    log: list
    stage: str = ""
    profiler: RequestProfiler | None = None
    phases: bool = False

    def call(self, method, path, payload=None, *, kind, label):
        body = None if payload is None else json.dumps(payload).encode()
        http_request = request.Request(self.base + path, data=body, method=method)
        http_request.add_header("content-type", "application/json")
        before = memory_kib()
        wall, cpu = time.perf_counter(), time.process_time()
        try:
            with request.urlopen(http_request, timeout=7200) as response:
                code, raw = response.status, response.read()
        except error.HTTPError as exc:
            code, raw = exc.code, exc.read()
        seconds = time.perf_counter() - wall
        cpu_seconds = time.process_time() - cpu
        after = memory_kib()
        record = {
            "stage": self.stage, "kind": kind, "label": label, "method": method,
            "status": code, "wall": round(seconds, 3), "process_cpu": round(cpu_seconds, 3),
            "response_bytes": len(raw), "rss_mib_after": round(after.get("VmRSS", 0) / 1024, 1),
            "peak_rss_mib": round(after.get("VmHWM", 0) / 1024, 1),
            "rss_mib_before": round(before.get("VmRSS", 0) / 1024, 1),
        }
        if self.phases:
            record["phases"] = take_phases()
        if self.profiler is not None:
            record["profiler"] = self.profiler.take()
        self.log.append(record)
        print(json.dumps({k: record[k] for k in ("stage", "kind", "label", "status", "wall", "response_bytes")}),
              flush=True)
        value = json.loads(raw) if raw else {}
        if code >= 300:
            raise RuntimeError(f"{method} {path} -> {code}: {str(value)[:2000]}")
        return code, value


class Tour:
    def __init__(self, client: Client, run_id: str, branch_id: str):
        self.client = client
        self.path = TOUR.format(run=run_id, branch=branch_id)

    def inspect(self, label="inspect"):
        return self.client.call("GET", self.path, kind="GET", label=label)[1]

    def preview(self, cmd):
        return self.client.call("POST", self.path + "/preview", cmd, kind="POST preview",
                                label=cmd["action"])[1]

    def execute(self, payload, *, include_inspection=False, label="execute"):
        suffix = "?include_inspection=true" if include_inspection else ""
        return self.client.call("POST", self.path + "/execute" + suffix, payload,
                                kind="POST execute", label=label)[1]

    def save(self, view):
        return self.client.call("POST", self.path + "/save", {
            "expected_draft_version": view["draft_version"],
            "expected_calendar_tour_fingerprint": view["tour_fingerprint"],
        }, kind="POST save", label="save")[1]


def command(view, action, *, name=None, edition_id=None, data=None):
    # Identical to tests.api.test_calendar_tour_flow.command (seed 231).
    return {
        "action": action, "command_id": name or action, "edition_id": edition_id,
        "expected_saved_head": view["saved_head_revision_id"],
        "expected_checkpoint_fingerprint": view["checkpoint_fingerprint"],
        "expected_tour_fingerprint": view["tour_fingerprint"],
        "seed": 231, "operator_label": "Admin",
        "audit_reason": "Reviewed actual configured native Tour operation",
        "data": data or {},
    }


class Flow:
    """The two request strategies over the identical command sequence."""

    def __init__(self, tour: Tour, variant: str):
        self.tour, self.variant = tour, variant
        self.view = None  # minimal: the current inspection of the CURRENT state

    # -- harness: exact tests.api.test_calendar_tour_flow helpers -------------
    def current(self, label="inspect"):
        if self.variant == "harness" or self.view is None:
            self.view = self.tour.inspect(label)
        return self.view

    def run(self, action, *, name, edition_id=None, data=None, view=None):
        # ``view``: the caller's own just-read inspection, exactly where the
        # giant harness builds the command from it (plan, next-slot).
        if self.variant == "harness":
            view = view if view is not None else self.tour.inspect("inspect:before-" + action)
        else:
            view = self.current("inspect:before-" + action)
        cmd = command(view, action, name=name, edition_id=edition_id, data=data)
        preview = self.tour.preview(cmd)
        confirm = {"command": cmd, "expected_preview_fingerprint": preview["preview_fingerprint"],
                   "explicit_confirmation": True}
        if self.variant == "harness":
            result = self.tour.execute(confirm, label=action)
            if action in {"play", "transition"}:
                # The helper's deliberate exact-retry idempotency check.
                again = self.tour.execute(confirm, label=action + ":idempotency-retry")
                assert again == result
            self.view = None
            return result
        out = self.tour.execute(confirm, include_inspection=True, label=action)
        assert out["schema_version"] == "calendar_tour_execution_inspection.v1"
        if action in {"play", "transition"}:
            # Not a read: the same idempotency retry stays in this arm too.
            again = self.tour.execute(confirm, label=action + ":idempotency-retry")
            assert again == out["result"]
        self.view = out["inspection"]
        return out["result"]

    def save(self):
        if self.variant == "harness":
            view = self.tour.inspect("inspect:before-save")
            assert not view["saved"]
            receipt = self.tour.save(view)
            assert self.tour.inspect("inspect:after-save")["saved"]
            self.view = None
            return receipt
        view = self.current()
        assert not view["saved"]
        receipt = self.tour.save(view)
        # The next command needs the new Saved HEAD/fingerprints: one GET.
        self.view = self.tour.inspect("inspect:after-save")
        assert self.view["saved"]
        return receipt


# --------------------------------------------------------------------------
# One giant "compatible" week (schedule logic from giant_native_five_season_load.py
# at harness pin 51dbde8990e0118af9827485ac12d3f27286c3e4, unchanged semantics)
# --------------------------------------------------------------------------

WEEKS_PER_SEASON = 52
MAIN_WEEKS = tuple(range(4, 51))
EXTRA_WEEKS = tuple(range(8, 49, 4)) + (44,)
TIERS = (("regional", 16, 100), ("challenger", 32, 250), ("international", 64, 500),
         ("major", 128, 1000), ("elite", 32, 1500))
STAGES = {n: tuple(("champion", "finalist", "semifinal", "quarterfinal", "round16", "round32",
                    "round64", "round128")[:n.bit_length()]) for n in (4, 8, 16, 32, 64, 128)}


@dataclass(frozen=True)
class Edition:
    season: int
    week: int
    tier: str
    size: int
    points: int
    number: int
    is_world_championship: bool = False
    entrant_offset: int = 0

    @property
    def edition_id(self):
        return f"load-s{self.season + 1:02d}-w{self.week:02d}-{self.number:03d}-{self.tier}"

    @property
    def point_table(self):
        return {stage: round(self.points * (0.60 ** i)) for i, stage in enumerate(STAGES[self.size])}


def compatible_schedule(season: int) -> tuple[Edition, ...]:
    entries = []
    for i, week in enumerate(MAIN_WEEKS):
        tier, size, points = TIERS[i % len(TIERS)]
        entries.append((week, season * 60 + i, tier, size, points, False))
    for i, week in enumerate(EXTRA_WEEKS):
        entries.append((week, season * 60 + len(MAIN_WEEKS) + i, "side", (16, 32, 64)[i % 3],
                        125 + 50 * (i % 3), False))
    entries.append((51, season * 60 + 59, "world-championship", 128, 3000, True))
    entries.sort(key=lambda e: (e[0], e[1]))
    out, previous, offset = [], None, 0
    for week, number, tier, size, points, wc in entries[:60]:
        if week != previous:
            offset = 0
        previous = week
        e = Edition(season, week, tier + "-compatible", 4 if size <= 32 else 8, points, number, wc, offset)
        out.append(e)
        offset += e.size
    return tuple(out)


def play_week(flow: Flow, season: int, week: int, initial_professionals: tuple[str, ...]):
    schedule = compatible_schedule(season)
    plans = [e for e in schedule if e.week - 2 == week]
    events = [e for e in schedule if e.week == week]
    view = flow.current("inspect:week-start")
    assert (view["state"]["week"]["season_index"], view["state"]["week"]["week"]) == (season, week)
    for edition in plans:
        flow.tour.client.stage = "plan:" + edition.edition_id
        view = flow.current("inspect:plan")
        wk = view["state"]["week"]
        payload = {
            "schema_version": "calendar_tournament_edition.v2", "edition_id": edition.edition_id,
            "name": (f"World Championship compatibility surrogate ({edition.size}-entrant Main)"
                     if edition.is_world_championship and edition.size <= 8
                     else f"{edition.tier.title()} Load Cup S{edition.season + 1} W{edition.week}"),
            "week": {**wk, "week": edition.week}, "announcement_week": {**wk, "week": edition.week - 1},
            "start_slot": 1, "simulation_seed": 90100 + edition.number,
            "main_entrant_count": edition.size, "ranked": True,
            "validity_weeks": WEEKS_PER_SEASON, "point_table": edition.point_table,
        }
        flow.run("create-edition", name=edition.edition_id + ":plan", data=payload, view=view)
        flow.save()
    matches = 0
    if events:
        flow.tour.client.stage = "fields"
        view = flow.current("inspect:fields")
        active = {p["player_id"] for p in view["players"]}
        eligible = [pid for pid in initial_professionals if pid in active]
        base = (season * 127 + week * 19) % len(eligible)
        fields = {e.edition_id: [eligible[(base + e.entrant_offset + n) % len(eligible)]
                                 for n in range(e.size)] for e in events}
        for e in events:
            flow.tour.client.stage = "entry:" + e.edition_id
            flow.run("submit", name=e.edition_id + ":submit", edition_id=e.edition_id,
                     data={"player_ids": fields[e.edition_id]})
            for action in ("approve", "draw"):
                flow.run(action, name=e.edition_id + ":" + action, edition_id=e.edition_id)
            flow.save()
        slot_count = 0
        while True:
            flow.tour.client.stage = f"slot:{slot_count + 1}"
            view = flow.current("inspect:next-slot")
            slot = view["next_slot"]
            if slot is None:
                break
            assert not slot["conflicts"] and slot["matches"], slot
            slot_count += 1
            matches += len(slot["matches"])
            flow.run("next-slot", name=f"load-s{season + 1}-w{week}-slot-{slot_count}", view=view)
            flow.save()
        for e in events:
            flow.tour.client.stage = "confirm:" + e.edition_id
            flow.run("confirm-result", name=e.edition_id + ":confirm", edition_id=e.edition_id)
            flow.save()
            view = flow.current("inspect:confirmed")
            assert next(r for r in view["state"]["editions"]
                        if r["edition"]["edition_id"] == e.edition_id)["result_confirmed"]
            assert len(view["edition_evidence"][e.edition_id]["matches"]) == e.size - 1
    flow.tour.client.stage = "transition"
    action = "transition" if week < WEEKS_PER_SEASON else "season-transition"
    flow.run(action, name=f"load-s{season + 1}-week-{week}-{action}")
    flow.save()
    flow.tour.client.stage = "week-end"
    final = flow.current("inspect:week-end")
    return {"planned": [e.edition_id for e in plans], "played": [e.edition_id for e in events],
            "matches": matches, "final_view": final}


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def summarize(log):
    by_kind = defaultdict(lambda: {"calls": 0, "wall": 0.0})
    for row in log:
        entry = by_kind[row["kind"]]
        entry["calls"] += 1
        entry["wall"] = round(entry["wall"] + row["wall"], 3)
    return dict(by_kind)


def deterministic_ids(seed: str):
    """Same API ID factory as scripts/profile_native_week_ab.py; gates unchanged."""
    from itertools import count
    from uuid import NAMESPACE_URL, uuid5

    from beta_engine.api import deps

    ids = count()
    deps.uuid4 = lambda: uuid5(NAMESPACE_URL, f"tour-inspection:{seed}:{next(ids)}")


def serve(database: Path, args, *, stage: str):
    from tests.api.test_saved_revision_history_api import ApiServer

    # Same sequence for both variants: they issue the same Saves in the same
    # order, so equal history digests prove equal sporting results.
    deterministic_ids(f"{args.sha256}:{args.scenario}:{stage}")
    log = []
    profiler = None
    if args.mode in {"profile", "alloc"}:
        profiler = RequestProfiler(args.mode, args.root)
        profiler.install()
    if args.mode == "phases":
        install_phase_timers()
    server = ApiServer(database_url=f"sqlite:///{database}")
    return server, Client(server.base_url, log, stage=stage, profiler=profiler,
                          phases=args.mode == "phases"), log


def restart_child(args) -> dict:
    """First GET in a brand-new interpreter on the same database copy."""
    database = args.root / "run.db"
    server, client, log = serve(database, args, stage="restart")
    with server:
        view = Tour(client, args.run_id, args.branch_id).inspect("inspect:after-restart")
    return {"log": log, "view_digest": normalized_view_digest(view)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--run-id", default="run")
    parser.add_argument("--branch-id", default="branch")
    parser.add_argument("--scenario", choices=("states", "week"), default="states")
    parser.add_argument("--variant", choices=("harness", "minimal"), default="harness")
    parser.add_argument("--mode", choices=("timing", "phases", "profile", "alloc"), default="timing")
    parser.add_argument("--no-restart", action="store_true")
    parser.add_argument("--restart-child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    os.environ.setdefault("BETA_ENGINE_NEW_RUN_SAVED_STORAGE", "saved_v2")
    if args.restart_child:
        print("RESULT " + json.dumps(restart_child(args)), flush=True)
        return 0
    if not (args.input and args.sha256 and args.out):
        parser.error("--input, --sha256 and --out are required")
    args.root.mkdir(parents=True, exist_ok=True)
    if any(args.root.iterdir()):
        raise SystemExit("--root must be empty: every case uses its own fresh copy")
    database = args.root / "run.db"
    shutil.copyfile(args.input, database)
    started = time.perf_counter()
    snapshot = verify_copy(database, args.sha256, args.run_id, args.branch_id)
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", "src"],
                           capture_output=True, text=True).stdout.strip()
    result = {"repository_head": head, "src_dirty": bool(dirty), "scenario": args.scenario,
              "variant": args.variant, "mode": args.mode, "snapshot": snapshot,
              "python": sys.version.split()[0], "machine": machine(),
              "hashseed": os.environ.get("PYTHONHASHSEED")}
    wall0, cpu0 = time.perf_counter(), time.process_time()
    server, client, log = serve(database, args, stage="restart")
    with server:
        tour = Tour(client, args.run_id, args.branch_id)
        if args.scenario == "states":
            first = tour.inspect("first-after-restart")
            repeat = tour.inspect("repeat-unchanged")
            assert normalized_view_digest(first) == normalized_view_digest(repeat)
            assert first["saved"], "the snapshot must start from a clean Saved state"
            week = first["state"]["week"]
            schedule = compatible_schedule(week["season_index"])
            plan = next((e for e in schedule if e.week - 2 == week["week"]), None)
            client.stage = "draft-change"
            if plan is not None:
                flow = Flow(tour, "minimal")
                flow.view = first
                wk = first["state"]["week"]
                cmd = command(first, "create-edition", name=plan.edition_id + ":plan", data={
                    "schema_version": "calendar_tournament_edition.v2", "edition_id": plan.edition_id,
                    "name": f"{plan.tier.title()} Load Cup S{plan.season + 1} W{plan.week}",
                    "week": {**wk, "week": plan.week}, "announcement_week": {**wk, "week": plan.week - 1},
                    "start_slot": 1, "simulation_seed": 90100 + plan.number,
                    "main_entrant_count": plan.size, "ranked": True,
                    "validity_weeks": WEEKS_PER_SEASON, "point_table": plan.point_table})
            else:
                cmd = command(first, "transition", name="states-transition")
            preview = tour.preview(cmd)
            tour.execute({"command": cmd, "expected_preview_fingerprint": preview["preview_fingerprint"],
                          "explicit_confirmation": True}, label=cmd["action"])
            changed = tour.inspect("first-after-draft-change")
            assert not changed["saved"]
            tour.inspect("repeat-after-draft-change")
            client.stage = "save"
            tour.save(changed)
            saved = tour.inspect("first-after-save")
            assert saved["saved"]
            again = tour.inspect("repeat-after-save")
            final_digest = normalized_view_digest(again)
            result["states"] = {"command": cmd["action"], "edition_id": plan.edition_id if plan else None}
        else:
            from beta_engine.api.deps import build_runtime
            world = build_runtime(database_url=f"sqlite:///{database}").repository.get_initial_world(
                run_id=args.run_id, branch_id=args.branch_id)
            if world.lifecycle_policy.requires_turn_pro:
                pros = tuple(sorted(world.initial_turn_pro.professional_player_ids))
            else:
                pros = tuple(sorted(p.player_id for p in world.players))
            flow = Flow(tour, args.variant)
            view = flow.current("inspect:first-after-restart")
            week = view["state"]["week"]
            outcome = play_week(flow, week["season_index"], week["week"], pros)
            final_digest = normalized_view_digest(outcome.pop("final_view"))
            result["week"] = {"season_index": week["season_index"], "week": week["week"], **outcome}
    result["sequence_wall"] = round(time.perf_counter() - wall0, 3)
    result["sequence_process_cpu"] = round(time.process_time() - cpu0, 3)
    result["final_view_digest"] = final_digest
    if not args.no_restart:
        child = subprocess.run(
            [sys.executable, __file__, "--root", str(args.root), "--restart-child", "--mode", args.mode,
             "--run-id", args.run_id, "--branch-id", args.branch_id, "--sha256", args.sha256,
             "--scenario", args.scenario, "--variant", args.variant],
            capture_output=True, text=True, env={**os.environ},
        )
        line = next((l for l in child.stdout.splitlines() if l.startswith("RESULT ")), None)
        if child.returncode or line is None:
            raise RuntimeError(child.stdout[-4000:] + child.stderr[-4000:])
        restarted = json.loads(line[len("RESULT "):])
        for row in restarted["log"]:
            row["process"] = "restart-child"
        log.extend(restarted["log"])
        result["restart_view_equal"] = restarted["view_digest"] == final_digest
        assert result["restart_view_equal"], "inspection after restart differs"
    result["peak_rss_mib_parent"] = round(memory_kib().get("VmHWM", 0) / 1024, 1)
    result["db_bytes"] = database.stat().st_size
    wal = database.with_name(database.name + "-wal")
    result["wal_bytes"] = wal.stat().st_size if wal.exists() else 0
    result["history"] = history_digest(database, args.run_id, args.branch_id)
    result["requests"] = log
    result["by_kind"] = summarize(log)
    result["elapsed_total"] = round(time.perf_counter() - started, 3)
    args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("by_kind", "sequence_wall", "final_view_digest", "history")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Reproduce the W16 manual Draw Save from the verified #1936 after-W15 snapshot.

Run from the root of the source tree under test with
PYTHONPATH=src:.:tests/api, BETA_ENGINE_NEW_RUN_SAVED_STORAGE=saved_v2,
BETA_ENGINE_MATCH_WORKERS=0. Every write goes to a fresh disposable copy whose
SHA-256 is checked first; the input is never opened for writing.

Subcommands
  prepare  golden after-W15 -> plan W18 + Save -> W16 event 1 submit, approve
           (checkpoint pre-draw) -> draw (checkpoint pre-save). Same harness
           helpers, seeds and 120 s transport as the pinned #1936 harness.
  save     one Save case in THIS process: warm (pre-draw input, draw, inspect,
           Save) or cold (pre-save input, fresh process, inspect, Save).
           mode timing  : no instrumentation (start/stop timestamps only)
           mode phases  : inclusive wall/thread-CPU per named function
           mode cprofile: cProfile of the Save worker thread
  restart  fresh process on a post-Save copy: inspect, history API, and
           continue with W16 event 2 submit/approve/draw + Save.

Transport: every measured /save keeps the unchanged 120 s client timeout. Setup
reads and commands (and, in ``prepare`` only, fixture Saves) may wait up to an
hour because the first cold GET of this 1,040-player W15 state alone exceeds
120 s; each such request is logged with its real duration, never hidden. After a
Save timeout the driver waits for the server's own outcome and records whether
and when it committed. REPRO_HARNESS points at ``scripts/`` of the pinned #1936
harness ``51dbde8990e0118af9827485ac12d3f27286c3e4``. Diagnostic only; never
part of pytest or CI. See docs/NATIVE_DRAW_SAVE_W16_LONG_TAIL_V1.md.
"""
from __future__ import annotations

import argparse
import contextlib
import cProfile
import functools
import gc
import hashlib
import json
import os
import pstats
import resource
import shutil
import sqlite3
import sys
import threading
import time
from pathlib import Path

HARNESS = os.environ.get("REPRO_HARNESS")  # pinned harness scripts/ directory


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_input(source: Path, expected: str, destination: Path) -> None:
    if destination.exists():
        raise SystemExit(f"refusing to overwrite {destination}")
    actual = sha256(source)
    if actual != expected:
        raise SystemExit(f"input SHA mismatch {actual} != {expected}")
    shutil.copyfile(source, destination)
    if sha256(destination) != expected:
        raise SystemExit("copy SHA mismatch")


def backup(database: Path, destination: Path) -> dict:
    with contextlib.closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as src, \
            contextlib.closing(sqlite3.connect(destination)) as dst:
        src.backup(dst)
        assert dst.execute("PRAGMA quick_check").fetchall() == [("ok",)]
    os.chmod(destination, 0o444)
    return {"database": destination.name, "sha256": sha256(destination),
            "size_bytes": destination.stat().st_size}


REQUEST_LOG: list[dict] = []


def install_request_log(setup_timeout: float = 3600.0, *, extend_save: bool = False) -> None:
    """Every /save keeps the unchanged 120 s transport; setup reads/commands
    (inspect, preview, execute) may wait longer and are logged, never hidden."""
    from urllib import request as urlrequest
    from urllib.parse import urlsplit

    original = urlrequest.urlopen

    def logged(req, *args, **kwargs):
        target = req.full_url if hasattr(req, "full_url") else str(req)
        endpoint = urlsplit(target).path
        method = req.get_method() if hasattr(req, "get_method") else "GET"
        if extend_save or not endpoint.endswith("/save"):
            kwargs["timeout"] = setup_timeout
        t0 = time.perf_counter()
        status = None
        try:
            response = original(req, *args, **kwargs)
            status = getattr(response, "status", None)
            return response
        except BaseException as exc:
            status = getattr(exc, "code", type(exc).__name__)
            raise
        finally:
            REQUEST_LOG.append({"method": method, "endpoint": endpoint.rsplit("/branches/branch", 1)[-1] or endpoint,
                                "status": status, "wall_s": round(time.perf_counter() - t0, 3), "at": round(time.perf_counter(), 3),
                                "transport_timeout_s": kwargs.get("timeout", args[1] if len(args) > 1 else None)})
            print("REQ", json.dumps(REQUEST_LOG[-1]), file=sys.stderr, flush=True)

    urlrequest.urlopen = logged


def deterministic_ids(seed: str) -> None:
    """Saved/audit identities from a fixed sequence so both arms write equal bytes."""
    import beta_engine.api.deps as deps

    counters: dict[str, int] = {}
    lock = threading.Lock()

    def factory(kind: str) -> str:
        with lock:
            counters[kind] = counters.get(kind, 0) + 1
            n = counters[kind]
        return f"{kind}-{hashlib.sha256(f'{seed}:{kind}:{n}'.encode()).hexdigest()[:32]}"

    deps._new_product_entity_id = factory


def history(database: Path) -> dict:
    with contextlib.closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as c:
        head = c.execute("SELECT saved_head_revision_id FROM run_branches WHERE run_id='run' AND branch_id='branch'").fetchone()[0]
        rows = c.execute("SELECT revision_id, parent_revision_id, sequence, kind, content_hash, payload_json, change_summary_json "
                         "FROM branch_saved_revisions ORDER BY sequence, revision_id").fetchall()
        audits = c.execute("SELECT audit_event_id, saved_revision_id, payload_json FROM branch_revision_audit_events ORDER BY audit_event_id").fetchall()
        nodes = c.execute("SELECT COUNT(*) FROM saved_revision_nodes").fetchone()[0]
        node_digest = hashlib.sha256()
        for row in c.execute("SELECT * FROM saved_revision_nodes ORDER BY 1, 2"):
            node_digest.update(repr(row).encode())
        draft = c.execute("SELECT draft_version, status, change_count, base_revision_id FROM branch_working_drafts").fetchall()
    digest = hashlib.sha256()
    for row in rows:
        digest.update(repr(row).encode())
    audit_digest = hashlib.sha256()
    for row in audits:
        audit_digest.update(repr(row).encode())
    head_row = next(r for r in rows if r[0] == head)
    return {"saved_head_revision_id": head, "revision_count": len(rows),
            "head_sequence": head_row[2], "head_kind": head_row[3], "head_content_hash": head_row[4],
            "head_payload_sha256": hashlib.sha256(head_row[5].encode()).hexdigest(),
            "head_payload_bytes": len(head_row[5]),
            "history_sha256": digest.hexdigest(), "audit_count": len(audits),
            "audit_sha256": audit_digest.hexdigest(), "node_count": nodes,
            "nodes_sha256": node_digest.hexdigest(), "working_drafts": draft}


def status_kib() -> dict:
    out = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in ("VmRSS", "VmHWM"):
            out[key] = int(value.split()[0])
    return out


def reset_peak_rss() -> None:
    with contextlib.suppress(OSError):
        Path("/proc/self/clear_refs").write_text("5")


def db_sizes(database: Path) -> dict:
    wal = Path(str(database) + "-wal")
    return {"db_bytes": database.stat().st_size, "wal_bytes": wal.stat().st_size if wal.exists() else 0}


# ----------------------------------------------------------------- server-side


class ServerSave:
    """Start/stop timestamps of the actual Save service call (all modes)."""

    def __init__(self, mode: str, out: Path):
        from beta_engine.application.run_working_draft_service import RunWorkingDraftService

        self.events: list[dict] = []
        self.done = threading.Event()
        self.mode = mode
        self.out = out
        original = RunWorkingDraftService.save_calendar_tour
        recorder = self

        @functools.wraps(original)
        def wrapped(service, **kwargs):
            started, cpu = time.perf_counter(), time.thread_time()
            profiler = cProfile.Profile() if recorder.mode == "cprofile" else None
            row = {"started": started}
            try:
                if profiler is not None:
                    profiler.enable()
                result = original(service, **kwargs)
                row["outcome"] = "returned"
                row["revision_id"] = result.saved_revision.revision_id
                return result
            except BaseException as exc:
                row["outcome"] = type(exc).__name__ + ": " + str(exc)[:300]
                raise
            finally:
                if profiler is not None:
                    profiler.disable()
                    profiler.dump_stats(str(recorder.out / f"save-{len(recorder.events)}.prof"))
                row["service_wall_s"] = time.perf_counter() - started
                row["service_thread_cpu_s"] = time.thread_time() - cpu
                row["finished"] = time.perf_counter()
                recorder.events.append(row)
                recorder.done.set()

        RunWorkingDraftService.save_calendar_tour = wrapped


PHASES = [
    # (module, attribute, label)
    ("beta_engine.infrastructure.db.repositories", "SimulationPersistenceRepository._viewer_branch_working_draft_in_session", "draft+HEAD lineage validation"),
    ("beta_engine.infrastructure.db.repositories", "SimulationPersistenceRepository._validated_branch_revision_lineage_in_session", "  lineage (validated)"),
    ("beta_engine.infrastructure.db.repositories", "SimulationPersistenceRepository._to_branch_saved_revision", "  _to_branch_saved_revision"),
    ("beta_engine.infrastructure.db.native_fork_runtime_state", "actual_dependency_signature", "actual_dependency_signature"),
    ("beta_engine.infrastructure.db.native_fork_runtime_state", "has_actual_dependency_proof", "has_actual_dependency_proof"),
    ("beta_engine.infrastructure.db.native_fork_runtime_state", "actual_saved_revision_reference", "actual_saved_revision_reference"),
    ("beta_engine.domain.run_revisions", "viewer_branch_saved_revision_payload", "build payload (copy base)"),
    ("beta_engine.infrastructure.db.calendar_sporting_checkpoint", "read_checkpoint_for_save", "read_checkpoint_for_save"),
    ("beta_engine.infrastructure.db.calendar_tour", "borrow_origin_projection_values", "borrow_origin_projection_values"),
    ("beta_engine.infrastructure.db.calendar_tour", "decode_authenticated_tour", "decode_authenticated_tour"),
    ("beta_engine.infrastructure.db.calendar_standalone_match_state", "capture_saved_calendar_match", "capture_saved_calendar_match"),
    ("beta_engine.infrastructure.db.native_fork_source_projection", "decoded_global_tour_source", "decoded_global_tour_source"),
    ("beta_engine.infrastructure.db.calendar_standalone_match_state", "load_saved_calendar_sources", "load_saved_calendar_sources (full replay)"),
    ("beta_engine.domain.run_packages", "canonical_hash", "canonical_hash"),
    ("beta_engine.infrastructure.db.repositories", "_to_json", "_to_json"),
    ("beta_engine.infrastructure.db.repositories", "_saved_revision_content_hash_from_new_canonical_parts", "content hash"),
    ("beta_engine.infrastructure.db.calendar_global_slot_origins", "verify_saved_global_origins", "verify_saved_global_origins"),
    ("beta_engine.infrastructure.db.calendar_terminal_results", "verify_saved_terminal_results", "verify_saved_terminal_results"),
    ("beta_engine.application.native_full_simulation_closure", "verify_saved_native_closure", "verify_saved_native_closure"),
    ("beta_engine.infrastructure.db.native_fork_runtime_state", "install_verified_global_save_head", "install_verified_global_save_head"),
    ("beta_engine.infrastructure.db.native_fork_runtime_state", "snapshot_proofs", "snapshot_proofs"),
    ("beta_engine.infrastructure.db.native_fork_runtime_state", "assert_global_save_append", "assert_global_save_append"),
    ("beta_engine.infrastructure.db.native_fork_source_projection", "remember_committed_global_sources", "remember_committed_global_sources"),
    ("beta_engine.application.calendar_tour_save_projection", "saved_inspection_value_fingerprint", "router saved_inspection_value_fingerprint"),
    ("sqlalchemy.orm.session", "Session.commit", "Session.commit"),
    ("sqlalchemy.orm.session", "Session.flush", "Session.flush"),
    ("json", "loads", "json.loads"),
    ("json", "dumps", "json.dumps"),
    ("beta_engine.infrastructure.db.native_fork_source_projection", "_value_identity", "_value_identity (full canonical encode+sha)"),
    ("beta_engine.infrastructure.db.native_fork_source_projection", "decoded_global_checkpoint_component", "decoded_global_checkpoint_component"),
    ("beta_engine.infrastructure.db.native_fork_source_projection", "take_live_calendar_component", "take_live_calendar_component (#1907)"),
    ("beta_engine.infrastructure.db.native_fork_source_projection", "decoded_live_calendar_component", "decoded_live_calendar_component"),
    ("beta_engine.infrastructure.db.native_fork_source_projection", "live_component_digest", "live_component_digest"),
    ("beta_engine.infrastructure.db.calendar_sporting_checkpoint", "parse_checkpoint_json", "parse_checkpoint_json (strict decode)"),
    ("beta_engine.infrastructure.db.calendar_sporting_checkpoint", "saved_checkpoint", "saved_checkpoint"),
    ("beta_engine.infrastructure.db.calendar_standalone_match_state", "decode_prevalidated_calendar_sources", "decode_prevalidated_calendar_sources"),
    ("beta_engine.infrastructure.db.calendar_tour", "capture_tour", "capture_tour"),
    ("beta_engine.infrastructure.db.calendar_tour", "verify_tour_origins", "verify_tour_origins"),
    ("beta_engine.infrastructure.db.calendar_native_competition", "verify_competition_payload", "verify_competition_payload"),
    ("beta_engine.infrastructure.db.exact_text_digest", "row_text_sha256", "row_text_sha256"),
    ("beta_engine.domain.tournaments.calendar_global_slots", "_replay_fingerprint", "checkpoint/tour fingerprint (_replay_fingerprint)"),
    ("beta_engine.domain.run_revisions", "canonical_json", "canonical_json"),
]


def install_phases(table: dict) -> list[str]:
    import importlib

    missing = []
    local = threading.local()
    for module_name, attribute, label in PHASES:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            missing.append(f"{module_name}.{attribute}")
            continue
        owner = module
        parts = attribute.split(".")
        for part in parts[:-1]:
            owner = getattr(owner, part, None)
            if owner is None:
                break
        if owner is None or not hasattr(owner, parts[-1]):
            missing.append(f"{module_name}.{attribute}")
            continue
        original = getattr(owner, parts[-1])

        def make(original, label):
            @functools.wraps(original)
            def wrapped(*args, **kwargs):
                depth = getattr(local, label, 0)
                setattr(local, label, depth + 1)
                t0, c0 = time.perf_counter(), time.thread_time()
                result = None
                try:
                    result = original(*args, **kwargs)
                    return result
                finally:
                    setattr(local, label, depth)
                    if depth == 0:  # inclusive, outermost only
                        row = table.setdefault(label, {"calls": 0, "wall_s": 0.0, "cpu_s": 0.0})
                        row["calls"] += 1
                        row["wall_s"] += time.perf_counter() - t0
                        row["cpu_s"] += time.thread_time() - c0
                        row["none_results"] = row.get("none_results", 0) + (result is None)
            return wrapped

        wrapper = make(original, label)
        import inspect as _inspect
        static = _inspect.getattr_static(owner, parts[-1])
        if isinstance(static, staticmethod):
            setattr(owner, parts[-1], staticmethod(wrapper))
        elif isinstance(static, classmethod):
            setattr(owner, parts[-1], classmethod(make(static.__func__, label)))
        else:
            setattr(owner, parts[-1], wrapper)
        if owner is module:  # rebind already-imported module globals too
            for other in list(sys.modules.values()):
                namespace = getattr(other, "__dict__", None)
                if isinstance(namespace, dict):
                    for key, value in list(namespace.items()):
                        if value is original and other is not module:
                            namespace[key] = wrapper
    return missing


# ------------------------------------------------------------------- harness


def harness_module():
    import runpy

    if not HARNESS:
        raise SystemExit("REPRO_HARNESS must point at the pinned harness scripts directory")
    return runpy.run_path(str(Path(HARNESS) / "giant_native_five_season_load.py"), run_name="repro")


def w16_fields(server, ns):
    from tests.api.test_calendar_tour_flow import inspect

    repo = server.app.state.runtime.repository
    world = repo.get_initial_world(run_id="run", branch_id="branch")
    if world.lifecycle_policy.requires_turn_pro:
        initial = tuple(sorted(world.initial_turn_pro.professional_player_ids))
    else:
        initial = tuple(sorted(p.player_id for p in world.players))
    schedule = ns["make_schedule"](5, 60, profile="compatible")
    editions = tuple(e for e in schedule if (e.season, e.week) == (0, 16))
    view = inspect(server)
    active = {p["player_id"] for p in view["players"]}
    eligible = [pid for pid in initial if pid in active]
    base = (0 * 127 + 16 * 19) % len(eligible)
    fields = {e.edition_id: [eligible[(base + e.entrant_offset + n) % len(eligible)] for n in range(e.size)]
              for e in editions}
    return editions, fields, schedule


def timed_request(method, url, payload):
    from tests.api.test_saved_revision_history_api import _request

    before = status_kib()
    reset_peak_rss()
    t0, c0 = time.perf_counter(), time.process_time()
    error = None
    try:
        code, body = _request(method, url, payload)  # unchanged 120 s transport
    except TimeoutError as exc:
        code, body, error = None, None, type(exc).__name__
    wall, cpu = time.perf_counter() - t0, time.process_time() - c0
    after = status_kib()
    return {"http_status": code, "error": error, "client_wall_s": wall, "process_cpu_s": cpu,
            "rss_before_kib": before.get("VmRSS"), "rss_after_kib": after.get("VmRSS"),
            "peak_rss_kib": after.get("VmHWM")}, body


def do_save(server, database: Path, recorder: ServerSave | None, before_post=None):
    from tests.api.test_calendar_tour_flow import inspect, tour_url

    t_inspect = time.perf_counter()
    view = inspect(server)
    inspect_wall = time.perf_counter() - t_inspect
    assert not view["saved"]
    request_body = {"expected_draft_version": view["draft_version"],
                    "expected_calendar_tour_fingerprint": view["tour_fingerprint"]}
    sizes_before = db_sizes(database)
    if before_post is not None:
        before_post()  # attribute only the Save request, not the inspect GET
    sent = time.perf_counter()
    metrics, body = timed_request("POST", tour_url(server) + "/save", request_body)
    metrics["pre_save_inspect_wall_s"] = inspect_wall
    metrics.update({f"before_{k}": v for k, v in sizes_before.items()})
    if metrics["http_status"] is None and recorder is not None:
        # Uncertain response: the client gave up at 120 s. Wait for the server's
        # own outcome, then record whether and when it committed.
        recorder.done.wait(timeout=1800)
    if recorder is not None and recorder.events:
        event = recorder.events[-1]
        metrics["server"] = {k: v for k, v in event.items() if k not in ("started", "finished")}
        metrics["server"]["started_after_send_s"] = event["started"] - sent
        metrics["server"]["completed_after_send_s"] = event["finished"] - sent
    metrics.update({f"after_{k}": v for k, v in db_sizes(database).items()})
    metrics["receipt"] = None if body is None else {
        "revision_id": body.get("saved_revision", {}).get("revision_id"),
        "content_hash": body.get("saved_revision", {}).get("content_hash"),
        "has_projection": body.get("saved_projection") is not None,
    } if metrics["http_status"] == 201 else body
    return metrics, request_body


def start(database: Path):
    from tests.api.test_saved_revision_history_api import ApiServer

    return ApiServer(database_url=f"sqlite:///{database}")


def environment_record(tree: Path) -> dict:
    import platform
    import subprocess

    def git(*args):
        return subprocess.run(["git", *args], cwd=tree, capture_output=True, text=True).stdout.strip()

    return {"head": git("rev-parse", "HEAD"), "tree": git("rev-parse", "HEAD^{tree}"),
            "dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
            "python": sys.version.split()[0], "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "env": {k: os.environ.get(k) for k in ("BETA_ENGINE_NEW_RUN_SAVED_STORAGE", "BETA_ENGINE_MATCH_WORKERS", "PYTHONHASHSEED")}}


def cmd_prepare(args):
    from tests.api.test_calendar_tour_flow import command, execute, inspect

    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    work = out / "work.sqlite"
    copy_input(args.golden, args.golden_sha, work)
    deterministic_ids("repro-prepare")
    # Fixture preparation only (never a measured case): its Saves may exceed
    # 120 s from a cold process and are logged with their real duration.
    install_request_log(extend_save=True)
    ns = harness_module()
    log = {"environment": environment_record(Path.cwd()), "input_sha256": args.golden_sha, "steps": []}
    recorder = ServerSave("timing", out)
    with start(work) as server:
        view = inspect(server)
        assert (view["state"]["week"]["season_index"], view["state"]["week"]["week"]) == (0, 16), view["state"]["week"]
        log["start_head"] = view["saved_head_revision_id"]
        schedule = ns["make_schedule"](5, 60, profile="compatible")
        for event in (e for e in schedule if (e.season, e.week - 2) == (0, 16)):
            t0 = time.perf_counter()
            ns["_plan_edition"](server, event)  # create-edition + Save, as the harness
            log["steps"].append({"step": "plan+save " + event.edition_id, "wall_s": time.perf_counter() - t0})
        editions, fields, _ = w16_fields(server, ns)
        first = editions[0]
        log["w16_editions"] = [e.edition_id for e in editions]
        for action in ("submit", "approve"):
            t0 = time.perf_counter()
            execute(server, command(inspect(server), action, name=first.edition_id + ":" + action,
                                    edition_id=first.edition_id,
                                    data={"player_ids": fields[first.edition_id]} if action == "submit" else None))
            log["steps"].append({"step": action, "wall_s": time.perf_counter() - t0})
        log["pre_draw"] = backup(work, out / "pre-draw.sqlite")
        t0 = time.perf_counter()
        execute(server, command(inspect(server), "draw", name=first.edition_id + ":draw", edition_id=first.edition_id))
        log["steps"].append({"step": "draw", "wall_s": time.perf_counter() - t0})
        log["pre_save"] = backup(work, out / "pre-save.sqlite")
        log["pre_save_history"] = history(out / "pre-save.sqlite")
    log["requests"] = REQUEST_LOG
    (out / "prepare.json").write_text(json.dumps(log, indent=2) + "\n")
    print(json.dumps(log, indent=2))


def install_equivalence_check(record: list) -> None:
    """Independent check of the arm-B oversize decision on the real committed value."""
    import beta_engine.infrastructure.db.native_fork_source_projection as projection
    from beta_engine.domain.run_revisions import canonical_json

    original = projection.remember_committed_global_sources

    def checked(repository, source, captured, **kwargs):
        text = kwargs.get("_payload_text")
        row = {"payload_text_given": text is not None}
        if text is not None:
            full = canonical_json(source.payload)
            component = source.payload["content"]["calendar_player_sporting_checkpoint"]
            actual_component = len(canonical_json({"calendar_player_sporting_checkpoint": component}))
            derived = projection._committed_checkpoint_text_length(source, text) + len('{"calendar_player_sporting_checkpoint":}')
            row.update(text_equals_canonical_json=full == text, text_len=len(text), full_len=len(full),
                       component_envelope_len=actual_component, derived_component_envelope_len=derived,
                       limit=projection.MAX_GLOBAL_TOUR_BYTES,
                       original_payload_oversize=len(full.encode()) > projection.MAX_GLOBAL_TOUR_BYTES,
                       original_component_oversize=actual_component > projection.MAX_GLOBAL_TOUR_BYTES)
            del full
        t0 = time.perf_counter()
        result = original(repository, source, captured, **kwargs)
        row["call_wall_s"] = time.perf_counter() - t0
        record.append(row)
        return result

    projection.remember_committed_global_sources = checked


def cmd_save(args):
    from tests.api.test_calendar_tour_flow import command, execute, inspect, tour_url

    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    work = out / "work.sqlite"
    copy_input(args.input, args.sha, work)
    deterministic_ids("repro-save")
    install_request_log()
    result = {"case": args.case, "mode": args.mode, "input": str(args.input), "input_sha256": args.sha,
              "environment": environment_record(Path.cwd())}
    phases: dict = {}
    equivalence: list = []
    if args.check_equivalence:
        install_equivalence_check(equivalence)
        result["equivalence"] = equivalence
    if args.mode == "phases":
        result["phase_install_missing"] = install_phases(phases)
    recorder = ServerSave(args.mode, out)
    gc_time = {"collections": 0, "s": 0.0}
    gc_start = {}

    def on_gc(phase, info):
        if phase == "start":
            gc_start["t"] = time.perf_counter()
        elif "t" in gc_start:
            gc_time["collections"] += 1
            gc_time["s"] += time.perf_counter() - gc_start.pop("t")

    gc.callbacks.append(on_gc)
    with start(work) as server:
        if args.case == "warm":
            ns = harness_module()
            editions, fields, _ = w16_fields(server, ns)
            first = editions[0]
            t0 = time.perf_counter()
            execute(server, command(inspect(server), "draw", name=first.edition_id + ":draw", edition_id=first.edition_id))
            result["draw_wall_s"] = time.perf_counter() - t0
        def reset():
            phases.clear()
            gc_time.update(collections=0, s=0.0)
        metrics, request_body = do_save(server, work, recorder, before_post=reset)
        metrics["gc_during_request"] = dict(gc_time)
        result["save"] = metrics
        if args.mode == "phases":
            result["phases"] = dict(sorted(phases.items(), key=lambda kv: -kv[1]["cpu_s"]))
        if args.retry and metrics["http_status"] in (201, None):
            # Retry the very same request after an uncertain/lost response.
            t0 = time.perf_counter()
            from tests.api.test_saved_revision_history_api import _request
            code, body = _request("POST", tour_url(server) + "/save", request_body)
            view = inspect(server)
            result["retry"] = {"http_status": code, "detail": body.get("detail") if isinstance(body, dict) else None,
                               "wall_s": time.perf_counter() - t0, "saved": view["saved"],
                               "saved_head_revision_id": view["saved_head_revision_id"]}
    result["requests"] = REQUEST_LOG
    result["history"] = history(work)
    if args.keep:
        result["post_save"] = backup(work, out / "post-save.sqlite")
    work.unlink()
    for suffix in ("-wal", "-shm"):
        Path(str(work) + suffix).unlink(missing_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def cmd_restart(args):
    from tests.api.test_calendar_tour_flow import command, execute, inspect
    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    work = out / "work.sqlite"
    copy_input(args.input, args.sha, work)
    deterministic_ids("repro-restart")
    install_request_log()
    ns = harness_module()
    before = history(work)
    result = {"environment": environment_record(Path.cwd()), "before": before}
    recorder = ServerSave("timing", out)
    with start(work) as server:
        t0 = time.perf_counter()
        view = inspect(server)
        result["first_inspect_wall_s"] = time.perf_counter() - t0
        assert view["saved"] and view["saved_head_revision_id"] == before["saved_head_revision_id"]
        ns["verify_saved_history_http"](server, before["saved_head_revision_id"])
        editions, fields, _ = w16_fields(server, ns)
        second = editions[1]
        steps = []
        for action in ("submit", "approve", "draw"):
            t0 = time.perf_counter()
            execute(server, command(inspect(server), action, name=second.edition_id + ":" + action,
                                    edition_id=second.edition_id,
                                    data={"player_ids": fields[second.edition_id]} if action == "submit" else None))
            steps.append({"step": action, "wall_s": time.perf_counter() - t0})
        result["steps"] = steps
        metrics, _ = do_save(server, work, recorder)
        result["save"] = metrics
    result["requests"] = REQUEST_LOG
    result["after"] = history(work)
    ns["verify_saved_v2_sqlite_history"](work, result["after"]["saved_head_revision_id"])
    work.unlink()
    for suffix in ("-wal", "-shm"):
        Path(str(work) + suffix).unlink(missing_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--golden", type=Path, required=True)
    p.add_argument("--golden-sha", required=True)
    p.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("save")
    s.add_argument("--input", type=Path, required=True)
    s.add_argument("--sha", required=True)
    s.add_argument("--case", choices=("warm", "cold"), required=True)
    s.add_argument("--mode", choices=("timing", "phases", "cprofile"), default="timing")
    s.add_argument("--retry", action="store_true")
    s.add_argument("--keep", action="store_true")
    s.add_argument("--check-equivalence", action="store_true")
    s.add_argument("--out", type=Path, required=True)
    r = sub.add_parser("restart")
    r.add_argument("--input", type=Path, required=True)
    r.add_argument("--sha", required=True)
    r.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    {"prepare": cmd_prepare, "save": cmd_save, "restart": cmd_restart}[args.cmd](args)


if __name__ == "__main__":
    main()

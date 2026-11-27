"""Full-output parity of frozen slot matches: ``buuk``, candidate without and with workers.

Real uvicorn HTTP + SQLite, Saved v2, two Runs (two databases, one server
process, one shared pool) and two Branches (a public fork of a partially played
slot). The scenario is a fixed sequence of real commands:

1. Run A: ``next-match`` (partial slot), Save, fork the Save into Branch A2.
2. Concurrently, started by one barrier: ``next-slot`` on A, on A2 and on Run B,
   while two readers GET A and B. Every read must equal the complete view
   before or after the concurrent write (never a partial step).
3. Save A, A2 and B. Restart (new app instances), inspect cold.
4. ``next-slot`` (finals) on A and A2, Save; Restore A to the step 1 Save,
   retry the exact step 1 request (identical receipt) and play the rest of
   the slot again, Save.
5. Restart again; collect receipts, inspections, full sporting checkpoints
   (every MatchResult, seed, anchor and state effect), Saved revision history
   and recovery audit of each Branch, in order.

Random Saved revision/Branch ids are replaced by their order of appearance and
values derived from them are dropped; everything else is compared verbatim.

``replay`` opens the finished database copy in a *new* process with workers
off: its cold inspection re-verifies every stored match by a sequential
MatchEngine replay of the same stored inputs.

    python scripts/verify_slot_worker_parity.py prepare --database work/parity.db
    python scripts/verify_slot_worker_parity.py scenario --root <tree> --input work/parity.db \\
        --sha256 <sha> --workers 0|2|3 --out work/parity-<label>.json
    python scripts/verify_slot_worker_parity.py replay --root <tree> --input work/<final>.db --out x.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

SAVED_STORAGE = "BETA_ENGINE_NEW_RUN_SAVED_STORAGE"
WORKERS = "BETA_ENGINE_MATCH_WORKERS"
_RANDOM = re.compile(r"saved-revision-[0-9a-f]{32}|safety-checkpoint-[0-9a-f]{32}")
_DERIVED = {"tour_fingerprint", "save_projection_fingerprint", "expected_preview_fingerprint",
            "expected_tour_fingerprint", "expected_saved_head", "preview_fingerprint"}
_TIMES = re.compile(r".*(_at|_time|timestamp)$")


def _use(root):
    root = Path(root).resolve()
    sys.path[:0] = [str(root / "src"), str(root)]
    os.chdir(root)
    return root


def normalized(value, extra_ids=()):
    order = {}
    text = json.dumps(value, sort_keys=True, default=_jsonable)
    for literal in extra_ids:
        text = text.replace(literal, "branch-#%d" % order.setdefault(literal, len(order)))
    text = _RANDOM.sub(lambda m: "random-#%d" % order.setdefault(m.group(), len(order)), text)

    def strip(node):
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if k not in _DERIVED and not _TIMES.match(k)}
        if isinstance(node, list):
            return [strip(v) for v in node]
        return node
    return strip(json.loads(text))


def _jsonable(value):
    dump = getattr(value, "model_dump", None)
    if dump is not None:
        return dump(mode="json")
    raise TypeError(type(value))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def copy_database(source, target):
    with sqlite3.connect(source) as a, sqlite3.connect(target) as b:
        a.backup(b)


def prepare(database):
    from tests.api.test_calendar_global_slots import ready
    from tests.api.test_saved_revision_history_api import ApiServer

    os.environ[SAVED_STORAGE] = "saved_v2"
    os.environ.pop(WORKERS, None)
    with ApiServer(database_url=f"sqlite:///{database}") as server:
        ready(server, 52)
    with sqlite3.connect(database) as connection:  # one self-contained file to hash
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def _branch(server, branch):
    from tests.api.test_native_fork_public_continuation import Tour
    return Tour(server, branch)


def _sporting(server, branch):
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint
    with server.app.state.runtime.repository._session_factory() as session:
        return load_checkpoint(session, run_id="run", branch_id=branch)


def _history(server, branch):
    from tests.api.test_saved_revision_history_api import _request
    root = f"{server.base_url}/run-containers/run/branches/{branch}"
    code, history = _request("GET", root + "/saved-revisions")
    assert code == 200, history
    # The recovery-activity endpoint declines native Tour Save audit kinds
    # (``saved_revision_recovery_activity_conflict``): read the audit rows.
    from sqlalchemy import text
    with server.app.state.runtime.repository._engine.connect() as connection:
        audit = [list(row) for row in connection.execute(text(
            "SELECT audit_event_id, saved_revision_id, event_kind, payload_json "
            "FROM branch_revision_audit_events WHERE run_id='run' AND branch_id=:branch "
            "ORDER BY rowid"), {"branch": branch})]
    return {"history": history, "audit": audit}


def scenario(db_a, db_b, *, before_concurrent=None):
    """Run the fixed scenario on two prepared databases; returns raw evidence."""
    from tests.api.test_calendar_population_sporting_checkpoint import restore
    from tests.api.test_calendar_tour_flow import tour_url
    from tests.api.test_native_fork_public_continuation import fork
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    # Deterministic product ids (Saved revisions, audit events, safety
    # checkpoints, Branches) so that hashes over them are comparable across
    # trees; the barrier-synchronized step itself creates none of them.
    import itertools
    import uuid

    from beta_engine.api import deps
    sequence = itertools.count()
    deps.uuid4 = lambda: uuid.uuid5(uuid.NAMESPACE_URL, f"slot-worker-parity:{next(sequence)}")
    evidence, reads = {"receipts": {}, "views": {}}, {}
    receipts = evidence["receipts"]
    with ApiServer(database_url=f"sqlite:///{db_a}") as a, ApiServer(database_url=f"sqlite:///{db_b}") as b:
        main_a, main_b = _branch(a, "branch"), _branch(b, "branch")
        receipts["a.one"], one_request = main_a.execute("next-match", "a-one")
        saved_one = main_a.save()
        created = fork(a, saved_one["revision_id"], name="Parallel branch")
        fork_id = evidence["fork_id"] = created["branch_id"]
        a2 = _branch(a, fork_id)
        requests = {"a": main_a.prepare("next-slot", "a-rest"),
                    "a2": a2.prepare("next-slot", "a2-rest"),
                    "b": main_b.prepare("next-slot", "b-slot")}
        tours = {"a": main_a, "a2": a2, "b": main_b}
        before = {name: tour.view() for name, tour in tours.items()}
        if before_concurrent is not None:
            before_concurrent()
        barrier = threading.Barrier(len(requests) + 2)
        out, errors = {}, []

        def write(name):
            try:
                barrier.wait()
                out[name] = _request("POST", tours[name].url + "/execute", requests[name])
            except BaseException as error:  # noqa: BLE001
                errors.append(error)

        def read(name):
            try:
                barrier.wait()
                seen = []
                for _ in range(4):
                    code, body = _request("GET", tours[name].url)
                    seen.append((code, body))
                reads[name] = seen
            except BaseException as error:  # noqa: BLE001
                errors.append(error)

        threads = [threading.Thread(target=write, args=(n,)) for n in requests]
        threads += [threading.Thread(target=read, args=(n,)) for n in ("a", "b")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors, errors
        for name, (code, body) in sorted(out.items()):
            assert code == 201, (name, body)
            receipts[f"{name}.concurrent"] = body
        after = {name: tour.view() for name, tour in tours.items()}
        for name, seen in reads.items():
            for code, body in seen:
                assert code == 200, body
                assert body in (before[name], after[name]), f"{name}: partial or foreign read"
        for name in ("a", "a2", "b"):
            tours[name].save()
        evidence["views"]["after-concurrent"] = {n: t.view() for n, t in tours.items()}
    with ApiServer(database_url=f"sqlite:///{db_a}") as a, ApiServer(database_url=f"sqlite:///{db_b}") as b:
        tours = {"a": _branch(a, "branch"), "a2": _branch(a, fork_id), "b": _branch(b, "branch")}
        evidence["views"]["restart-1"] = {n: t.view() for n, t in tours.items()}
        assert evidence["views"]["restart-1"] == evidence["views"]["after-concurrent"]
        for name in ("a", "a2"):
            receipts[f"{name}.finals"] = tours[name].execute("next-slot", f"{name}-finals")[0]
            tours[name].save()
        restore(a, saved_one["revision_id"])
        # The exact retry of a command contained in the restored revision.
        assert _request("POST", tour_url(a) + "/execute", one_request) == (201, receipts["a.one"])
        receipts["a.after-restore"] = tours["a"].execute("next-slot", "a-rest")[0]
        tours["a"].save()
        receipts["b.second"] = tours["b"].execute("next-slot", "b-second")[0]
        tours["b"].save()
    with ApiServer(database_url=f"sqlite:///{db_a}") as a, ApiServer(database_url=f"sqlite:///{db_b}") as b:
        tours = {"a": _branch(a, "branch"), "a2": _branch(a, fork_id), "b": _branch(b, "branch")}
        evidence["views"]["restart-2"] = {n: t.view() for n, t in tours.items()}
        evidence["sporting"] = {"a": _sporting(a, "branch"), "a2": _sporting(a, fork_id),
                                "b": _sporting(b, "branch")}
        evidence["saved"] = {"a": _history(a, "branch"), "a2": _history(a, fork_id),
                             "b": _history(b, "branch")}
    return evidence


def summarize(evidence):
    value = normalized({k: v for k, v in evidence.items() if k != "fork_id"}, (evidence["fork_id"],))
    matches = []
    for name, checkpoint in sorted(value["sporting"].items()):
        text = json.dumps(checkpoint, sort_keys=True)
        matches.append((name, text.count('"log_anchor_hash"')))
    return {"digest": digest(value), "parts": {k: digest(v) for k, v in value.items()},
            "anchors": matches}, value


def replay(database, branches):
    """New process, workers off: cold inspection re-verifies stored matches."""
    from tests.api.test_saved_revision_history_api import ApiServer

    os.environ.pop(WORKERS, None)
    with ApiServer(database_url=f"sqlite:///{database}") as server:
        views = {branch: _branch(server, branch).view() for branch in branches}
        sporting = {branch: _sporting(server, branch) for branch in branches}
    return {"views": views, "sporting": sporting}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--root", default=".")
    p.add_argument("--database", required=True)
    s = sub.add_parser("scenario")
    s.add_argument("--root", default=".")
    s.add_argument("--input", required=True)
    s.add_argument("--sha256", required=True)
    s.add_argument("--workers", default="0")
    s.add_argument("--keep", help="copy the finished Run A database here")
    s.add_argument("--out", required=True)
    r = sub.add_parser("replay")
    r.add_argument("--root", default=".")
    r.add_argument("--input", required=True)
    r.add_argument("--branches", required=True, help="comma separated Branch ids")
    r.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.mode == "prepare":
        database = Path(args.database).resolve()
        _use(args.root)
        prepare(database)
        print(hashlib.sha256(database.read_bytes()).hexdigest())
        return
    source = Path(args.input).resolve()
    out = Path(args.out).resolve()
    keep = Path(args.keep).resolve() if getattr(args, "keep", None) else None
    root = _use(args.root)
    if args.mode == "replay":
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "replay.db"
            copy_database(source, target)
            branches = args.branches.split(",")
            result = replay(target, branches)
        out.write_text(json.dumps({"digest": digest(normalized(result, branches)),
                                   "parts": {k: digest(normalized(v, branches)) for k, v in result.items()},
                                   "root_head": _head(root)}, indent=1))
        return
    assert hashlib.sha256(source.read_bytes()).hexdigest() == args.sha256, "input differs"
    os.environ[SAVED_STORAGE] = "saved_v2"
    os.environ[WORKERS] = args.workers
    with tempfile.TemporaryDirectory() as tmp:
        db_a, db_b = Path(tmp) / "a.db", Path(tmp) / "b.db"
        copy_database(source, db_a)
        copy_database(source, db_b)
        evidence = scenario(db_a, db_b)
        if keep is not None:
            shutil.copyfile(db_a, keep)
    summary, value = summarize(evidence)
    out.with_suffix(".value.json").write_text(json.dumps(value, sort_keys=True, indent=1))
    counters = None
    try:
        from beta_engine.domain.matches import slot_batch
        counters = slot_batch.batch_counters()
    except ImportError:
        pass
    import beta_engine
    assert Path(beta_engine.__file__).resolve().is_relative_to(root), beta_engine.__file__
    out.write_text(json.dumps({**summary, "fork_id": evidence["fork_id"], "workers": args.workers, "root_head": _head(root),
                               "python": sys.version.split()[0], "counters": counters}, indent=1))
    print(summary["digest"])


def _head(root):
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


if __name__ == "__main__":
    main()

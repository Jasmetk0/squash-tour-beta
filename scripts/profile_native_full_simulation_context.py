"""Read-only context timings of a disposable real-week SQLite snapshot."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import cProfile
import hashlib
import json
import platform
import pstats
import resource
import sqlite3
import subprocess
import time
from collections import Counter

from sqlalchemy import event, text

from beta_engine.application.full_simulation_tasks import inspect_tasks
from beta_engine.application.native_full_simulation import (
    native_context,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.native_fork_runtime_state import (
    native_read_proof_scope,
)
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository
from scripts.profile_native_full_simulation_metrics import measure_fetches

p = argparse.ArgumentParser()
p.add_argument("--database", type=Path, required=True)
p.add_argument("--root", type=Path, required=True)
p.add_argument("--branch", required=True)
p.add_argument("--profile", action="store_true")
a = p.parse_args()
source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
source_tree = subprocess.check_output(
    ["git", "rev-parse", "HEAD:src"], text=True
).strip()
if subprocess.run(
    ["git", "diff", "--quiet", "HEAD", "--", "src"], check=False
).returncode:
    raise ValueError("Commit the production candidate before measuring it")
a.root.mkdir(parents=True, exist_ok=True)
local = a.root / "input.db"
if local.exists():
    raise ValueError("Use a fresh output directory")
with sqlite3.connect(a.database) as s, sqlite3.connect(local) as d:
    s.backup(d)
with local.open("rb") as stream:
    input_hash = hashlib.file_digest(stream, "sha256").hexdigest()
(a.root / "metadata.json").write_text(
    json.dumps(
        {
            "git_sha": source_commit,
            "production_source_tree": source_tree,
            "input_sha256": input_hash,
            "python": sys.version,
            "platform": platform.platform(),
        },
        indent=2,
    )
)
engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{local}"))
fetches = measure_fetches(engine)
factory = create_session_factory(engine)
sql = Counter()


def count(conn, cursor, statement, parameters, ctx, many):
    sql["count"] += 1
    sql["statement_bytes"] += len(statement.encode())
    sql["parameter_bytes"] += len(str(parameters).encode())


event.listen(engine, "before_cursor_execute", count)
repo = SimulationPersistenceRepository(engine=engine, session_factory=factory)
records = []
for label in ["cold", "warm", "warm2"]:
    sql.clear()
    fetches.clear()
    start = time.perf_counter()
    with factory() as session:
        session.execute(text("BEGIN"))
        ctx = native_context(repo, session, "run", a.branch)
    records.append(
        {
            "label": label,
            "seconds": time.perf_counter() - start,
            "sql": dict(sql),
            "fetched": dict(fetches),
            "rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "week": ctx["week"],
        }
    )
    print(json.dumps(records[-1]), flush=True)
with factory() as session, native_read_proof_scope():
    session.execute(text("BEGIN"))
    native_context(repo, session, "run", a.branch)
    sql.clear()
    fetches.clear()
    start = time.perf_counter()
    native_context(repo, session, "run", a.branch)
    records.append(
        {
            "label": "same_snapshot_warm",
            "seconds": time.perf_counter() - start,
            "sql": dict(sql),
            "fetched": dict(fetches),
            "rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "week": ctx["week"],
        }
    )
sql.clear()
fetches.clear()
start = time.perf_counter()
progress = inspect_tasks(factory, run_id="run", branch_id=a.branch)
records.append(
    {
        "label": "task_progress",
        "seconds": time.perf_counter() - start,
        "sql": dict(sql),
        "fetched": dict(fetches),
        "tasks": len(progress["tasks"]),
        "rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
)
(a.root / "timings.json").write_text(json.dumps(records, indent=2))
if a.profile:
    for label in ["cold", "warm"]:
        if label == "cold":
            repo = SimulationPersistenceRepository(
                engine=engine, session_factory=factory
            )
        profile = cProfile.Profile()
        profile.enable()
        with factory() as session:
            session.execute(text("BEGIN"))
            native_context(repo, session, "run", a.branch)
        profile.disable()
        profile.dump_stats(str(a.root / f"{label}.pstats"))
        with (a.root / f"{label}.txt").open("w") as f:
            pstats.Stats(profile, stream=f).strip_dirs().sort_stats(
                "cumulative"
            ).print_stats(55)
engine.dispose()

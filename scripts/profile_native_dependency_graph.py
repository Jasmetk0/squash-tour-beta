#!/usr/bin/env python3
"""Profile Saved dependency walks on synthetic, disposable SQLite chains.

The fixtures only exercise physical graph construction. They have no sporting
state and are not valid inputs to a simulation or to full Saved replay.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--checkout", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--revisions", type=int, nargs="+", default=[128, 256, 512, 1024, 2048])
    args = parser.parse_args()
    if any(count < 1 for count in args.revisions):
        parser.error("--revisions must contain positive counts")

    checkout = args.checkout.resolve()
    sys.path[:0] = [str(checkout / "src"), str(checkout)]
    for count in args.revisions:
        fixture = args.fixtures.resolve() / str(count)
        ids = [f"revision-{index:05}" for index in range(1, count + 1)]
        if args.prepare:
            fixture.mkdir(parents=True, exist_ok=False)
            prepare(fixture, ids)
        else:
            database = fixture / "task-clock.sqlite"
            if not database.is_file():
                parser.error(f"fixture missing: {database}")
            print(json.dumps(profile(database, ids)), flush=True)


def prepare(fixture, ids):
    from sqlalchemy import insert, update

    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from beta_engine.domain.run_revisions import VIEWER_BRANCH_SELECTION_SAVED_REVISION_KIND
    from beta_engine.infrastructure.db.models import BranchSavedRevisionModel, RunBranchModel
    from tests.application.test_full_simulation_task_calendar import setup_calendar

    engine, factory, _ = setup_calendar(fixture, RunCalendar(52, 1, 2030, 25))
    try:
        with factory.begin() as session:
            root = session.get(BranchSavedRevisionModel, "saved")
            session.execute(insert(BranchSavedRevisionModel), [
                {
                    "revision_id": revision_id,
                    "run_id": "run",
                    "branch_id": "branch",
                    "sequence": root.sequence + index + 1,
                    "parent_revision_id": ids[index - 1] if index else root.revision_id,
                    "kind": VIEWER_BRANCH_SELECTION_SAVED_REVISION_KIND,
                    "payload_schema_version": root.payload_schema_version,
                    "content_hash_algorithm": root.content_hash_algorithm,
                    "content_hash": root.content_hash,
                    "payload_json": '{"content":{"calendar_tour_authority":{}}}',
                    "change_summary_json": "{}",
                }
                for index, revision_id in enumerate(ids)
            ])
            session.execute(update(RunBranchModel).where(RunBranchModel.branch_id == "branch")
                            .values(saved_head_revision_id=ids[-1]))
    finally:
        engine.dispose()


def profile(database, ids):
    from sqlalchemy import select, text

    from beta_engine.domain.run_revisions import canonical_json
    from beta_engine.infrastructure.db.engine import DatabaseSettings, create_session_factory, create_sqlite_engine
    from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
    from beta_engine.infrastructure.db import native_fork_runtime_state as runtime

    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{database}"))
    factory = create_session_factory(engine)
    try:
        with factory() as session, runtime.native_read_proof_scope():
            session.execute(text("BEGIN"))
            rows = {row.revision_id: row for row in session.scalars(select(BranchSavedRevisionModel))}
            start = time.perf_counter()
            cpu_start = time.process_time()
            graph_hash = None
            for revision_id in reversed(ids):
                signature = runtime.actual_dependency_signature(session, rows[revision_id])
                runtime._dependency_proof_key(signature)
                if graph_hash is None:
                    graph_hash = hashlib.sha256(canonical_json(signature[1:]).encode()).hexdigest()
            cpu = time.process_time() - cpu_start
            elapsed = time.perf_counter() - start
            closures = runtime._physical_read_cache(session)["dependency_closures"]
            graphs = {id(graph): graph for graph, _ in closures.values()}
            return {
                "revisions": len(ids),
                "seconds": round(elapsed, 4),
                "cpu_seconds": round(cpu, 4),
                "retained_graphs": len(graphs),
                "retained_row_references": sum(map(len, graphs.values())),
                "canonical_graph_sha256": graph_hash,
            }
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

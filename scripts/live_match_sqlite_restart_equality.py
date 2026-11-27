"""Live match on real SQLite: Next Rally, commit, NEW process, continue; two trees.

For each pinned source tree (``--a``/``--b`` directories, e.g. detached
worktrees of two commits) and each case, three fresh processes run:

1. ``start``: create a disposable SQLite file, start the persisted live match
   (``PersistedLiveMatchStore.start_from_engine_input``), run ``--rallies``
   ``Simulate Next Rally`` commands, each committed in its own session (the
   saved live state), then exit;
2. ``finish``: a NEW process opens the same file and continues command by
   command until the final result;
3. ``bulk``: one uninterrupted ``MatchEngine.simulate`` of the same snapshot.

Recorded per case: every response (rally event JSON, state fingerprint), the
final result (``model_dump(mode="json")`` sorted bytes) and the SQLite file's
``integrity_check``. The verdict requires start+finish == bulk inside each tree
and byte-identical records between the trees.

    python scripts/live_match_sqlite_restart_equality.py --a <tree> --b <tree> --out <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

CASES = {
    # name: (seed, base_a, base_b, style_a, style_b, rallies before the restart)
    "classic": (8128, 86, 82, "tempo-controller", "tempo-controller", 23),
    "mismatch": (2**127 + 7, 91, 64, "attacking", "front-court", 9),
    "long-rallies": (4242, 80, 80, "retrieving", "retrieving", 41),
    "close-negative-seed": (-(2**80) + 3, 77, 77, "counter-punching", "attacking", 1),
}


def _snapshot(case: str):
    from beta_engine.domain.matches import (
        MatchContext, MatchInputSnapshot, MatchParticipantContext,
        official_match_format_snapshot,
    )
    from beta_engine.domain.players import Player
    from beta_engine.domain.players.models import HiddenCareerTraits

    seed, base_a, base_b, style_a, style_b, _ = CASES[case]

    def player(player_id, base, style):
        return Player(
            player_id=player_id, name=player_id, age=27, nationality="TST",
            technique=base, movement=base, physical=base, mental=base,
            consistency=base, clutch=base, recovery=base, play_style=style,
            archetype="all-court tactician",
            hidden_career_traits=HiddenCareerTraits(
                potential_ceiling=90, growth_curve="balanced", professionalism=0.7,
                ambition=0.7, travel_tolerance=0.7, schedule_aggression=0.6,
                injury_proneness=0.2, resilience=0.8,
            ),
        )

    context = MatchContext(
        match_id=f"LIVE-{case}",
        player_a=MatchParticipantContext(player=player("A", base_a, style_a)),
        player_b=MatchParticipantContext(player=player("B", base_b, style_b)),
    )
    return MatchInputSnapshot.create(
        context=context, effective_match_format=official_match_format_snapshot(),
        simulation_seed=seed, match_engine_version="match_engine_v10",
    )


def _sessions(database: Path):
    from beta_engine.infrastructure.db import (
        DatabaseSettings, create_session_factory, create_sqlite_engine,
    )
    from beta_engine.infrastructure.db.models import Base

    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{database}"))
    Base.metadata.create_all(engine)
    return create_session_factory(engine), engine


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _next(store_cls, sessions, command: int, fingerprint: str) -> dict:
    with sessions() as session:
        response = store_cls(session).simulate_next_rally(
            run_id="RUN", branch_id="BRANCH", week_ordinal=0, slot_id="SLOT-1",
            group_id="GROUP-1", command_id=f"rally-{command}",
            expected_state_fingerprint=fingerprint,
        )
        session.commit()
    return response


def worker(phase: str, case: str, database: Path, out: Path) -> None:
    from beta_engine.core import DeterministicRng
    from beta_engine.domain.matches import MatchEngine
    from beta_engine.infrastructure.db.live_match_state import PersistedLiveMatchStore
    import beta_engine

    snapshot = _snapshot(case)
    record: dict = {"phase": phase, "case": case, "beta_engine_file": beta_engine.__file__,
                    "pythonhashseed": os.environ.get("PYTHONHASHSEED")}
    if phase == "bulk":
        result = MatchEngine(rng=DeterministicRng(snapshot.simulation_seed)).simulate(
            snapshot.context, log_anchor_hash=snapshot.snapshot_hash,
            effective_match_timing=snapshot.effective_match_timing,
            effective_match_stamina=snapshot.effective_match_stamina,
            rally_calibration_profile=snapshot.rally_calibration_profile,
            effective_match_gameplans=snapshot.effective_match_gameplans,
            effective_rally_rules=snapshot.effective_rally_rules,
        )
        record["final"] = _canonical(result.model_dump(mode="json"))
        record["rallies"] = [_canonical(event.model_dump(mode="json"))
                             for event in result.rally_log.events]
    else:
        sessions, engine = _sessions(database)
        responses = []
        if phase == "start":
            with sessions() as session:
                state = PersistedLiveMatchStore(session).start_from_engine_input(
                    run_id="RUN", branch_id="BRANCH", week_ordinal=0, slot_id="SLOT-1",
                    group_id="GROUP-1", engine_input=snapshot,
                )
                session.commit()
                fingerprint = state.fingerprint
            record["start_fingerprint"] = fingerprint
            for command in range(1, CASES[case][5] + 1):
                response = _next(PersistedLiveMatchStore, sessions, command, fingerprint)
                fingerprint = response["state_fingerprint"]
                responses.append(_canonical(response))
                if response["final_result"] is not None:
                    raise SystemExit(f"{case}: match finished before the restart point")
            record["resume"] = {"command": command, "fingerprint": fingerprint}
        else:
            resume = json.loads((out.parent / f"{case}-start.json").read_text())["resume"]
            command, fingerprint = resume["command"], resume["fingerprint"]
            final = None
            while final is None:
                command += 1
                response = _next(PersistedLiveMatchStore, sessions, command, fingerprint)
                fingerprint = response["state_fingerprint"]
                responses.append(_canonical(response))
                final = response["final_result"]
                if command > 2000:
                    raise SystemExit("live match did not finish")
            record["final"] = _canonical(final)
        engine.dispose()
        with sqlite3.connect(database) as connection:
            record["integrity_check"] = connection.execute("PRAGMA integrity_check").fetchone()[0]
        record["responses"] = responses
    out.write_text(json.dumps(record, sort_keys=True))


def _run_tree(tree: Path, out: Path, python: str) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONHASHSEED": "0", "PYTHONPATH": str(tree / "src")}
    summary = {}
    for case in CASES:
        database = out / f"{case}.sqlite"
        database.unlink(missing_ok=True)
        for phase in ("start", "finish", "bulk"):
            subprocess.run([python, str(Path(__file__).resolve()), "_worker", phase, case,
                            str(database), str(out / f"{case}-{phase}.json")],
                           env=env, check=True)
        start, finish, bulk = (json.loads((out / f"{case}-{p}.json").read_text())
                               for p in ("start", "finish", "bulk"))
        for record in (start, finish, bulk):
            if not Path(record["beta_engine_file"]).resolve().is_relative_to(tree.resolve()):
                raise SystemExit(f"imported {record['beta_engine_file']} outside {tree}")
        live_rallies = [json.loads(r)["rally"] for r in start["responses"] + finish["responses"]]
        live_rallies = [_canonical(r) for r in live_rallies if r is not None]
        payload = _canonical({"start": start["responses"], "finish": finish["responses"],
                              "final": finish["final"], "start_fp": start["start_fingerprint"]})
        summary[case] = {
            "restart_after_command": start["resume"]["command"],
            "commands_total": len(start["responses"]) + len(finish["responses"]),
            "rallies": len(bulk["rallies"]),
            "live_equals_bulk": finish["final"] == bulk["final"] and live_rallies == bulk["rallies"],
            "integrity": [start["integrity_check"], finish["integrity_check"]],
            "live_sha256": hashlib.sha256(payload.encode()).hexdigest(),
            "bulk_sha256": hashlib.sha256(bulk["final"].encode()).hexdigest(),
        }
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="action")
    w = sub.add_parser("_worker")
    w.add_argument("phase", choices=("start", "finish", "bulk"))
    w.add_argument("case", choices=CASES)
    w.add_argument("database", type=Path)
    w.add_argument("out", type=Path)
    parser.add_argument("--a", type=Path)
    parser.add_argument("--b", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args(argv)
    if args.action == "_worker":
        worker(args.phase, args.case, args.database, args.out)
        return 0
    report = {"a": str(args.a), "b": str(args.b), "cases": {}}
    a = _run_tree(args.a.resolve(), args.out / "a", args.python)
    b = _run_tree(args.b.resolve(), args.out / "b", args.python)
    equal = True
    for case in CASES:
        same = a[case] == b[case]
        ok = same and a[case]["live_equals_bulk"] and a[case]["integrity"] == ["ok", "ok"]
        equal &= ok
        report["cases"][case] = {"a": a[case], "b": b[case], "trees_identical": same}
        print(f"{'equal' if ok else 'DIFFERENT':9s} {case:20s} restart@{a[case]['restart_after_command']:3d} "
              f"commands={a[case]['commands_total']:3d} rallies={a[case]['rallies']:3d} "
              f"live==bulk {a[case]['live_equals_bulk']}/{b[case]['live_equals_bulk']} "
              f"{a[case]['live_sha256'][:12]} {b[case]['live_sha256'][:12]}")
    report["verdict"] = "equal" if equal else "DIFFERENT"
    (args.out / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("verdict:", report["verdict"])
    return 0 if equal else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Opt-in real HTTP/SQLite load experiment; never a normal pytest test.

The opening Tour consumes the first week. Five signed 52-week seasons therefore
require a six-season *horizon* to transition across the fifth boundary.
All actual commands use the existing preview -> confirm -> explicit Save path.
"""
from __future__ import annotations

import argparse
import json
import math
import resource
import sqlite3
import sys
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

WEEKS_PER_SEASON = 52
EVENT_WEEKS = tuple(range(4, 51, 2))  # 24 Editions/season, weeks 4..50
TIERS = (
    ("satellite", 4, 100),
    ("challenger", 8, 250),
    ("international", 16, 500),
    ("major", 32, 1000),
)
STAGES = {
    4: ("champion", "finalist", "semifinal"),
    8: ("champion", "finalist", "semifinal", "quarterfinal"),
    16: ("champion", "finalist", "semifinal", "quarterfinal", "round16"),
    32: ("champion", "finalist", "semifinal", "quarterfinal", "round16", "round32"),
}


@dataclass(frozen=True)
class Edition:
    season: int
    week: int
    tier: str
    size: int
    points: int
    number: int

    @property
    def edition_id(self) -> str:
        return f"load-s{self.season + 1:02d}-w{self.week:02d}-{self.tier}"

    @property
    def point_table(self) -> dict[str, int]:
        return {
            stage: round(self.points * (0.60 ** index))
            for index, stage in enumerate(STAGES[self.size])
        }


def make_schedule(seasons: int = 5, editions_per_season: int = 24) -> tuple[Edition, ...]:
    if not 1 <= seasons <= 5 or not 1 <= editions_per_season <= len(EVENT_WEEKS):
        raise ValueError("seasons must be 1..5; Editions per season must be 1..24")
    return tuple(
        Edition(season, week, *TIERS[index % len(TIERS)], number=season * editions_per_season + index)
        for season in range(seasons)
        for index, week in enumerate(EVENT_WEEKS[:editions_per_season])
    )


class BudgetExpired(RuntimeError):
    pass


class Evidence:
    def __init__(self, root: Path, db: Path, budget_minutes: int):
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "timeline.jsonl"
        self.summary_path = root / "summary.json"
        self.db = db
        self.started = time.perf_counter()
        self.budget_seconds = budget_minutes * 60
        self.total = {"seasons_completed": 0, "editions_completed": 0,
                      "matches_completed": 0, "last_position": None,
                      "initial_players": None, "final_players": None,
                      "new_player_ids_seen": 0, "saved_revision_count": None}
        self.write_summary("running")

    def elapsed(self) -> float:
        return time.perf_counter() - self.started

    def metric(self, kind: str, **fields):
        obj = {"kind": kind, "elapsed_seconds": round(self.elapsed(), 3),
               "sqlite_bytes": self.db.stat().st_size if self.db.exists() else 0,
               "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               **fields}
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
        print("GIANT_LOAD " + json.dumps(obj, ensure_ascii=False, default=str), flush=True)

    @contextmanager
    def timed(self, name: str, **fields):
        started = time.perf_counter()
        try:
            yield
        finally:
            self.metric("operation", operation=name,
                        duration_seconds=round(time.perf_counter() - started, 3), **fields)

    def check_budget(self):
        if self.elapsed() >= self.budget_seconds:
            raise BudgetExpired(f"Wall-clock budget of {self.budget_seconds / 60:.0f} minutes reached")

    def write_summary(self, status: str, **extra):
        report = {"status": status, "elapsed_seconds": round(self.elapsed(), 3),
                  "budget_minutes": self.budget_seconds // 60,
                  "db_bytes": self.db.stat().st_size if self.db.exists() else 0,
                  **self.total, **extra}
        tmp = self.summary_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(self.summary_path)


def _save_prospects(server, repo, *, season: int, target_week: int, count: int):
    """Sign exactly the same source and Save gate exercised by native birth tests."""
    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from beta_engine.domain.calendar.run_week_position import RunWeekPosition
    from beta_engine.infrastructure.db.repositories import RunProspectRecord
    from tests.api.test_calendar_native_birth_week_execution import _record, source_at
    from tests.api.test_saved_revision_history_api import _request

    if not count:
        return ()
    world = repo.get_initial_world(run_id="run", branch_id="branch")
    clock = RunCalendar(WEEKS_PER_SEASON, 1, 2030, 6)
    target = RunWeekPosition(calendar=clock, season_index=season, week=target_week)
    records = []
    ids = []
    for index in range(count):
        player_id = f"load-born-{season:02d}-{index:03d}"
        source = source_at(clock, target, pid=player_id)
        # Reuse the real native cohort provenance and canonical sporting profile.
        record = RunProspectRecord(**(_record().__dict__ | {
            "prospect_id": player_id, "run_id": "run",
            "world_id": world.world_package_id,
            "season_start_year": source["season_start_year"],
            "season_label": str(source["season_start_year"]),
            "season_week": source["season_week"],
            "calendar_year": source["calendar_year"], "year_week": source["year_week"],
            "birth_year": source["birth_year"], "birth_year_week": source["birth_year_week"],
            "age": 15, "country_code": source["country_code"], "status": "prospect",
            "display_name": f"Load cohort {season + 1} athlete {index + 1}",
            "source_type": "native_calendar_15yo_cohort",
            "cohort_policy_version": "native_calendar_15yo_cohort_v1",
            "profile_version": "prospect_profile_v1",
            "profile_seed": "profile", "development_seed": "development",
            "potential_seed": "potential",
            "profile_json": source["profile"], "development_json": source["development"],
            "potential_json": source["potential"],
        }))
        records.append(record)
        ids.append(player_id)
    repo.upsert_run_prospects(records)
    root = server.base_url + "/admin/runs/run/branches/branch/authoritative-simulation/prospect-source/save"
    code, review = _request("GET", root + "/preview")
    assert code == 200 and review["can_save"], (code, review)
    code, saved = _request("POST", root, {
        "expected_draft_version": review["draft_version"],
        "expected_run_prospect_source_fingerprint": review["run_prospect_source_fingerprint"],
    })
    assert code == 201 and saved["saved_revision"], (code, saved)
    return tuple(ids)


def _plan_edition(server, edition: Edition):
    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour
    view = inspect(server)
    week = view["state"]["week"]
    assert (week["season_index"], week["week"]) == (edition.season, edition.week - 2)
    payload = {
        "schema_version": "calendar_tournament_edition.v2",
        "edition_id": edition.edition_id,
        "name": f"{edition.tier.title()} Load Cup S{edition.season + 1} W{edition.week}",
        "week": {**week, "week": edition.week},
        "announcement_week": {**week, "week": edition.week - 1},
        "start_slot": 1, "simulation_seed": 90100 + edition.number,
        "main_entrant_count": edition.size, "ranked": True,
        "validity_weeks": WEEKS_PER_SEASON, "point_table": edition.point_table,
    }
    execute(server, command(view, "create-edition", name=edition.edition_id + ":plan", data=payload))
    save_tour(server)


def _play_edition(server, edition: Edition, initial_professionals: tuple[str, ...]):
    """Only real signed Entry, actual global-slot rally matches and confirmation."""
    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour
    view = inspect(server)
    active = {p["player_id"] for p in view["players"]}
    eligible = [pid for pid in initial_professionals if pid in active]
    if len(eligible) < edition.size:
        raise RuntimeError(
            f"Cannot truthfully play {edition.size}-entrant Edition: "
            f"only {len(eligible)} initially signed professionals still present"
        )
    start = (edition.number * 17) % len(eligible)
    entrants = [eligible[(start + n) % len(eligible)] for n in range(edition.size)]
    execute(server, command(view, "submit", name=edition.edition_id + ":submit",
                            edition_id=edition.edition_id, data={"player_ids": entrants}))
    for action in ("approve", "draw"):
        execute(server, command(inspect(server), action,
                                name=edition.edition_id + ":" + action,
                                edition_id=edition.edition_id))
    save_tour(server)

    slots = 0
    match_count = 0
    while True:
        view = inspect(server)
        slot = view["next_slot"]
        if slot is None:
            break
        assert not slot["conflicts"] and slot["matches"], slot
        slots += 1
        if slots > int(math.log2(edition.size)) + 4:
            raise RuntimeError(f"Unexpected number of global slots for {edition.edition_id}")
        match_count += len(slot["matches"])
        execute(server, command(view, "next-slot", name=edition.edition_id + f":slot-{slots}"))
        save_tour(server)
    execute(server, command(inspect(server), "confirm-result",
                            name=edition.edition_id + ":confirm", edition_id=edition.edition_id))
    save_tour(server)
    view = inspect(server)
    assert next(row for row in view["state"]["editions"]
                if row["edition"]["edition_id"] == edition.edition_id)["result_confirmed"]
    # Keep compact evidence for later sporting analysis; no raw database upload needed.
    source = view["edition_evidence"][edition.edition_id]
    assert len(source["matches"]) == edition.size - 1
    assert len(source["results"]) == edition.size
    return {"edition_id": edition.edition_id, "tier": edition.tier,
            "entrant_ids": entrants, "slots": slots, "match_count": match_count,
            "results": source["results"]}


def run(args, evidence: Evidence):
    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup, tour_url
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    schedule = make_schedule(args.seasons, args.editions_per_season)
    by_play = {(event.season, event.week): event for event in schedule}
    by_plan = {(event.season, event.week - 2): event for event in schedule}
    all_new_ids = set()
    with ApiServer(database_url=f"sqlite:///{args.database}") as server:
        evidence.check_budget()
        with evidence.timed("initial-1000-player-world-and-tour"):
            repo, _ = setup(server, RunCalendar(52, 1, 2030, args.seasons + 1), count=args.players)
        world = repo.get_initial_world(run_id="run", branch_id="branch")
        if world.lifecycle_policy.requires_turn_pro:
            initial_professionals = tuple(sorted(world.initial_turn_pro.professional_player_ids))
        else:
            initial_professionals = tuple(sorted(p.player_id for p in world.players))
        if len(initial_professionals) < 32:
            raise RuntimeError(f"Large Edition requires 32 signed opening professionals; got {len(initial_professionals)}")
        evidence.total["initial_players"] = len(world.players)
        assert evidence.total["initial_players"] == args.players
        evidence.metric("initialized", players=args.players, eligible_professionals=len(initial_professionals),
                        editions_planned=len(schedule), seasons=args.seasons, horizon=args.seasons + 1)
        for season in range(args.seasons):
            view = inspect(server)
            starting_week = view["state"]["week"]["week"]
            assert view["state"]["week"]["season_index"] == season
            assert starting_week == (2 if season == 0 else 1), view["state"]["week"]
            # The initial Tour has already completed Week 1; use Week 3 birth in S1.
            birth_week = 3 if season == 0 else 2
            with evidence.timed("signed-prospect-source", season=season):
                new_ids = _save_prospects(server, repo, season=season,
                                          target_week=birth_week, count=args.born_per_season)
            all_new_ids.update(new_ids)
            season_start = time.perf_counter()
            for week in range(starting_week, WEEKS_PER_SEASON + 1):
                evidence.check_budget()
                view = inspect(server)
                assert (view["state"]["week"]["season_index"], view["state"]["week"]["week"]) == (season, week)
                week_start = time.perf_counter()
                if (season, week) in by_plan:
                    with evidence.timed("edition-plan-and-save", season=season, week=week):
                        _plan_edition(server, by_plan[(season, week)])
                if (season, week) in by_play:
                    event = by_play[(season, week)]
                    with evidence.timed("edition-real-match-play-and-save", season=season, week=week,
                                        edition_id=event.edition_id, entrants=event.size):
                        result = _play_edition(server, event, initial_professionals)
                    evidence.total["editions_completed"] += 1
                    evidence.total["matches_completed"] += result["match_count"]
                    evidence.metric("edition_completed", season=season, week=week, **result)
                with evidence.timed("week-transition-and-save", season=season, week=week):
                    action = "transition" if week < WEEKS_PER_SEASON else "season-transition"
                    execute(server, command(inspect(server), action,
                                            name=f"load-s{season + 1}-week-{week}-{action}"))
                    save_tour(server)
                current = inspect(server)
                new_active = {p["player_id"] for p in current["players"]} & all_new_ids
                evidence.total.update(
                    last_position=current["state"]["week"],
                    final_players=len(current["players"]),
                    new_player_ids_seen=len(new_active),
                )
                evidence.metric("week_completed", season=season, week=week,
                                duration_seconds=round(time.perf_counter() - week_start, 3),
                                players=len(current["players"]),
                                editions_completed=evidence.total["editions_completed"])
                evidence.write_summary("running")
            completed = inspect(server)["saved_completed_seasons"]
            assert completed == list(range(season + 1)), completed
            code, season_view = _request("GET", tour_url(server) + f"/seasons/{season}")
            assert code == 200 and season_view["selected"], (code, season_view)
            evidence.total["seasons_completed"] = season + 1
            evidence.metric("season_completed", season=season,
                            duration_seconds=round(time.perf_counter() - season_start, 3),
                            signed_seasons=completed,
                            overview=season_view["selected"].get("overview", {}))
            evidence.write_summary("running")
        # Current Saved HEAD is genuinely closed after the fifth Season Transition.
        final = inspect(server)
        assert final["saved_completed_seasons"] == list(range(args.seasons))
        assert final["saved"], "Must finish on an explicit signed Saved Revision"
        assert evidence.total["editions_completed"] == len(schedule)
        assert evidence.total["new_player_ids_seen"] >= args.born_per_season * args.seasons
        evidence.total["saved_revision_count"] = _saved_revision_count(args.database)
    evidence.metric("finished", **evidence.total)


def _saved_revision_count(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM branch_saved_revisions").fetchone()[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", type=int, default=5)
    parser.add_argument("--players", type=int, default=1000)
    parser.add_argument("--editions-per-season", type=int, default=24)
    parser.add_argument("--born-per-season", type=int, default=16)
    parser.add_argument("--budget-minutes", type=int, default=315)
    parser.add_argument("--output-dir", type=Path, default=Path("giant-load-evidence"))
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    schedule = make_schedule(args.seasons, args.editions_per_season)
    if args.players < 32 or args.born_per_season < 0 or args.budget_minutes < 1:
        parser.error("players must be >=32, births >=0, budget >=1")
    plan = {
        "simulated_seasons": args.seasons, "weeks_per_season": WEEKS_PER_SEASON,
        "simulated_week_positions": args.seasons * WEEKS_PER_SEASON,
        "clock_horizon_seasons": args.seasons + 1, "initial_players": args.players,
        "signed_births_planned": args.seasons * args.born_per_season,
        "editions": len(schedule),
        "category_counts": {tier: sum(e.tier == tier for e in schedule)
                            for tier, _, _ in TIERS},
        "field_sizes": sorted({e.size for e in schedule}),
        "event_weeks": sorted({e.week for e in schedule}),
    }
    if args.plan_only:
        print(json.dumps(plan, indent=2))
        return 0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.database = args.output_dir / "run.sqlite"
    if args.database.exists():
        parser.error("Refusing to overwrite an existing benchmark SQLite Run")
    evidence = Evidence(args.output_dir, args.database, args.budget_minutes)
    evidence.metric("plan", **plan)
    try:
        run(args, evidence)
    except BudgetExpired as exc:
        evidence.metric("budget_exhausted", message=str(exc))
        evidence.write_summary("budget_exhausted", message=str(exc))
        return 3
    except BaseException as exc:
        evidence.metric("failed", message=str(exc), traceback=traceback.format_exc())
        evidence.write_summary("failed", message=str(exc))
        raise
    else:
        evidence.write_summary("complete")
        return 0


if __name__ == "__main__":
    sys.exit(main())

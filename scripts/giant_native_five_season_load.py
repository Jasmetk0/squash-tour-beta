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
MAIN_WEEKS = tuple(range(4, 51))  # one regular event in each week 4..50
EXTRA_WEEKS = tuple(range(8, 49, 4)) + (44,)  # concurrent, diverse events
EVENT_WEEKS = tuple(sorted({*MAIN_WEEKS, *EXTRA_WEEKS, 51}))
EDITION_COUNT_PER_SEASON = len(MAIN_WEEKS) + len(EXTRA_WEEKS) + 1  # 60
TIERS = (
    ("regional", 16, 100),
    ("challenger", 32, 250),
    ("international", 64, 500),
    ("major", 128, 1000),
    ("elite", 32, 1500),
)
STAGES = {
    n: tuple(("champion", "finalist", "semifinal", "quarterfinal",
              "round16", "round32", "round64", "round128")[:n.bit_length()])
    for n in (4, 8, 16, 32, 64, 128)
}


@dataclass(frozen=True)
class Edition:
    season: int
    week: int
    tier: str
    size: int
    points: int
    number: int
    qualification_size: int = 0
    qualifier_spots: int = 0
    is_world_championship: bool = False
    entrant_offset: int = 0

    @property
    def edition_id(self) -> str:
        return f"load-s{self.season + 1:02d}-w{self.week:02d}-{self.number:03d}-{self.tier}"

    @property
    def point_table(self) -> dict[str, int]:
        return {
            stage: round(self.points * (0.60 ** index))
            for index, stage in enumerate(STAGES[self.size])
        }

    @property
    def expected_played_matches(self) -> int:
        # Only a planned minimum for an ordinary, fully contested binary Q/Main
        # with four independent qualifier brackets and no BYEs/WOs.
        return self.size - 1 + (
            self.qualification_size - self.qualifier_spots if self.qualification_size else 0
        )


def cohort_weeks(season: int) -> tuple[int, ...]:
    """Four signed birth waves; none is retroactive to the current Tour week."""
    return (3, 15, 28, 41) if season == 0 else (2, 14, 27, 40)


def make_schedule(seasons: int = 5, editions_per_season: int = 60,
                  *, profile: str = "requested") -> tuple[Edition, ...]:
    if profile not in {"requested", "compatible"}:
        raise ValueError("Unknown benchmark profile")
    if not 1 <= seasons <= 5 or not 1 <= editions_per_season <= EDITION_COUNT_PER_SEASON:
        raise ValueError("seasons must be 1..5; Editions per season must be 1..60")
    schedule = []
    for season in range(seasons):
        entries = []
        for i, week in enumerate(MAIN_WEEKS):
            tier, size, points = TIERS[i % len(TIERS)]
            qualifying = i % 3 == 0
            q_size = (16 if size <= 32 else 32) if qualifying else 0
            entries.append(Edition(season, week, tier, size, points,
                                   number=season * 60 + i,
                                   qualification_size=q_size,
                                   qualifier_spots=4 if qualifying else 0))
        for i, week in enumerate(EXTRA_WEEKS):
            size = (16, 32, 64)[i % 3]
            q_size = 16 if i % 2 == 0 else 0
            entries.append(Edition(season, week, "side", size, 125 + 50 * (i % 3),
                                   number=season * 60 + len(MAIN_WEEKS) + i,
                                   qualification_size=q_size,
                                   qualifier_spots=4 if q_size else 0))
        entries.append(Edition(season, 51, "world-championship", 128, 3000,
                               number=season * 60 + 59,
                               qualification_size=32, qualifier_spots=4,
                               is_world_championship=True))
        entries.sort(key=lambda e: (e.week, e.number))
        entries = entries[:editions_per_season]
        previous_week = None
        offset = 0
        for e in entries:
            if e.week != previous_week:
                offset = 0
            previous_week = e.week
            # In the compatible run, a real supported v2 Main-only event
            # replaces the unexecutable requested draw; never label it as 128.
            if profile == "compatible":
                e = Edition(e.season, e.week, e.tier + "-compatible",
                            4 if e.size <= 32 else 8, e.points, e.number,
                            is_world_championship=e.is_world_championship,
                            entrant_offset=offset)
            else:
                e = Edition(e.season, e.week, e.tier, e.size, e.points,
                            e.number, e.qualification_size, e.qualifier_spots,
                            e.is_world_championship, offset)
            schedule.append(e)
            offset += e.size
    return tuple(schedule)


def unsupported_execution_capabilities(schedule: tuple[Edition, ...]) -> list[dict]:
    """Never silently substitute an imagined 128-player engine executor."""
    problems = []
    large = sum(e.size not in (4, 8) for e in schedule)
    qualifying = sum(e.qualification_size > 0 for e in schedule)
    if large:
        problems.append({
            "code": "configured_native_v2_main_not_16_to_128",
            "affected_editions": large,
            "detail": "The v2 global-slot configured knockout executor has actual full-match support for 4/8 only.",
        })
    if qualifying:
        problems.append({
            "code": "native_v2_qualification_not_supported",
            "affected_editions": qualifying,
            "detail": "Canonical v4 needs source-bound Saved Draw Q/Main adoption; a v2 Edition has no Q phase.",
        })
    return problems


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


def _save_prospects(server, repo, *, season: int, count: int, horizon: int):
    """Sign exactly the same source and Save gate exercised by native birth tests."""
    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from beta_engine.domain.calendar.run_week_position import RunWeekPosition
    from beta_engine.infrastructure.db.repositories import RunProspectRecord
    from tests.application.test_calendar_native_prospect_intake import source_at
    from tests.application.test_prospect_persistence import _record
    from tests.api.test_saved_revision_history_api import _request

    if not count:
        return ()
    world = repo.get_initial_world(run_id="run", branch_id="branch")
    clock = RunCalendar(WEEKS_PER_SEASON, 1, 2030, horizon)
    targets = tuple(RunWeekPosition(calendar=clock, season_index=season, week=week)
                    for week in cohort_weeks(season))
    records = []
    ids = []
    for index in range(count):
        player_id = f"load-born-{season:02d}-{index:03d}"
        source = source_at(clock, targets[index % len(targets)], pid=player_id)
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
        "name": (f"World Championship compatibility surrogate ({edition.size}-entrant Main)"
                 if edition.is_world_championship and edition.size <= 8
                 else f"{edition.tier.title()} Load Cup S{edition.season + 1} W{edition.week}"),
        "week": {**week, "week": edition.week},
        "announcement_week": {**week, "week": edition.week - 1},
        "start_slot": 1, "simulation_seed": 90100 + edition.number,
        "main_entrant_count": edition.size, "ranked": True,
        "validity_weeks": WEEKS_PER_SEASON, "point_table": edition.point_table,
    }
    execute(server, command(view, "create-edition", name=edition.edition_id + ":plan", data=payload))
    save_tour(server)


def _play_week(server, editions: tuple[Edition, ...], initial_professionals: tuple[str, ...]):
    """Prepare all same-week fields first, then execute *shared* real slots.

    Multiple simultaneous Editions are independent only when their player
    fields are disjoint, so prevent cross-Edition sporting-input conflicts.
    """
    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour
    if not editions:
        return []
    view = inspect(server)
    active = {p["player_id"] for p in view["players"]}
    eligible = [pid for pid in initial_professionals if pid in active]
    required = max(e.entrant_offset + e.size for e in editions)
    if len(eligible) < required:
        raise RuntimeError(f"Need {required} separate eligible initial professionals; got {len(eligible)}")
    week = editions[0].week
    season = editions[0].season
    assert all((e.week, e.season) == (week, season) for e in editions)
    base = (season * 127 + week * 19) % len(eligible)
    fields = {}
    for event in editions:
        entrants = [eligible[(base + event.entrant_offset + n) % len(eligible)]
                    for n in range(event.size)]
        fields[event.edition_id] = entrants
    flat = [player for ids in fields.values() for player in ids]
    assert len(flat) == len(set(flat)), "A simultaneous player must not enter two tournaments"
    for event in editions:
        event_id = event.edition_id
        execute(server, command(inspect(server), "submit", name=event_id + ":submit",
                                edition_id=event_id, data={"player_ids": fields[event_id]}))
        for action in ("approve", "draw"):
            execute(server, command(inspect(server), action,
                                    name=event_id + ":" + action, edition_id=event_id))
        save_tour(server)
    slot_count = 0
    slot_match_count = 0
    while True:
        view = inspect(server)
        slot = view["next_slot"]
        if slot is None:
            break
        assert not slot["conflicts"] and slot["matches"], slot
        slot_count += 1
        if slot_count > 16:
            raise RuntimeError(f"Unbounded global slots at season={season} week={week}")
        slot_match_count += len(slot["matches"])
        execute(server, command(view, "next-slot",
                                name=f"load-s{season + 1}-w{week}-slot-{slot_count}"))
        save_tour(server)

    completed = []
    for event in editions:
        event_id = event.edition_id
        execute(server, command(inspect(server), "confirm-result",
                                name=event_id + ":confirm", edition_id=event_id))
        save_tour(server)
        view = inspect(server)
        assert next(row for row in view["state"]["editions"]
                    if row["edition"]["edition_id"] == event_id)["result_confirmed"]
        evidence = view["edition_evidence"][event_id]
        assert len(evidence["matches"]) == event.size - 1
        assert len(evidence["results"]) == event.size
        completed.append({
            "edition_id": event_id, "tier": event.tier,
            "world_championship_compatibility_surrogate": event.is_world_championship,
            "main_entrants": event.size,
            "qualification_entrants": 0,
            "entrant_ids": fields[event_id], "slots_in_week": slot_count,
            "match_count": len(evidence["matches"]), "results": evidence["results"],
        })
    assert sum(item["match_count"] for item in completed) == slot_match_count
    return completed


def run(args, evidence: Evidence):
    from collections import defaultdict
    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup, tour_url
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    schedule = make_schedule(args.seasons, args.editions_per_season, profile=args.profile)
    blockers = unsupported_execution_capabilities(schedule)
    if blockers:
        raise RuntimeError(f"The requested profile is not playable by native v2: {blockers}")
    by_play = defaultdict(list)
    by_plan = defaultdict(list)
    for event in schedule:
        by_play[(event.season, event.week)].append(event)
        by_plan[(event.season, event.week - 2)].append(event)
    all_new_ids = set()
    with ApiServer(database_url=f"sqlite:///{args.database}") as server:
        evidence.check_budget()
        with evidence.timed("initial-world-and-tour", player_count=args.players):
            repo, _ = setup(server, RunCalendar(52, 1, 2030, args.seasons + 1), count=args.players)
        world = repo.get_initial_world(run_id="run", branch_id="branch")
        if world.lifecycle_policy.requires_turn_pro:
            initial_professionals = tuple(sorted(world.initial_turn_pro.professional_player_ids))
        else:
            initial_professionals = tuple(sorted(p.player_id for p in world.players))
        needed = max(sum(event.size for event in by_play[key]) for key in by_play)
        if len(initial_professionals) < needed:
            raise RuntimeError(f"Simultaneous fields require {needed} independently signed pros; got {len(initial_professionals)}")
        evidence.total["initial_players"] = len(world.players)
        assert evidence.total["initial_players"] == args.players
        evidence.metric("initialized", players=args.players, eligible_professionals=len(initial_professionals),
                        editions_planned=len(schedule), seasons=args.seasons, horizon=args.seasons + 1)
        for season in range(args.seasons):
            view = inspect(server)
            starting_week = view["state"]["week"]["week"]
            assert view["state"]["week"]["season_index"] == season
            assert starting_week == (2 if season == 0 else 1), view["state"]["week"]
            with evidence.timed("four-signed-prospect-waves", season=season,
                                wave_weeks=cohort_weeks(season), planned_players=args.born_per_season):
                new_ids = _save_prospects(server, repo, season=season,
                                          count=args.born_per_season,
                                          horizon=args.seasons + 1)
            assert len(new_ids) == args.born_per_season
            all_new_ids.update(new_ids)
            evidence.metric("cohort_source_signed", season=season,
                            source_players=len(new_ids), wave_weeks=cohort_weeks(season))
            season_start = time.perf_counter()
            for week in range(starting_week, WEEKS_PER_SEASON + 1):
                evidence.check_budget()
                view = inspect(server)
                assert (view["state"]["week"]["season_index"], view["state"]["week"]["week"]) == (season, week)
                week_start = time.perf_counter()
                for event in by_plan[(season, week)]:
                    with evidence.timed("edition-plan-and-save", season=season, week=week,
                                        edition_id=event.edition_id, entrants=event.size):
                        _plan_edition(server, event)
                if by_play[(season, week)]:
                    events = tuple(by_play[(season, week)])
                    with evidence.timed("week-real-match-play-and-save", season=season, week=week,
                                        edition_count=len(events), entrants=sum(e.size for e in events)):
                        completed = _play_week(server, events, initial_professionals)
                    for result in completed:
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
                                new_arrivals_active=len(new_active),
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
        final = inspect(server)
        assert final["saved_completed_seasons"] == list(range(args.seasons))
        assert final["saved"], "Must finish on an explicit signed Saved Revision"
        assert evidence.total["editions_completed"] == len(schedule)
        assert evidence.total["new_player_ids_seen"] >= args.born_per_season * args.seasons
        evidence.total["saved_revision_count"] = _saved_revision_count(args.database)
    # Cold-start reads of five signed seasons are part of the true benchmark.
    with evidence.timed("final-cold-restart-and-signed-season-archive"):
        with ApiServer(database_url=f"sqlite:///{args.database}") as restarted:
            actual = inspect(restarted)
            assert actual["saved_completed_seasons"] == list(range(args.seasons))
            code, archived = _request("GET", tour_url(restarted) + "/seasons")
            assert code == 200 and len(archived["seasons"]) == args.seasons
            assert actual["saved"]
    evidence.metric("finished", **evidence.total)


def _saved_revision_count(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM branch_saved_revisions").fetchone()[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("requested", "compatible"), default="requested",
                        help="requested is a 16-128/Q/world specification; compatible is an explicitly separate 4/8 Main-only benchmark")
    parser.add_argument("--seasons", type=int, default=5)
    parser.add_argument("--players", type=int, default=1000)
    parser.add_argument("--editions-per-season", type=int, default=60)
    parser.add_argument("--born-per-season", type=int, default=80)
    parser.add_argument("--budget-minutes", type=int, default=315)
    parser.add_argument("--output-dir", type=Path, default=Path("giant-load-evidence"))
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    schedule = make_schedule(args.seasons, args.editions_per_season, profile=args.profile)
    if args.players < 128 or args.born_per_season < 0 or args.budget_minutes < 1:
        parser.error("initial players must be >=128; arrivals >=0; budget >=1")
    blockers = unsupported_execution_capabilities(schedule)
    plan = {
        "profile": args.profile, "status": "blocked" if blockers else "runnable",
        "simulated_seasons": args.seasons, "weeks_per_season": WEEKS_PER_SEASON,
        "simulated_week_positions": args.seasons * WEEKS_PER_SEASON,
        "clock_horizon_seasons": args.seasons + 1,
        "initial_players": args.players, "planned_annual_arrivals": args.born_per_season,
        "total_signed_births_planned": args.seasons * args.born_per_season,
        "birth_week_waves": {str(s + 1): cohort_weeks(s) for s in range(args.seasons)},
        "editions": len(schedule), "editions_per_season": args.editions_per_season,
        "category_counts": {tier: sum(e.tier == tier for e in schedule)
                            for tier in sorted({e.tier for e in schedule})},
        "field_sizes": sorted({e.size for e in schedule}),
        "qualifying_editions": sum(e.qualification_size > 0 for e in schedule),
        "qualifying_field_sizes": sorted({e.qualification_size for e in schedule if e.qualification_size}),
        "world_championship_editions": sum(e.is_world_championship for e in schedule),
        "world_championships_are_compatible_surrogates": (
            args.profile == "compatible"),
        "min_expected_match_engine_matches": sum(e.expected_played_matches for e in schedule),
        "event_weeks": sorted({e.week for e in schedule}),
        "blockers": blockers,
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
    if blockers:
        evidence.write_summary("unsupported", blockers=blockers, profile=args.profile)
        evidence.metric("not_executed", reason="Required production tournament capabilities are absent")
        return 4
    try:
        run(args, evidence)
    except BudgetExpired as exc:
        evidence.metric("budget_exhausted", message=str(exc))
        evidence.write_summary("budget_exhausted", message=str(exc), profile=args.profile)
        return 3
    except BaseException as exc:
        evidence.metric("failed", message=str(exc), traceback=traceback.format_exc())
        evidence.write_summary("failed", message=str(exc), profile=args.profile)
        raise
    else:
        evidence.write_summary("complete", profile=args.profile)
        return 0


if __name__ == "__main__":
    sys.exit(main())

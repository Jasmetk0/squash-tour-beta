"""Read-only evidence gate for genuinely Signed native Tour seasons.

Requires production-authenticated Admin GET projections. It cannot produce
a Season, Save a Draft, authorize sport, or turn planned Editions into results.
Usage:
 python tools/audit_native_signed_seasons.py \
     --base-url http://127.0.0.1:8000 --run RUN --branch BRANCH \
     --required-seasons 50 --minimum-completed-editions 80

The 80 threshold counts *all* confirmed Editions, NOT specifically the
80 World Tour calendar identities. The separate FAX category/roster,
50-season scientific validity, and internal release gates remain mandatory.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen


class EvidenceFailure(ValueError):
    """A required source, fact or immutable lineage check did not pass."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise EvidenceFailure(reason)


def positive_integer(value: Any, *, allow_zero: bool = True) -> bool:
    return type(value) is int and value >= (0 if allow_zero else 1)


def items(value: Any, what: str) -> list:
    require(type(value) is list, what + " must be a JSON array")
    return value


def record_identity(row: dict, name: str) -> str:
    value = row.get(name)
    require(type(value) is str and bool(value.strip()), name + " must be present")
    return value


def nonnegative(row: dict, key: str) -> int:
    value = row.get(key)
    require(positive_integer(value), key + " must be a nonnegative integer")
    return value


def inspect_season(row: dict, index: int, fingerprint: str) -> dict:
    require(type(row) is dict, "Season response is not an object")
    require(row.get("schema_version") in {
        "native_tour_signed_season_summary.v1",
        "native_tour_signed_season_summary.v2",
    }, "Season has an unsupported Signed summary schema")
    require(row.get("season_index") == index, "Season index mismatch")
    require(row.get("source_tour_fingerprint") == fingerprint,
            "Season's signed sporting source differs from Records")
    record_identity(row, "boundary_command_id")
    require(positive_integer(row.get("weeks_per_season"), allow_zero=False),
            "Season has no valid sporting calendar width")
    last = row.get("last_week_published_ranking")
    require(type(last) is dict and last.get("week") == row["weeks_per_season"],
            "Missing actual final-week published Official Ranking")
    record_identity(last, "source_fingerprint")
    ranking_players = items(last.get("top_players"), "Final-week ranking players")
    ids = [record_identity(p, "player_id") for p in ranking_players]
    require(len(set(ids)) == len(ids), "Final-week ranking has duplicate player IDs")
    for p in ranking_players:
        nonnegative(p, "points")
        require(positive_integer(p.get("rank"), allow_zero=False),
                "Final-week player has an invalid rank")

    editions = items(row.get("editions"), "Signed played Editions")
    require(nonnegative(row, "completed_edition_count") == len(editions),
            "Completed Edition count differs from actual signed edition records")
    identities: set[str] = set()
    champion_count = finalist_count = 0
    for event in editions:
        require(type(event) is dict, "Completed Edition item is not an object")
        eid = record_identity(event, "edition_id")
        require(eid not in identities, "Repeated Edition ID in Signed season")
        identities.add(eid)
        require(positive_integer(event.get("week"), allow_zero=False)
                and event["week"] <= row["weeks_per_season"],
                "Completed Edition has no valid season week")
        record_identity(event, "source_tournament_fingerprint")
        winner, runner = event.get("champion_player_id"), event.get("finalist_player_id")
        # v2 multi-group events legitimately have no single champion/finalist.
        require((winner is None) == (runner is None),
                "Signed Edition has an incomplete champion/finalist pair")
        if winner is not None:
            require(type(winner) is str and bool(winner.strip())
                    and type(runner) is str and bool(runner.strip())
                    and winner != runner, "Signed Edition has invalid final identities")
            champion_count += 1
            finalist_count += 1

    countries = items(row.get("countries"), "Signed country totals")
    players = items(row.get("players"), "Signed player totals")
    summary: dict[str, dict[str, dict[str, int]]] = {"player": {}, "country": {}}
    for category, data, key in (
        ("player", players, "player_id"),
        ("country", countries, "country_code"),
    ):
        for item in data:
            require(type(item) is dict, "Invalid signed participant aggregate")
            identity = record_identity(item, key)
            require(identity not in summary[category],
                    "Duplicated Signed participant aggregate")
            summary[category][identity] = {
                f: nonnegative(item, f) for f in ("titles", "finals", "awarded_points")
            }
    for category in ("player", "country"):
        require(sum(p["titles"] for p in summary[category].values()) == champion_count,
                category + " titles do not reconcile with actual finals")
        require(sum(p["finals"] for p in summary[category].values()) == finalist_count,
                category + " finalist counts do not reconcile")
    require(sum(p["awarded_points"] for p in summary["player"].values())
            == sum(c["awarded_points"] for c in summary["country"].values()),
            "Player and country awarded Edition points disagree")
    return {
        "season_index": index,
        "weeks_per_season": row["weeks_per_season"],
        "signed_boundary_command_id": row["boundary_command_id"],
        "completed_edition_count": len(editions),
        "actual_champions": champion_count,
        "nonfinal_group_editions": len(editions) - champion_count,
        "awarded_edition_points": sum(c["awarded_points"]
                                      for c in summary["country"].values()),
        "last_week_ranking_fingerprint": last["source_fingerprint"],
        "aggregates": summary,
    }


def audit_signed_seasons(
    read: Callable[[str], dict], *, run_id: str, branch_id: str,
    required_seasons: int = 50, minimum_completed_editions: int = 80,
) -> dict:
    """Read-only acceptance facts; source/HEAD must remain identical throughout.

    `read` requests exact relative API paths. If a source changes mid-audit,
    fail rather than silently mixing histories from multiple Saved heads.
    A PASS is *only* for the requested bounded conditions.
    """
    require(bool(run_id.strip()) and bool(branch_id.strip()),
            "Run and Branch must be explicit")
    require(positive_integer(required_seasons, allow_zero=False),
            "Required completed season count must be positive")
    require(positive_integer(minimum_completed_editions),
            "Minimum completed Editions must be nonnegative")
    root = ("/admin/runs/" + quote(run_id, safe="")
            + "/branches/" + quote(branch_id, safe="") + "/calendar-tour")
    records_path = root + "/records"
    records = read(records_path)
    require(type(records) is dict
            and records.get("schema_version") == "calendar_tour_signed_records_response.v1",
            "Native Signed Records endpoint did not return a supported projection")
    require(records.get("run_id") == run_id and records.get("branch_id") == branch_id,
            "Records belong to another Run or Branch")
    head = record_identity(records, "saved_head_revision_id")
    fingerprint = record_identity(records, "source_tour_fingerprint")
    complete = items(records.get("completed_seasons"), "Signed season indices")
    require(all(positive_integer(s) for s in complete)
            and complete == list(range(len(complete))),
            "Signed completed seasons are missing, repeated or noncontiguous")
    require(len(complete) >= required_seasons,
            f"Only {len(complete)} Signed seasons; {required_seasons} required")
    require(records.get("as_of_season_index") == complete[-1]
            and records.get("from_season_index") == 0
            and records.get("country_code") is None,
            "Records do not cover the complete unfiltered Signed window")

    sources = items(records.get("source_seasons"), "Records source seasons")
    require(len(sources) == len(complete),
            "Records signed season source count mismatch")
    evidence = []
    totals: dict[str, dict[str, dict[str, int]]] = {
        "player": defaultdict(lambda: {"titles": 0, "finals": 0, "awarded_points": 0}),
        "country": defaultdict(lambda: {"titles": 0, "finals": 0, "awarded_points": 0}),
    }
    for index, source in enumerate(sources):
        require(type(source) is dict
                and source.get("season_index") == index
                and source.get("source_tour_fingerprint") == fingerprint,
                "Records season source disagrees with Signed Tour lineage")
        report = read(root + "/seasons/" + str(index))
        require(type(report) is dict
                and report.get("schema_version") == "calendar_tour_season_comparison.v1"
                and report.get("run_id") == run_id
                and report.get("branch_id") == branch_id
                and report.get("saved_head_revision_id") == head
                and report.get("comparison") is None,
                "Season comparison comes from another Saved Run/Branch/HEAD")
        data = inspect_season(report.get("selected"), index, fingerprint)
        require(source.get("boundary_command_id") == data["signed_boundary_command_id"]
                and source.get("completed_edition_count") == data["completed_edition_count"]
                and source.get("published_ranking_fingerprint")
                == data["last_week_ranking_fingerprint"],
                "Signed Record/season boundary, ranking or completed count differs")
        require(data["completed_edition_count"] >= minimum_completed_editions
                or index >= required_seasons,
                f"S{index + 1} contains only {data['completed_edition_count']} actually "
                f"confirmed Editions; required at least {minimum_completed_editions}")
        for kind in ("player", "country"):
            for identity, values in data["aggregates"][kind].items():
                for field, value in values.items():
                    totals[kind][identity][field] += value
        evidence.append({k: v for k, v in data.items() if k != "aggregates"})

    require(nonnegative(records, "completed_edition_count")
            == sum(s["completed_edition_count"] for s in evidence),
            "Records cumulative Edition count does not match all signed seasons")
    metrics = items(records.get("records"), "Signed records catalog")
    expected = {(scope, field) for scope in ("player", "country")
                for field in ("titles", "finals", "awarded_points")}
    require({(m.get("scope"), m.get("metric")) for m in metrics
             if type(m) is dict} == expected and len(metrics) == len(expected),
            "Signed records metric catalog is incomplete or duplicated")
    for metric in metrics:
        kind, field = metric["scope"], metric["metric"]
        require(metric.get("record_id") == f"native_tour.{kind}.{field}.v1",
                "Signed record identity is unsupported")
        actual_max = max((v[field] for v in totals[kind].values()), default=0)
        require(nonnegative(metric, "value") == actual_max,
                "Cumulative historical record differs from signed season totals")
        holders = items(metric.get("holders"), "Full tied record holders")
        actual_ids = {identity for identity, counts in totals[kind].items()
                      if actual_max > 0 and counts[field] == actual_max}
        require({h.get("entity_id") for h in holders} == actual_ids
                and len(holders) == len(actual_ids),
                "Signed record co-holders differ from all authenticated season totals")

    # Detect a concurrent Save/fork/rebase while scanning up to 50 year reports.
    final = read(records_path)
    require(final == records,
            "Signed Records/HEAD changed during audit; retry from one consistent source")
    return {
        "schema_version": "native_signed_season_evidence.v1",
        "status": "SCOPED_EVIDENCE_PASS",
        "not_a_prealpha_release": True,
        "authority": "server_authenticated_saved_native_tour_reads",
        "run_id": run_id, "branch_id": branch_id,
        "saved_head_revision_id": head,
        "source_tour_fingerprint": fingerprint,
        "required_completed_seasons": required_seasons,
        "observed_completed_seasons": len(complete),
        "minimum_completed_editions_per_required_season": minimum_completed_editions,
        "observed_completed_editions_all_seasons": records["completed_edition_count"],
        "season_evidence": evidence,
        "limitations": [
            "All completed Editions, not necessarily 80 World Tour Editions by category",
            "No 1000-player initial historical cohort verification",
            "No scientific realism validation or 50-season numerical stability proof",
            "No Windows/browser, archive recovery, full suite or security clearance",
        ],
    }


def http_reader(base_url: str, timeout: float) -> Callable[[str], dict]:
    parsed = urlsplit(base_url)
    require(parsed.scheme in {"http", "https"}
            and bool(parsed.netloc) and not parsed.username and not parsed.password
            and not parsed.query and not parsed.fragment,
            "Use an explicit HTTP(S) base URL without embedded credentials")
    require(timeout > 0 and timeout <= 120, "HTTP timeout must be between 0 and 120s")
    base = base_url.rstrip("/")
    def read(path: str) -> dict:
        require(path.startswith("/admin/runs/"), "Audit may read only Admin Tour sources")
        try:
            request = Request(base + path, method="GET",
                              headers={"Accept": "application/json"})
            with urlopen(request, timeout=timeout) as response:
                require(response.status == 200, f"GET {path}: HTTP {response.status}")
                body = response.read(12 * 1024 * 1024 + 1)
                require(len(body) <= 12 * 1024 * 1024,
                        "Signed response exceeds bounded 12 MiB")
                data = json.loads(body)
                require(type(data) is dict, "Signed response is not a JSON object")
                return data
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise EvidenceFailure(f"GET {path} did not return authenticated JSON: "
                                  f"{type(exc).__name__}") from exc
    return read


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--run", required=True, help="Exact existing native Run ID")
    parser.add_argument("--branch", required=True, help="Exact signed Branch ID")
    parser.add_argument("--required-seasons", type=int, default=50)
    parser.add_argument("--minimum-completed-editions", type=int, default=80)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output", type=Path, default=None,
                        help="Optional path for machine-readable evidence JSON")
    args = parser.parse_args(argv)
    try:
        result = audit_signed_seasons(
            http_reader(args.base_url, args.timeout), run_id=args.run,
            branch_id=args.branch, required_seasons=args.required_seasons,
            minimum_completed_editions=args.minimum_completed_editions,
        )
        data = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output is not None:
            args.output.write_text(data, encoding="utf-8")
        print(data, end="")
        return 0
    except (EvidenceFailure, ValueError) as exc:
        print(json.dumps({
            "schema_version": "native_signed_season_evidence.v1",
            "status": "FAIL",
            "not_a_prealpha_release": True,
            "error": str(exc),
        }, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Read a licensed local audit-only input, never install or export player/match records."""
import argparse
import csv
import io
import json
from pathlib import Path

from scripts.audit_atp_2019_research import ROOT, load
from scripts.audit_atp_2019_external_tournaments import read_pinned


def audit_matches(raw):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    required = {"tourney_id", "tourney_name", "tourney_level", "tourney_date",
                "draw_size", "match_num", "round", "winner_rank_points", "loser_rank_points"}
    if reader.fieldnames is None or not required <= set(reader.fieldnames):
        raise ValueError("Unexpected Sackmann main-draw columns")
    groups, scoped, seen = set(), set(), set()
    count = scope_count = 0
    for row in reader:
        if None in row or any(row[k] is None for k in required):
            raise ValueError("Malformed main-draw row")
        key = row["tourney_id"]
        if not key.startswith("2019-"):
            raise ValueError("Unexpected season")
        match = (key, row["match_num"])
        if match in seen:
            raise ValueError("Duplicate source match identity")
        seen.add(match)
        groups.add(key)
        count += 1
        if row["tourney_level"] in {"A", "M", "F"} and key != "2019-9210":
            scoped.add(key)
            scope_count += 1
    return dict(all_rows=count, all_groups=len(groups), scope_groups=len(scoped),
                scope_rows=scope_count)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--matches", type=Path)
    args = p.parse_args()
    m = load(ROOT / "research_2019/sackmann_input.json")
    if args.matches is None:
        print(json.dumps({"status": "missing_local_input", "source": m["source"]}))
        return 2
    result = audit_matches(read_pinned(args.matches, m["source"]))
    if any(result[k] != m["aggregate_observation"][k] for k in result):
        raise ValueError("Pinned source aggregate mismatch")
    from scripts.audit_atp_2019_match_crosscheck import compare_match_groups
    crosswalk = load(ROOT / "research_2019/identity_crosswalk.json")
    comparison = compare_match_groups(read_pinned(args.matches, m["source"]), crosswalk, m)
    print(json.dumps({"aggregate": result, "comparison": comparison}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

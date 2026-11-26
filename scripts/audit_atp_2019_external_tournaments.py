"""Reproduce the external 2019 tournament roster check from the exact local CSV."""
from collections import Counter
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

from scripts.audit_atp_2019_research import ROOT, load

SCOPE = {"ATP 250": "atp_250", "ATP 500": "atp_500",
         "Masters 1000": "atp_masters_1000", "ATP Finals": "atp_finals",
         "Next Gen Finals": "next_gen_finals"}


def read_pinned(path, source):
    data = path.read_bytes()
    if len(data) != source["bytes"] or hashlib.sha256(data).hexdigest() != source["sha256"]:
        raise ValueError("External input bytes do not match the pinned source")
    return data


def compare_2019(data, manifest, inventory):
    rows = [r for r in csv.reader(io.StringIO(data.decode("utf-8"), newline=""))
            if r and r[0].startswith("2019-")]
    if any(len(r) != 31 or r[8] != "2019" or r[0] != f"2019-{r[4]}" for r in rows):
        raise ValueError("Invalid 2019 tournament identity/row layout")
    by_id = {r[4]: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError("Duplicate ATP event ID")
    actual = manifest["observed_2019"]
    by_type = dict(Counter(r[2] for r in rows))
    excluded = sorted(r[4] for r in rows if r[2] not in SCOPE)
    if len(rows) != actual["all"] or by_type != actual["by_type"] or excluded != sorted(actual["excluded_ids"]):
        raise ValueError("External 2019 roster differs from recorded evidence")
    year = next(y for y in inventory["years"] if y["year"] == 2019)
    canonical = {e["occurrence_id"]: e for e in year["events"]}
    categories = Counter(e["category_id"] for e in canonical.values())
    external = {SCOPE[k]: v for k, v in by_type.items() if k in SCOPE}
    if dict(categories) != external or sum(external.values()) != actual["in_scope"]:
        raise ValueError("Canonical/external category counts differ")
    matched, ids = set(), set()
    for e in actual["matched_reviewed"]:
        key, event_id = e["occurrence_id"], e["atp_id"]
        row = by_id[event_id]
        c = canonical[key]
        start = row[7].replace(".", "-")
        if (key in matched or event_id in ids or row[2] != e["type"]
                or start != e["start"] or c["main_start"] != start
                or c["category_id"] != SCOPE[row[2]] or int(row[11]) != e["advertised_main"]):
            raise ValueError(f"Reviewed external binding mismatch: {key}")
        matched.add(key)
        ids.add(event_id)
    unresolved = sorted(set(canonical) - matched)
    unmatched_external_ids = sorted(set(r[4] for r in rows if r[2] in SCOPE) - ids)
    if len(unresolved) != actual["remaining_identity_review"]:
        raise ValueError("Identity-review queue changed")
    return {"all_external": len(rows), "in_scope": sum(external.values()),
            "categories": external, "reviewed_identity_count": len(matched),
            "unmatched_canonical": unresolved, "unmatched_external_atp_ids": unmatched_external_ids,
            "qualification_dates_certified": 0, "production_profiles_certified": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tournaments", type=Path)
    args = parser.parse_args()
    root = ROOT / "research_2019"
    manifest = load(root / "external_tournament_input.json")
    if args.tournaments is None:
        print(json.dumps({"status": "missing_local_input", "source": manifest["source"]}, indent=2))
        return 2
    data = read_pinned(args.tournaments, manifest["source"])
    print(json.dumps(compare_2019(data, manifest, load(root / "inventory.json")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

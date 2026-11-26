"""Offline inventory validation for the 2019 research batch (not import authority)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "config/reference_packages/atp_tour_1990_2026"
RESEARCH = ROOT / "research_2019"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def audit(root=ROOT):
    research = root / "research_2019"
    inventory = load(research / "inventory.json")
    evidence = load(research / "edition_evidence.json")
    for name, expected in inventory["source_blobs"].items():
        if git_blob_sha(root / name) != expected:
            raise ValueError(f"Pinned canonical input changed: {name}")
    calendar = load(root / "calendar_dates_v1.json")["year_sources"]
    seasons = load(root / "seasons_1990_2026.json")["seasons"]
    sporting = load(root / "squash_sporting_profiles_v1.json")
    profiles = {p["occurrence_id"] for p in sporting["profiles"]}
    if len(profiles) != len(sporting["profiles"]):
        raise ValueError("Duplicate sporting profile")
    years, events = [], {}
    for season in seasons:
        year = season["year"]
        dated = calendar[str(year)]["events"]
        memberships = season["series_category_ids"]
        held = {e["series_id"] for e in dated}
        cancelled = set(season["known_not_held_series_ids"])
        if len(held) != len(dated) or held & cancelled or not held <= memberships.keys():
            raise ValueError(f"Invalid membership partition: {year}")
        for e in dated:
            key = f"atp_{year}_{e['series_id']}"
            if key in events:
                raise ValueError(f"Duplicate occurrence: {key}")
            events[key] = (memberships[e["series_id"]], e["start_date"], e["end_date"])
        years.append(dict(year=year, dated=len(dated), not_held=sorted(cancelled),
                          profiled=sum(f"atp_{year}_{s}" in profiles for s in held),
                          undated=sorted(memberships.keys() - held - cancelled)))
    if not profiles <= events.keys():
        raise ValueError("Orphan sporting profile")
    for actual, recorded in zip(years, inventory["years"], strict=True):
        if actual != {key: recorded[key] if key != "not_held" else sorted(recorded[key])
                      for key in actual}:
            raise ValueError(f"Inventory drift: {actual['year']}")
    totals = dict(dated=len(events), not_held=sum(len(y["not_held"]) for y in years),
                  profiled=len(profiles))
    if totals != inventory["totals"] or sporting["source_version"] != inventory["source_version"]:
        raise ValueError("Inventory totals/version drift")
    if {e["occurrence_id"] for e in inventory["years"][2019-1990]["events"]} != {
            key for key in events if key.startswith("atp_2019_")}:
        raise ValueError("2019 research queue is incomplete")
    seen = set()
    for e in evidence["rows"]:
        key, g = e["occurrence_id"], e["geometry"]
        if key in seen or events[key] != (e["category_id"], e["main_start"], e["main_end"]):
            raise ValueError(f"Bad evidence binding: {key}")
        seen.add(key)
        if (g["main_capacity"] - g["main_entrants"] != g["main_byes"]
                or g["q_capacity"] - g["q_entrants"] != g["q_byes"]
                or sum(e["q_round_matches"]) != g["q_entrants"] - g["q_spots"]):
            raise ValueError(f"Invalid evidence geometry: {key}")
        if e["profile_status"] != "blocked" or not e["gaps"] or key in profiles:
            raise ValueError(f"Research cannot certify production profile: {key}")
        if any(s["raw_sha256"] is not None for s in e["sources"]):
            raise ValueError("No original bytes were acquired in this batch")
    return dict(totals=totals, reviewed=len(seen), production_profiles_added=0,
                external_inputs=inventory["external_inputs"], years=years)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(audit(args.root), indent=2))


if __name__ == "__main__":
    main()

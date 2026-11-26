"""Machine-readable per-year ATP Tour historical inventory (read-only, offline).

Counts, from the committed canonical reference package, what each season has:
dated occurrences, explicit not-held memberships, week-projection review flags,
published sporting profiles, and which per-year evidence files exist in *this*
checkout.  Evidence in other Draft branches is deliberately not counted.

    PYTHONPATH=src python -m scripts.audit_atp_historical_inventory --check
    PYTHONPATH=src python -m scripts.audit_atp_historical_inventory --write
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "src"))

from beta_engine.application.atp_earth_week_mapping import SOURCE_FILE, build_projection

PKG = ROOT / "config/reference_packages/atp_tour_1990_2026"
OUT = PKG / "historical_inventory_v1.json"
SCHEMA = "atp.historical_inventory.v1"


def build() -> dict:
    dates = json.loads((PKG / "calendar_dates_v1.json").read_text(encoding="utf-8"))["year_sources"]
    seasons = {s["year"]: s for s in json.loads((PKG / "seasons_1990_2026.json").read_text(encoding="utf-8"))["seasons"]}
    profiles = json.loads((PKG / "squash_sporting_profiles_v1.json").read_text(encoding="utf-8"))["profiles"]
    mapping = build_projection(json.loads(SOURCE_FILE.read_text(encoding="utf-8")))["mappings"]
    flags: dict[int, Counter] = {}
    for m in mapping:
        flags.setdefault(m["atp_season_year"], Counter()).update(m["review_flags"])
    evid_dir = PKG / "phase_calendar_evidence"
    hist_dir = PKG / "historical_evidence"
    years = []
    for y in sorted(int(k) for k in dates):
        d = dates[str(y)]
        cats = Counter(seasons[y]["series_category_ids"][e["series_id"]] for e in d["events"])
        years.append({
            "year": y, "occurrences": len(d["events"]), "status": d["status"],
            "not_held_memberships": len(seasons[y]["known_not_held_series_ids"]),
            "categories": dict(sorted(cats.items())),
            "week_review_flags": dict(sorted(flags.get(y, Counter()).items())),
            "published_profiles": sorted(p["occurrence_id"] for p in profiles if p["occurrence_id"].startswith(f"atp_{y}_")),
            "phase_calendar_evidence_file": (evid_dir / f"{y}.json").exists(),
            "historical_evidence_files": sorted(p.name for p in hist_dir.glob(f"{y}_*.json")) if hist_dir.exists() else [],
        })
    return {
        "schema_version": SCHEMA,
        "totals": {"years": len(years), "occurrences": sum(r["occurrences"] for r in years),
                   "not_held_memberships": sum(r["not_held_memberships"] for r in years),
                   "published_profiles": sum(len(r["published_profiles"]) for r in years),
                   "years_with_phase_calendar_evidence": sum(r["phase_calendar_evidence_file"] for r in years)},
        "note": "Counts this checkout only; Draft branches are not included. 2026 is provisional.",
        "years": years,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="fail if the committed inventory is stale")
    g.add_argument("--write", action="store_true")
    a = ap.parse_args()
    text = json.dumps(build(), ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if a.write:
        OUT.write_text(text, encoding="utf-8")
        print(json.dumps(json.loads(text)["totals"]))
        return 0
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
        print("historical_inventory_v1.json is stale; run --write")
        return 1
    print(json.dumps(json.loads(text)["totals"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

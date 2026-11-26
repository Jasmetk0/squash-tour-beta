"""Check all 63 explicit candidate links against the pinned external tournament CSV."""
import argparse
import csv
import io
import json
from pathlib import Path

from scripts.audit_atp_2019_research import ROOT, load
from scripts.audit_atp_2019_external_tournaments import SCOPE, read_pinned, compare_2019


def check_crosswalk(data, manifest, inventory, crosswalk):
    previous = compare_2019(data, manifest, inventory)
    rows = {r[4]: r for r in csv.reader(io.StringIO(data.decode("utf-8"), newline=""))
            if r and r[0].startswith("2019-") and r[2] in SCOPE}
    canonical = {r["occurrence_id"]: r for y in inventory["years"] if y["year"] == 2019
                 for r in y["events"]}
    seen_keys, seen_ids = set(), set()
    counts = {"previously_reviewed": 0, "lineage_review_required": 0,
              "candidate_name_date_category_match": 0}
    prior_keys = {x["occurrence_id"] for x in manifest["observed_2019"]["matched_reviewed"]}
    for link in crosswalk["rows"]:
        key, aid = link["occurrence_id"], link["atp_id"]
        if key in seen_keys or aid in seen_ids:
            raise ValueError("Duplicate crosswalk identity")
        c, row = canonical[key], rows[aid]
        if (c["category_id"] != SCOPE[row[2]] or c["main_start"] != row[7].replace(".", "-")
                or link["external_start"] != c["main_start"] or link["external_type"] != row[2]
                or link["external_slug"] != row[5] or link["external_host"] != row[6]
                or link["advertised_main"] != int(row[11])
                or link["archive_url"] != "https://www.atptour.com" + row[18]):
            raise ValueError(f"Candidate crosswalk source mismatch: {key}")
        state = link["identity_state"]
        if (state == "previously_reviewed") != (key in prior_keys):
            raise ValueError("Unreviewed identity promoted")
        if (state == "lineage_review_required") != bool(link["lineage_note"]):
            raise ValueError("Missing lineage note")
        if link["profile_state"] != "not_installed" or link["runtime_state"] != "not_assessed":
            raise ValueError("Identity evidence cannot certify sporting execution")
        counts[state] += 1
        seen_keys.add(key)
        seen_ids.add(aid)
    if seen_keys != canonical.keys() or seen_ids != rows.keys():
        raise ValueError("Incomplete candidate crosswalk")
    if crosswalk["counts"] != {"candidate_pairs": len(seen_keys),
            "previously_reviewed": counts["previously_reviewed"],
            "lineage_review_required": counts["lineage_review_required"],
            "name_date_category_candidates": counts["candidate_name_date_category_match"],
            "unpaired_in_scope": 0}:
        raise ValueError("Crosswalk counts drift")
    return {"prior_review": previous["reviewed_identity_count"], "candidate_pairs": len(seen_keys),
            "states": counts, "production_profiles_certified": 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tournaments", type=Path, required=True)
    args = p.parse_args()
    root = ROOT / "research_2019"
    manifest = load(root / "external_tournament_input.json")
    report = check_crosswalk(read_pinned(args.tournaments, manifest["source"]), manifest,
                             load(root / "inventory.json"), load(root / "identity_crosswalk.json"))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

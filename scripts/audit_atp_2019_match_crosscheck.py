"""Reconcile the independent audit-only match file with the 2019 roster.

No match/player rows are persisted. Local M identifiers remain candidates.
"""
import csv
import io
from collections import Counter
from datetime import date

from scripts.audit_atp_2019_sackmann import audit_matches


def compare_match_groups(raw, crosswalk, manifest):
    audit_matches(raw)
    groups = {}
    for r in csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")):
        key = r["tourney_id"]
        if r["tourney_level"] not in {"A", "M", "F"} or key == "2019-9210":
            continue
        info = (r["tourney_level"], r["tourney_date"], r["draw_size"])
        g = groups.setdefault(key, {"info": info, "rounds": Counter()})
        if g["info"] != info:
            raise ValueError("Inconsistent source event metadata")
        g["rounds"][r["round"]] += 1
    overrides = manifest["crosscheck"]["candidate_local_id_overrides"]
    counts = Counter({k: 0 for k in manifest["crosscheck"]["expected"]})
    differences = []
    for row in crosswalk["rows"]:
        aid = row["atp_id"]
        local = aid in overrides
        key = "2019-" + (overrides[aid] if local else aid.zfill(4))
        if key not in groups:
            raise ValueError("Missing or duplicate mapped event: " + key)
        g = groups.pop(key)
        level, day, _ = g["info"]
        expected_level = {"ATP 250": "A", "ATP 500": "A", "Masters 1000": "M",
                          "ATP Finals": "F", "Next Gen Finals": "F"}[row["external_type"]]
        if level != expected_level:
            raise ValueError("Mapped event level mismatch")
        counts["paired"] += 1
        counts["local_id_candidates" if local else "direct_numeric"] += 1
        day = date(int(day[:4]), int(day[4:6]), int(day[6:])).isoformat()
        same = day == row["external_start"]
        counts["archive_date_equal" if same else "archive_date_diff"] += 1
        if not same:
            differences.append({"occurrence_id": row["occurrence_id"],
                                "archive_start": row["external_start"], "match_week_anchor": day})
        if level == "F":
            if g["rounds"] != {"RR": 12, "SF": 2, "F": 1}:
                raise ValueError("Unexpected Finals group structure")
            counts["group_finals_count_matches"] += 1
        else:
            eq = sum(g["rounds"].values()) == row["advertised_main"] - 1
            counts["knockout_group_count_matches" if eq else "knockout_group_count_diff"] += 1
    if groups:
        raise ValueError("Unpaired in-scope source events")
    if dict(counts) != manifest["crosscheck"]["expected"]:
        raise ValueError("Cross-source comparison aggregate changed")
    return {"counts": dict(counts), "date_differences": differences,
            "qualification_dates_certified": 0, "production_profiles_certified": 0}

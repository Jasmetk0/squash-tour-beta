#!/usr/bin/env python3
"""Growth of request time and RAM with the number of Saved revisions.

    python scripts/w10_growth_report.py LABEL=RUN_DIR [LABEL=RUN_DIR ...] [--cold LABEL=COLD.json ...]

Reads ``requests.jsonl`` of benchmark runs. Each request is attributed to the
revision count it had to process (before its own Save). Reports, per run:
the first cold inspect, warm inspects, previews, executes and Saves by
revision count, a least-squares slope (seconds per added revision) for each,
and the process peak RSS. Cold-read JSON files from
``scripts/measure_cold_tour_read.py`` add cold points at other sizes.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path


def slope(points):
    if len(points) < 2 or len({x for x, _ in points}) < 2:
        return None
    n = len(points)
    mx = sum(x for x, _ in points) / n
    my = sum(y for _, y in points) / n
    return sum((x - mx) * (y - my) for x, y in points) / sum((x - mx) ** 2 for x, _ in points)


def main(argv):
    runs, colds = [], []
    target = runs
    for arg in argv:
        if arg == "--cold":
            target = colds
            continue
        label, _, path = arg.partition("=")
        target.append((label, Path(path)))
    report = {}
    for label, run in runs:
        rows = [json.loads(line) for line in (run / "requests.jsonl").read_text().splitlines()]
        classes = defaultdict(list)
        current = None
        for r in rows:
            # Older outputs carry the count only on start/save_confirmed records.
            if r["kind"] in ("start", "save_confirmed") and r.get("revisions") is not None:
                current = r["revisions"]
            if r["kind"] != "client" or r.get("status") not in (200, 201):
                continue
            r.setdefault("revisions", current)
            endpoint = r["path"].rsplit("/", 1)[-1]
            kind = ("cold_inspect" if r["phase"] == "cold-inspect" else
                    {"calendar-tour": "warm_inspect", "preview": "preview", "execute": "execute",
                     "save": "save"}.get(endpoint))
            if kind:
                classes[kind].append((r["revisions"], r["client_seconds"], r["peak_rss_mib"]))
        summary = {}
        for kind, values in classes.items():
            by = defaultdict(list)
            for revisions, seconds, _ in values:
                by[revisions].append(seconds)
            summary[kind] = {
                "by_revisions": {str(k): [round(min(v), 1), round(sum(v) / len(v), 1), round(max(v), 1)]
                                 for k, v in sorted(by.items())},
                "seconds_per_revision": (round(s, 2) if (s := slope([(x, y) for x, y, _ in values])) is not None
                                         else None),
                "max": round(max(y for _, y, _ in values), 1),
            }
        summary["peak_rss_mib"] = max(r["peak_rss_mib"] for r in rows)
        report[label] = summary
    for label, path in colds:
        data = json.loads(path.read_text())
        report.setdefault("cold_reads", {})[label] = {
            "seconds": data["seconds"], "peak_rss_mib": data["peak_rss_mib"],
            "exact": data["exact_expected_inspection"]}
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

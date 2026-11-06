"""CLI for the non-mutating ATP Earth W52 -> explicit RunCalendar preview.

Default clock is an illustrative 1990-2026 Earth W52 frame, NOT a Saved Run.
Use --year for a source-year slice and --run-start-year / --run-seasons /
--run-offset to inspect an alternative valid Earth frame. Never saves state.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from beta_engine.application.atp_earth_run_calendar_preview import (
    preview_atp_earth_weeks_on_run,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from scripts.audit_atp_earth_week_mapping_v1 import SOURCE_FILE, build_projection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-start-year", type=int, default=1990)
    parser.add_argument("--run-seasons", type=int, default=37)
    parser.add_argument("--run-offset", type=int, default=1)
    parser.add_argument("--year", type=int, action="append", dest="years")
    parser.add_argument("--json", action="store_true", help="Print full reviewable projection")
    args = parser.parse_args()
    clock = RunCalendar(
        weeks_per_year=52,
        season_start_year_week=args.run_offset,
        start_year=args.run_start_year,
        season_count=args.run_seasons,
    )
    source = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    projection = build_projection(source)
    report = preview_atp_earth_weeks_on_run(
        calendar=clock, mapping=projection, years=args.years,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(json.dumps({
            "schema_version": report["schema_version"],
            "clock_is_hypothetical_not_loaded_from_saved_run": True,
            "selected_atp_years": report["selected_atp_years"],
            "run_calendar": report["calendar"],
            "summary": report["summary"],
            "preview_fingerprint": report["preview_fingerprint"],
            "no_sporting_install": report["no_sporting_install"],
        }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build the ATP historical Calendar with --check or --write."""

import argparse
import json

from beta_engine.application.atp_historical_calendar_source import (
    ALLOWED_STATUSES as ALLOWED_STATUSES,
    CALENDAR_ID as CALENDAR_ID,
    CALENDAR_SCOPE as CALENDAR_SCOPE,
    CATEGORY_ID as CATEGORY_ID,
    DATES,
    FIRST as FIRST,
    LAST as LAST,
    ROOT as ROOT,
    SERIES_ID as SERIES_ID,
    SOURCE,
    TARGET,
    build,
    canonical,
    ensure_archive_year_matches as ensure_archive_year_matches,
    iso_weeks_touched as iso_weeks_touched,
    official_url as official_url,
    parse_exact_date as parse_exact_date,
    project_iso_week_to_run_w52 as project_iso_week_to_run_w52,
)

def main() -> int:
    args = argparse.ArgumentParser(description=__doc__)
    mode = args.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    options = args.parse_args()
    categories = json.loads((SOURCE / "category.json").read_text(encoding="utf-8"))
    series = json.loads((SOURCE / "series.json").read_text(encoding="utf-8"))
    seasons = json.loads((SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8"))
    dated = json.loads(DATES.read_text(encoding="utf-8"))
    document = canonical(build(categories, series, seasons, dated))
    if options.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != document:
            print("ATP Calendar snapshot stale; execute --write")
            return 1
        print("ATP Calendar reference snapshot verified, no invented dates")
        return 0
    TARGET.write_text(document, encoding="utf-8")
    print("Wrote", TARGET, "source-only ATP calendar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Print the deterministic, read-only ATP Earth W52 week projection."""

import argparse
import json

from beta_engine.application.atp_earth_week_mapping import (
    FIRST_YEAR as FIRST_YEAR,
    LAST_YEAR as LAST_YEAR,
    MAPPING_POLICY as MAPPING_POLICY,
    REVIEWED_ISO_53_SOURCE_ONLY as REVIEWED_ISO_53_SOURCE_ONLY,
    SOURCE_FILE,
    build_projection,
    map_one as map_one,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Read-only count and safety audit")
    group.add_argument("--json", action="store_true", help="Print full deterministic audit JSON")
    args = parser.parse_args()
    source = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    report = build_projection(source)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
        print("Reference-only projection; no Run or sporting calendar was modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

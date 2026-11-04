"""Promote a fully reconciled ATP historical Calendar candidate and regenerate snapshot.

Requires an explicit --write; --check is read-only. This avoids half-updating
calendar_dates_v1.json while leaving calendar.json stale.

Usage:
    python scripts/promote_atp_calendar_candidate.py --check --year 2003
    python scripts/promote_atp_calendar_candidate.py --write --year 2003

No source URL or historical legal lineage is independently certified by this
mechanical promotion. Historical exceptions require separate source review.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

from scripts.audit_atp_calendar_backfill import audit_candidates
from scripts.build_atp_historical_calendar import SOURCE, build, canonical

PENDING_CONFLICTS = {
    # The published ATP annual archive labels 10–16 Nov, whereas an ATP
    # historical tournament overview cites 8–16 Nov. Resolve which date
    # convention the calendar represents before a whole-year import.
    2003: {
        "atp_finals": (
            "ATP 2003 year results archive: 2003-11-10 to 2003-11-16; "
            "ATP Tournament History overview: 2003-11-08 to 2003-11-16"
        ),
    },
}


def prepare(year: int, *, allow_unresolved: bool = False):
    if year != 2003:
        raise ValueError("Only the explicit 2003 candidate ledger is supported")
    candidate = json.loads(
        (SOURCE / "calendar_backfill_2003_candidates_v1.json").read_text(
            encoding="utf-8"
        )
    )
    dated = json.loads(
        (SOURCE / "calendar_dates_v1.json").read_text(encoding="utf-8")
    )
    seasons = json.loads(
        (SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8")
    )
    categories = json.loads(
        (SOURCE / "category.json").read_text(encoding="utf-8")
    )
    series = json.loads(
        (SOURCE / "series.json").read_text(encoding="utf-8")
    )
    audit = audit_candidates(candidate, seasons, dated)
    if audit["year"] != year or not audit["ready_for_whole_year_promotion"]:
        raise ValueError("Historical year not fully reconciled to parent roster")
    conflicts = PENDING_CONFLICTS.get(year, {})
    if conflicts and not allow_unresolved:
        raise ValueError(
            "Unresolved official ATP dates block whole-year promotion: "
            + "; ".join(f"{sid}: {why}" for sid, why in conflicts.items())
        )
    # Deliberately do not expose a --force flag. Historical disagreement
    # requires source curation rather than bypassing evidence gates.
    if conflicts:
        raise ValueError("Historical ATP source conflict must be resolved")
    promoted = dict(dated)
    promoted["year_sources"] = dict(dated["year_sources"])
    if str(year) in promoted["year_sources"]:
        raise ValueError("Year already exists; never overwrite dated history")
    rows = [
        {
            "series_id": row["series_id"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "source_url": candidate["source_url"],
            "source_basis": "official_published_event_dates",
        }
        for row in audit["candidate_events"]
    ]
    promoted["year_sources"][str(year)] = {
        "as_of": candidate["as_of"],
        "status": "verified_results_archive",
        "source_url": candidate["source_url"],
        "events": rows,
    }
    promoted["year_sources"] = dict(
        sorted(promoted["year_sources"].items(), key=lambda item: int(item[0]))
    )
    generated = build(categories, series, seasons, promoted)
    old_generated = build(categories, series, seasons, dated)
    old = {
        entity["source_entity_id"]: entity
        for entity in old_generated["entities"]
        if entity["entity_kind"] == "tennis.calendar.occurrence.reference.v1"
    }
    new = {
        entity["source_entity_id"]: entity
        for entity in generated["entities"]
        if entity["entity_kind"] == "tennis.calendar.occurrence.reference.v1"
    }
    if any(new.get(key) != value for key, value in old.items()):
        raise ValueError("Promotion mutated existing historical occurrences")
    if len(new) - len(old) != len(rows):
        raise ValueError("Unexpected occurrence delta in promoted calendar")
    return promoted, generated, audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args()
    promoted, generated, audit = prepare(args.year)
    if args.check:
        print(
            f"ATP {args.year} eligible: {audit['candidate_count']} dates; "
            "all old Calendar entities unchanged"
        )
        return 0
    # The generated content is complete before either file is replaced.
    # Serialize to temporary files in each target directory first.
    targets = [
        (SOURCE / "calendar_dates_v1.json", canonical(promoted)),
        (SOURCE / "calendar.json", canonical(generated)),
    ]
    staged = []
    try:
        for path, content in targets:
            with tempfile.NamedTemporaryFile(
                mode="w", dir=path.parent, encoding="utf-8",
                delete=False, newline="\n"
            ) as tmp:
                tmp.write(content)
                staged.append((path, Path(tmp.name)))
        # Updating two independent files cannot be truly atomic on ordinary
        # filesystems. Failure restores backups; git callers commit both.
        original = [(path, path.read_bytes()) for path, _ in staged]
        try:
            for path, tmp in staged:
                os.replace(tmp, path)
        except Exception:
            for path, blob in original:
                path.write_bytes(blob)
            raise
    finally:
        for _, tmp in staged:
            tmp.unlink(missing_ok=True)
    print(f"Promoted {audit['candidate_count']} ATP dates in {args.year}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The committed historical inventory reproduces the canonical package totals."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_atp_historical_inventory import OUT, build


def test_inventory_totals_match_canonical_package_and_audit_baseline() -> None:
    inv = build()
    assert inv["totals"]["years"] == 37
    assert inv["totals"]["occurrences"] == 2407
    assert inv["totals"]["not_held_memberships"] == 24
    profiles = json.loads((Path(OUT).parent / "squash_sporting_profiles_v1.json").read_text(encoding="utf-8"))["profiles"]
    assert inv["totals"]["published_profiles"] == len(profiles)
    assert [y["year"] for y in inv["years"]] == list(range(1990, 2027))
    assert sum(y["occurrences"] for y in inv["years"]) == 2407
    assert next(y for y in inv["years"] if y["year"] == 2019)["occurrences"] == 63
    assert next(y for y in inv["years"] if y["year"] == 2026)["status"] == "provisional_published_schedule"


def test_committed_inventory_has_the_same_per_year_counts() -> None:
    committed = json.loads(Path(OUT).read_text(encoding="utf-8"))
    fresh = build()
    strip = lambda y: {k: v for k, v in y.items() if k not in ("phase_calendar_evidence_file", "historical_evidence_files")}
    assert [strip(y) for y in committed["years"]] == [strip(y) for y in fresh["years"]]

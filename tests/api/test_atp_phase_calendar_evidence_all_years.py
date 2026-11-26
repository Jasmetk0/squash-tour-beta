"""Generic invariants for every ``atp.phase_calendar_evidence.v2`` year file in this checkout."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from beta_engine.application.atp_earth_run_calendar_preview import (
    preview_atp_earth_weeks_on_run,
)
from beta_engine.application.atp_earth_week_mapping import SOURCE_FILE, build_projection
from beta_engine.domain.calendar.run_calendar import RunCalendar

PKG = Path(__file__).resolve().parents[2] / "config/reference_packages/atp_tour_1990_2026"
SHA = re.compile(r"^[0-9a-f]{64}$")
FILES = {}
for _p in sorted((PKG / "phase_calendar_evidence").glob("*.json")):
    _d = json.loads(_p.read_text(encoding="utf-8"))
    if isinstance(_d, dict) and _d.get("schema_version") == "atp.phase_calendar_evidence.v2":
        FILES[_d["atp_season_year"]] = _d
CANON = json.loads((PKG / "calendar_dates_v1.json").read_text(encoding="utf-8"))["year_sources"]
SEASONS = {s["year"]: s for s in json.loads((PKG / "seasons_1990_2026.json").read_text(encoding="utf-8"))["seasons"]}
MAPPING = build_projection(json.loads(SOURCE_FILE.read_text(encoding="utf-8")))
ALLOWED_MATCH = {"manual_reviewed", "name_and_date", "date_only_unique_lineage"}


@pytest.mark.parametrize("year", sorted(FILES))
def test_year_covers_canonical_occurrences_unchanged(year: int) -> None:
    data = FILES[year]
    events = CANON[str(year)]["events"]
    assert data["sporting_schedule_installed"] is False
    assert len(data["occurrences"]) == len(events)
    by_id = {o["occurrence_id"]: o for o in data["occurrences"]}
    assert len(by_id) == len(events)
    for ev in events:
        rec = by_id[f"atp_{year}_{ev['series_id']}"]
        assert (rec["main_start_date"], rec["main_end_date"]) == (ev["start_date"], ev["end_date"])
        assert rec["category_id"] == SEASONS[year]["series_category_ids"][ev["series_id"]]
        assert rec["main_source_url"] == ev["source_url"]
        assert rec["qualifying_dates"]["status"] == "open" and rec["points"]["status"] == "open"
        assert rec["status"]["published_profile"] == "none"
        cross = rec["wikipedia_cross_check"]
        if cross is None:
            assert rec["conflicts"]
            continue
        assert cross["role"] == "secondary_source" and cross["match_method"] in ALLOWED_MATCH
        assert SHA.match(cross["main_article"]["sha256"])
        if cross["date_status"] == "differs":
            assert "canonical (ATP archive) retained" in rec["conflicts"][0]


@pytest.mark.parametrize("year", sorted(FILES))
@pytest.mark.parametrize("offset", [1, 37])
def test_run_weeks_match_production_run_calendar(year: int, offset: int) -> None:
    clock = RunCalendar(weeks_per_year=52, season_start_year_week=offset,
                        start_year=year if offset == 1 else year - 1, season_count=3)
    report = preview_atp_earth_weeks_on_run(calendar=clock, mapping=MAPPING, years=[year])
    expected = {e["source_identity"]: [w["season_week"] for w in e["run_weeks"]] for e in report["events"]}
    got = {o["occurrence_id"]: o[f"run_weeks_offset_{offset}"] for o in FILES[year]["occurrences"]}
    assert got == expected


@pytest.mark.parametrize("year", sorted(FILES))
def test_format_geometry_is_arithmetic_only(year: int) -> None:
    for rec in FILES[year]["occurrences"]:
        fmt = rec.get("format_evidence")
        if not fmt or not fmt.get("main_draw_players") or fmt.get("bracket_capacity") is None:
            continue
        if rec["category_id"] in ("atp_finals", "next_gen_finals"):
            continue
        cap, players = fmt["bracket_capacity"], fmt["main_draw_players"]
        assert cap >= players and cap & (cap - 1) == 0
        assert fmt["byes_derived"] == cap - players
        assert 2 ** fmt["main_rounds"] == cap

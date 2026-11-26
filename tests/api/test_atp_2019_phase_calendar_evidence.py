"""2019 ATP Tour phase evidence stays consistent with the canonical reference package."""

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
YEAR = 2019
EVIDENCE = json.loads((PKG / "phase_calendar_evidence" / f"{YEAR}.json").read_text(encoding="utf-8"))
CANON = json.loads((PKG / "calendar_dates_v1.json").read_text(encoding="utf-8"))["year_sources"][str(YEAR)]
SEASON = next(s for s in json.loads((PKG / "seasons_1990_2026.json").read_text(encoding="utf-8"))["seasons"]
              if s["year"] == YEAR)
BY_ID = {o["occurrence_id"]: o for o in EVIDENCE["occurrences"]}
SHA = re.compile(r"^[0-9a-f]{64}$")


def test_every_canonical_occurrence_is_covered_once_with_unchanged_identity_and_dates() -> None:
    assert EVIDENCE["schema_version"] == "atp.phase_calendar_evidence.v2"
    assert EVIDENCE["sporting_schedule_installed"] is False
    assert len(EVIDENCE["occurrences"]) == len(BY_ID) == len(CANON["events"]) == 63
    for ev in CANON["events"]:
        rec = BY_ID[f"atp_{YEAR}_{ev['series_id']}"]
        assert (rec["main_start_date"], rec["main_end_date"]) == (ev["start_date"], ev["end_date"])
        assert rec["category_id"] == SEASON["series_category_ids"][ev["series_id"]]
        assert rec["main_source_url"] == ev["source_url"]


def test_scope_excludes_majors_team_and_lower_tier_events() -> None:
    allowed = {"atp_250", "atp_500", "atp_masters_1000", "atp_finals", "next_gen_finals"}
    assert {o["category_id"] for o in EVIDENCE["occurrences"]} <= allowed
    banned = ("australian_open", "roland", "french_open", "wimbledon", "us_open", "challenger",
              "davis", "laver", "hopman", "olymp")
    assert not [o["series_id"] for o in EVIDENCE["occurrences"] if any(b in o["series_id"] for b in banned)]
    per_cat = {c: sum(1 for o in EVIDENCE["occurrences"] if o["category_id"] == c) for c in allowed}
    assert per_cat == {"atp_250": 39, "atp_500": 13, "atp_masters_1000": 9, "atp_finals": 1, "next_gen_finals": 1}


@pytest.mark.parametrize("offset", [1, 37])
def test_run_weeks_match_the_production_run_calendar(offset: int) -> None:
    mapping = build_projection(json.loads(SOURCE_FILE.read_text(encoding="utf-8")))
    clock = RunCalendar(weeks_per_year=52, season_start_year_week=offset,
                        start_year=YEAR if offset == 1 else YEAR - 1, season_count=3)
    report = preview_atp_earth_weeks_on_run(calendar=clock, mapping=mapping, years=[YEAR])
    expected = {e["source_identity"]: [w["season_week"] for w in e["run_weeks"]] for e in report["events"]}
    assert {k: v[f"run_weeks_offset_{offset}"] for k, v in BY_ID.items()} == expected


def test_week_53_boundaries_and_cross_year_start_are_preserved() -> None:
    for sid in ("doha", "brisbane", "hong_kong"):
        rec = BY_ID[f"atp_{YEAR}_{sid}"]
        assert rec["main_start_date"] == "2018-12-31"
        assert rec["main_year_weeks"] == [[YEAR, 1]]


def test_format_geometry_is_arithmetically_consistent_and_never_invented() -> None:
    seen_28 = 0
    for rec in EVIDENCE["occurrences"]:
        fmt = rec.get("format_evidence")
        if not fmt or not fmt.get("main_draw_players") or rec["category_id"] in ("atp_finals", "next_gen_finals"):
            continue
        players, cap = fmt["main_draw_players"], fmt["bracket_capacity"]
        assert cap >= players and cap & (cap - 1) == 0
        assert fmt["byes_derived"] == cap - players
        assert 2 ** fmt["main_rounds"] == cap
        if fmt.get("qualifier_places") and fmt.get("qualifying_draw_size"):
            q = fmt["qualifying_draw_size"] // fmt["qualifier_places"]
            assert 2 ** fmt["qualifying_rounds_derived"] == q
        if players == 28:
            seen_28 += 1
            assert fmt["byes_derived"] == 4
    assert seen_28 >= 30


def test_open_evidence_is_not_filled_by_template() -> None:
    for rec in EVIDENCE["occurrences"]:
        assert rec["qualifying_dates"]["status"] == "open"
        assert rec["points"]["status"] == "open"
        assert rec["status"] == {"calendar_evidence": "main_dates_archive_dated",
                                 "published_profile": "none", "verified_schedule": "not_verified",
                                 "played_and_reopened": "not_played"}
        assert "qualifying_dates" in rec["open_fields"] and "point_table" in rec["open_fields"]


def test_secondary_source_hashes_and_conflicts_are_recorded_honestly() -> None:
    assert SHA.match(EVIDENCE["season_source"]["sha256"]) and EVIDENCE["season_source"]["role"] == "secondary_source"
    for rec in EVIDENCE["occurrences"]:
        cross = rec["wikipedia_cross_check"]
        assert cross["role"] == "secondary_source"
        assert SHA.match(cross["main_article"]["sha256"]) and cross["main_article"]["revision_id"] > 0
        if cross["date_status"] == "differs":
            assert rec["conflicts"] and "canonical (ATP archive) retained" in rec["conflicts"][0]
        else:
            assert not rec["conflicts"]
    counts = EVIDENCE["counts"]
    assert counts["wikipedia_dates_agree"] + counts["wikipedia_dates_differ"] + counts["wikipedia_dates_not_parsed"] == 63
    assert counts["wikipedia_dates_not_parsed"] == 0


def test_licence_lineage_identities_are_not_renamed() -> None:
    assert BY_ID["atp_2019_hong_kong"]["identity_note"].startswith("Pune")
    assert BY_ID["atp_2019_lyon"]["identity_note"].startswith("Marseille")
    assert BY_ID["atp_2019_dallas"]["identity_note"].startswith("New York")
    assert BY_ID["atp_2019_hangzhou"]["identity_note"].startswith("Zhuhai")
    assert BY_ID["atp_2019_belgrade_clay_2021"]["identity_note"].startswith("Budapest")

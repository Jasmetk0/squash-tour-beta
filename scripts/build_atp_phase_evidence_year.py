"""Merge Wikipedia format cross-checks into canonical per-year ATP phase evidence.

Offline (no network): reads the JSON written by
``build_atp_wikipedia_season_evidence`` and the committed canonical reference
package files.  It never changes the canonical dates, Series or categories; a
disagreement is recorded as a conflict.  Qualifying dates, points and Q/Main
PDF hashes are left open when no read source states them.

    PYTHONPATH=src python -m scripts.build_atp_phase_evidence_year 2019 WP.json OUT.json
"""

from __future__ import annotations

import argparse
import html
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "src"))

from beta_engine.application.atp_earth_run_calendar_preview import (
    preview_atp_earth_weeks_on_run,
)
from beta_engine.application.atp_earth_week_mapping import SOURCE_FILE, build_projection
from beta_engine.domain.calendar.run_calendar import RunCalendar

PKG = ROOT / "config/reference_packages/atp_tour_1990_2026"
SCHEMA = "atp.phase_calendar_evidence.v2"
ARCHIVE_ACCESS = (
    "atptour.com results archive, draws and order-of-play pages answered HTTP 403 from this "
    "environment, so ATP-published qualifying dates and point tables were not read")

# Wikipedia article title -> canonical stable Series (2019).  The licence-lineage
# identities already documented in ATP_TOUR_1990_2026_HISTORICAL_CALENDAR_REFERENCE.md
# are kept: they are not renamed to the 2019 host city.
SERIES_BY_TITLE = {
    "Qatar_ExxonMobil_Open": "doha", "Brisbane_International": "brisbane",
    "Maharashtra_Open": "hong_kong", "Sydney_International": "sydney_2019",
    "ASB_Classic": "auckland", "Open_Sud_de_France": "montpellier", "Sofia_Open": "sofia",
    "Córdoba_Open": "cordoba", "ABN_AMRO_World_Tennis_Tournament": "rotterdam",
    "New_York_Open": "dallas", "Argentina_Open": "buenos_aires", "Rio_Open": "rio",
    "Open_13": "lyon", "Delray_Beach_Open": "delray_beach", "Dubai_Tennis_Championships": "dubai",
    "Abierto_Mexicano_Telcel": "acapulco", "Brasil_Open": "sao_paulo",
    "BNP_Paribas_Open": "indian_wells", "Miami_Open": "miami",
    "U.S._Men's_Clay_Court_Championships": "houston", "Grand_Prix_Hassan_II": "marrakech",
    "Monte-Carlo_Masters": "monte_carlo", "Barcelona_Open_Banco_Sabadell": "barcelona",
    "Hungarian_Open_(tennis)": "belgrade_clay_2021", "Estoril_Open": "estoril",
    "BMW_Open": "munich", "Mutua_Madrid_Open": "madrid", "Italian_Open_(tennis)": "rome",
    "Geneva_Open": "geneva", "Lyon_Open": "lyon_old", "MercedesCup": "stuttgart",
    "Rosmalen_Grass_Court_Championships": "s_hertogenbosch", "Noventi_Open": "halle",
    "Queen's_Club_Championships": "queens_club", "Eastbourne_International": "eastbourne",
    "Antalya_Open": "antalya_2019", "Hall_of_Fame_Open": "newport", "Swedish_Open": "bastad",
    "Croatia_Open_Umag": "umag", "Hamburg_European_Open": "hamburg",
    "BB&T_Atlanta_Open": "atlanta", "Swiss_Open_Gstaad": "gstaad", "Citi_Open": "washington",
    "Los_Cabos_Open": "los_cabos", "Generali_Open_Kitzbühel": "kitzbuhel",
    "Rogers_Cup": "canadian_open", "Western_&_Southern_Open": "cincinnati",
    "Winston-Salem_Open": "winston_salem", "St._Petersburg_Open": "st_petersburg",
    "Moselle_Open": "metz", "Chengdu_Open": "chengdu", "Zhuhai_Championships": "hangzhou",
    "China_Open_(tennis)": "beijing", "Rakuten_Japan_Open_Tennis_Championships": "tokyo",
    "Rolex_Shanghai_Masters": "shanghai", "Kremlin_Cup": "moscow", "Stockholm_Open": "stockholm",
    "European_Open": "brussels", "Erste_Bank_Open": "vienna", "Swiss_Indoors": "basel",
    "Rolex_Paris_Masters": "paris_masters", "Next_Generation_ATP_Finals": "next_gen_atp_finals",
    "ATP_Finals": "atp_finals",
}
LINEAGE_NOTE = {
    "hong_kong": "Pune (Maharashtra Open) licence lineage; not renamed to the later host",
    "belgrade_clay_2021": "Budapest (Hungarian Open) licence lineage",
    "lyon": "Marseille (Open 13) licence lineage; distinct clay Lyon is lyon_old",
    "hangzhou": "Zhuhai Championships licence lineage",
    "dallas": "New York Open (Uniondale) licence lineage",
    "brussels": "Antwerp (European Open) licence lineage",
}


def _pow2(n: int) -> int:
    return 1 << max(0, math.ceil(math.log2(n)))


def _run_weeks(year: int, offset: int, mapping: dict) -> dict[str, list[dict]]:
    start = year if offset == 1 else year - 1
    clock = RunCalendar(weeks_per_year=52, season_start_year_week=offset,
                        start_year=start, season_count=3)
    rep = preview_atp_earth_weeks_on_run(calendar=clock, mapping=mapping, years=[year])
    return {e["source_identity"]: e["run_weeks"] for e in rep["events"]}


def build(year: int, wp: dict) -> dict:
    dates = json.loads((PKG / "calendar_dates_v1.json").read_text(encoding="utf-8"))["year_sources"][str(year)]
    seasons = json.loads((PKG / "seasons_1990_2026.json").read_text(encoding="utf-8"))["seasons"]
    cats = next(s for s in seasons if s["year"] == year)["series_category_ids"]
    mapping = build_projection(json.loads(SOURCE_FILE.read_text(encoding="utf-8")))
    year_map = {m["source_identity"]: m for m in mapping["mappings"] if m["atp_season_year"] == year}
    runs = {off: _run_weeks(year, off, mapping) for off in (1, 37)}
    wiki = {}
    for ev in wp["events"]:
        title = html.unescape(ev["wikipedia_main"]).split("_", 1)[1]
        series = SERIES_BY_TITLE.get(title)
        if series and series not in wiki:
            wiki[series] = ev
    out_occ = []
    for e in sorted(dates["events"], key=lambda x: (x["start_date"], x["series_id"])):
        sid = e["series_id"]
        oid = f"atp_{year}_{sid}"
        w = wiki.get(sid)
        rec: dict = {
            "occurrence_id": oid, "series_id": sid, "category_id": cats[sid],
            "main_start_date": e["start_date"], "main_end_date": e["end_date"],
            "main_year_weeks": [[x["calendar_year"], x["year_week"]] for x in year_map[oid]["mapped_year_weeks"]],
            "main_source_url": e["source_url"],
            "run_weeks_offset_1": [x["season_week"] for x in runs[1][oid]],
            "run_weeks_offset_37": [x["season_week"] for x in runs[37][oid]],
            "review_flags": year_map[oid]["review_flags"],
        }
        if sid in LINEAGE_NOTE:
            rec["identity_note"] = LINEAGE_NOTE[sid]
        conflicts, open_fields = [], ["qualifying_dates", "point_table", "qualifying_pdf_hashes"]
        if w is None:
            rec["wikipedia_cross_check"] = None
            conflicts.append("no matching English Wikipedia event article found")
        else:
            sing = w.get("singles") or {}
            wd = w["wikipedia_dates"]
            if wd is None:
                date_status = "not_machine_parsed"
            elif tuple(wd) == (e["start_date"], e["end_date"]):
                date_status = "agrees"
            else:
                date_status = "differs"
                conflicts.append(f"Wikipedia infobox dates {wd[0]}..{wd[1]} differ from canonical "
                                 f"{e['start_date']}..{e['end_date']}; canonical (ATP archive) retained")
            rec["wikipedia_cross_check"] = {
                "role": "secondary_source", "article": html.unescape(w["wikipedia_main"]),
                "main_article": w["main_source"], "singles_article": w.get("singles_source"),
                "infobox_dates": wd, "date_status": date_status,
                "schedule_row": w["schedule_text"],
            }
            players = sing.get("main_draw_players") or w.get("schedule_main_capacity")
            fmt = {"main_draw_players": players,
                   "qualifier_places": sing.get("qualifier_places"),
                   "wild_cards": sing.get("wild_cards"),
                   "seeds": sing.get("seeds"),
                   "qualifying_draw_size": w.get("schedule_qualifying_draw"),
                   "bye_statement": sing.get("bye_statement")}
            if players:
                cap = _pow2(players)
                fmt["bracket_capacity"] = cap
                fmt["main_rounds"] = int(math.log2(cap))
                fmt["byes_derived"] = cap - players
            q, qp = fmt["qualifying_draw_size"], fmt["qualifier_places"]
            if q and qp:
                fmt["qualifying_rounds_derived"] = int(math.log2(q // qp))
            for k in ("qualifier_places", "wild_cards", "seeds"):
                if fmt[k] is None:
                    open_fields.append(k)
            rec["format_evidence"] = fmt
            if wd is None:
                open_fields.append("secondary_date_cross_check")
        rec["qualifying_dates"] = {"status": "open", "missing_evidence": ARCHIVE_ACCESS
                                   if sid not in ("next_gen_atp_finals", "atp_finals")
                                   else "round-robin Finals have no qualifying draw"}
        rec["points"] = {"status": "open",
                         "missing_evidence": "2019 ATP Rulebook points table (Main and Q) not read: " + ARCHIVE_ACCESS}
        rec["status"] = {"calendar_evidence": "main_dates_archive_dated", "published_profile": "none",
                         "verified_schedule": "not_verified", "played_and_reopened": "not_played"}
        rec["conflicts"] = conflicts
        rec["open_fields"] = open_fields
        out_occ.append(rec)
    return {
        "schema_version": SCHEMA, "atp_season_year": year,
        "scope": "ATP Tour men's singles main tour, Next Gen Finals and ATP Finals; no Grand Slam, Challenger, ITF, team or doubles",
        "sporting_schedule_installed": False,
        "retrieved_at": wp["retrieved_at"],
        "season_source": {"role": "secondary_source", **wp["season_source"]},
        "counts": {"occurrences": len(out_occ),
                   "wikipedia_dates_agree": sum(1 for o in out_occ if (o.get("wikipedia_cross_check") or {}).get("date_status") == "agrees"),
                   "wikipedia_dates_differ": sum(1 for o in out_occ if (o.get("wikipedia_cross_check") or {}).get("date_status") == "differs"),
                   "wikipedia_dates_not_parsed": sum(1 for o in out_occ if (o.get("wikipedia_cross_check") or {}).get("date_status") == "not_machine_parsed")},
        "occurrences": out_occ,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("year", type=int)
    ap.add_argument("wikipedia_json", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    data = build(a.year, json.loads(a.wikipedia_json.read_text(encoding="utf-8")))
    a.out.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(data["counts"]))


if __name__ == "__main__":
    main()

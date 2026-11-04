# ATP Tour 2003 — independently checked date evidence (incremental)

**Status:** research ledger only; not imported into `calendar_dates_v1.json`, not a complete 2003 census. Parent Category/Series source IDs must be checked before ingestion. This document must not be counted as date-complete coverage.

**Primary source:** [ATP Tour 2003 official results archive](https://www.atptour.com/en/scores/results-archive?year=2003), consulted 2026-11-04. It reports played tournaments, not a legal licence-lineage certificate. Use the original 2003 historical host, then independently join to parent Series ID. Exclude Australian Open, Roland Garros, other Grand Slams and team events from ATP original-tier Calendar.

| 2003 played host | Official start | Official end | Notes |
| --- | --- | --- | --- |
| Doha | 2002-12-30 | 2003-01-05 | Crosses Gregorian year and ISO year |
| Chennai | 2002-12-30 | 2003-01-05 | Crosses Gregorian year and ISO year |
| Adelaide | 2002-12-30 | 2003-01-05 | Crosses Gregorian year and ISO year |
| Auckland | 2003-01-06 | 2003-01-12 | Source-listed |
| Sydney | 2003-01-06 | 2003-01-12 | Source-listed |
| Milan | 2003-01-27 | 2003-02-02 | Source-listed |
| Marseille | 2003-02-10 | 2003-02-16 | Historical Marseille, not present-day city inferred |
| San Jose | 2003-02-10 | 2003-02-16 | Historic licence/Series identity needs parent join |
| Viña del Mar | 2003-02-10 | 2003-02-16 | Source-listed |
| Rotterdam | 2003-02-17 | 2003-02-23 | Source-listed |
| Memphis | 2003-02-17 | 2003-02-23 | Historical tier must be taken from 2003 parent |
| Buenos Aires | 2003-02-17 | 2003-02-23 | Source-listed |
| Dubai | 2003-02-24 | 2003-03-02 | Source-listed |
| Acapulco | 2003-02-24 | 2003-03-02 | Source-listed |
| Copenhagen | 2003-02-24 | 2003-03-02 | Source-listed |
| Houston | 2003-04-21 | 2003-04-27 | Source-listed |
| Valencia | 2003-04-28 | 2003-05-04 | Source-listed |
| Munich | 2003-04-28 | 2003-05-04 | Source-listed |
| Rome Masters | 2003-05-05 | 2003-05-11 | Original Masters category; no modern backfill |
| Hamburg Masters | 2003-05-12 | 2003-05-18 | Original Masters category; no modern backfill |
| St. Pölten | 2003-05-19 | 2003-05-25 | Source-listed |
| London / Queen's Club | 2003-06-09 | 2003-06-15 | Source-listed |
| Long Island | 2003-08-18 | 2003-08-24 | Source-listed |
| Bucharest | 2003-09-08 | 2003-09-14 | Source-listed |
| Costa do Sauípe | 2003-09-08 | 2003-09-14 | Historical location; do not replace with modern host |
| Bangkok | 2003-09-22 | 2003-09-28 | Source-listed |
| Palermo | 2003-09-22 | 2003-09-28 | Source-listed |
| Shanghai | 2003-09-22 | 2003-09-28 | Historical Shanghai event, not modern Masters conflation |
| Moscow | 2003-09-29 | 2003-10-05 | Source-listed |
| Tokyo | 2003-09-29 | 2003-10-05 | Source-listed |

## Required gates before importing
1. Check **each** event against 2003 `seasons_1990_2026.json` active Series membership and original tier, including licence-lineage distinction.
2. Compare full official ATP 2003 played-results roster against the parent membership roster. Record every unpaired, cancelled, team, Grand Slam, Challenger or duplicate event explicitly.
3. Transcribe remaining exact official date intervals; do not infer adjacent events from the same week or from 2004.
4. Only then insert all verified rows into `calendar_dates_v1.json`, run builder `--write` and `--check`, PR-critical tests, frontend tests and hosted CI.
5. Preserve ISO week-year separately from season-year. In particular, 2002-12-30 through 2003-01-05 is **ISO 2003/W01**, not ISO 2002/W53.

**Scope warning:** These 30 dated examples are not represented as Calendar entities until formally curated and built. No sporting engine changes, score claims, auto-save or merge.

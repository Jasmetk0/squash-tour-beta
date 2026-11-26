# ATP Tour 2019 phase evidence and inventory (secondary-source batch)

Scope: men's ATP Tour 250/500/Masters 1000, Next Gen Finals and ATP Finals for
2019 (63 canonical occurrences). Grand Slams, Challenger, ITF, team events and
doubles are excluded. This is evidence only: no profile is published, no schedule
is installed and nothing was played. Draft `#1898` owns 2020–2025 and `#1891`
owns 1990, so 2019 does not overlap.

## What is in the data

`config/reference_packages/atp_tour_1990_2026/phase_calendar_evidence/2019.json`
keeps the canonical ATP-archive dates, stable Series and categories unchanged and
adds, per occurrence:

- production `RunCalendar` positions for season offsets 1 and 37;
- format evidence read from the English Wikipedia event and singles articles
  (main draw players, qualifier places, wild cards, seeds, Q draw size), with
  derived bracket capacity, rounds and BYEs marked as arithmetic;
- the revision id and SHA-256 of the exact bytes received for each page;
- infobox dates compared with the canonical dates. 46 agree and 17 differ. Every
  difference is recorded as a conflict and the canonical date is kept. The most
  frequent pattern is a canonical Sunday start (Monte-Carlo 14 Apr, Rome 12 May,
  Metz and St. Petersburg 15 Sep, Cincinnati 11 Aug) against a Monday start in the
  article. Whether that Sunday is a qualifying day is not established by any
  source read here;
- licence-lineage identity notes (Pune = `hong_kong`, Budapest =
  `belgrade_clay_2021`, Marseille = `lyon`, Zhuhai = `hangzhou`, New York =
  `dallas`). They are preserved, not renamed.

## Not established (left open)

- Qualifying dates. ATP draws, results archive and the Tennis Temple order-of-play
  pages answered HTTP 403 from this environment. No date was copied from the
  usual weekend-before pattern.
- Point tables (Main and Q) and the 2019 ATP Rulebook revision and page.
- Qualifying draw PDFs and their SHA-256 hashes.
- Qualifier places, wild cards or seeds for the pages whose infobox does not state
  them (listed in each record's `open_fields`).

Wikipedia is a secondary source. It is a cross-check and format hypothesis, never
the decider where it disagrees with the ATP archive.

## Reproduce

```bash
PYTHONPATH=. python -m scripts.build_atp_wikipedia_season_evidence 2019 --raw RAW_DIR --out WP.json
PYTHONPATH=src python -m scripts.build_atp_phase_evidence_year 2019 WP.json OUT.json
PYTHONPATH=src python -m scripts.audit_atp_historical_inventory --check
```

The first command needs network access to `en.wikipedia.org`. The second and third
are offline.

## Next

1. Obtain a readable qualifying-date source for 2019 (ATP draws or a dated
   order-of-play archive). Then publish one compatible Q/Main profile through
   Preview → Confirm → explicit Save → reopen in a new process.
2. Repeat this batch for 2018, 2017 and so on, after checking that the previous
   year's boundaries are written down and no other Draft covers them.

## Extension to 1991–2018

The same pipeline produced `phase_calendar_evidence/<year>.json` for 1991–2018.
1990 belongs to #1891, 2020–2025 to #1898, and 2026 is provisional. Matching a
canonical Series to a Wikipedia article uses name tokens plus a start date within
four days. A remaining pair that is the only one in its week is matched by date
alone and marked `date_only_unique_lineage`. Everything else stays unmatched and
records a conflict; no pairing is guessed. Older seasons have weaker coverage
(2000 matched only 22 of 65, mostly because many articles do not exist), so their format fields are mostly open.

| Year | Occurrences | Dates agree | Dates differ | Date not parsed | No Wikipedia match | Matched by date only |
|---|---|---|---|---|---|---|
| 2019 | 63 | 46 | 17 | 0 | 0 | 0 |
| 2018 | 64 | 54 | 10 | 0 | 0 | 5 |
| 2017 | 64 | 54 | 10 | 0 | 0 | 5 |
| 2016 | 62 | 48 | 14 | 0 | 0 | 7 |
| 2015 | 62 | 47 | 13 | 0 | 2 | 9 |
| 2014 | 60 | 41 | 13 | 2 | 4 | 11 |
| 2013 | 61 | 30 | 23 | 2 | 6 | 10 |
| 2012 | 61 | 32 | 24 | 0 | 5 | 8 |
| 2011 | 61 | 29 | 28 | 0 | 4 | 8 |
| 2010 | 61 | 38 | 19 | 0 | 4 | 10 |
| 2009 | 61 | 25 | 31 | 0 | 5 | 12 |
| 2008 | 61 | 35 | 17 | 0 | 9 | 12 |
| 2007 | 62 | 28 | 26 | 1 | 7 | 8 |
| 2006 | 63 | 31 | 21 | 0 | 11 | 7 |
| 2005 | 63 | 30 | 21 | 1 | 11 | 12 |
| 2004 | 63 | 38 | 16 | 0 | 9 | 11 |
| 2003 | 63 | 53 | 3 | 0 | 7 | 9 |
| 2002 | 62 | 47 | 5 | 0 | 10 | 9 |
| 2001 | 65 | 54 | 6 | 0 | 5 | 14 |
| 2000 | 65 | 12 | 10 | 0 | 43 | 1 |
| 1999 | 66 | 36 | 24 | 1 | 5 | 19 |
| 1998 | 74 | 34 | 19 | 0 | 21 | 17 |
| 1997 | 75 | 37 | 15 | 0 | 23 | 17 |
| 1996 | 78 | 66 | 3 | 0 | 9 | 14 |
| 1995 | 80 | 34 | 39 | 0 | 7 | 11 |
| 1994 | 85 | 29 | 44 | 0 | 12 | 12 |
| 1993 | 84 | 40 | 27 | 0 | 17 | 9 |
| 1992 | 78 | 43 | 22 | 0 | 13 | 8 |
| 1991 | 76 | 42 | 24 | 0 | 10 | 10 |

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

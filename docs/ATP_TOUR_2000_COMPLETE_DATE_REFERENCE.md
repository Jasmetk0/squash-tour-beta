# ATP Tour 2000 — original dated Tour reference cohort

**Status:** Canonically imported to `calendar_dates_v1.json` and the
regenerated `calendar.json` in Calendar Draft PR #1741, with 65/65
date-bearing year-effective Series from parent PR #1731.

**Main dated source:** [Official ATP 2000 results archive](https://www.atptour.com/en/scores/results-archive?year=2000).
The source lists actual played events and date ranges. It is **not** itself a
legal certificate for all historical tournament rights or transfers.

## Explicit historical boundaries

- **Doha, Chennai and Adelaide:** 3–9 January 2000 (ISO **2000/W01**).
- **Mexico City** (source Series `acapulco`): 21–27 February, not yet
  present-day Acapulco host.
- **London-1** (source Series `sofia`): 21–27 February, not present-day Sofia.
- **Orlando** (source Series `houston`): 1–7 May, not modern Houston.
- **Mallorca** (source Series `brussels`): 1–7 May.
- **Separate Stuttgart events:** clay Stuttgart, 17–23 July (`stuttgart`),
  and indoor Stuttgart Masters, 30 October–5 November
  (`stuttgart_indoor_masters`), with their original 2000 ATP tiers.
- **San Marino**, 24–30 July (`san_marino_2000`).
- **Tennis Masters Cup Lisbon**, 27 November–3 December
  (`atp_finals`).
- **Not part of this reference Package:** Sydney Olympics, Grand Slams,
  Davis Cup, World Team Cup, Challenger Tour and match-level scores.

Every original dated host has a separately recorded historical name in
`calendar_backfill_2000_candidates_v1.json`. The canonical occurrence
stores the **persistent parent Series ID**, original 2000 Category and the
exact start/end plus ISO week labels; it does not convert a date into a
playable FAX Calendar edition.

## Reproducible quality gates

```bash
python scripts/audit_atp_calendar_backfill.py --year 2000 --json
python scripts/promote_atp_calendar_candidate.py --check --year 2000
python scripts/build_atp_historical_calendar.py --check
python -m pytest -q tests/domain/test_atp_calendar_backfill_2000.py
```

The read-only promotion check verifies exact candidate/canonical identity and
the generated Calendar snapshot. A green build establishes internal
consistency, **not** independent adjudication of tournament licence-lineage
evidence. As of 2026-11-04, years 1990–1999 and 2003 are still undated in the
canonical reference; 2003 has a separately documented official ATP Finals
start-date conflict.

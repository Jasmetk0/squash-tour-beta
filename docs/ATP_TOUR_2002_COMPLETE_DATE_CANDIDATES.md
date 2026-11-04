# 🎾 ATP Tour 2002 — full original-tier date candidate roster

**Current status:** 62 of 62 year-effective ATP source Series from the parent historical Category/Series roster have been individually dated using the [official 2002 ATP Tour played-results archive](https://www.atptour.com/en/scores/results-archive?year=2002). This is a **source candidate**, not yet a committed canonical Calendar year.

## Evidence and interpretation

- All 62 rows live in `config/reference_packages/atp_tour_1990_2026/calendar_backfill_2002_candidates_v1.json`. Each row includes original historic host, persistent source Series ID, exact start and end.
- Doha, Chennai and Adelaide occurred **31 December 2001 – 6 January 2002**, ISO **2002/W01**, not 2001/W53. Original host identity and season year remain separate.
- The 2002 Tennis Masters Cup in Shanghai is **11–17 November** by the 2002 annual results archive.
- Historical 2002 Tashkent corresponds to source Series `bangkok_2013`; the event is recorded as **Tashkent** in this year, not fictitiously as Bangkok. Likewise `hong_kong_salem_2002` denotes played Hong Kong and `montpellier` denotes played Lyon.
- The parent Series mapping is reused, but the ATP annual results archive does **not by itself prove legal tournament licence continuity**. Preserve this uncertainty.
- Grand Slams and team competitions are excluded; no match results, ranking scores, ATP gameplay, FAX season events or Save actions are created.

## Verification / promotion gates

```bash
python scripts/audit_atp_calendar_backfill.py --year 2002 --json
pytest -q tests/domain/test_atp_calendar_backfill_2002.py
pytest -q tests/domain/test_atp_calendar_promotion.py
python scripts/promote_atp_calendar_candidate.py --check --year 2002
```

After source review and green tests, an explicit `--write --year 2002` performs source and generated snapshot updates together in the working tree; commit **both** files in one PR. The script performs old-occurrence immutability checks; it has not been run and no generated snapshot has been committed in this contribution.

The distinct 2003 official ATP Finals date discrepancy remains blocked for canonical promotion. Neither parent #1731 nor stacked #1741 is merged.


## Canonical import — 4 November 2026

All **62** 2002 original-tier source candidates have now been promoted into
the canonical ATP Calendar source and regenerated Calendar snapshot, together
with the 65 events of 2001. These are historical reference dates and ISO
week labels, **not** runnable FAX tournament editions or certified legal
Series transfers. The idempotent verification is:

```bash
python scripts/promote_atp_calendar_candidate.py --check --year 2002
python scripts/build_atp_historical_calendar.py --check
```

The earlier instructions above describing the 2002 cohort as staged and
uncommitted predate this import.

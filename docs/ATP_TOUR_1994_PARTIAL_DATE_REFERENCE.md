# ATP Tour 1994 — verified early-season dates (partial evidence ledger)

**Status: partial, NOT imported into canonical Calendar.** As of 4 November 2026 the parent Category/Series snapshot has **85** year-effective original ATP Tour/World Championship identities in 1994. The new `calendar_backfill_1994_candidates_v1.json` contains **16 exact event intervals**, leaving **69 not yet dated**. No 1994 coverage state, source Package fingerprint, Run Working Draft, or sporting clock is changed.

## Sources and methodological limits

- [Official ATP 1994 results archive](https://www.atptour.com/en/scores/results-archive?year=1994) — original January–February historical host names and dates for the first **15** dated tournament identities. The archived chronology starts **Doha, Adelaide, Oahu (3–9 January)**; **Auckland, Jakarta, Sydney-1 (10–16 January)** and includes Dubai, Marseille, San José, Milan, Memphis, Stuttgart-1, Philadelphia, Rotterdam and Mexico City.
- [Official Nitto ATP Finals historical results, 1970–1999](https://www.nittoatpfinals.com/en/heritage/results-1970-1999) — original **Frankfurt World Championships 15–20 November 1994**, not a later Masters or a different city's finals.
- Original pre-2009 **ATP World Series / Championship Series / Single-Week** categorisation is inherited from the existing parent Series year, not overwritten with modern 250/500/1000 labels.

Only the recorded historical venues and inclusive date intervals are treated as observed dates. The persistent Series IDs (e.g. `brisbane` for Adelaide, `lyon` for Marseille, `dallas` for San José, `rio` for Memphis) reference the existing parent package; they **do not prove legal licence lineage**. Crucially, **Oahu 1994** is a separate Series, not a generic Hawaii alias; Sydney-1 is not Sydney Indoor. Grand Slams, Challenger events, team competitions and Davis Cup are not part of this reference.

## Validation and further work

```bash
python scripts/audit_atp_calendar_backfill.py --year 1994 --json
python -m pytest -q tests/domain/test_atp_calendar_backfill_1994.py
python scripts/build_atp_historical_calendar.py --check
```

The audit must report `candidate_count=16`, `expected_played_source_count=85`, `roster_reconciled=false` and `ready_for_whole_year_promotion=false`. Explicit `--check` or `--write` promotion is **blocked** until the remaining 69 dates are supported and reconciled. No interpolation from adjacent seasons or forced completion. The previously canonical 1,731 occurrences and 37 annual coverage records remain untouched.

Later seasons 1997–1999 and 2003 still have separately documented official ATP Finals start-date conflicts; this 1994 partial cohort does not resolve them. The 2026 season remains provisional.

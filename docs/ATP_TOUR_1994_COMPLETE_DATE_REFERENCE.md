# ATP Tour 1994 — complete original date reference (85/85)

**Canonical source-only reference:** all **85 original 1994 ATP main-tour singles and Frankfurt ATP Tour World Championships source Series** have official historically dated intervals in `calendar_dates_v1.json` and derived `calendar.json`. Source-only tennis evidence; **not a playable FAX/squash calendar**, not generated Editions, matches, scores, points, or a legal licence transfer certification.

## Source and exclusions

- [1994 ATP official results archive](https://www.atptour.com/en/scores/results-archive?year=1994): all original event names, inclusive date bounds and hosts, January–November, used as the **source-of-record**. Note: the ATP modern web UI sometimes labels old Masters as modern Masters 1000; our Category IDs retain the actual 1994 **ATP Championship Series, Single-Week**, **Championship Series**, **World Series** and **World Championships**.
- [1994 ATP Tour World Championship primary tournament history](https://www.atptour.com/-/media/08887c4b3be347dd8a2d701c23fcd587.pdf): Frankfurt **15–20 November 1994**, also agreed by the [Nitto ATP Finals heritage](https://www.nittoatpfinals.com/en/heritage/results-1970-1999).
- Grand Slams (Australian Open, Roland Garros, Wimbledon, US Open), World Team Cup, Davis Cup, Grand Slam Cup, Hopman Cup and Challenger events **are explicitly outside this ATP Tour original-tier package**.

## Historically distinct original events

| Original 1994 event | Existing source Series ID | Exact ATP date interval |
| --- | --- | --- |
| Sydney-1 | `sydney_2019` | 10–16 January |
| Sydney-2 (indoor) | `sydney_indoor_1994` | 3–9 October |
| Tokyo-1 (Japan Open) | `tokyo` | 4–10 April |
| Tokyo-2 (indoor) | `tokyo_indoor_1995` | 10–16 October |
| Stuttgart-1 (indoor) | `stuttgart_indoor_feb_1995` | 14–20 February |
| Stuttgart-2 (clay) | `stuttgart` | 18–24 July |
| Atlanta | `atlanta_verizon_2001` | 25 April–1 May |
| Indianapolis | `atlanta` | 15–21 August |
| Manchester | `eastbourne` | 13–19 June |
| Hilversum | `belgrade_2012` | 25–31 July |
| Sun City | `johannesburg_1995` | 28 March–3 April |
| Frankfurt World Championships | `atp_finals` | 15–20 November |

All other 1994 historical hosts and periods are in the immutable source date ledger and year-specific candidate ledger. Persistent `series_id` values represent the **parent package's** historical entity identity and cannot on their own prove a legally transferred ATP licence. No host is relabelled to a future city. The archived Zaragoza **7–20 March** interval is retained as published rather than silently rewritten to a conventional seven-day tournament. Dates are the ATP archive's published event windows, not independently verified daily match-by-match schedules.

## Verification and boundary

```bash
python -m scripts.audit_atp_calendar_backfill --year 1994 --json
python -m scripts.promote_atp_calendar_candidate --check --year 1994
python -m scripts.build_atp_historical_calendar --check
python -m pytest -q tests/domain/test_atp_calendar_backfill_1994.py
```

The candidate auditor deliberately reports `canonical_conflicts=85` (every already-present original Source Series), `roster_reconciled=true`, and `ready_for_whole_year_promotion=false` because **re-importing an existing canonical year is forbidden**. The idempotent promoter `--check` verifies the date-source and generated Calendar snapshots are identical and does not mutate them. The Calendar now has **1,816 dated occurrences + 37 year coverage = 1,853 Calendar entities** and **29/37 originally dated ATP seasons**.

Not resolved by this archival import: four official date-window conflicts in **1997–1999 and 2003**, **1990–1993** lacking canonical dates, incomplete independent event-specific legal licence evidence, or the still-provisional **2026** season. No automatic sporting projection from ISO week numbers into a Run's arbitrary W52/W61/W80 clock is authorised. User-owned merge only.

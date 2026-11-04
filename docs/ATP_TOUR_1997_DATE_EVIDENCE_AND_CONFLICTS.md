# ATP Tour 1997 — source-accurate event-date candidate roster

**Historical source:** [ATP official 1997 played-results archive](https://www.atptour.com/en/scores/results-archive?year=1997).

**Coverage:** 75 of 75 year-effective parent Category/Series source
memberships have an archived played-event date interval and original tournament
host in `calendar_backfill_1997_candidates_v1.json`.

This is **not yet a canonical Calendar import**. All 75 remain staged because
the 1997 ATP Tour World Championship start dates are represented differently by
two official sources.

## Contemporaneous history correctly preserved

- **Doha** and **Adelaide** start on **30 December 1996**, end 5 January 1997:
  both belong to **ISO 1997/W01**, and to the **1997 ATP season**.
- **Zagreb**, 27 January–2 February, uses the historic parent ID
  `split_1998`; **Shanghai**, the same week, uses `bangalore_2008`.
  Neither is relabelled using the later hosting city.
- **St Petersburg**, 17–30 March, is left as the source-published
  two-week interval, with no assumption of a seven-day date window.
- **Rosmalen** in June is `s_hertogenbosch`; **Marbella** in September
  is `brussels`. Those refer to the parent historical Series model,
  without a new assertion of legal licence sale.
- **Bucharest** and **Toulouse** are both represented by their
  published **22 September–5 October** intervals. Their source windows
  touch two ISO weeks, even though a single-week sporting calendar might
  normally be expected.
- **Beijing** 29 September–5 October is a distinct `beijing_1997`
  source Series.
- The historic Stuttgart clay Series and indoor Masters remain separate,
  as do the excluded **Grand Slam Cup, Grand Slams, Davis Cup and World Team Cup**.

## Official historical Finals mismatch

- The [ATP yearly results archive](https://www.atptour.com/en/scores/results-archive?year=1997)
  displays World Championship **10–16 November 1997**.
- The [ATP Finals historical record](https://www.nittoatpfinals.com/en/heritage/results-1970-1999)
  dates the Hanover competition **11–16 November 1997**.

Until the difference between archive *event window* and historical *actual
competition dates* is documented, the candidate retains the ATP annual
archive value as a source-attributed observation and the canonical promoter
refuses to publish it as a single definitively correct start date.

## Read-only acceptance

```bash
python scripts/audit_atp_calendar_backfill.py --year 1997 --json
python -m pytest -q tests/domain/test_atp_calendar_backfill_1997.py
python scripts/promote_atp_calendar_candidate.py --check --year 1997
```

The last command **must currently reject the unresolved start-date conflict**.
A structural 75/75 join is not a certification of licensing chains, source
completeness beyond the parent roster or playable FAX calendar weeks.

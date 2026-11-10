# ATP Tour 1995 — year-effective dates, Finals and distinct historic series

**Canonical status:** 80 of the 80 year-effective parent original-tour
ATP Series are dated in `calendar_dates_v1.json` and the generated
`calendar.json`. Original host labels and exact dates are also preserved
in `calendar_backfill_1995_candidates_v1.json`.

## Official sources

- [ATP Tour 1995 original results archive](https://www.atptour.com/en/scores/results-archive?year=1995): original played event dates, host-city names and event order. Modern website tier labels should **not** overwrite 1995 World Series / Championship Series / Single-Week Championship categories.
- [Nitto ATP Finals historical results 1970–1999](https://www.nittoatpfinals.com/en/heritage/results-1970-1999): original **Frankfurt World Championship 14–19 November 1995**. This **agrees with the annual ATP results archive**.

## Contemporaneous distinctions — preserved, not invented

- **Two separate Tokyo editions:** `tokyo` original Japan Open 10–16 April and `tokyo_indoor_1995` Tokyo-2 indoor 9–15 October. They share a city but not a single event ID.
- **Two separate Stuttgart editions:** `stuttgart_indoor_feb_1995` indoor Championship Series **20–26 February** and `stuttgart` outdoor Stuttgart-2 clay Championship Series **17–23 July**. Neither may be conflated with the post-1995 Stuttgart Indoor Masters later represented by other Series IDs.
- **Masters in Essen**, 23–29 October, is `essen_masters` under the contemporaneous single-week Masters tier. It is not arbitrarily renamed Stuttgart/Madrid.
- **Nice**, 17–23 April, is the historical `hong_kong` parent-source Series, distinct from *Hong Kong itself* under `hong_kong_salem_2002` during the same week. The link follows the pre-existing parent package and does **not certify a legal licence sale**.
- **Johannesburg**, **Bordeaux**, **Montevideo** and the 1995 **Buenos Aires** year-effective source Series remain distinct historic events.
- **Pinehurst**, **Coral Springs**, **Rosmalen**, **St. Pölten**, **Kuala Lumpur**, **Valencia** and other original 1995 hosts remain explicitly recoverable in the source candidate ledger.
- Grand Slams, World Team Cup, Davis Cup and Grand Slam Cup are out of the original ATP main-tier + Finals reference scope. These dates are **non-playable reference events** and cannot generate FAX match results, rankings, draws or automatic saves.

## Reproducible acceptance and caveat

```bash
python -m scripts.audit_atp_calendar_backfill --year 1995 --json
python -m scripts.promote_atp_calendar_candidate --check --year 1995
python -m scripts.build_atp_historical_calendar --check
python -m pytest -q tests/domain/test_atp_calendar_backfill_1995.py
```

The year-source audit reports 80/80 *parent Series reconciliation*, along
with 80 *already canonical* source overlaps; its promotion readiness flag
is intentionally false because re-importing an existing year is disallowed.
The `--check` promoter verifies identical already-imported data without
mutation. This distinction protects against duplicate imports.

Both 1995 and 1996 commits were built by independently reconstructing
the existing canonical Calendar snapshot and comparing every pre-existing
occurrence outside the imported season. This checks internal consistency,
**not the legal history of tournament licence transfers**. The year 2026
remains provisional; 1997–1999 and 2003 remain blocked on official Finals
start-date discrepancies.

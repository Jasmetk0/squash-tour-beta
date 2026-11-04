# ATP Tour 1990 — all original source-year dates, unresolved Frankfurt Finals window

> **Historical audit snapshot (superseded import status).** This report
> documents the original pre-reconciliation evidence and the reason this
> year's promotion was formerly blocked. The year is now canonically dated
> **only as an ATP annual results-archive event window**; the distinct official
> Finals historical window remains separately preserved in
> `calendar_dates_v1.json`, in each relevant Finals occurrence, and in
> [the reviewed source-window policy](ATP_TOUR_FINALS_DATE_WINDOW_SEMANTICS.md).
> Phrases below about a blocked, staged or undated calendar describe the
> historical audit stage, **not the current state**. There is no claim of
> actual first-match dates, playable squash calendars or complete licence
> lineage.
>

**Status: 75/75 historical ATP Tour / singles World Championship original-tier Series date candidates, NOT canonical.** The new `calendar_backfill_1990_candidates_v1.json` exactly matches all 75 year-effective parent source Series. The complete source list is the [1990 original ATP Tour results archive](https://www.atptour.com/en/scores/results-archive?year=1990), including historical event-city labels and inclusive date intervals.

## Two official Finals date concepts — unresolved

- The [ATP 1990 results-year archive](https://www.atptour.com/en/scores/results-archive?year=1990) records **12–18 November 1990** for the original Frankfurt ATP Tour World Championship.
- The separate [Nitto ATP Finals historical results 1970–1999](https://www.nittoatpfinals.com/en/heritage/results-1970-1999) reports **13–18 November 1990** for competition. These may represent an inclusive event-administration window and a played-match window respectively, but a general rule has not yet been established.
- We preserve the archive's exact `1990-11-12..1990-11-18` as a **candidate**, while `SOURCE_DATE_CONFLICTS[1990]` prevents any canonical year import. Both date ranges are documented. Editing the archive candidate without resolving the conflict fails validation.

## Historically important source identities

| Original 1990 ATP event | Stable parent Series ID | Annual archive event window |
| --- | --- | --- |
| Adelaide | `brisbane` | 1–7 January |
| Wellington | `wellington_1992` | 1–7 January |
| Guarujá | `maceio_1992` | 5–11 February |
| Toronto-1 indoor | `toronto_indoor_1990` | 12–18 February |
| Canadian Open, Toronto | `canadian_open` | 23–29 July |
| Rio de Janeiro | `rio_carpet_1990` | 2–8 April |
| Memphis | `rio` | 26 February–4 March |
| Kiawah Island | `birmingham_1994` | 7–13 May |
| San Remo | `san_remo_1990` | 30 July–5 August |
| Sydney-1 / Sydney-2 | `sydney_2019` / `sydney_indoor_1994` | 8–14 Jan / 1–7 Oct |
| Tokyo-1 / Tokyo-2 | `tokyo` / `tokyo_indoor_1995` | 9–15 Apr / 8–14 Oct |
| Stuttgart-1 / Stuttgart-2 | `stuttgart_indoor_feb_1995` / `stuttgart` | 19–25 Feb / 16–22 Jul |
| Wembley | `wembley_1990` | 5–11 November |
| Itaparica | `itaparica_1990` | 5–11 November |
| Frankfurt Singles World Championships | `atp_finals` | **12–18 November, archive window — disputed** |

These are year-effective parent *reference identities*, **not independent legal licence-chain proof**. The original World Series / Championship Series / Single-Week / year-end categories are inherited for 1990; no retrospective 2009 ATP tier or squash scoring is applied. The Australian Open, Roland Garros, Wimbledon, US Open, World Team Cup, Davis Cup, Grand Slam Cup, Challengers and separate doubles championships are out of scope.

## Reproducible fail-closed checks

```bash
python scripts/audit_atp_calendar_backfill.py --year 1990 --json
python -m pytest -q tests/domain/test_atp_calendar_backfill_1990.py
python scripts/build_atp_historical_calendar.py --check
```

Expected audit: `candidate_count=75`, `expected_played_source_count=75`, `remaining_series_ids=[]`, `roster_reconciled=true`, `canonical_conflicts=[]`, `unresolved_date_conflicts.atp_finals` present, and `ready_for_whole_year_promotion=false`. Both `prepare(1990)` and `--write --year 1990` must reject the unresolved official conflict with no source mutation. The parent Calendar stays **1,892 occurrences + 37 coverages = 1,929 source entities**, **30/37 canonically dated**.

The remaining undated canonical years **1990, 1992–1993, 1997–1999, 2003** each have source evidence and an explicit non-automatic Finals date-window resolution gate. The official 2026 schedule remains provisional. Do not claim a playable Run season, complete legal licence lineage or pre-alpha release.

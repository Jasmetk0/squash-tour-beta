# ATP Tour 1992 — complete original-year source candidates, unresolved Finals dates

**Status: 78/78 original historical ATP Series-year source-date candidates, but NOT canonical.** All exact published original-tour tournament date windows were transcribed from [ATP's official 1992 year archive](https://www.atptour.com/en/scores/results-archive?year=1992), preserving the real chronology and stable parent year-effective Category IDs.

## Official date evidence and critical conflict

- Historical 1992 tour opens **30 December 1991–5 January 1992** at both **Adelaide** and **Wellington**. Those dates carry ISO **1992/W01**, rather than a fabricated 1991/W53 or single-calendar-year assumption.
- A *different* **Brisbane (autumn)** event was held **28 September–4 October 1992**, distinct from January Adelaide. Original Tokyo-1/Tokyo-2, Sydney-1/Sydney-2 and Stuttgart-1/Stuttgart-2 have independent year-specific dated identities; never collapse paired events sharing a city.
- **Unresolved Frankfurt Finals:** official ATP results-year archive uses an event-window label of **16–22 November 1992**. Both [official ATP Finals heritage](https://www.nittoatpfinals.com/en/heritage/results-1970-1999) and [ATP tournament history PDF](https://www.atptour.com/-/media/08887c4b3be347dd8a2d701c23fcd587.pdf) instead show actual Singles Championship competition as **17–22 November**. The date concepts must not be equated without a defined event-window convention, and neither should be silently selected as canonical. `SOURCE_DATE_CONFLICTS[1992]` blocks whole-year promotion.

## Representative original event lineage IDs

| 1992 ATP event | Existing Series ID | Archive date range |
| --- | --- | --- |
| Adelaide | `brisbane` | 30 Dec 1991–5 Jan 1992 |
| Wellington | `wellington_1992` | 30 Dec 1991–5 Jan 1992 |
| Brisbane (autumn) | `brisbane_autumn_1992` | 28 Sep–4 Oct |
| Brussels | `brussels_championship_1992` | 10–16 Feb |
| Maceió | `maceio_1992` | 3–9 Feb |
| Singapore | `singapore_march_1992` | 30 Mar–5 Apr |
| Cologne | `cologne_1992_clay` | 14–20 Sep |
| Taipei | `taipei_1992` | 19–25 Oct |
| Guarujá | `guaruja_1992` | 26 Oct–1 Nov |
| Búzios | `buzios_1992` | 2–8 Nov |
| Frankfurt ATP Tour World Championships | `atp_finals` | **16–22 Nov annual archive window — disputed** |

The source `series_id` tracks the parent reference entity, not proof of legal ATP licence transfer; host aliases are historical not current. Original pre-2009 ATP World Series and Championship Series hierarchy is retained. The four Grand Slams, Barcelona Olympics, World Team Cup, Davis Cup, Grand Slam Cup, Challenger events and separate doubles Finals are excluded.

## Read-only verification

```bash
python scripts/audit_atp_calendar_backfill.py --year 1992 --json
python -m pytest -q tests/domain/test_atp_calendar_backfill_1992.py
python scripts/build_atp_historical_calendar.py --check
```

The auditor reports `candidate_count=78`, `expected_played_source_count=78`, `remaining_series_ids=[]`, `roster_reconciled=true`, and `ready_for_whole_year_promotion=false` due to the explicit 1992 Finals date-source conflict. Both `prepare(1992)` and `--write --year 1992` must reject with a descriptive error. Canonical **1,816** dates, **37** year ledgers and **29/37** dated seasons remain unchanged. Other unresolved: 1990 staged with a Finals date-window conflict; 1993/1997–1999/2003 Finals date conflicts, partially proven legal licence history, and provisional 2026.

# ATP Tour 1993 — complete original-year candidate roster with unresolved Finals date-window conflict

**Status:** **84/84 source year-effective historical ATP main-tour + Frankfurt Finals candidates independently transcribed from the official annual archive**; **NOT promoted** into canonical Calendar. Existing 1994–1996, 2000–2002 and 2004–2026 canonical dates remain untouched.

## Primary evidence

- [Official ATP 1993 annual results archive](https://www.atptour.com/en/scores/results-archive?year=1993) lists all original ATP 1993 tournament identities and exact archived date windows. We preserve these original labels in `calendar_backfill_1993_candidates_v1.json`; 84 Series match the 1993 year-effective parent roster.
- **Unresolved exception:** ATP yearly archive labels Frankfurt ATP Tour World Championships **15–21 November 1993**, while [official ATP Finals heritage](https://www.nittoatpfinals.com/en/heritage/results-1970-1999), [primary ATP tournament history PDF](https://www.atptour.com/-/media/08887c4b3be347dd8a2d701c23fcd587.pdf) and [ITF event record](https://www.itftennis.com/en/tournament/atp-finals/ger/1993/m-csr-ger-01a-1993/draws-and-results/) indicate actual **16–21 November 1993**. Different definitions of `start_date` (archived event window versus days of competition) may account for the difference, but that is not established as a universal rule. **Do not silently choose the date or declare canonical year complete.** Conflict is explicitly blocked in `SOURCE_DATE_CONFLICTS`.

## Historic Series identities preserved

| Event | Source Series identity | Archived dates |
| --- | --- | --- |
| Kuala Lumpur-1 | `kuala_lumpur_jan_1993` | 4–10 January |
| Kuala Lumpur-2 | `singapore_1999` | 27 September–3 October |
| Sydney-1 | `sydney_2019` | 11–17 January |
| Sydney-2 (indoor) | `sydney_indoor_1994` | 4–10 October |
| Tokyo-1 | `tokyo` | 5–11 April |
| Tokyo-2 (indoor) | `tokyo_indoor_1995` | 11–17 October |
| Stuttgart-1 (indoor) | `stuttgart_indoor_feb_1995` | 15–21 February |
| Stuttgart-2 (clay) | `stuttgart` | 19–25 July |
| San Francisco | `dallas` | 1–7 February |
| Charlotte | `birmingham_1994` | 12–18 April |
| Tampa | `houston` | 3–9 May |
| Durban | `johannesburg_1995` | 29 March–4 April |
| Genoa | `poertschach_2008` | 14–20 June |
| Frankfurt | `atp_finals` | **15–21 November archival window — disputed** |

These are the parent Package's existing Series identity links, not independent proof of historical legal sanction/licence lineage. Original 1993 World Series / Championship Series / Single-Week category labels are retained from parent year-effective sources; today's 250/500/1000 tiers are not backdated. Grand Slams, World Team Cup, Davis Cup, Grand Slam Cup, Challengers, and separate doubles Finals are out of scope.

## Read-only verification

```bash
python scripts/audit_atp_calendar_backfill.py --year 1993 --json
python -m pytest -q tests/domain/test_atp_calendar_backfill_1993.py
python scripts/build_atp_historical_calendar.py --check
```

The auditor must yield `candidate_count=84`, `expected_played_source_count=84`, `remaining_series_ids=[]`, `roster_reconciled=true`, `unresolved_date_conflicts.atp_finals` present and `ready_for_whole_year_promotion=false`. `prepare(1993)` fails closed even if attempted with `--write` or `--check`. **No approval to change game mechanics, Edition dates or Run clock.** Canonical historical Calendar remains **1,816 occurrences + 37 coverage entries; 29/37 dated seasons**.

Other remaining missing canonical years: 1990 and 1992 (both now separately staged with Finals event-window conflicts); other unresolved historical Finals date-window discrepancies: 1997–1999 and 2003; 2026 still provisional. Do not treat this evidence as full independent ATP event licence certification.

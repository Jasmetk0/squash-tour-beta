# ATP Tour 2003 — complete year-roster date candidates, pending canonical build

**Commit scope:** 63 of the 63 year-effective source Series from the established 2003 parent Category/Series package have been matched against the [official ATP Tour 2003 results archive](https://www.atptour.com/en/scores/results-archive?year=2003). The dated, historic-host-identified candidates reside in `config/reference_packages/atp_tour_1990_2026/calendar_backfill_2003_candidates_v1.json`. The existing `calendar_dates_v1.json` and generated `calendar.json` remain unchanged until an atomic, validated canonical promotion.

## Important boundaries

- **63/63 parent roster date coverage is not equivalent to legal Series-licence certification.** Source IDs were joined against the already curated parent source; unresolved historical licence evidence must remain explicit.
- **No Slam or team tournaments:** Australian Open, Roland Garros, Wimbledon, US Open, Davis Cup and World Team Cup are excluded from this Category/Series source coverage. The ATP-operated Tennis Masters Cup is included as `atp_finals`.
- **No fabricated dates:** the ATP results-archive display dates are transcribed exactly. Doha, Chennai and Adelaide begin on **2002-12-30**, which is **ISO 2003 week 1**, not a fictitious 2002 week 53. ISO weeks are source labels, *not* automatically executable Run/FAX calendar week positions.
- **Reference only:** no Edition/Match/Ranking generation, no auto-Save, no engine mutation.
- **Unresolved source limitation:** the ATP results archive labels some old Masters as the present-day `Masters 1000`; historical category names must come exclusively from the year-effective parent source, not modern ATP website labels.

## Reproduce the candidate audit

```bash
python scripts/audit_atp_calendar_backfill.py
python scripts/audit_atp_calendar_backfill.py --json
pytest -q tests/domain/test_atp_calendar_backfill.py
```

Expected for the 2003 candidate inventory: 63 candidates, zero unmatched parent IDs, zero existing canonical conflicts, candidate eligibility for whole-year promotion. The executable source builder currently has **no 2003 dated Canonical Calendar rows**; do not treat candidate eligibility as a successful promotion.

## Next acceptance gates

1. Confirm the 2003 match-venue-to-licence continuity exceptions against sources other than a single ATP results archive index.
2. Move the fully vetted 2003 rows to the canonical dates source, keeping official evidence links, and regenerate its committed `calendar.json` snapshot with `python scripts/build_atp_historical_calendar.py --write`.
3. Run `--check`, all PR-critical and API/FE tests and review final-head hosted CI.
4. Continue 2002 through 1990 as separate year-specific audited cohorts. Maintain exact dates, annual tier identity and transparent missing/uncertain history.

## Newly verified official ATP Finals date-source conflict (2026-11-04)

There are two different **official ATP** 2003 source representations:

- [Official ATP 2003 annual results archive](https://www.atptour.com/en/scores/results-archive?year=2003) lists the **Tennis Masters Cup as 10–16 November 2003**; the provisional 2003 candidate ledger follows this event-date definition.
- [ATP tournament-history document](https://www.atptour.com/-/media/08887c4b3be347dd8a2d701c23fcd587.pdf) describes the **2003 Tennis Masters Cup as 8–16 November 2003**.

The difference could concern competition/tournament-calendar definition, but that explanation has **not been independently established**. Do not silently prefer one definition while presenting it as resolved historical truth. The candidate data remains source attributed but cannot be promoted to the official final Calendar while this is unresolved.

`scripts/promote_atp_calendar_candidate.py --check --year 2003` therefore currently **fails closed** with the explicit historical date conflict. The script additionally checks complete roster reconciliation and that no existing source-era Calendar occurrence changes during any future promotion.


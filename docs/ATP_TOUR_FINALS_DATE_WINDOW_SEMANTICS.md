# ATP historical Finals — evidence-preserving dual official date windows

## Normative calendar date meaning

The Squash Engine ATP reference `Calendar` is an **opaque, read-only tennis source**, not playable FAX/squash Editions. For 1990–2026 its event `start_date` and `end_date` always denote the interval published in the **official ATP annual Results Archive** for that original ATP Tour source year. They are *not* an assertion about the first or last actually played singles match, draws, qualifying, travel, or a broader tournament's doubles activity. The separate ATP Finals historical record can publish an interval beginning a day earlier/later depending on its scope.

The approved, reviewable semantic policy is implemented and pinned in `scripts/atp_finals_date_window_evidence.py`; each of the seven alternate official intervals is copied into canonical `calendar_dates_v1.json` under `finals_date_window_evidence` and is exposed unmodified in the relevant generated `atp_{year}_atp_finals` source occurrence's `alternate_official_finals_window` payload. A strict source policy rejects date changes, missing evidence, changed citations and contradictory concepts. This is a **representation decision**, not an unverified choice that the alternate dates never existed.

## Original official sources (1990–2003)

| Year | ATP original annual archive event window | Independent official Finals record | Meaning |
| --- | --- | --- | --- |
| 1990 | 12–18 Nov | 13–18 Nov | Different archival / Finals heritage start bounds |
| 1992 | 16–22 Nov | 17–22 Nov | Different archival / Finals heritage start bounds |
| 1993 | 15–21 Nov | 16–21 Nov | Different archival / Finals heritage start bounds |
| 1997 | 10–16 Nov | 11–16 Nov | Different archival / Finals heritage start bounds |
| 1998 | 23–29 Nov | 24–29 Nov | Different archival / Finals heritage start bounds |
| 1999 | 22–28 Nov | 23–28 Nov | Different archival / Finals heritage start bounds |
| 2003 | 10–16 Nov | 8–16 Nov | ATP annual singles event window versus a **broader Finals tournament-history interval**, not the same date concept |

ATP annual year archives: [1990](https://www.atptour.com/en/scores/results-archive?year=1990), [1992](https://www.atptour.com/en/scores/results-archive?year=1992), [1993](https://www.atptour.com/en/scores/results-archive?year=1993), [1997](https://www.atptour.com/en/scores/results-archive?year=1997), [1998](https://www.atptour.com/en/scores/results-archive?year=1998), [1999](https://www.atptour.com/en/scores/results-archive?year=1999), [2003](https://www.atptour.com/en/scores/results-archive?year=2003). Independent results: [official Nitto ATP Finals 1970–1999 heritage](https://www.nittoatpfinals.com/en/heritage/results-1970-1999), [ATP Finals 2000–2025 heritage](https://www.nittoatpfinals.com/en/heritage/results-2000-2023), and [ITF Tennis Masters Cup 2003](https://www.itftennis.com/en/tournament/tennis-masters-cup/usa/2003/m-mc-usa-01a-2003/draws-and-results/). ATP's own [singles tournament history](https://www.atptour.com/-/media/08887c4b3be347dd8a2d701c23fcd587.pdf) also documents broader 2003 dates.

**Important:** Even the two official sources for 2003 can refer to a singles-competition window and broader Finals event/tournament dates; neither establishes a complete match-by-match schedule. The seven archived source ranges and alternative ranges remain independently inspectable and cannot be silently normalized to a made-up seven-day pattern.

## Mechanical implementation and safety

- Year source state `verified_atp_results_archive_with_separate_finals_historical_window` identifies the explicitly reconciled seven years; all 37 have canonical ATP archive dates, while **2026 remains `provisional_published_schedule`**.
- Original audited `calendar_backfill_YYYY_candidates_v1.json` ledgers remain unchanged; year-effective Category/Series IDs, historical hosts, non-held and cross-year dates are not guessed or relabelled to future 2026 cities.
- `scripts/build_atp_historical_calendar.py` builds source-only Calendar deterministically. Its canonical serialisation is sorted-key **compact JSON**, to keep the 2,444-entity snapshot within reliable Git transport limits while preserving every field. Category and Series source packages are unaffected.
- `scripts/promote_atp_calendar_candidate.py --check --year YYYY` is idempotent for each of the seven years. It verifies exact candidate parity and independently pinned official Finals alternative windows, without writing or merging. `--write` is not necessary after canonical import.
- All 2,407 source-dated original played Tour parent event identities remain **non-playable**; FIFA/FAX Run clock and Weeks, tournament results, rank points, save history and explicit Save behavior are unchanged.
- Reproducibility:
  ```bash
  python scripts/audit_atp_calendar_full_roster.py --check
  python scripts/build_atp_historical_calendar.py --check
  python -m pytest -q tests/domain/test_atp_calendar_finals_date_window_policy.py
  ```

## Remaining release qualifications

**2026 is provisional**, not yet certified as a final year-end results ledger. The parent Category/Series inventory is an *evidence-bounded original ATP Tour source roster*, with some independent historical tennis event licence succession still not fully documented. This date-policy import establishes source-time consistency and preserves alternate history, **not comprehensive independent licence lineage**. The PR remains stacked as Draft on parent Draft #1731; the owner alone merges both.

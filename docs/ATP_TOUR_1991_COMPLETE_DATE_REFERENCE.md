# ATP Tour 1991 — complete historical source dates (76/76)

**Canonical reference-only Calendar**, sourced from the [1991 official ATP results archive](https://www.atptour.com/en/scores/results-archive?year=1991), cross-checked against [1991 Frankfurt World Championships in official ATP Finals history](https://www.nittoatpfinals.com/en/heritage/results-1970-1999): **12–17 November 1991**. The two official sources agree for this year.

All **76** year-effective original ATP Tour and singles World Championships parent Series have individually recorded inclusive historical date intervals in `calendar_backfill_1991_candidates_v1.json` and `calendar_dates_v1.json`.

- 31 December **1990**–6 January 1991: **Adelaide** (`brisbane` lineage) and **Wellington** (`wellington_1992`), both correctly ISO **1991/W01**.
- Two **Guarujá** events were distinct: 4–10 February (`maceio_1992`) and 21–27 October (`guaruja_1992`).
- Two **Sydney**, two **Tokyo**, two **Stuttgart** editions; distinct Chicago, Orlando, Berlin, Brasília and Birmingham indoor entities; original **Geneva** (`cologne_1992_clay` parent), and September **Brisbane** (`brisbane_autumn_1992`).
- Original contemporary ATP World Series, Championship Series and Single-Week tiers were preserved; later ATP 250/500/1000 labels were not backfilled.
- Four Grand Slams, World Team Cup, Davis Cup, Grand Slam Cup, Challengers and separate doubles championships are outside this main-tour source.

Run `python -m scripts.audit_atp_calendar_backfill --year 1991 --json`, `python -m scripts.promote_atp_calendar_candidate --check --year 1991`, `python -m scripts.build_atp_historical_calendar --check` and `python -m pytest -q tests/domain/test_atp_calendar_backfill_1991.py`. The read-only candidate audit should show 76 already canonical overlaps, and the `--check` promoter must confirm exact idempotence. No duplication or implicit Save.

After 1991: **1,892 dated original Tour occurrences + 37 annual ledgers = 1,929 Calendar entities**, **30/37** ATP years dated. 1992–1993, 1997–1999 and 2003 Finals date-window conflicts remain open; 1990 undated; 2026 provisional. Historical parent Series do not independently certify full legal licence lineage. This is **not** a playable tennis/FAX/squash Calendar or sporting policy. Owner alone merges.

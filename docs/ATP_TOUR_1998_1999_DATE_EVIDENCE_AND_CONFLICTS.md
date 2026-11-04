# ATP Tour historical 1998–1999 source-date backfill

This is a **read-only evidence ledger** for two complete historical parent
Category/Series rosters, not a canonical Calendar import. All event intervals
are transcribed from the original ATP Tour played-results archives:

- [ATP 1998 official results archive](https://www.atptour.com/en/scores/results-archive?year=1998)
- [ATP 1999 official results archive](https://www.atptour.com/en/scores/results-archive?year=1999)
- [ATP Finals historical results, 1970–1999](https://www.nittoatpfinals.com/en/heritage/results-1970-1999)

| Season | Original parent Series | Dated candidate rows | Canonical dated rows |
| --- | ---: | ---: | ---: |
| 1998 | 74 | 74 | 0 |
| 1999 | 66 | 66 | 0 |

## Historical identity safeguards

- The original 1998 ATP archive includes **Antwerp**, **Split**, **Bologna**,
  **New Haven** and **Ostrava**. These remain separately named original Series
  where the parent source has them, not modern renamed tournaments.
- Original 1999 **Prague**, **Meran**, **Boston** and **Singapore** event IDs
  are retained.
- The 1998/1999 **Bournemouth** grass/appropriate historic event is linked to
  `brighton_2000` only through the *existing* parent Series model; the
  source-host is never silently rewritten to modern Brighton.
- 1998 **Coral Springs** remains explicitly attributed to the parent
  `delray_beach` Series, 1998 **Mexico City** to `acapulco`, and old
  **London-1** to `sofia`. These Series IDs are reference identities,
  **not independent certificates of venue transfer or licence sale**.
- In both years there are **two different Stuttgart events**: clay
  `stuttgart` and indoor Masters `stuttgart_indoor_masters`. ATP website
  current-category labels must never overwrite contemporaneous ATP tiers.
- The 1998 Amsterdam archive says **3–8 August**, not 3–9 August. Candidate
  dates preserve the specific Saturday ending.
- Grand Slams, team events and the historical Grand Slam Cup are **excluded**.
  The ATP-operated year-end World Championship is included.

## Unresolved official date-definition discrepancies — blocks

The annual results archive and ATP Finals official history disagree on the
*starting day* for the year-end tournament:

| Season | Annual ATP results archive interval | Official ATP Finals historical interval |
| --- | --- | --- |
| 1998 | **23–29 November** | **24–29 November** |
| 1999 | **22–28 November** | **23–28 November** |

Whether this is a difference between tournament calendar window and first
played competition has **not been established by these source records**.
Keep the archive interval attributed to its source in candidate JSON; do not
present it as a fully adjudicated universal event start. The official source
conflicts are encoded in `PENDING_CONFLICTS` and cause
`scripts/promote_atp_calendar_candidate.py` to **fail closed**.

## Reproducible tests

```bash
python scripts/audit_atp_calendar_backfill.py --year 1998 --json
python scripts/audit_atp_calendar_backfill.py --year 1999 --json
python -m pytest -q tests/domain/test_atp_calendar_backfill_1998.py
python -m pytest -q tests/domain/test_atp_calendar_backfill_1999.py
python scripts/promote_atp_calendar_candidate.py --check --year 1998
python scripts/promote_atp_calendar_candidate.py --check --year 1999
```

The last two commands **must currently fail with the explicitly disclosed
historical evidence conflict**. Structural membership audit passing only
proves exact alignment with the pre-existing parent roster, not an exhaustive
external event census, competition-date convention, or independent licence
lineage. Canonical 1998/1999 date coverage remains `undated` until reviewed.

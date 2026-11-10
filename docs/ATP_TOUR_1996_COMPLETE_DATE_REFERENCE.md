# ATP Tour 1996 — complete original date-source cohort and canonical import

## Exact source

The [official ATP 1996 played-results archive](https://www.atptour.com/en/scores/results-archive?year=1996) provides the original event dates and host names for **78 year-effective original-tour source Series** (ATP World Series / Championship Series / Championship Series Single Week plus ATP-operated World Championship). The `calendar_backfill_1996_candidates_v1.json` record preserves that evidence and historical host, while canonical `calendar_dates_v1.json` and generated `calendar.json` contain the 78 date references and exact ISO labels.

The [independent official ATP Finals historical results (1996)](https://www.nittoatpfinals.com/en/heritage/results-1970-1999) agree with the annual ATP archive on the original year-end World Championship in **Hanover, 19–24 November 1996**. Unlike 1997–1999, there is no known conflicting official starting-day convention for this year. Nothing has been invented to fill missing weeks.

## Important historical host/series distinctions

- **Jakarta, 8–14 January** is a distinct `jakarta_1996` source Series; **Zagreb**, 29 January–4 February, maps to the source Series `split_1998`, and Shanghai to `bangalore_2008`. These names describe *the original hosting locations* without independently establishing legal sale or licence chains.
- **New Delhi**, 8–14 April, uses source identity `hong_kong`, while *the separate played Hong Kong event* that same week uses `hong_kong_salem_2002`. The two cannot be merged as one event.
- Original **Bermuda**, **Seoul**, **Porto** and **Tel Aviv** are individually represented by their distinct series IDs.
- **Pinehurst**, 6–12 May, appears under the parent `houston` Series; **Coral Springs**, 13–19 May, under `delray_beach`.
- Original **Rosmalen** (today's `s_hertogenbosch` series identity) was 10–16 June. Original **Bologna** and **Porto** retain their original host and timing.
- **Stuttgart outdoor clay**, 15–21 July, is distinct from **Stuttgart Indoor Masters**, 21–27 October. Their contemporary categories must not be overwritten by modern Masters 1000/500/250 labels.
- The official ATP archive gives **St. Petersburg 18–31 March**; the sourced two-week interval and its two ISO-week labels are preserved exactly.
- **Atlanta Olympic tournament** (22–28 July), Grand Slams, Davis Cup, World Team Cup and Grand Slam Cup are intentionally out of the original ATP Tour main-tier + Finals Package.

## Quality and non-playability boundaries

- 78/78 parent year-effective Series IDs, no duplicate or missing IDs.
- Each source ID and year-effective Category has been cross-checked against the parent Series history.
- Prior to committing, rebuilding the old 1,573-date Calendar independently reproduced its serialized snapshot exactly. The 1996 import produced 1,651 date occurrences and **1,688 Calendar entities** (including the unchanged 37-year coverage ledger), without altering any other historical-year occurrence entity.
- The whole Package is a **source-only reference**; no playable FAX match, calendar event, ATP ranking score, match result or automated Run Save is created.
- The parent's Series history is not an independently verified legal tournament licence transfer record. This source proves reported dates and host labels, not a legal lineage.
- The 2026 source calendar remains provisional.

## Reproducibility

```bash
python -m scripts.audit_atp_calendar_backfill --year 1996 --json
python -m scripts.promote_atp_calendar_candidate --check --year 1996
python -m scripts.build_atp_historical_calendar --check
python -m pytest -q tests/domain/test_atp_calendar_backfill_1996.py
```

The first command reports the original roster match and existing canonical overlap separately; the second must be **read-only and idempotent**. Hosted CI results must be checked for the final PR head before any merge decision.

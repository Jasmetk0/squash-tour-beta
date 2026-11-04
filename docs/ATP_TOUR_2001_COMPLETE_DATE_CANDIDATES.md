# ATP Tour 2001 — full dated reference-candidate roster

**Status (4 November 2026):** The original [ATP Tour 2001 official results archive](https://www.atptour.com/en/scores/results-archive?year=2001) has been transcribed into **65 separately dated source-identity candidates**: `config/reference_packages/atp_tour_1990_2026/calendar_backfill_2001_candidates_v1.json`. The 2001 parent Category/Series roster also contains 65 IDs. This is a **complete match against the existing reference roster**, not proof of a fully independently audited ATP played-event census or legal Series licence continuity.

## Historically significant details

- The 2001 annual schedule begins **1 January 2001** with Doha, Chennai and Adelaide (ISO 2001/W01).
- Bogotá (**28 January – 3 February**) and Milan (**29 January – 4 February**) were contemporaneous original events; not later host substitutions.
- Both the original Stuttgart clay ATP event (**16–22 July**) and the distinct indoor Stuttgart Masters (**15–21 October**) are represented by separate `stuttgart` and `stuttgart_indoor_masters` IDs. They must not be conflated or relabelled with current ATP tiers.
- The 2001 **Amsterdam** edition is attributed to parent `belgrade_2012` historical Series; **Sopot** to `warsaw_2008`; **Indianapolis** to `atlanta` and the separate spring **Atlanta** event to `atlanta_verizon_2001`. Those are source-level historical licence identity associations, not independently certified legal transfers.
- 2001 Canadian Masters was held in **Montréal, 30 July – 5 August**.
- The 2001 Tennis Masters Cup is dated **12–18 November** in the year archive. No match scores are imported.
- Team tournaments, Grand Slams and Challenger events are outside the ATP original-tier/Finals reference boundary.

## Reproducible validation

```bash
python scripts/audit_atp_calendar_backfill.py --year 2001 --json
python -m pytest -q tests/domain/test_atp_calendar_backfill_2001.py
python -m pytest -q tests/domain/test_atp_calendar_promotion.py
python scripts/promote_atp_calendar_candidate.py --check --year 2001
```

Full canonical promotion still requires running `--write --year 2001`, regenerating and committing **both** `calendar_dates_v1.json` and `calendar.json`, checking the resulting source fingerprint and host CI and reviewing unresolved historical legal continuity. Those files were **not** updated as part of these staged data edits; do not describe 2001 as playable or already installed.

Parent #1731 and stacked child #1741 remain Draft, owner-only merge.


## Canonical import — 4 November 2026

All **65** 2001 original-tier source candidates have now been promoted into
`calendar_dates_v1.json` and generated `calendar.json` on the existing
Calendar Draft branch. The resulting 2001 reference events are **not playable
editions** and the 2001 Series lineage is **not independently legally
certified**. The reproducible read-only check is:

```bash
python scripts/promote_atp_calendar_candidate.py --check --year 2001
python scripts/build_atp_historical_calendar.py --check
```

The preceding staged-only promotion checklist is a historical record
written before this import; the above canonical status supersedes it.

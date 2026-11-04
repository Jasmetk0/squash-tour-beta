# ATP Earth Week Mapping V1 — source-only candidate, 4 November 2026

**Status:** implemented as a **read-only, deterministic projection and audit**, not as an approved playable tournament calendar. The user discussed the approach for mapping original ATP Tour reference events to 52 abstract Earth weeks. The existing authoritative Master/constitution still controls simulation. This candidate introduces **no new authoritative Match, Entry, Ranking, Edition, Simulation Slot, Run state, historical revision or Save behavior**.

**Dependencies:** stacked on Category+Series Draft PR #1731 and Calendar Draft PR #1741. Parent source: config/reference_packages/atp_tour_1990_2026/calendar_dates_v1.json and its exact source dates. No files in the parent Drafts are changed here.

## Why days remain source-only

The core Run Calendar has Year Week 1..W and Season Week 1..W, but not civil days. Default Earth W=52, FAX W=61; ISO week 53 is not a valid Earth Run week. A real ATP event can occupy partial civil weeks, end on any weekday, or cross civil/ISO years. A direct assignment of every touched ISO week to an entire simulation week would artificially lengthen many eight-day Sunday-to-Sunday tournaments.

This projection is explicitly **Earth W52 only**. No attempt is made to map ATP source weeks to a FAX W61 Run, to invent seven Run days, or to replace the original date windows with synthesized dates.

## Deterministic proposed week rules

1. **5–8 inclusive civil days:** assign **one** W52 label: the ISO calendar year/week of the officially published source **end date**. Other touched ISO weeks remain in source_iso_weeks; a shortened boundary is flagged.
2. **9–14 inclusive civil days and two ISO weeks:** preserve both ISO week labels. There are 79 events under the current source.
3. **9–14 inclusive civil days and three ISO weeks:** preserve all three labels **as a review-only mapping**, not an automatic 3-week playable Edition. There are three cases, including the 2025/2026 Canadian Open and 2025 Cincinnati. The sports-calendar duration still needs an explicit integration rule.
4. **Cross-year source:** preserve original ATP season identity and both original civil dates. Any compressed single-week event uses the end-year ISO week. The historical record remains intact.
5. **Source ISO W53:** explicit, versioned special case. Brisbane 2010 starts Sunday 3 January 2010 (ISO 2009/W53) and finishes Sunday 10 January (ISO 2010/W01). Its proposed one-week label is 2010/W01; the 2009/W53 source week is retained separately, never clamped to 2009/W52. Any new W53 occurrence **fails closed** pending source-specific review.
6. **Non-Saturday/Sunday finishes** and **short Monday finishes whose main seven days fall in the prior ISO week** receive flags. The initial end-week convention does *not* certify the realistic round distribution, calendar conflicts or player availability.
7. **2026 remains provisional** (provisional_published_schedule). None of the mapped dates is a claim of a completed 2026 ATP result.

The helper supports only source intervals of 5–14 days because those are the reviewed lengths in the currently frozen parent dataset. New length patterns, unknown W53 behavior or changes to aggregate source counts deliberately fail closed rather than silently invent future rules.

## Actual counts from the parent calendar source

| Metric | Occurrences |
|---|---:|
| Original ATP Tour source occurrences 1990–2026 | 2,407 |
| Originally touching exactly 1 ISO week | 2,075 |
| Originally touching exactly 2 ISO weeks | 329 |
| Originally touching exactly 3 ISO weeks | 3 |
| V1 one-week projections | 2,325 |
| V1 two-week projections | 79 |
| V1 three-week *review-only* projections | 3 |
| Original intervals crossing an ISO year boundary | 10 |
| Original intervals touching an ISO W53 | 1 |
| Non-weekend original event end dates | 29 |

The 2,325 one-week results include 250 brief intervals that touch two ISO weeks but are intentionally compressed under the proposed rule. Among them, some Monday finishes are tagged because the rule assigns the last partial week rather than the majority-play week. This must be independently reviewed before producing sporting slots, especially when event dates overlap.

**Numerical completeness does not equal historical certification.** Category/Series licence lineage remains incompletely sourced in the parent Draft, seven Finals year-date concepts are separately evidenced in the Calendar Draft, and the original 2026 published calendar is provisional.

## Audit and acceptance

Read-only from the repository root:

    python scripts/audit_atp_earth_week_mapping_v1.py --check
    python scripts/audit_atp_earth_week_mapping_v1.py --json
    python -m pytest -q tests/domain/test_atp_earth_week_mapping_v1.py

The --json command prints the complete machine-readable report (one mapping per year/Series) without changing files. The report contains a deterministic source digest, original dates and original ISO weeks, chosen W52 labels, rule, flags, season provenance and an explicit sporting_schedule_installed=false boundary. The --check command validates the expected current-source totals.

## Required independent follow-up before playable installation

- Decide the actual **sporting occupancy** of the three 12-day, three-ISO-week cases. The reported three-week projection is not a source assertion that three full weeks of matches were played.
- Review short events ending Monday or on other weekdays: using only the finishing ISO week can move seven real playing days into a different week. Any sporting import must state whether completion week, majority week or round-specific allocations have authority.
- Validate conflicts, rest, multi-event Entry and Simulation Slot ordering on an actual Run Calendar; a week label alone cannot prove player availability.
- Handle ranking/season-transition boundaries and historical ISO anomalies as separately checked application rules, never as a property of ATP reference dates.
- Keep original source Package snapshots immutable after explicit Run Save. Do not merge or rewrite the parent Drafts implicitly.

**No Master update, no automatic Run import and no release certification.**

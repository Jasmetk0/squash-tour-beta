# ATP Earth Week Mapping V1 — source-only candidate, 4 November 2026

**Status:** implemented as a **read-only, deterministic projection and audit**, not as an approved playable tournament calendar. The user discussed the approach for mapping original ATP Tour reference events to 52 abstract Earth weeks. The existing authoritative Master/constitution still controls simulation. This candidate introduces **no new authoritative Match, Entry, Ranking, Edition, Simulation Slot, Run state, historical revision or Save behavior**.

**Dependencies:** stacked on Category+Series Draft PR #1731 and Calendar Draft PR #1741. Parent source: config/reference_packages/atp_tour_1990_2026/calendar_dates_v1.json and its exact source dates. No files in the parent Drafts are changed here.

## Why days remain source-only

The core Run Calendar has Year Week 1..W and Season Week 1..W, but not civil days. Default Earth W=52, FAX W=61; ISO week 53 is not a valid Earth Run week. A real ATP event can occupy partial civil weeks, end on any weekday, or cross civil/ISO years. A direct assignment of every touched ISO week to an entire simulation week would artificially lengthen many eight-day Sunday-to-Sunday tournaments.

This projection is explicitly **Earth W52 only**. No attempt is made to map ATP source weeks to a FAX W61 Run, to invent seven Run days, or to replace the original date windows with synthesized dates.

## Deterministic proposed week rules

1. **5–8 inclusive civil days:** assign **one** W52 label: the ISO year/week containing the **largest number of source-event calendar days**. A tie fails closed, never guessed. The published end-date ISO week is retained separately in source_finish_iso_week, along with the original dates and per-week day counts. A shortened boundary and any week shift are flagged.
2. **9–14 inclusive civil days and two ISO weeks:** preserve both ISO week labels. There are 79 events under the current source.
3. **9–14 inclusive civil days and three ISO weeks:** preserve all three labels **as a review-only mapping**, not an automatic 3-week playable Edition. There are three cases, including the 2025/2026 Canadian Open and 2025 Cincinnati. The sports-calendar duration still needs an explicit integration rule.
4. **Cross-year source:** preserve original ATP season identity and both original civil dates. A compressed single-week event uses its majority-week label. The source-year relationship must validate; otherwise the audit fails rather than silently shifting seasons. The historical record remains intact.
5. **Source ISO W53:** explicit, versioned special case. Brisbane 2010 starts Sunday 3 January 2010 (ISO 2009/W53) and finishes Sunday 10 January (ISO 2010/W01). Its proposed one-week label is 2010/W01; the 2009/W53 source week is retained separately, never clamped to 2009/W52. Any new W53 occurrence **fails closed** pending source-specific review.
6. **Non-Saturday/Sunday finishes** and **short events assigned to the week before the recorded finish week** receive flags. The majority-week label does *not* certify the realistic round distribution, calendar conflicts or player availability. This corrects 26 short-event assignments previously based only on the closing week.
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
| Short cross-week events assigned to majority week before finish | 26 |
| Distinct mapped Year/Week labels containing at least one event | 1,284 |
| Maximum simultaneous source tournaments in one mapped week | 5 |

The 2,325 one-week results include 250 brief intervals that touch two ISO weeks but are intentionally compressed under the proposed rule. **26 of those 250** now select the *earlier* majority-play week instead of the mostly empty closing week; this includes eight short events ending on Monday. Every original finish week is preserved for future ranking/transition review. The projection occupies **1,284 distinct year/weeks**; concurrent source tournaments reach a maximum of **five in one mapped week**. Concurrent events are not inherently invalid or evidence that the same player would play twice. The true player/round conflict checks must occur at sporting import.

**Numerical completeness does not equal historical certification.** Category/Series licence lineage remains incompletely sourced in the parent Draft, seven Finals year-date concepts are separately evidenced in the Calendar Draft, and the original 2026 published calendar is provisional.

## Audit and acceptance

Read-only from the repository root:

    python scripts/audit_atp_earth_week_mapping_v1.py --check
    python scripts/audit_atp_earth_week_mapping_v1.py --json
    python -m pytest -q tests/domain/test_atp_earth_week_mapping_v1.py

The --json command prints the complete machine-readable report (one mapping per year/Series) without changing files. The report contains a deterministic source digest, original dates and original ISO weeks, chosen W52 labels, rule, flags, season provenance and an explicit sporting_schedule_installed=false boundary. The --check command validates the expected current-source totals.

## Explicit Run Calendar bridge (read-only native-week preview)

The pure application adapter src/beta_engine/application/atp_earth_run_calendar_preview.py
takes a **supplied explicit RunCalendar**, validates the source-only 2,407-event
projection and produces native RunCalendarPosition rows with season_index,
season_week, calendar_year, year_week and canonical elapsed-week ordinal. It
round-trips each ordinal and refuses noncontiguous spans, mismatched season
identities or weeks outside the requested Run's actual horizon. This is a
real mapping to the *native clock contract*, **not** a DB-backed actual Run
command, authenticated state write, or playable Edition.

A Run may have an offset other than 1. The adapter uses calendar_to_season
rather than assuming ISO Wxx equals Season Week xx. It requires an explicit
current-schema 52-week Run clock. A legacy/FAX 61-week Run, nonexistent year,
invalid chosen year, incomplete 37-year source, or out-of-horizon week is
rejected rather than silently clamped. A subset can be selected with explicit
year(s); only those years must fit the Run horizon.

Reproducible read-only CLI example (from an environment with project deps):

    python scripts/preview_atp_earth_run_calendar_v1.py
    python scripts/preview_atp_earth_run_calendar_v1.py --year 2025 --run-start-year 2025 --run-seasons 2 --json
    python scripts/preview_atp_earth_run_calendar_v1.py --year 1990 --run-start-year 1989 --run-seasons 40 --run-offset 37
    python -m pytest -q tests/application/test_atp_earth_run_calendar_preview.py

The CLI constructs an **illustrative clock from passed args**, not a real
persisted Run. The application's preview is deterministic, carries an input
fingerprint and explicit run metadata, lists all projected positions and
source-exception flags, summarizes week overlap, and always states
sporting_ready=false / no_sporting_install=true.

The preview audit of the *full* 1990–2026 Earth W52 frame expects 2,407
occurrences, 1,284 occupied week positions and maximum five source tournaments
in one week. It preserves all 26 majority-week-vs-finish exceptions and three
source intervals spanning three ISO weeks. Those 3-week projections are **not**
automatically scheduled as three full weeks of matches.

**Boundaries that remain open:** a live saved Run adapter, per-Edition sporting
duration, Entry/application/announcement windows, match/round ordering, common
Simulation Slot simultaneity, rest, ranking closure semantics, and explicit
snapshot/Preview/Confirm/Save ownership. This PR does not invent those
mechanics from date metadata.

## Required independent follow-up before playable installation

- Decide the actual **sporting occupancy** of the three 12-day, three-ISO-week cases. The reported three-week projection is not a source assertion that three full weeks of matches were played.
- Inspect the 26 short events where the majority week is before the recorded finish week. This mapping is more faithful to occupied days but does not choose a source-match completion/ranking publication week. Any sporting import must distinguish majority-week occupancy from completion and from round-specific Slot authority.
- Validate conflicts, rest, multi-event Entry and Simulation Slot ordering on an actual Run Calendar; a week label alone cannot prove player availability.
- Handle ranking/season-transition boundaries and historical ISO anomalies as separately checked application rules, never as a property of ATP reference dates.
- Keep original source Package snapshots immutable after explicit Run Save. Do not merge or rewrite the parent Drafts implicitly.

**No Master update, no automatic Run import and no release certification.**

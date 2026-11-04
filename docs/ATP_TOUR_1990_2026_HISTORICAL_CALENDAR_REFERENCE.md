# 🎾 ATP Tour Historical Calendar Reference — 1990–2026

> **STATUS: incremental Draft, NOT historical date complete.** Historical
> Category+Series parent [PR #1731](https://github.com/Jasmetk0/squash-tour-beta/pull/1731)
> must merge before this [stacked Calendar PR #1741](https://github.com/Jasmetk0/squash-tour-beta/pull/1741)
> is retargeted to `buuk`. Neither PR is automatically merged.

## Purpose and non-goals

A **reference-only** `Calendar` Package that connects real exact ATP main-tour
event dates to previously sourced stable Series IDs and original Category years.

It **does not** create playable FAX/squash `SeasonCalendarEvent`,
`CalendarTourEdition`, ATP matches, rankings, prizes, Calendar mutation, or
a native tournament schedule. Its `tennis.calendar.occurrence.reference.v1`
kind and dedicated scope are intentionally opaque to FAX sporting consumers.

The three-child Setup is `atp_tour_1990_2026_calendar_reference_setup`
with Category (11), Series (164) and Calendar (984 entities at the current
source revision, comprising 37 provenance-coverage entities and 947 dated
occurrences). The whole source is fingerprinted; Read-only Preview and
all-or-nothing Confirm use existing Run Package CAS; **Save remains explicit**.

## 2011 archive coverage

All **61 named 2011 historical main-tour and ATP Finals source Series** are dated to their original [ATP 2011 results archive](https://www.atptour.com/en/scores/results-archive?year=2011). Separate contemporaneous editions include San José ATP 250 (`dallas`) and Memphis ATP 500 (`rio`); spring Belgrade (`belgrade_2012`) versus autumn Bucharest (`belgrade_clay_2021`); Johannesburg (`johannesburg_2011`), Santiago (`cordoba`), Costa do Sauípe (`sao_paulo`), Los Angeles (`los_cabos`), Kuala Lumpur (`chengdu`), Valencia (`brussels`) and London ATP Finals. Brisbane opened **2 Jan 2011 in ISO 2010/W52** and ended ISO 2011/W01. The ATP-listed World Team Cup and Grand Slam competitions were not imported. Historical parent roster explicitly does not claim to census every ATP event beyond its source series. Event start and end are the archive's displayed original dates, not copied from a newer season.

## 2012 archive coverage

All 61 named 2012 ATP main Tour and ATP Finals reference Series are dated against the [2012 official ATP archive](https://www.atptour.com/en/scores/results-archive?year=2012), retaining separate San José ATP 250 (`dallas`) versus Memphis ATP 500 (`rio`), plus Belgrade ATP 250 (`belgrade_2012`) versus Bucharest (`belgrade_clay_2021`), Nice (`lyon_old`), Los Angeles (`los_cabos`) and Valencia (`brussels`). The **2012 London Olympics** and World Team Cup in Düsseldorf were **not ATP Tour ranking tiers and are excluded**. Brisbane on 1 Jan 2012 spans ISO 2011/W52 and 2012/W01 rather than simply 2012/W01.

## 2013 archive coverage

All 61 source Series for ATP 2013 are independently dated from the [official year-specific ATP archive](https://www.atptour.com/en/scores/results-archive?year=2013). Important **two distinct 2013 US licences**: San José ATP 250 uses source Series `dallas`, while Memphis ATP 500 uses source Series `rio`; later destinations are not substituted for the actual 2013 host. Other historical sites: Viña del Mar (`cordoba`), Düsseldorf (`geneva`), Nice (`lyon_old`), Kuala Lumpur (`chengdu`), Bangkok (`bangkok_2013`) and Valencia (`brussels`). Brisbane begins 30 Dec 2012 and covers ISO 2012/W52 and 2013/W01. Davis Cup and Grand Slams are not included.

## 2014 archive coverage

All 60 historic 2014 ATP Tour / ATP Finals source Series have original exact dated event intervals from the [ATP 2014 official played archive](https://www.atptour.com/en/scores/results-archive?year=2014). Historical host identities are retained: Viña del Mar (`cordoba`), Düsseldorf (`geneva`), Nice (`lyon_old`), 2014 July clay-court Stuttgart, Bogotá (`los_cabos`), Kuala Lumpur (`chengdu`) and Valencia (`brussels`). Brisbane starts 29 December 2013 in ISO 2013/W52; Doha and Chennai start 30 December 2013 in ISO 2014/W01. Grand Slams and team competitions are explicitly excluded.

## 2015 archive coverage

All 62 ATP Tour and ATP Finals source Series dated against [ATP's official played 2015 archive](https://www.atptour.com/en/scores/results-archive?year=2015), including historical original hosts: Zagreb (`sofia`), Casablanca (`marrakech`), Bucharest (`belgrade_clay_2021`), Nottingham (`eastbourne`), Nice (`lyon_old`), Bogotá (`los_cabos`), Kuala Lumpur (`chengdu`), and Valencia (`brussels`). No Grand Slams, team events or later Next Gen events were added. Dates are contemporaneous, not 2026 defaults.

## 2016 archive coverage

The 62 named original 2016 ATP Tour / ATP Finals source Series have been dated from [ATP's 2016 original results archive](https://www.atptour.com/en/scores/results-archive?year=2016). Original host aliases are preserved: Chennai (`hong_kong` lineage), Quito (`cordoba`), Memphis (`dallas`), Bucharest (`belgrade_clay_2021`), Nice (`lyon_old`), and Nottingham (`eastbourne`). 2016 Olympic tennis is not an ATP Tour tier; Next Gen ATP Finals did not begin until 2017. All date intervals are real dated source spans, not a port of 2025 scheduling.

## 2017 archive coverage

All 64 played 2017 ATP Tour / ATP-operated Finals source Series have sourced exact dates from the [2017 ATP results archive](https://www.atptour.com/en/scores/results-archive?year=2017), preserving contemporaneous Chennai (`hong_kong` lineage), Quito (`cordoba`), Memphis (`dallas`), Budapest (`belgrade_clay_2021`), and separate Marseille / outdoor Lyon events. Brisbane on 1 Jan 2017 starts in ISO **2016/W52** even though the tournament year is 2017; the correct two ISO weeks are retained. The first Next Gen Finals are dated 7–11 Nov 2017. No Grand Slam or team events were imported.

## 2018 archive coverage

All 64 main ATP Tour and ATP-operated Finals source Series have individually dated events from the original [2018 ATP results archive](https://www.atptour.com/en/scores/results-archive?year=2018), *not* extrapolated 2019 week positions. 2018 source IDs for Quito (`cordoba`), Pune (`hong_kong`), Budapest (`belgrade_clay_2021`), Marseille (`lyon`), distinct clay Lyon (`lyon_old`), Shenzhen (`shenzhen_2018`) and Antwerp (`brussels`) retain the licence-lineage source IDs rather than misrepresenting the historical cities. Brisbane crosses 2017/W52–2018/W01. Grand Slams and team events were excluded from the 2018 official archive.

## 2019 archive coverage

All 63 named 2019 source Series are now independently dated from the ATP
2019 played-results archive, including Doha/Brisbane/Pune starting on
31 December **2018**, which belong to ISO **2019/W01**. Former Budapest
(`belgrade_clay_2021`), Pune (`hong_kong`), Zhuhai (`hangzhou`) and New York
(`dallas`) are linked to their actual 2019 venue contexts without
manufacturing extra licences. Grand Slams and team events remain excluded.

## 2020 archive coverage

All 29 actually played 2020 main ATP Tour / Finals Series are dated from
ATP's year-specific results archive. Twelve historical roster memberships
that were **not played** due to the 2020 COVID disruption remain explicitly
not held: no fake March Indian Wells/Miami/Madrid, no cancelled European grass
or China events, no Next Gen Finals. Cincinnati was held in New York from
22–29 August, Rome 14–21 September, and two Cologne editions and Sardinia
ran as exceptional autumn events. All results remain unimported.

## 2021 archive coverage

All 58 actually held 2021 ATP Tour/Finals Series are dated from the ATP
results archive; seven Series with historical membership but no played
edition remain explicitly not held. The pandemic-displaced Indian Wells
occurred **7–17 October** instead of its normal spring dates, Delray Beach
was held **7–13 January**, and the two Belgrade and two Melbourne editions
are kept separate. No cancelled tournament was assigned a fabricated date.

## 2022 archive coverage

All 65 actually held 2022 historical source Series are independently dated
from the official ATP archive. The four not-held China events (Beijing,
Chengdu, Zhuhai licence and Shanghai) remain in the annual historical
membership ledger as **not held**, and do not acquire fabricated event dates.
The played 2022 Belgrade edition maps to the later Banja Luka licence source
ID; Pune and Astana retain historical licence identities rather than later
host labels. The 2022 season contains 69 source memberships, of which
65 were played and four were expressly not held.

## 2023 archive coverage

All 62 named 2023 ATP main-tour/Finals Series are now individually dated from
the ATP official played-results archive. The two separate Adelaide editions
retain their separate Series IDs; historical source alias `hong_kong` denotes
Pune, `hangzhou` denotes Zhuhai, `almaty` denotes Astana, and `lyon` denotes
Marseille in the 2023 licence lineage. These are original 2023 venues, not
the later host names. Excluded Grand Slams, Olympic and team events stay
excluded. Source dates are not claims of match scores.

## 2024 archive coverage

All 62 known 2024 main ATP Tour reference Series now have source-linked
start/end dates and ISO week spans. The existing historical Series continuity
is retained for Marseille (`lyon`), old outdoor Lyon (`lyon_old`) and
Antwerp (`brussels`). Brisbane starts in 2023/W52 and ends in 2024/W01.
Grand Slams, Olympic and team events remain out of scope.

## Current actual date coverage

| Year(s) | Source status | Dated Series | Undated |
| --- | --- | ---: | ---: |
| 1990–2010 | No independently verified per-Series dates yet | 0 | Explicit missing IDs for every year |
| 2011 | Official ATP results archive, original venues and ATP Finals | **61 / 61** | 0 |
| 2012 | Official ATP results archive, played Tour + Finals | **61 / 61** | 0 |
| 2013 | Official ATP results archive, played Tour + Finals | **61 / 61** | 0 |
| 2014 | Official ATP results archive, dated played main Tour and Finals | **60 / 60** | 0 |
| 2015 | ATP official results archive, 62 held source Series | **62 / 62** | 0 |
| 2016 | ATP official results archive, 62 held source Series | **62 / 62** | 0 |
| 2017 | ATP official results archive, complete original host dates | **64 / 64** | 0 |
| 2018 | ATP official results archive, complete original host dates | **64 / 64** | 0 |
| 2019 | Official ATP played results archive, all named Series | **63 / 63** | 0 |
| 2020 | Official ATP results archive; 29 played, 12 not held | **29 / 29 played** | 0 |
| 2021 | Official ATP results archive; 58 played, 7 not held | **58 / 58 played** | 0 |
| 2022 | Official ATP results archive; 65 played, 4 not held | **65 / 65 played** | 0 |
| 2023 | Official ATP played results archive, all named Series | **62 / 62** | 0 |
| 2024 | Official ATP played results archive, all named Series | **62 / 62** | 0 |
| 2025 | Official ATP played results archive, all named Series | **57 / 57** | 0 |
| 2026 | Official published calendar + dated finals announcement, with seven subsequent corrections from played archive | **56 / 56** | 0 named Series, **year still provisional** |

**No generic history period or week is interpreted as a tournament date.**
The parent Category/Series dataset contains 2,431 year-effective memberships;
947 unique year/Series occurrences currently have original *date* sources.
The other historical years will be sourced individually, not filled by
inventing dates or extrapolating 2025/2026 patterns.

Source links:

- [2011 official results archive](https://www.atptour.com/en/scores/results-archive?year=2011).
- [2012 official results archive](https://www.atptour.com/en/scores/results-archive?year=2012).
- [2013 official results archive](https://www.atptour.com/en/scores/results-archive?year=2013).
- [2014 official results archive](https://www.atptour.com/en/scores/results-archive?year=2014).
- [2015 official results archive](https://www.atptour.com/en/scores/results-archive?year=2015).
- [2016 official results archive](https://www.atptour.com/en/scores/results-archive?year=2016).
- [2017 official results archive](https://www.atptour.com/en/scores/results-archive?year=2017).
- [2018 official results archive](https://www.atptour.com/en/scores/results-archive?year=2018).
- [2019 official results archive](https://www.atptour.com/en/scores/results-archive?year=2019).
- [2020 official results archive](https://www.atptour.com/en/scores/results-archive?year=2020).
- [2021 official results archive](https://www.atptour.com/en/scores/results-archive?year=2021).
- [2022 official results archive](https://www.atptour.com/en/scores/results-archive?year=2022).
- [2023 official results archive](https://www.atptour.com/en/scores/results-archive?year=2023).
- [2024 official results archive](https://www.atptour.com/en/scores/results-archive?year=2024).
- [2025 official results archive](https://www.atptour.com/en/scores/results-archive?year=2025).
- [2026 official published schedule](https://www.atptour.com/en/news/what-is-the-2026-atp-tour-calendar/).
- [2026 official results archive](https://www.atptour.com/en/scores/results-archive?year=2026) for later corrections.
- [2026 Next Gen Finals venue/dates in Reggio Calabria](https://www.nextgenatpfinals.com/en/news/reggio-calabria-to-host-2026-next-gen-atp-finals).
- [2025 Marseille -> 2026 Lyon ATP-approved transfer](https://www.atptour.com/en/news/marseille-lyon-relocation).

### Crucial licensed-identity example

The source Series ID `lyon` for **2025** refers to **Marseille**, held
10–16 February, and the **2026** licensed successor in Lyon is dated
19–25 October. The *distinct* former outdoor clay ATP Lyon event ended in
2024. Never backdate the 2026 Lyon indoor name to the 2025 actual host.

### Published vs played 2026 schedule

Seven dates of already played events needed corrections relative to the
original 2026 published calendar, verified in ATP's year-specific results
archive: Brisbane starts **4 January**, Doha ends **21 February**, Dubai
ends **28 February**, Umag ends **18 July**, Kitzbühel ends **25 July**,
Los Cabos ends **1 August**, Canadian Open ends **13 August**. Each revised
entry cites the official played archive. The rest still cite the official
published 2026 schedule. Next Gen Finals 9–13 December are scheduled, not
played as of November 3. The source is `provisional_published_schedule`
until the year closes and the final played roster is re-audited.

## Exact calendar and ISO week rules

Every dated source event records:

- Exact inclusive `start_date` and `end_date` (Gregorian ISO `YYYY-MM-DD`).
- `atp_season_year`, stable source `series_id`, original `category_id`.
- Source URL, source basis, as-of date, and provenance state.
- `start_year_week`, `end_year_week` and `iso_weeks_occupied` computed
  using ISO 8601 **Monday-to-Sunday** weeks and correct ISO **week-years**.
- Actual inclusive `duration_days_inclusive`, which is not necessarily
  seven days for all events.
- Explicit `run_week_projection=not_applied_source_only`.

Example: Brisbane's **2025** edition ran 29 December 2024 – 5 January
2025. Its recorded ISO span is **2024/W52 and 2025/W01**. The corrected
**2026** Brisbane dates 4–11 January 2026 touch **2026/W01 and W02**.

`project_iso_week_to_run_w52(date,run_calendar=...)` is an **optional,
fail-closed label-only adapter**, *not* a date-respecting native Run schedule:
- Only accepts an explicitly specified **W52 RunCalendar**.
- Rejects ISO **week 53** rather than silently clamping to week 52 or 1.
- Rejects dates outside the specified Run horizon.
- Does not map ISO labels onto W61/W80, and **must not infer the physical
  week/day boundaries** of an equal-length Run year from the Gregorian year.

This keeps three concepts separate: event date, ISO year-week,
and Run's `season_index/season_week`. Native sporting import will need
its own separately reviewed date-to-Run-clock policy.

## Files

- `config/reference_packages/atp_tour_1990_2026/calendar_dates_v1.json`
  — curated authoritative event dates, separately source-linked by season.
- `config/reference_packages/atp_tour_1990_2026/calendar.json`
  — canonical deterministic Calendar Package snapshot.
- `scripts/build_atp_historical_calendar.py`
  — pure offline `--write` / `--check`; never scrapes live ATP data or
  mutates Run.
- `src/beta_engine/application/atp_historical_calendar_adapter.py`
  — fail-closed server validation of source and fixed three-child Setup.
- Backend fixed-source catalog/Preview/Confirm endpoints and CS/EN
  `/admin/packages/atp-tour-calendar-reference` admin page.
- PR-critical backend domain tests, HTTP integration (Save/restart), and
  frontend API/React route tests.

## Safe usage

1. Merge parent Category/Series PR first; change this stacked PR's base
   to `buuk` only after the parent is merged.
2. Run `python scripts/build_atp_historical_calendar.py --check`.
3. Open Packages → **ATP Calendar reference**, inspect source coverage.
4. Choose writable Run and Branch; inspect read-only Preview and conflicts.
5. Explicitly Confirm to Working Draft, then independently **Save** the
   Saved Revision. No source-only date reference may be promoted to playable
   FAX events by these steps.

The work is **not complete for 1990–2010**. Source-year coverage must be
upgraded year by year using original contemporaneous calendars and/or official
ATP results archives. 2026 final validation remains pending.

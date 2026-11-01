# ATP Tour 1990–2026: Category and Series reference Packages

**Scope:** the Association of Tennis Professionals' men's top-level **ATP Tour
since 1 January 1990**, not the entire history of men's tennis. The Category
and Series Package are optional **source-only historical references** for
Squash Engine's data-driven future, not tennis gameplay.

## Canonical boundaries

- **Inside:** ATP Tour World Series / Championship Series (1990–99),
  Masters Series / International Series Gold / International Series (2000–08),
  Masters 1000 / ATP 500 / ATP 250 (2009–26), and ATP's year-end Finals.
- **Separate ATP-operated special event:** Next Gen ATP Finals (from 2017).
  It has no standard ATP ranking points, and must never be treated as a
  normal Tour 250/500/1000 or identical to the year-end elite Finals.
- **Outside:** Grand Slam tournaments (run by the Grand Slam organisations,
  although they affect ATP rankings), ATP Challenger Tour (separate lower tour),
  ITF M15/M25, Davis Cup, United Cup and Laver Cup, and every pre-1990 circuit.
- **Temporal span:** exactly **37 seasons, 1990–2026 inclusive**. No fabricated
  pre-1990 ATP Tour seasons and no retrospective application of 2026 tiers.

The original pre-1990 and mixed-tour research candidate was deliberately removed
after the product owner narrowed the scope to the ATP Tour beginning in 1990.

## Files and hierarchy

`config/reference_packages/atp_tour_1990_2026/category.json` records
time-effective category names and year-specific 2026 headline point maxima.
Historical complete ranking point matrices **are not yet certified**, and
2026 winner points are not retroactively assigned to earlier years.

`config/reference_packages/atp_tour_1990_2026/series.json` records stable
Series IDs and temporal Category relationships. Each Series references the
exact Category source identity and entity kind. The data currently holds
**59 identities** across 2026 ATP Tour fixtures and selected older masters.
A changed venue/title/category does **not** create a new Series by itself.

`config/reference_packages/atp_tour_1990_2026/seasons_1990_2026.json`
contains an explicit 37-year **derived reference** from those two source
documents. Rebuild deterministically with:

```sh
python scripts/build_atp_tour_historical_seasons.py --write
python scripts/build_atp_tour_historical_seasons.py --check
PYTHONPATH=src pytest -q tests/domain/test_atp_tour_1990_2026_reference_packages.py
```

**Important precision:** these are not 37 proven-complete ATP Tour calendars.
Not every Series from 1990–2025 has been enumerated and assigned an
evidence-supported category for every year. `unlisted` means
**unverified/unknown**, not `did not exist`. Even a listed Series identity
does **not** assert that a played Tournament Edition existed that year:
COVID cancellations, host changes and discontinued/moved licences require
separate Edition evidence. Historical statistical completeness remains a
follow-on evidence and reconciliation gate before calling the data exact.

The 2026 source roster records nine Masters 1000, 16 ATP 500 and 29 named
ATP 250s, plus ATP Finals and Next Gen Finals. Historical 2026 calendar
announcements and later changes have included a `TBD` ATP 250 listing;
**do not mint a fabricated Series ID for an unconfirmed slot**. Reconcile
the finalized official tournament directory before promoting a current-season
roster to a certified source.

## Official ATP evidence starting points

- [ATP launch and nine top tier tournaments, 1990](https://www.atptour.com/en/news/atp-50-moments-longform-part-3)
- [ATP ranking structures 1990 and 2000](https://www.atptour.com/en/news/the-rankings-that-changed-tennis)
- [ATP Finals name and location history](https://www.nittoatpfinals.com/en/heritage/history)
- [2026 ATP Tour calendar and separate Grand Slams](https://www.atptour.com/en/news/what-is-the-2026-atp-tour-calendar)
- [2026 ATP Tour media guide](https://www.atptour.com/-/media/files/media-guide/2026/2026-atp-media-guide-full.pdf)
- [2026 calendar announcement (subsequently updated)](https://www.atptour.com/en/news/2026-atp-tour-calendar-announced)

All source links and date-effective historical labels are review evidence,
not a certification that all Series intervals, calendar years or point
tables have been independently exhaustively audited.

## Architecture and safety

Both JSON files conform to `CanonicalPackageDocument` v1: Package types
`Category` and `Series`, stable globally unique package IDs and exact
source entity references. These files live in a new reference-data
subdirectory: **there is no new production Package registry, semantic
Category/Series adapter, UI import, tennis simulation, Run/Branch mutation,
Saved Revision modification or automatic sporting consumer**.
Their existence does not make a runnable Tour in Squash Engine, and sport
rules remain squash. No code/files owned by parallel open PRs are modified.

A future separately authorised implementation can expose the source
library, validate per-Edition semantics against the Master, and allow
explicit reviewed application/Save. That is separate from this source
research task; never silently bind ATP point awards into FAX.

## Remaining verification

The included tests assert Python canonical document shape, source identity
integrity, cross-Package links, 37 derived years, the main historical
category-era transitions and the 2026 roster. A clean test run / CI
and full independent historical event audit must be confirmed separately.


## Verified 1990–2026 Masters-tier lineage and 2015/2025 upgrades

The ATP explicitly traces its nine-event Masters lineage to 1990. The
year-resolved source identifies **nine top-tier Series slots in every season**,
while the name of their Category changes across epochs. These are Series
membership **references**, not evidence that every tournament was played
without interruption. Official archival source examples:
[1990 ATP Masters archive](https://www.atptour.com/en/scores/results-archive?tournamentType=1000&year=1990),
[2002 ATP Masters archive](https://www.atptour.com/en/scores/results-archive?tournamentType=1000&year=2002),
[2022 ATP media guide with historical Masters records](https://www.atptour.com/-/media/files/media-guide/2022/2022-atp-media-guide-updated-may.pdf).

- 1990–1994: Stockholm completes the nine Series; **Essen in 1995**
  and **Stuttgart indoor 1996–2001** take its historical slot.
- 2002–2008: Madrid replaces Stuttgart indoor in the Masters tier;
  Hamburg remains a Masters through 2008.
- 2009–2026: Shanghai replaces Hamburg in the top-nine category.
- **2015:** ATP recategorized Queen's Club and Halle from ATP 250 to 500
  ([official 2015 ATP media guide](https://www.atptour.com/-/media/files/media-guide/2015/atp_media_guide_2015.pdf)).
- **2025:** ATP upgraded Dallas, Doha and Munich from 250 to 500
  ([official announcement](https://www.atptour.com/en/news/atp-500-upgrades-from-2025)).
- Source-backed ATP 500 Series totals in **2024, 2025 and 2026** are
  **13, 16 and 16**, respectively. Evidence:
  [2024 final calendar](https://www.atptour.com/-/media/files/final-2024-atp-calendar.pdf),
  [2025 announcement](https://www.atptour.com/en/news/2025-atp-tour-calendar-announced),
  [2026 calendar](https://www.atptour.com/en/news/what-is-the-2026-atp-tour-calendar).

### Cancellations are not category deletions

The cancelled Masters at Indian Wells, Miami, Monte-Carlo, Madrid, Canada
and Shanghai in **2020** retain their historical Series membership, but
are marked in `known_not_held_series_ids` rather than synthesized as
played editions. An equally explicit marker is present for 2020 Halle,
Queen's Club, Beijing and Chengdu. Sources:
[ATP's 2022 historical Masters table](https://www.atptour.com/-/media/files/media-guide/2022/2022-atp-media-guide-updated-may.pdf),
[ATP China cancellations](https://www.atptour.com/-/media/sites/atp-tour/press/press-releases/atp-announces-cancellation-of-the-2020-china-swing.pdf),
[ATP suspension through July](https://www.usopen.org/en_US/news/articles/2020-05-15/atp_wta_itf_announce_further_covid19_suspensions_into_july.html).
The generator now rejects a cancellation for a year in which the source
Series has **no category-effective interval**; this prevents claiming a
never-created tournament was cancelled (for example Hangzhou in 2020).

### Exact coverage warning

The ATP 2024 calendar contains **many more** ATP Tour events than the
currently identified 27 Series references for 2024. The same applies to
the 2025 partial registry. The top-nine historical tour tier and the
2024–2026 ATP 500 upgrades are narrowly supported, but the lower tiers
from the older decades have NOT been populated exhaustively. Never infer
a complete category/Series distribution in an earlier year from the
current incomplete count, and never conflate an `unlisted` event with
`did not exist`.

### Special one-year ATP 500 and Next Gen Finals in 2020

In addition to ordinary long-term reclassifications, the ATP temporarily
upgraded the St. Petersburg Open to **ATP 500 for its 2020 edition**, then
confirmed its return to ATP 250 in 2021. Source:
[ATP 2020 revised calendar](https://www.atptour.com/en/news/revised-atp-tour-calendar-13-august-2020),
[ATP Q4 2021 calendar](https://www.atptour.com/-/media/sites/atp-tour/press/press-releases/atp-updates-2021-q4-calendar.pdf).
This is one persistent Series identity, not separate permanent 250/500
tournaments. The ATP's 2022 relocation of that tournament licence to
Nur-Sultan is **not yet reconciled** with subsequent Series identity.
The 2014 gap in the St. Petersburg reference is preserved.

The **2020 Next Gen ATP Finals were not held**, whereas the main 2020 ATP
Finals did take place behind closed doors:
[Next Gen official history](https://www.nextgenatpfinals.com/en/heritage/history),
[ATP Finals official history](https://www.nittoatpfinals.com/en/heritage/history).
The data differentiates those outcomes rather than treating every ATP
year-end competition as identical.


## Source completeness dashboard (NOT an ATP tournament census)

These counts describe **currently documented source identities** in this
incomplete historical reference. They must never be presented as the actual
number of ATP events held. Sources may also include cancelled 2020 Series
identities while no played tournament Edition is present.

| Reference year | Defined Series-category relationships | Masters-tier identities |
| --- | ---: | ---: |
| 1990 | 10 | 9 |
| 1995 | 11 | 9 |
| 2000 | 11 | 9 |
| 2010 | 14 | 9 |
| 2020 | 18 | 9 (only 3 actually played) |
| 2024 | 27 | 9 |
| 2025 | 28 | 9 |
| 2026 | 56 | 9 |

The very low pre-2024 counts are a visible **blocker** for a complete ATP
Tour historical Category/Series library. The 2026 reference is also a
**dated, provisional roster**: the ATP's published calendar included a
non-named ATP 250 `TBD` entry, which must never be invented as a
persistent Series identity. A final ATP source inventory and event
lineage audit are required before release.

### Data licensing boundary

A public dataset mirror is not automatically a suitable authoring source.
Some Jeff Sackmann-derived historical match-data mirrors retain a
CC BY-NC-SA 4.0 licence, which does not authorize unrestricted commercial
reuse. This PR contains **no imported third-party match results**, no
bulk mirroring, and no inferred tennis player records. Any future
data-scale import must document provenance, rights, attribution,
redistribution permissions and the licence compatibility of any derivative.
Official ATP webpages cited here support bounded historical assertions,
not wholesale republishing of their content.

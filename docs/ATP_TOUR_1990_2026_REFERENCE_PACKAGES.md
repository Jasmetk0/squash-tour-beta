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
**105 identities** across 2026 ATP Tour fixtures and selected older masters.
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
Not every Series from 1990–2020 has been enumerated and assigned an
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

The ATP **2023, 2024 and 2025** Tour category rosters have now been
reconciled with official ATP results archives: **38, 38 and 30** ATP 250
events, respectively, alongside all nine Masters and **13/13/16** ATP 500s.
Earlier 1990–2020 lower tiers have NOT been populated exhaustively. The 2026
calendar remains a dated/provisional reference, not certified final. Never infer
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
| 2023 | 62 | 9 |
| 2024 | 62 | 9 |
| 2025 | 57 | 9 |
| 2026 | 56 | 9 |

The very low pre-2023 counts are a visible **blocker** for a complete ATP
Tour historical Category/Series library. The 2023–2025 counts, by contrast,
now include the complete main-Tour category rosters for those specific years. The 2026 reference is also a
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

## Completed ATP 250 rosters for 2024 and 2025 (played events, not assumptions)

The source includes **all 38 played ATP 250 events in 2024** and
**all 30 played ATP 250 events in 2025**, cross-checked against official
[ATP 2024 results archive](https://www.atptour.com/en/scores/results-archive?year=2024)
and [ATP 2025 results archive](https://www.atptour.com/en/scores/results-archive?year=2025).
ATP's [2025 schedule overview](https://www.atptour.com/en/news/what-is-the-2025-atp-tour-calendar)
is not itself an exhaustive result record: the 2025 Hangzhou edition
was demonstrably played, as confirmed by
[ATP's 2025 final report](https://www.atptour.com/en/news/bublik-royer-hangzhou-2025-final).
The year-effective roster therefore includes Hangzhou in both 2024 and 2025.

| Year | Masters tier | ATP 500 | ATP 250 | ATP Finals | Next Gen Finals | Source identities |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2024 | 9 | 13 | **38** | 1 | 1 | **62** |
| 2025 | 9 | 16 | **30** | 1 | 1 | **57** |
| 2026 (dated reference) | 9 | 16 | 29 | 1 | 1 | 56 |

The 2024/2025 counts reflect tournament identities at their tour level;
no player or match results were imported. The source categorisation is now
closed for those specific two played seasons, **not** for 1990–2020 or
for the definitive outcome of late 2026.

### Identities that must not be collapsed

- The **2024 Lyon clay ATP 250** and the **2026 Lyon indoor ATP 250**
  are **not the same Series**: the former historical Lyon event
  is `lyon_old`, while the latter belongs to the existing Marseille
  licence tracked under `lyon`, with 2024/2025 host Marseille
  and 2026 host Lyon. The ATP
  [2026 calendar announcement](https://www.atptour.com/en/news/2026-atp-tour-calendar-announced)
  records the Marseille schedule change; relocation and licence history
  require review before assigning any earlier years.
- `brussels` is the continuing European Open reference: its 2024
  location was **Antwerp**, and it moved to **Brussels** for 2025.
- **Córdoba, Newport and Atlanta** have verified 2024 ATP 250
  entries, but are absent from the 2025 Tour 250 roster. They remain
  separate identities rather than being silently reused for another city.
- **Belgrade and Metz** occur in 2024 and 2025, but neither belongs to
  the 2026 ATP 250 roster. **Estoril** appears in 2024 and 2026,
  not 2025. These source gaps are intentional category years, never
  automatic tournament closures.

No claim of a complete **historical Run Calendar Package** follows
from these categorical year rosters. Actual Tournament Editions,
date/time, draw structure, qualifying, points-by-round and temporal
name/location changes remain a separate and more detailed data layer.

## Completed 2023 Tour 250/500 roster and preserved tournament relocation history

The [ATP 2023 official results archive](https://www.atptour.com/en/scores/results-archive?year=2023)
confirms **38 ATP 250** and **13 ATP 500** events, together with
nine Masters 1000 tournaments and the two ATP year-end Finals identities
(62 source-level identities). This **does not** automatically make an
edition-based calendar: the reference documents Category assignment only.

Important historical identities newly differentiated:

- **2023 Adelaide International 1 and Adelaide International 2** were
  two different consecutive ATP 250 events, not one event played twice:
  [ATP Adelaide 1 overview](https://www.atptour.com/en/tournaments/adelaide-1/2843/overview).
  The 2023 second event has a separate `adelaide_2` reference; the existing
  `adelaide` source records Adelaide 1.
- **Zhuhai 2023 → Hangzhou 2024:** the same ATP Tour 250 tournament
  licence moved. We retain a single `hangzhou` source identity with
  historical hosts and no fabricated concurrent Zhuhai tournament:
  [ATP relocation notice](https://www.atptour.com/en/news/to).
- **Astana 2023 → Almaty 2024:** the same 250 tournament relocated.
  The `almaty` source identity preserves both historical hosts:
  [ATP calendar update](https://www.atptour.com/en/news/2024-atp-calendar-update-gijon-almaty).
- **Pune 2023 → Hong Kong 2024:** ATP confirmed that the Pune ATP 250
  tournament licence (owned by IMG) moved to Hong Kong. It therefore
  remains a single `hong_kong` Series identity for Pune editions
  2022–2023 and Hong Kong editions from 2024. The old 1990–2002
  Hong Kong ATP event is not automatically assumed to have shared this
  later licence. Banja Luka and Sofia remain distinct ATP 250 Series
  whose 2024 status must not be guessed.
- The 2023 clay **Lyon Open** and the 2023 **Marseille Open 13**
  remain separate Series. The latter eventually moves its licence
  to Lyon in 2026; equal host cities do not imply identical Series IDs.

| Year | Masters tier | ATP 500 | ATP 250 | ATP Finals | Next Gen Finals | Source identities |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023 | 9 | 13 | 38 | 1 | 1 | **62** |
| 2024 | 9 | 13 | 38 | 1 | 1 | **62** |
| 2025 | 9 | 16 | 30 | 1 | 1 | **57** |
| 2026 (provisional) | 9 | 16 | 29 | 1 | 1 | 56 |

**Remaining material gap:** roughly the first 33 years of lower ATP Tour
categories (1990–2020) are still *not exhaustively reconstructed*. Their
annual category references must not be marketed as historical complete
seasons. Full historically accurate pre-alpha consumption additionally
requires the semantic Package registry/Run adapters and explicit Save.

## 2022 pandemic-adjusted ATP Tour — confirmed exceptions, partial ordinary lower-tier roster

Official [ATP press release of 21 July 2022](https://www.atptour.com/-/media/sites/atp-tour/press/press-releases/atp-issues-2022-calendar-updates-21-july-2022.pdf)
explicitly documents four **cancelled** tournaments on the China swing:
Shanghai (Masters 1000), Beijing (500), Chengdu (250), and Zhuhai
(250, now tracked via the continuing `hangzhou` identity after the
2024 Zhuhai→Hangzhou relocation).

The same release confirms six **single-year 2022 ATP 250 licences**:
San Diego, Seoul, Tel Aviv, Florence, Gijón and Naples. We represent
each as its own Series identity with only 2022 effective, not as
permanent competitions or phantom 2023 editions. The corresponding
played events are also documented in the
[ATP 2022 results archive](https://www.atptour.com/en/scores/results-archive?year=2022).

The 2022 **Astana Open was elevated to ATP 500**, returning to ATP 250
in 2023. Its separate permanent tournament membership was transferred
from St. Petersburg. As the pre-2022 Astana editions had one-year
licences, we preserve the historical licence ancestry explicitly:

- `st_petersburg.licence_lineage.successor_source_entity_id = almaty`
- `almaty.licence_lineage.predecessor_source_entity_id = st_petersburg`
- Transfer year: **2022**, with the ATP official press release as evidence.

These legacy technical identities are **not yet consolidated into a
single source identity**, so a future full licence-continuity audit
must resolve the precise pre-2022 boundary before promoting the
source set into a production Series registry. The venue continuity
across **Astana 2022–23 → Almaty 2024** is already represented.

**2022 source counts must not be confused with played events:** the
year-resolved state contains **14 ATP 500 category-effective Series
identities**, but Beijing is marked as **cancelled**, giving 13
actually played ATP 500 events. The nine top-tier Masters Series
identities likewise include **cancelled Shanghai**, yielding only
eight played Masters 1000 tournaments that year. The 2022 ATP 250 played roster has now been independently reconciled
against the official Results Archive; its cancelled licences remain separate.

By contrast, the 2023–2025 year-specific Masters/500/250 category
rosters have been reconciled to published ATP results, not merely
copied from prospective season announcements. Distinguishing
(1) source identity, (2) scheduled/cancelled annual category and
(3) a genuinely played Tournament Edition is essential to preserving
historical realism.

## 2022 completed played main-Tour category roster — official results archive

After cross-checking the [ATP 2022 results archive](https://www.atptour.com/en/scores/results-archive?year=2022)
against ATP's July 2022 cancelled-event notice, the reference contains
**42 played ATP 250** identities plus **2 cancelled/scheduled 250**
identities (**Chengdu** and **Zhuhai**, the predecessor venue of
`hangzhou`). The cancelled event is **not** a played Edition.

| 2022 Tour class | Source category-effective identities | Known cancelled | Actually played |
| --- | ---: | ---: | ---: |
| Masters 1000 | 9 | 1 (Shanghai) | 8 |
| ATP 500 | 14 | 1 (Beijing) | 13 |
| ATP 250 | 44 | 2 (Chengdu, Zhuhai) | 42 |
| ATP Finals | 1 | 0 | 1 |
| Next Gen ATP Finals | 1 | 0 | 1 |
| **Total** | **69** | **4** | **65** |

A player's record or award does not appear in this package, even when
the ATP results archive was consulted for category counts; those results
are not imported.

Three 2022-only source identities are now separately represented:
**Melbourne Summer Set**, **Sydney Tennis Classic**, and the **Belgrade
clay** event (not automatically identified with the later Belgrade indoor
event). Adelaide 1 and Adelaide 2 are two independently counted
ATP 250 editions; no licence overlap is invented. The existing six
one-year ATP 250 replacement licences remain individually traceable.

Thus **2021–2025** are reconciled at the broad Masters/500/250
played-vs-cancelled event level, subject to all remaining identity
and event-specific semantic audits. The historic category/Series coverage
for **1990–2020** still has significant unverified lower tiers, and
2026 remains provisional. A complete factual ATP Calendar Package
remains outside this PR's current source-only scope.

## 2021 played ATP Tour category roster — cancelled events separated

The official [ATP 2021 Results Archive](https://www.atptour.com/en/scores/results-archive?year=2021)
records **39 played ATP 250**, **9 played ATP 500** and **8 played
Masters 1000** events. The Package's category-effective 2021 references
additionally retain *known cancelled events*, not incorrectly scored
as played Editions.

| 2021 category | Defined category-effective Series | Known cancellations | Played |
| --- | ---: | ---: | ---: |
| ATP Masters 1000 | 9 | Shanghai | 8 |
| ATP 500 | 12 | Beijing, Rio, Basel | 9 |
| ATP 250 | 42 | Houston, Chengdu, Zhuhai | 39 |
| ATP Finals | 1 | — | 1 |
| Next Gen ATP Finals | 1 | — | 1 |
| **Total** | **65** | **7** | **58** |

The currently listed cancellations are **individually evidenced,
not an exhaustive claim about every originally planned competition**.
Specifically [Swiss Indoors Basel](https://www.swissindoorsbasel.ch/en/tournament/tournament-news/articles/2021-06-04_Swiss-Indoors-Basel-2021-cancelled.php)
confirms the cancelled Basel 500; 2021 Rio was cancelled
([tournament announcement](https://www1.folha.uol.com.br/esporte/2021/04/rio-open-e-cancelado-em-2021-por-conta-do-agravamento-da-pandemia.shtml));
and [ATP's January 2021 update](https://www.atptour.com/en/news/atp-2021-calendar-updates-new-events)
confirms the cancelled Houston 250.

Distinct one-off historical sources include **Melbourne 1 and Melbourne 2**,
**Belgrade 1 and Belgrade 2**, Singapore and Marbella. The two Belgrade
2021 events cannot be collapsed into the 2022 Belgrade clay edition,
much less the later Belgrade indoor tournaments, without a documented
tournament licence mapping. The ATP confirmed Singapore and Marbella
one-year licences and a Budapest-to-Belgrade relocation for one
2021 event. Kazakhstan's 2021 venue was **Nur-Sultan**, not Almaty;
the data records Nur-Sultan (2021), Astana (2022–23), and
Almaty (2024 onward) independently of any unresolved legal
licence ancestry.

The main ATP Tour's played top-tier roster is now reconciled at
the **2021–2025** year level, with the explicit non-played subset
and without duplicating match results. **1990–2020 remains
partially documented** in the lower tour categories. Source-only
Package semantics and missing Run adapters are separate integration
blockers; an indexed annual reference is not a historical Edition.

### Critical source-identity reconciliation: Pune to Hong Kong

On 12 June 2023 ATP [announced the relocation of the Pune ATP 250
tournament to Hong Kong for 2024](https://www.atptour.com/en/news/hong-kong-atp-250-2024),
with approval of the ATP Board and the same IMG-owned licence.
The previous separate `pune` reference would have **double counted
one persistent Series identity**. Its 2022 and 2023 ATP 250 intervals
are now stored under `hong_kong`, which continues in Hong Kong from
2024 through the currently reviewed 2026 roster.

The fact that Hong Kong previously hosted an ATP Tour competition
in 1990–2002 does not prove it was the *same* licence as the later
Pune-to-Hong-Kong transfer. That older event remains separate
historical identity work and is not silently backfilled under this ID.

### Critical source-identity reconciliation: Belgrade clay to Banja Luka

[ATP's 2023 calendar announcement](https://www.atptour.com/en/news/united-cup-to-kick-off-2023-tennis-season)
confirms that the **April 2023 Belgrade ATP 250 moved to
Banja Luka, Bosnia and Herzegovina**. The previous `belgrade_clay_2022`
technical identity has been consolidated into the stable `banja_luka`
Series (with a 2022 Belgrade host and a 2023 Banja Luka host).
This avoids inventing a second permanent tournament after relocation.

The independent **Belgrade 2024/2025 indoor tournament** came from a
**Gijón calendar slot** and was not the same 2022 Belgrade clay
tournament: [ATP's 2024 announcement](https://www.atptour.com/en/news/belgrade-2024-announcement).
The two separate Belgrade 2021 events remain separately recorded
because the exact licence-level relationships with 2022 have not yet
been exhaustively established. Same city, same name or adjacent year
is never by itself proof of identical Series licensing.

The data now contain **87 stable, partially historically reconstructed
Series source identities** and 37 annual snapshots. Among those
snapshots, Masters/ATP500/ATP250 **2021–2025** played rosters have been
reconciled with ATP Results Archive; **1990–2020** lower tiers remain
incomplete and the 2026 roster is still provisional.


## Completed ATP Tour played-tier roster for the exceptional 2020 season

The [ATP 2020 Results Archive](https://www.atptour.com/en/scores/results-archive?year=2020)
establishes the played men's main Tour singles tournament inventory:
**3 ATP Masters 1000, 7 ATP 500, 18 ATP 250**, and the played ATP Finals.
The Next Gen Finals were **not held** in 2020. This is *not* a count of
Grand Slams, ATP Cup team events, Challenger events, ITF or Davis Cup.

| 2020 Tier | Played | Known cancelled in Category references | Category-effective source IDs |
| --- | ---: | ---: | ---: |
| ATP Masters 1000 | **3** | 6 | 9 |
| ATP 500 | **7** | Halle, Queen's, Beijing | 10 |
| ATP 250 | **18** | Zhuhai, Chengdu | 20 |
| ATP Finals | **1** | — | 1 |
| Next Gen Finals | **0** | Yes | 1 |

Other 2020 cancellations are intentionally not claimed to be an
exhaustive roster of every originally planned tournament. The 2020
ATP Cup was a separately formatted team competition and remains
outside these Category/Series singles Tour packages.

The 2020 singles ATP 250 field includes separately identified
**Cologne 1**, **Cologne 2** and **Sardinia**, all one-year
replacements. ATP's [10 September 2020 official release](https://www.atptour.com/-/media/sites/atp-tour/press/press-releases/10-september-2020-atp-announces-four-new-events.pdf)
also confirms a *one-year Nur-Sultan ATP 250* that year; the
source retains a Nur-Sultan 2020 row under the Kazakhstan venue-family
identity while explicitly warning that the later permanent Astana
membership has a different legal licence ancestry.

Source identity continuity was reconciled as follows:

- **New York Open 2020 → Dallas Open from 2022**, one continuous
  ATP 250 licence, subsequently upgraded to ATP 500 in 2025:
  [ATP 2025 Dallas history](https://www.atptour.com/en/news/fritz-dallas-2025-preview).
- **Cincinnati Masters played at New York/Flushing Meadows in 2020**
  due to COVID, rather than minting a second New York Masters Series:
  [ATP chairman's chronology](https://www.atptour.com/en/news/andrea-gaudenzi-chairman-q-and-a-march-2021/).
- The two Cologne weeks were independent tournaments with independent
  winners' draws, not one tournament counted once or an assumed
  permanent Cologne Series.
- **2020 St Petersburg ATP 500** was a temporary elevation,
  not the start of a permanent 500 category.
- The **Sardinia 2020** clay ATP 250 is not silently merged
  with the distinct **Cagliari 2021** event licence without a
  sourced same-licence record.

### Explicit completeness / rejection gate

The deterministic source resolver now emits
`played_tier_roster_validation` for every annual snapshot:

- **2008–2025**: `played_tour_tiers_reconciled_to_atp_results_archive`,
  with year-specific reference counts independently asserted against
  played (category-effective minus known-cancelled) identities.
- **1990–2007**: `unverified_incomplete`. No invented total
  or assumption that present-day event structure already existed.
- **2026**: `provisional_calendar_not_final_results`; ATP
  calendar changes and remaining matches are not misreported as
  completed historical facts.

A source mutation that breaks one of the validated played-year
counts raises a `ValueError` before a stale annual reference
can pass the source generator's `--check`. Tests additionally
assert 2020 one-off events, Category references and location changes.

**Remaining gap:** 1990–2007 lower Tour tiers are not fully reconstructed
and still require ATP results archive research. Runtime integration
into the Squash Engine Packages library and sporting Calendar is still
absent, and no source file implies a playable tennis simulation.

## 2019 complete ATP Tour tier roster (year-resolved Series references)

Official [ATP 2019 Results Archive](https://www.atptour.com/en/scores/results-archive?year=2019)
and [ATP 2019 Tour calendar announcement](https://www.atptour.com/en/news/atp-announces-2019-atp-world-tour-calendar)
independently confirm that the 2019 men's main Tour consisted of
**9 ATP Masters 1000 + 13 ATP 500 + 39 ATP 250** competitions;
together with ATP Finals and Next Gen Finals, this is **63 source
Series identities** for that single season. No Grand Slam, Davis Cup,
Challenger or ITF event is included.

ATP's archive lists the 2019 main Tour tournaments by their **then
current venue and sponsor title**. This is not a licence to assume
those cities are permanent Series identifiers. The new year-effective
2019 assignments preserve important transitions:

- **2019 Budapest Hungarian Open → 2021 Belgrade ATP 250**:
  ATP [approved the Budapest relocation for 2021](https://www.atptour.com/en/news/atp-2021-calendar-updates-new-events).
  The source identity `belgrade_clay_2021` now contains both
  verified year-effective events. The absent 2020 played edition
  is not fabricated. The further precise licence relationships
  with 2022 Belgrade / 2023 Banja Luka remain reviewable.
- **2019 New York Open** and **2020 New York Open** continue under
  the `dallas` Series: the same licence
  [moved to Dallas in 2022](https://www.atptour.com/en/news/fritz-dallas-2025-preview).
  Its 2025 upgrade to 500 remains within this single Series ID.
- **2019 Pune** and **2020 Pune** remain under `hong_kong`,
  the later relocated Tour 250 licence. Its previous pre-2019
  locations are not automatically inferred.
- **2019 Sydney International** is a separate source identity
  from the special 2022 Sydney Tennis Classic pending definitive
  licence-continuity evidence; equal city is not enough.
- **2019 grass Antalya** is kept separate from the independently
  granted **2021 temporary hard-court Antalya** event; no unverified
  permanent same-Series identity.
- **2019 Kremlin Cup Moscow** and **2021 Moscow** use one stable
  Series ID `moscow`. The 2020 Tour played record does not contain
  a Moscow tournament and is left absent, not a fabricated edition.
- The final Tour 250 **São Paulo Brasil Open 2019** is preserved as
  a source identity with no inferred continuation thereafter.

The historical ATP 2019 tier census is included in the generator's
fail-closed played-tier validation: any source mutation that silently
removes or reclassifies one of those 63 identities rejects regeneration,
even when the JSON remains syntactically valid.

| Year | Played Masters | Played 500 | Played 250 | Finals identities | Tier roster evidence |
| --- | ---: | ---: | ---: | ---: | --- |
| **2019** | **9** | **13** | **39** | 2 | ATP 2019 results |
| 2020 | 3 | 7 | 18 | ATP Finals only; Next Gen cancelled | ATP 2020 results |
| 2021 | 8 | 9 | 39 | 2 | ATP 2021 results |
| 2022 | 8 | 13 | 42 | 2 | ATP 2022 results |
| 2023 | 9 | 13 | 38 | 2 | ATP 2023 results |
| 2024 | 9 | 13 | 38 | 2 | ATP 2024 results |
| 2025 | 9 | 16 | 30 | 2 | ATP 2025 results |

These ten year-specific rosters are source-level and **NOT**
Calendar Edition packages, complete points/format histories or
full tournament draw result archives. **1990–2007 remains
historically incomplete**, and 2026 remains provisional.

## 2018 official ATP Tour calendar: 64 identities with verified tiers

The ATP's own
[2018 ATP World Tour Calendar](https://www.atptour.com/-/media/files/partnerships/about-2018-atp-world-tour.pdf)
lists **9 Masters 1000, 13 ATP 500 and 40 ATP 250 events**
plus the Nitto ATP Finals and Next Gen ATP Finals — **64 ATP
competition identities** in the tournament schedule. The ATP's
[2018 Results Archive](https://www.atptour.com/en/scores/results-archive?year=2018)
corroborates the played competitions. Grand Slam and Davis Cup
entries appear separately in ATP publications and are **excluded**
from this ATP-only source model.

For 2018, these historical Series identities have been explicitly
preserved or differentiated:

- The last **Quito 250** held in 2018, followed by
  **Córdoba 250 in 2019**, shares the transferable tour-calendar
  licence/slot; the documented sale and replacement is described
  by the contemporary
  [La Nación report](https://www.lanacion.com.ar/deportes/tenis/historico-argentina-organizara-segundo-torneo-atp-2019-nid2165990/).
  The `cordoba` ID has host Quito in 2018 and Córdoba in 2019.
  This is an economically documented transfer, not a mere guess
  based on adjacent weeks.
- The **2018 Shenzhen ATP 250** is a separate identity
  `shenzhen_2018` and is not silently merged into the new
  Zhuhai 2019 event. An equivalent competition category and
  China venue alone does not establish common legal licence.
- The **2018 Istanbul 250** source is independently retained
  without inventing a played 2019 edition.
- **Sydney 2018 and 2019** share their verified venue-event
  identity, as do grass **Antalya 2018 and 2019**. Separate
  COVID-era 2021 Antalya and 2022 Sydney licences remain
  distinct pending explicit legal transfer evidence.
- **Budapest 2018–19** remains one identity with its ATP-approved
  relocation to Belgrade in 2021, not a parallel created series.
- **New York 2018–20 → Dallas from 2022**, and **Pune
  2018–20, 2022–23 → Hong Kong from 2024**, are tracked
  through their historical host changes rather than rebranding
  retroactively.

The 2018 annual Category roster is now included in the generator's
fail-closed source validation (9/13/40). The year-resolved
record does not contain players, scores, tournament draw results,
qualification details or a tennis sporting engine.

**2008–2025** are the eighteen consecutive ATP years reconciled at
the played Tour Category level. **1990–2007** lower-tier event
Series remain incomplete; the 2026 roster is provisional.

## 2016 and 2017 ATP Tour category coverage: complete official played-year rosters

[ATP 2016 Results Archive](https://www.atptour.com/en/scores/results-archive?year=2016)
and the [2016 ATP media guide](https://www.atptour.com/-/media/files/media-guide/2016/atp2016_media_guide.pdf)
document **9 Masters 1000, 13 ATP 500, 39 ATP 250 and one ATP Finals
event**: **62 ATP Tour identities**. The 2016 Rio Olympics and four
Grand Slams are *not* ATP Tour event Series in this model, even though
some results count in the external ATP ranking.

[ATP 2017 Results Archive](https://www.atptour.com/en/scores/results-archive?year=2017)
and [ATP calendar release](https://www.atptour.com/en/news/atp-announces-2017-2018-calendars)
document **9 Masters, 13 ATP 500, 40 ATP 250** plus ATP Finals
and the inaugural Next Gen ATP Finals: **64 ATP Tour identities**.
The Laver Cup and Davis Cup appear in some public calendar archives
but are explicitly excluded from this strictly ATP Tour source package.

| Year | Played Masters | Played ATP 500 | Played ATP 250 | ATP Finals | Next Gen Finals | Source Series |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2016 | 9 | 13 | 39 | 1 | 0 (not yet created) | **62** |
| 2017 | 9 | 13 | 40 | 1 | 1 | **64** |

**2016–2017 important real Tour Series licence moves:**
- **Chennai 2016–2017 → Pune 2018 → Hong Kong 2024:**
  contemporaneous [Indian tennis reporting](https://scroll.in/field/844022/)
  confirms Chennai's move to Pune, and the
  [ATP Hong Kong 2024 release](https://www.atptour.com/en/news/hong-kong-atp-250-2024)
  confirms Pune's later move. One identity `hong_kong` is
  preserved without creating parallel permanent City Series.
- **Memphis 2016–2017 → Long Island/New York 2018 → Dallas 2022:**
  [official ATP New York press notes](https://www.atptour.com/-/media/931dfc248f6e4ccbba6e75cf4020fd44.pdf)
  describe Memphis-to-Long-Island; the same source identity `dallas`
  later changes tier to ATP 500 in 2025.
- **Bucharest 2016 → Budapest 2017–2019 → Belgrade 2021:**
  [2016 licence announcement](https://www.profit.ro/stiri/social/tiriac-anunta-ca-turneul-atp-de-la-bucuresti-se-muta-la-budapesta-jucam-in-tiganie-15501062)
  establishes the 2016 departure from Bucharest. The later
  **2024+ Bucharest** tournament is not automatically assumed to
  be the same licence: the source distinguishes `bucharest`
  from the 2016–2021 historical identity `belgrade_clay_2021`.
- **Nice 2016 → Lyon 2017**: the ATP 250 Nice clay tournament
  moved to Lyon, as independently
  [reported in November 2016](https://www.lequipe.fr/Tennis/Actualites/Un-nouveau-tournoi-atp-a-lyon-la-semaine-avant-roland-garros/748030).
  The `lyon_old` ID spans both hosts, and is **separate** from
  the Marseille licence that moved to Lyon for 2026.
- **Nottingham 2016 → Eastbourne 2017**:
  [LTA's official grass calendar](https://www.lta.org.uk/news/2016/april/british-grass-court-season-announced-for-2017/)
  confirms the ATP 250 moved to Eastbourne in 2017.
  Nottingham's subsequent men's Challenger is **not** represented
  as an ATP Tour 250 and is not a parallel Tour Series.

For all eighteen **2008–2025** completed seasons, the annual resolver now
rejects source changes that corrupt the count of actually played
Masters/500/250 tournaments. This is verified **source identity/category
reconstruction**, not a historic Calendar Package with draw dates,
licence transaction registry, match results or player ranking points
by round.

**Remaining scope:** precisely **1990–2007** lack complete lower-tier
Series coverage; **2026** is a provisional Tour calendar. Current
files are not yet integrated into the Squash Engine's production
Package catalog or Run-application workflow.

## 2015 ATP Tour: 62 played top-tier events and five explicit 2016 licence moves

The official [2015 ATP Tour results archive](https://www.atptour.com/en/scores/results-archive?year=2015)
supports **9 Masters 1000**, **13 ATP 500**, **39 ATP 250**
and **one ATP Finals event**: 62 played ATP Tour source identities.
Next Gen ATP Finals did not exist yet; the four independently
governed Grand Slams and Davis Cup are outside this strict ATP Tour
Category/Series model.

The 2015 category-history source now identifies five *actual
licensed Tour event moves* rather than minting unrelated city Series:

| 2015 ATP Tour event location | 2016 location | Stable Series source ID | Evidence |
| --- | --- | --- | --- |
| Zagreb (Croatia) | Sofia (Bulgaria) | `sofia` | [ATP calendar announcement](https://www.atptour.com/en/news/atp-announces-2017-2018-calendars) |
| Casablanca (Morocco) | Marrakech (Morocco) | `marrakech` | [Official ATP event profile](https://www.atptour.com/en/tournaments/casablanca/360/overview) |
| Bogotá (Colombia) | Los Cabos (Mexico) | `los_cabos` | [ATP calendar announcement](https://www.atptour.com/en/news/atp-announces-2017-2018-calendars) |
| Kuala Lumpur (Malaysia) | Chengdu (China) | `chengdu` | [ATP-approved relocation](https://www.ausleisure.com.au/news/malaysia-farewells-another-international-sporting-event) |
| Valencia (Spain) | Antwerp (Belgium) | `brussels` | [ATP calendar announcement](https://www.atptour.com/en/news/atp-announces-2017-2018-calendars) |

Three additional persistent families also preserve **2015**
Chennai→Pune→Hong Kong, Memphis→New York→Dallas, and
Bucharest→Budapest→Belgrade. The **2015 Nottingham**
ATP 250 is one source Series as **2017 Eastbourne**, while
**Nice 2015** is the historical predecessor of the
**2017 Lyon clay** ATP 250.

All these changes are explicitly dated and source-backed; the
presence of one identity is **not** evidence of an annual played
edition in its unverified earlier years. There is no invented
separate `valencia_2015`, `kuala_lumpur_2015` etc.
The 2024+ Bucharest Series is deliberately distinct from the
pre-2017 Bucharest→Budapest licence, preserving uncertainty
about its later legal continuity.

### Updated verification boundary

The deterministic source-builder has an explicit played ATP Tour
tier census for each of the **11 complete consecutive years
2015–2025** (inclusive), with source-specific upper-tier and lower
tier counts and automated rejection on conflicting changes.

The remaining **19 seasons 1990–2007** have incomplete ATP 500/250
Series coverage, despite the nine top-tier historical Masters
identities and era-specific Category names. They require
independent tournament-by-tournament audit and cannot be
released as a complete historical Tour. Current 2026 data are
provisional. The read-only Category/Series Package documents
still require semantic integration into the Squash Engine
Package Catalogue and Admin/Run interfaces before use.

## 2014 ATP Tour results: 9 Masters 1000, 11 ATP 500 and 39 ATP 250

The [official ATP 2014 Results Archive](https://www.atptour.com/en/scores/results-archive?year=2014)
identifies the **60 played ATP Tour Series competitions**:
nine Masters 1000, eleven ATP 500, thirty-nine ATP 250 and one
ATP Finals. The four Grand Slams and non-ATP team competitions
must **not** be added to this ATP Tour-only Category package.

Historical classification matters more than present-day event names:

- **Halle, Queen's Club and Vienna were ATP 250 events in 2014**,
  then became ATP 500 in 2015. The source therefore has different
  Category relationships effective in the two years.
- **Valencia was an ATP 500 in 2014**, was reclassified ATP 250
  for 2015 and its licence subsequently moved to **Antwerp**.
  The stable `brussels` identity (later European Open) preserves
  this change without minting a parallel Valencia 500 Series.
- **Rio 500** was introduced in **2014**, so its lower-year Category
  data are never fabricated.
- **Viña del Mar 2014 → Quito 2015 → Córdoba 2019** is one
  documented Tournament Calendar-slot/Series identity, confirmed
  by the [contemporaneous ATP-approved Viña move](https://www.emol.com/noticias/deportes/2014/08/26/677087/tenis-atp-oficializa-cambio-del-torneo-de-vina-del-mar-a-quito-desde-2015.html).
- The 2014 **Oeiras Portugal Open** is represented in the long-term
  Portugal/Estoril event family; its 2015 location and organizer
  change are noted explicitly. [Portuguese coverage](https://www.rtp.pt/noticias/outras-modalidades/estoril-open-volta-ao-circuito-atp-em-2026_d1631989)
  explains that event continuity does **not** automatically prove
  legal licence/organizer identity across the 2015 change.
- **Düsseldorf 2014** is preserved as a separate `duesseldorf_2014`
  Series identity. Geneva replaced its calendar placement in 2015,
  but legal licence continuity remains under review. This avoids
  merging identities on insufficient evidence.
- **St Petersburg was absent in 2014** and is not fabricated
  despite its source continuity in 2013 and 2015.

| Season | ATP Masters played | ATP 500 played | ATP 250 played | ATP year-end events | Validated ATP Tour Series |
| --- | ---: | ---: | ---: | ---: | ---: |
| **2014** | **9** | **11** | **39** | 1 | **60** |
| 2015 | 9 | 13 | 39 | 1 | 62 |
| 2016 | 9 | 13 | 39 | 1 | 62 |
| 2017 | 9 | 13 | 40 | 2 | 64 |

**2008–2025 now have 18 consecutive year-level ATP Tier rosters
validated against official results archives.** The source model
covers 37 labelled reference years 1990–2026, but the remaining
**1990–2007** years still lack comprehensive lower-category
Series histories and cannot be declared complete. The 2026
calendar is provisional. Production Package Catalog integration,
applicable historic Calendar Editions and audited historical
points tables are **still outstanding**.

## 2013 ATP Tour results: 9 Masters, 11 ATP 500, 40 ATP 250

The [2013 ATP Tour results archive](https://www.atptour.com/en/scores/results-archive?year=2013),
the detailed contemporaneous
[NOS 2013 Tour schedule](https://nos.nl/artikel/457783-atp-tenniskalender-2013),
and an independent [2013 seasonal record](https://de.wikipedia.org/wiki/ATP_World_Tour_2013)
agree on **9 ATP Masters 1000, 11 ATP 500, 40 ATP 250** and
ATP World Tour Finals: 61 source Tour event identities.
That 61 excludes the separately governed four Grand Slams
and Davis Cup, and correctly excludes the ITF Hopman Cup.
The Next Gen Finals were not established until 2017.

Historic Tier relationships need to be explicit rather than
retroactively inferred from the familiar 2026 category names:

- **Memphis in 2013 was ATP 500**. It became a 250 in 2014,
  moved to New York in 2018 and Dallas in 2022, then was
  upgraded back to ATP 500 in 2025. The stable source identity
  `dallas` preserves this *category timeline*.
- **Valencia 2013–14 was ATP 500**; Valencia 2015 was a 250;
  the licence transferred to Antwerp in 2016. This is one
  time-effective `brussels` identity, not multiple invented events.
- **Halle, Queen's Club and Vienna in 2013–14 were ATP 250**,
  subsequently promoted to 500 for 2015, and must not have
  modern tier labels applied to past years.
- **Viña del Mar 2013–14** is referenced under `cordoba`,
  followed by **Quito 2015–18** and **Córdoba 2019**.
- Historic ATP 250s **San Jose, Los Angeles and Bangkok
  (2013)** have separate Series references. Their legal successors
  are not guessed and no 2014 events are fabricated under
  those specific source identities.
- **Düsseldorf 2013–14** remains a separate 250 Series from
  2015 Geneva unless the transfer of the actual tournament
  licence is independently documented.

The annual source resolver validates the 2013 9/11/40 census,
as well as the other year-specific complete top Tour tier rosters
through 2025, without importing any tennis player results,
ranking-point records or actual Calendar Editions.

**2008–2025** are now eighteen consecutive completed year-level
main ATP Tour category/Series rosters; **1990–2007** still have
incomplete lower tiers, and 2026 remains provisional.

## New archive-backed early-modern ATP Tour years: 2009, 2010, 2011 and 2012

The **2009 reorganization** was the first season with the ATP
Masters 1000 / ATP 500 / ATP 250 Category labels. The separate
annual [ATP archive for 2009](https://www.atptour.com/en/scores/results-archive?year=2009)
shows **9 Masters / 11 ATP 500 / 40 ATP 250 / 1 ATP Finals**,
not including the four Grand Slams, Davis Cup or the Düsseldorf
World Team Cup.

The same source-tier totals were independently reconciled for
[2010](https://www.atptour.com/en/scores/results-archive?year=2010),
[2011](https://www.atptour.com/en/scores/results-archive?year=2011)
and [2012](https://www.atptour.com/en/scores/results-archive?year=2012).
These are four actual year-specific Tier rosters, not the same
current 2026 Series copied blindly.

| Year | Masters played | ATP 500 played | ATP 250 played | ATP Finals | Total played main Tour events |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2009 | 9 | 11 | 40 | 1 | 61 |
| 2010 | 9 | 11 | 40 | 1 | 61 |
| 2011 | 9 | 11 | 40 | 1 | 61 |
| 2012 | 9 | 11 | 40 | 1 | 61 |

**Historic ATP sanctions and host cities matter:**

- **2009 Indianapolis → 2010 Atlanta** is one Tour 250
  tournament sanction, confirmed by
  [the 2010 relocation announcement](https://www.ajc.com/sports/atlanta-athletic-club-chosen-site-for-pro-tennis-event/gYvoEEJE1Gr6pQan38h9NI/).
  The Series ID is `atlanta`, with the 2009 host set to
  Indianapolis. This should not be confused with the different
  Atlanta ATP event that existed before 2002.
- **2009 Lyon indoor → 2010 Montpellier indoor** is another
  explicitly ATP-approved transfer, documented by
  [L'Équipe](https://www.lequipe.fr/Tennis/Actualites/Montpellier-remplace-lyon/105494).
  The stable ID is `montpellier`. The 2009 Lyon indoor event
  is **not** the Nice→Lyon clay licence of 2017, and neither is
  automatically identical to Marseille→Lyon indoor in 2026.
- **2009–10 New Haven → 2011 Winston-Salem**:
  the USTA/ATP expressly announced sale and relocation of
  the sanction in December 2010;
  [Wake Forest announcement](https://godeacs.com/news/2010/12/13/Wake_Forest_to_Host_ATP_World_Tour_Event).
  The year-effective host changes, but one `winston_salem`
  Series identity continues.
- **2009 Kitzbühel → 2010 Challenger → 2011 ATP 250**:
  Kitzbühel is **not included** in 2010 ATP Tour Series
  membership because that year's event was Challenger level;
  it resumes Tour membership in 2011. Its cross-level
  Challenger history is not imported.
- **2009–11 Costa do Sauípe → São Paulo from 2012**:
  the long-running Brazil Open Series is tracked under
  `sao_paulo`. No two parallel 250 events are invented.
- **2010–11 Santiago → 2012–14 Viña del Mar → 2015–18
  Quito → 2019 Córdoba**: historically distinct hosts are
  tracked under one evolving Chile/Andes Series reference
  with source-year evidence.
- **Johannesburg** was an ATP Tour 250 event in 2009–11
  and is no longer assumed to exist at Tour level in 2012.
  **Belgrade Serbia Open** was played 2009–12, with
  the later Belgrade licence revivals kept separately.
- **2012 London Olympics, 2009–12 Düsseldorf World Team Cup,
  Grand Slams, Challenger and Davis Cup** remain excluded:
  those entries are visible on some ATP archive pages but
  do not constitute ATP Tour-owned Series packages.

### Updated coverage status and audit limitations

The deterministic generator now checks **18 consecutive played
ATP Tour tier rosters, 2008–2025**, respecting the original historical tier names. Its source references still
span all **37 years 1990–2026**, but **1990–2007** need
separate researched Category/Series identities for the pre-2009
International/Championship/World Series structure. Those
18 years are explicitly marked `unverified_incomplete`
rather than inferred from a 2009–2026 classification.
The 2026 reference remains provisional.

The file **is not a complete tournament Edition database**, and
the existence of 17 verified Tier rosters does not imply
certified match results, draw sizes, ranking awards, scheduling,
licence transaction documentation across every decade, or a
registered and applicable Squash Engine production Package.
Source arrays and tests are a historical research layer pending
semantic Package integration.


## 2008 ATP Tour — complete played historical Tier roster and corrections

The [2008 ATP official published calendar](https://ftpmirror.your.org/pub/wikimedia/images/wikipedia/commons/archive/9/93/20071121060750%21ATP_Calendar_2008.pdf)
and the [ATP 2008 Results Archive](https://www.atptour.com/en/scores/results-archive?year=2008)
have been compared event-by-event. The scheduled calendar is not a played
results census. A crucial difference is that its advertised Sopot slot was
**played in Warsaw**, while the planned Mumbai/Bangalore tournament was
**cancelled** for security reasons.

| 2008 historical ATP Tour category | Actually played | Known cancelled/scheduled |
| --- | ---: | --- |
| Tennis Masters Series | **9** | — |
| International Series Gold | **9** | — |
| International Series | **42** | Bangalore (formerly Mumbai) |
| Tennis Masters Cup / ATP Finals | **1** | — |
| **Total** | **61** | **1** |

The 2008 source Category/Series reference now contains **62 effective
identities**, exactly one of which is explicitly `known_not_held`.
The generator's played-roster validation checks **9 + 9 + 42**
excluding the cancelled Bangalore slot and treats the Finals separately.
The source includes **no Olympic event**, Grand Slams, Davis Cup,
Düsseldorf team cup, Challengers or ITF events. This is a complete
ATP Tour-owned *played tier identity roster*, not a match-results import,
edition calendar, draw-size registry or ranking-point ledger.

### Actual historical category transition — no backdated 500/250

The 2008 **International Series Gold** consisted of exactly nine played
events: **Rotterdam, Memphis, Dubai, Acapulco, Barcelona, Stuttgart,
Kitzbühel, Tokyo and Vienna**. Cross-check historical
[Gold membership](https://en.wikipedia.org/wiki/ATP_International_Series_Gold)
against the official ATP 2008 archive. When 2009 launched
the ATP 500/250 terminology, Rotterdam, Memphis, Dubai,
Acapulco, Barcelona and Tokyo became ATP 500; Stuttgart,
Kitzbühel and Vienna were ATP 250. Those 2008 Gold events
must **not** carry 2009 tier labels.

The Masters tier in **2008** still included **Hamburg** and
**Madrid as an autumn indoor tournament**, not Shanghai.
Shanghai became Masters from 2009, replacing Hamburg, while
Madrid's category/venue era shifted.

### Actual played venues and tournament licence evidence

- The original ATP PDF named **Sopot**, but the actual played
  2008 Polish International Series was the
  [Warsaw Open](https://www.atptour.com/en/tournaments/warsaw/475/overview),
  continuing Sopot's Tour slot after an emergency relocation.
  The source identity `warsaw_2008` records the actual city
  and does **not** assert a second played Sopot event.
  [Contemporaneous Polish report](https://sport.rp.pl/tenis/art16231731-ciag-dalszy-nastapil)
  explains the relocation.
- The original ATP PDF scheduled a **Mumbai** ATP International event.
  It was moved to Bangalore and then **cancelled** in August 2008
  for security reasons. The technical reference
  `bangalore_2008` has a year-effective Category with
  `not_held_years_known=[2008]`, never a fabricated played
  tournament. [2008 cancellation report](https://www.skysports.com/tennis/news/4050908/bangalore-open-cancelled).
- **2008 Amersfoort → 2009 Belgrade** was an
  [ATP Board-approved sale of the Dutch tournament sanction](https://sports.rediff.com/sports/report/belgrade-replaces-amersfoort-on-atp-calendar/20090102.htm).
  The stable `belgrade_2012` reference now spans actual
  **Amersfoort 2008** and **Serbia Open Belgrade 2009–12**.
  The later independent Budapest→Belgrade licence is separate.
- **2008 Adelaide men's hardcourt event → 2009 Brisbane** is
  documented by
  [contemporary Australian reporting](https://www.abc.net.au/news/2006-07-07/brisbane-to-host-mens-hard-court-champs-from-2009/1796818).
  The stable `brisbane` reference has Adelaide as its
  actual 2008 host; the modern Adelaide tournament's
  return from 2020 is not automatically a continuous licence.
- 2008 **Indianapolis** continued under `atlanta` from its
  transfer to Atlanta 2010; 2008 **Nottingham** is recorded
  as the earlier host of the `eastbourne` source, and
  2008 **Lyon indoor** as the earlier host of `montpellier`.
  Venue equality between multiple later Lyon events is
  explicitly **not** treated as proof of identical licensing.
- **Las Vegas** and **Pörtschach** remain separate 2008
  sources. Their later licenses have not been extrapolated.

### Completeness boundary

The generator now independently validates **18 played year-specific
ATP Tour top-tier rosters, 2008–2025**, using the **correct original
2008 category names**. The older years **1990–2007** remain
`unverified_incomplete`, despite their selected older Masters
identities. The still-evolving 2026 roster remains
`provisional_calendar_not_final_results`.

All historical roster assertions remain **source-level**, not
evidence of fully modelled tournament editions, formats, points
by round, qualifiers, draws, seeds, players or game rules. Real
Squash Engine production Package catalogue and Run Apply/Save
integration are separate release requirements.


## 2007 main Tour actual played-tier census — source-backed expansion (2026-11-02)

A historical **2007 ATP Tour** layer has now been reconciled. The actual
played event census is **9 Tennis Masters Series + 9 International Series
Gold + 43 International Series = 61 tier events**, plus the distinct
**Tennis Masters Cup (ATP Finals) = 62 ATP-only Series**. The 2007 calendar
listing of **65 regular tournaments** includes four *Grand Slams*, which
are intentionally NOT imported; no Davis Cup, World Team Cup or Hopman
Cup identities are imported. The year 2007 is **not** labelled ATP
1000/500/250, and no later point schedules are projected backwards.

- Primary actual-results cross-check: [ATP 2007 Results Archive](https://www.atptour.com/en/scores/results-archive?year=2007).
- Historical tier and 43-event denominator cross-check:
  [2007 ATP Tour category and schedule](https://en.wikipedia.org/wiki/2007_ATP_Tour).
- Secondary independently ordered calendar:
  [2007 ATP event results](https://www.tenispain.com/en/tenis-internacional/atp/year-2007/).

Nine historical Gold Series in 2007: Rotterdam, Memphis, Dubai,
Acapulco, Barcelona, Stuttgart, Kitzbühel, Tokyo and Vienna. The
generator gates all **61** played events at their actual historic
Category and will reject accidental cancellations or swapped tier
identities. The **2008 Bangalore non-held** Series remains excluded
from the 2008 played count but the original **Mumbai 2007** event is
correctly present.

Year-specific host records now distinguish **Sopot 2007 → Warsaw
2008**, **Mumbai 2007 → cancelled Bangalore 2008**, **Amersfoort →
Belgrade**, **Adelaide → Brisbane**, **Chennai → Pune → Hong Kong**,
**New Haven → Winston-Salem**, and the distinct historic Marseille,
Lyon indoor and Valencia licence tracks. These are source-history
links, *not* played Edition objects and *not* proof of every prior
or subsequent year in any Series.

**Coverage boundary after this expansion:** **19 consecutive played-tier
seasons (2007–2025)**, with 1990–2006 still incomplete, 2026
provisional, and the entire runtime Category/Series import/Save/Calendar
adapter unimplemented. No title points, draws, qualification or
match/player data was added. Keep this PR Draft.

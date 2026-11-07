# ATP Tour 1990–2026: Category and Series reference Packages

> **Current verified source state (2026-11-03):** 11 Category identities,
> **164** Series identities and 37 generated annual reference rows.
> The **36 played main ATP Tour tier rosters 1990–2025** have source-backed
> original year-effective categories. **2026 is
> provisional** until final results. The server now provides an
> **explicit, opaque Run Package reference Setup** for Preview/Confirm/Save,
> with two Category/Series children and a small API source manifest. This is
> **not** a playable Edition calendar, historical ranking system, sporting
> adapter. A dedicated ATP reference Apply page is now linked from the Admin Packages hub.
>
> Sections below preserve dated incremental research checkpoints. Statements
> about older incomplete year ranges (e.g. `1990–2007`) describe the state
> **at those earlier checkpoints**, not the current 1999–2025 coverage.
> Read the most recent dated historical appendix for up-to-date provenance.


**Scope:** the Association of Tennis Professionals' men's top-level **ATP Tour
since 1 January 1990**, not the entire history of men's tennis. The Category
and Series Package are optional **source-only historical references** for
Squash Engine's data-driven future, not tennis gameplay.

## 2026-11-03 — server-controlled Run reference Setup integration

The source adapter at `src/beta_engine/application/atp_reference_package_adapter.py`
loads only the two fixed repository-maintained JSON Package documents. The
`atp_tour_1990_2026_reference_setup` canonical Setup freezes Category and
Series together. It enforces document identity/type, technical schema, strictly
tennis-namespaced entity kind/scope, original 1990–2026 reference span,
`not_squash_rules`, and exact Series-to-Category source references.
There is no automatic sporting semantic translation.

The dedicated Admin page is `/admin/packages/atp-tour-reference` (Czech/English). Its catalog and preview are read-only; it never creates playable Editions, a Calendar or ranking results. After selecting a writable Run and Branch, confirming is distinct from explicitly saving the Working Draft. Existing non-ATP drafts are not silently deleted.

For an **existing writable Run/Branch** (URL-encode both IDs), the endpoints are:

- `GET /admin/reference-packages/atp-tour-1990-2026` — global, read-only immutable source manifest and fingerprints

- `GET /admin/runs/{run}/branches/{branch}/packages/source-atp-reference/catalog`
  — source manifest and deterministic hashes, with no Run mutation
- `POST /admin/runs/{run}/branches/{branch}/packages/source-atp-reference/preview`
  with `{}` — compact but fingerprint-bound Setup preview; no Run mutation. Its HTTP response excludes the full source JSON and includes `document_identity` linked to the independently loaded source manifest
- `POST /admin/runs/{run}/branches/{branch}/packages/source-atp-reference/confirm`
  — CAS-protected, atomic installation of **both** source Packages into the
  Working Draft through the existing generic Run Package service

Confirm request fields mirror ordinary source Package confirm:
`command_id`, `expected_head_revision_id`,
`expected_draft_version`, `expected_state_fingerprint`,
`expected_preview_fingerprint` and optionally `conflict_resolutions`.
All expected values must be copied from the immediately reviewed Preview.
Unlike generic partial Setup commands, the ATP server endpoint **rejects**
`selected_entities`: no partial/orphaned historical Series installation.
Conflicting local overrides require explicit source/Run resolution as in the
native Package contract. No implicit Save: use the existing Working Draft
Save endpoint, then normal immutable Saved Revision/Branch machinery.

**What this integration does:** store 11 Category and 164 Series entities with
stable source identity, audited references, source fingerprints and isolated
Run-owned snapshots; safely preview and explicitly apply/Save those
historical references. It does **not** create historical tournament Editions,
match results, points matrices, a Calendar, or change the squash simulation.
This reference Setup is deliberately not offered as a fully playable package.
The dedicated ATP reference UI is available from Packages. The generalized dynamic source Package Catalog remains World-only; this ATP entrypoint is a fixed historic source, not a universal Category/Series catalog.

**Future immutable versioning:** the initial reference documents use
`source_version: 1`. After a source version is merged/applied, changing its
content under the same version triggers the core conflict detection;
future historical corrections must be published with a higher source version
and valid parent source fingerprint. Historical evidence remains subject to
the independent licence-provenance audit.

## 2026-11-03 — Düsseldorf 2014 → Geneva 2015 ATP 250 licence continuity

The original historical data treated **2013–2014 Düsseldorf** and
**Geneva Open from 2015** as distinct source identities because the exact
legal transfer had not been independently verified. That conservative
boundary was justified then, but contemporaneous evidence now resolves it:

- [19 November 2014 report quoting ATP's approval of the Düsseldorf-to-Geneva licence move](https://www.welt.de/print/welt_kompakt/duesseldorf/article134566672/Aus-fuer-ATP-Turnier-besiegelt.html)
- [Separate contemporaneous ATP announcement coverage](https://www.zeit.de/news/2014-11/19/tennis-kuenftig-in-genf-aus-fuer-atp-turnier-im-rochusclub-perfekt-19193604)
- [Geneva organiser's own tournament history naming the licence's Düsseldorf origin](https://gonetgenevaopen.ch/le-tournoi/)

The two Düsseldorf source periods (2013–14) have been moved into the
continuing `geneva` identity from 2015 onward. Dated venues make that
transition inspectable without treating tournament-name changes as new
played events. The redundant `duesseldorf_2014` Series ID has been
removed, leaving **164** historical Series. No tier count or year-effective
membership changes.

**Distinct historical boundary:** the Geneva clay World Series held in
1990–1991 is already attributed to `cologne_1992_clay`, which moved to
Cologne in 1992. That is **not** the 2015 Geneva ATP 250 licence.
The historical ATP operated tournament must never be confused with the
separate World Team Cup at Düsseldorf.

## 2026-11-03 — corrected two independent 2013 → 2014 US licences (Memphis / San José)

Independent contemporary licence reporting exposed a **substantive identity bug**:
the earlier reference model treated **Memphis 2013 ATP 500** and **Memphis 2014
ATP 250** as one Series while ending **San José 2013 ATP 250** as a separate
historic Series. That preserves *tier counts* but **misrepresents two legally
different ATP sanctions**.

The actual ATP-approved transfers, in effect **2014**, are:

| 2013 source event | 2014 successor | Continuing Series ID |
| --- | --- | --- |
| **Memphis ATP 500** | **Rio de Janeiro ATP 500** | `rio` |
| **San José ATP 250** | **Memphis ATP 250** → New York 2018 → Dallas 2022 | `dallas` |

The earlier `san_jose_2013` standalone ID was therefore eliminated;
its 1990–2013 **San Francisco → San José** Category and host history was
moved under `dallas` without changing any year-effective Category.
The old 1990–2013 **Memphis Championship/Gold/500** Category and host
history was moved under `rio`, retaining Rio's year-effective ATP 500
membership from 2014 onward and 2021 known cancellation. Distinct
`rio_carpet_1990` World Series remains **separate** from that licence.
The reference now contains **165 Series**, and **all 37 derived annual
Category counts remain unchanged**.

Proof is unusually strong because it directly describes the *sanctions*
rather than guessing continuity from a tournament name:

- [Contemporary 23 April 2012 ATP Board-approved two-sanction agreement](https://www.sportsbusinessjournal.com/Daily/Issues/2012/04/24/Leagues-and-Governing-Bodies/ATP/)
- [2012 Tennis.com report explicitly distinguishing San José→Memphis and Memphis→Rio](https://www.tennis.com/news/articles/san-jose-atp-tourney-to-close-rio-gets-event)
- [2014 confirmation of the San José licence operating in Memphis](https://www.tennis.com/news/articles/usta-buying-memphis-tournament)
- [ATP's 2014 Results Archive showing both Memphis and Rio as separate tournaments](https://www.atptour.com/en/scores/results-archive?year=2014)

This correction does **not** backfill sporting results, historical ranking
points, invented editions, live Run data or a Package Apply adapter.

## 2026-11-03 — recent Canadian Masters alternating hosts (2024–2026)

The **same** Canadian Masters 1000 Series alternates its actual men's tournament
venue: **Montréal in 2024, Toronto in 2025, Montréal in 2026**.
The source now records explicit dated hosts and official ATP evidence rather than
allowing the 2026 current-host field to suggest Toronto 2025 happened in Montréal.
Evidence: [ATP 2024 results archive](https://www.atptour.com/en/scores/results-archive?year=2024),
[ATP 2025 Toronto results](https://www.atptour.com/en/scores/results-archive?year=2025),
and [ATP Montréal 2026 final report](https://www.atptour.com/en/news/montreal-2026-results).
The Category and annual Series memberships do **not** change.

## 2026-11-03 — independent 2025 Belgrade → Athens host correction

The official [ATP announcement of 4 August 2025](https://www.atptour.com/en/news/belgrade-athens-announcement-august-2025) confirms that the **2024 Belgrade Open ATP 250** sanction was moved to **Athens, Greece in 2025**, where it was held as the **Hellenic Championship** (2–8 November 2025, indoor hard). The 2025 `belgrade` Series membership was already correct, but its physical **venue history was missing** and the fixed displayed title `Belgrade Open` was misleading for the played Athens year.

The source retains **one unchanged Series ID** `belgrade` across those two annual ATP 250 category records, adds dated 2024 Belgrade / 2025 Athens venue evidence and labels both names. This is **not** the unrelated `athens_1994` ATP World Series and cannot be assumed to be the unresolved 2026 late-year ATP 250 TBD calendar slot. No played roster count or canonical season snapshot changes.

## 2026-11-03 — independent reference review: 2026 Next Gen location

The category roster was checked against the published [ATP 2026 calendar](https://www.atptour.com/en/news/what-is-the-2026-atp-tour-calendar/). That 2025 publication still had the Next Gen Finals host **TBC**, while the historical reference source stored `null` for 2026 city/country. The competition's [9 September 2026 official announcement](https://www.nextgenatpfinals.com/en/news/reggio-calabria-to-host-2026-next-gen-atp-finals) resolves the host to **Reggio Calabria, Italy**, with the event scheduled for **9–13 December 2026**. It is the *same* continuing Next Gen Series, not a new ATP 250/500/1000 tournament.

The `next_gen_atp_finals` 2026 host is now **Reggio Calabria / ITA** with announcement date and official source. The previous years, 2020 cancellation and the 2026 provisional roster/derived snapshots do not change. The main 2026 Tour roster remains provisional because the published ordinary ATP 250 schedule included a **TBD** slot and year-end completeness is not yet established.

## 2026-11-03 — corrected 2013 Los Angeles → Bogotá → Los Cabos ATP sanction

Independent verification found a real identity defect in the 2013 source roster:
the `los_angeles_2013` reference falsely suggested a 2013 Los Angeles
ATP 250, when the last Los Angeles ATP edition was in **2012**.
The ATP-approved sale transferred its sanction to **Bogotá for 2013**;
Bogotá's tournament licence subsequently moved to **Los Cabos for 2016**.

The registry now uses one continuous `los_cabos` Series identity for
**Los Angeles through 2012 → Bogotá 2013–2015 → Los Cabos from 2016**,
with separately documented year-effective city and Category history.
The obsolete `los_angeles_2013` ID was removed, leaving **166** unique
historical Series; annual snapshots for 1990–2013 were regenerated without
changing **any** played tier census (2013 remains 9 Masters / 11 ATP 500 /
40 ATP 250, plus singles Finals). The 2026 roster stays provisional.
This is *source reference* provenance, not a playable Edition or game rule.

Independent sources: [ATP 2012 Los Angeles results](https://www.atptour.com/en/tournaments/los-angeles/423/overview);
[ATP-approved sale to Bogotá, December 2012](https://www.tennis.com/news/articles/atp-finalizes-sale-of-l-a-tournament-to-bogota);
[ATP 2013 Bogotá results archive](https://www.atptour.com/en/scores/results-archive?year=2013);
[Bogotá-to-Los Cabos rights sale, November 2015](https://matchtenis.com/el-atp-de-bogota-se-traslada-a-mexico/).

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
**124 identities** across 2026 ATP Tour fixtures and selected older masters.
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
- **The Belgrade 2024 ATP 250 sanction played in Athens in 2025** as the
  Hellenic Championship, while Metz played its final 2025 edition. Neither
  is asserted in the published 2026 ATP 250 Series roster. **Estoril** appears in 2024 and 2026,
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
- **Düsseldorf 2013–14 → Geneva 2015** is one *confirmed* ATP 250
  tournament sanction, independently documented by contemporaneous
  ATP-announcement reporting and the Geneva organiser's history. The
  shared `geneva` source identity preserves each year's real host.
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

- **Two different ATP licences were present in Memphis across 2013–14.**
  The **2013 Memphis ATP 500 licence** transferred to **Rio de Janeiro
  for 2014**, and persists under source identity `rio`. The separate
  **2013 San José ATP 250 licence** moved to Memphis for **2014**, then
  New York in 2018 and Dallas in 2022, upgrading to 500 in 2025; that
  continuous identity is `dallas`. A city staying on the calendar did
  **not** mean that the same licence was downgraded.
- **Valencia 2013–14 was ATP 500**; Valencia 2015 was a 250;
  the licence transferred to Antwerp in 2016. This is one
  time-effective `brussels` identity, not multiple invented events.
- **Halle, Queen's Club and Vienna in 2013–14 were ATP 250**,
  subsequently promoted to 500 for 2015, and must not have
  modern tier labels applied to past years.
- **Viña del Mar 2013–14** is referenced under `cordoba`,
  followed by **Quito 2015–18** and **Córdoba 2019**.
- **San Jose and Bangkok** were played ATP 250 events in 2013 but have
  no 2014 Series membership under those source identities. **Los Angeles**
  held its last ATP edition in **2012**; its ATP sanction was sold for
  **Bogotá in 2013** and that same licence moved to **Los Cabos in 2016**.
  This continuous Series is `los_cabos`, with year-specific historical
  city records; there was **no 2013 Los Angeles ATP Tour edition**.
- **Düsseldorf 2013–14 → Geneva from 2015** is one confirmed licensed
  ATP 250 transfer; the `geneva` source identity carries both hosts.
  This does **not** merge the unrelated Geneva clay Tour event from
  1990–1991 (source `cologne_1992_clay`).

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

**Coverage boundary after this expansion:** **24 consecutive played-tier
seasons (2002–2025)**, with 1990–2001 still incomplete, 2026
provisional, and the entire runtime Category/Series import/Save/Calendar
adapter unimplemented. No title points, draws, qualification or
match/player data was added. Keep this PR Draft.


## 2006 played ATP Tour tiers, source-verified (2026-11-02)

**2006 historical ATP-only roster:** nine Tennis Masters Series,
nine International Series Gold, 44 International Series and the
separate Tennis Masters Cup; **63 source Series identities**.
The 44th International Series event, which was absent from the
2007 played main Tour calendar, is **Palermo, Italy**.

- Official ATP 2006 results archive:
  https://www.atptour.com/en/scores/results-archive?year=2006
- Official ATP Palermo 2006 edition (tournament identifier 325):
  https://www.atptour.com/en/tournaments/palermo/325/overview
- [2006 ATP Tour year and complete played category calendar](https://de.wikipedia.org/wiki/ATP_Tour_2006)
  (independent secondary classification cross-check).
- [Contemporary ATP 2006 calendar discussion](https://www.forodeltenis.com/noticias-de-tenis-y-tenis-en-general/calendario-atp-2006/)
  is *prospective only*: e.g. Milan/Ho Chi Minh City can appear on preliminary listings
  even though the final played season used Zagreb/Mumbai. The prospective listing
  must never override results-backed played membership.

The existing Series identities connect all 43 played 2007 International
Series to their evidence-supported 2006 predecessors. No fictitious second
Mumbai/Bangalore, Sopot/Warsaw, Chennai/Pune, Valencia/Antwerp, or
Nice/Lyon/Marseille lineage is minted. **Palermo** is a new, separately
sourced Series reference; its actual earlier ATP years remain to be
researched and must not be extrapolated from the 2006 success.

The generator now independently count-gates **20 consecutive played
ATP Tour tier rosters 2006–2025** with original era categories. The year
2006 has **44** International Series (2007 has **43**), and ATP Finals is
tracked separately from counted tiers. Grand Slams, World Team Cup,
Davis Cup, Challenger/ITF and incomplete 2006 preliminary events are excluded.

**Remaining work:** 1990–2005 incompletely sourced, 2026 provisional,
historical draws/points/rounds not imported, and no production Package
Catalog/Run Apply/Save semantic integration. Source-only, keep Draft.

## ATP Tour 2005 actual original tiers: source reconciliation (2026-11-02)

2005 played original ATP Tour events: **9 Tennis Masters Series,
9 International Series Gold, 44 International Series and a separate
Tennis Masters Cup**. Four Grand Slams, Davis Cup, World Team Cup and
Challengers/ITF are outside Package scope.

Source: https://www.atptour.com/en/scores/results-archive?year=2005
Historical category/calendar cross-check:
https://de.wikipedia.org/wiki/ATP_Tour_2005

Verified venue/licence transitions to played 2006:
- Milan to Zagreb (same source ID sofia):
  https://www.eurosport.it/tennis/atp-milano/2005/_sto787065/story.shtml
- Scottsdale to Las Vegas (las_vegas_2008):
  https://lasvegassun.com/news/2005/oct/19/columnist-ron-kantowski-dont-turn-channel-for-andr/
- Ho Chi Minh City to Mumbai (bangalore_2008):
  https://vnexpress.net/giai-quan-vot-mumbai-open-se-thay-the-vietnam-open-1189362.html
- St. Pölten to Pörtschach (poertschach_2008):
  https://www.derstandard.at/story/2389037/poertschach-bekommt-stpoelten-lizenz

Milan 2005 and Zagreb 2006 refer to one sanctioned Series, not two
annual events; the 2005 Vietnam Open is ATP main Tour, NOT a Vietnamese
Challenger. Played Palermo 2005 extends the existing 2006 source.

**21 consecutive played-tier year rosters 2005–2025** now source-gated.
1990–2004 remain incomplete, 2026 provisional. Source documents do not
include actual Edition draws, player results, per-round award point tables,
or production Package Apply/Run/Save. Keep Draft.


## ATP Tour 2004 original played categories (2026-11-02)

The 2004 main ATP Tour (not pre-1990 tennis, Challenger/ITF or Grand Slams)
played **9 Tennis Masters Series + 9 International Series Gold +
44 International Series**, plus the separate Tennis Masters Cup (Houston).
The 2004 ATP annual schedule has four Slams and a World Team Cup: those are
outside this reference Package scope. This makes exactly **63 source Series
identities** for the 2004 ATP main Tour-only census.

- [Official ATP played results archive 2004](https://www.atptour.com/en/scores/results-archive?year=2004)
- [2004 original Category classification and city-by-city schedule](https://de.wikipedia.org/wiki/ATP_Tour_2004)
- [2004 ATP Tour tier counts](https://en.wikipedia.org/wiki/2004_ATP_Tour)
- [ATP 2005 Shanghai → Ho Chi Minh City tournament licence announcement](https://www.abc.net.au/news/2005-04-27/vietnam-to-stage-its-first-atp-event/1559488)
- [ATP Long Island → New Haven 2005 licence transfer reporting](https://www.nhregister.com/news/article/Pilot-Pen-wants-to-add-men-s-tourney-in-August-11652949.php)

Two important correctly shared stable Series, not double-counted places:
- `bangalore_2008`: *Shanghai regular International Series 2004* →
  Vietnam Open in Ho Chi Minh City 2005 → Mumbai 2006–07 →
  cancelled Bangalore 2008. **Distinct from the ATP Finals**, which
  took place in Houston in 2004 and Shanghai in 2005–08.
- `winston_salem`: Long Island 2004 → New Haven 2005–10 →
  Winston-Salem 2011 and onward. All hosts belong to the documented
  licensed historical Series, no fictitious extra annual event.

The generator now verifies **22 consecutive played-category rosters
(2004–2025)** in the correct historic tiers. 1990–2003 remains incomplete,
2026 remains provisional; the source does not implement live Package
Catalog, native sporting Editions, match/draw/point data, Apply, or Saved
Run integration. Keep this existing PR Draft until latest-head CI passes.


## ATP Tour 2003 historical original Category rosters (2026-11-02)

Played Tour tiers were **9 Masters Series, 9 International Series Gold,
44 International Series**, plus **one distinct Tennis Masters Cup in
Houston**. The 2003 census contains 63 ATP-only source Series identities.
Grand Slams, World Team Cup, Davis Cup and lower circuits are excluded.

- [Official ATP 2003 played results archive](https://www.atptour.com/en/scores/results-archive?year=2003)
- [Contemporary-era classification/calendar source](https://de.wikipedia.org/wiki/ATP_Tour_2003)
- [ATP archive: Copenhagen played 2003](https://www.atptour.com/en/tournaments/copenhagen/481/overview)
- [ATP archive: Beijing played 2004](https://www.atptour.com/en/tournaments/beijing/590/overview)
- [Industry report, 2004 removed Copenhagen / added Beijing](https://www.sportscommissions.org/Portals/sportscommissions/Documents/Industry%20News/Sports%20Business%20International_The%20Bid%20Book_%20June%202013.pdf)

Copenhagen played in 2003, Beijing joined the main Tour in 2004.
No direct underlying ATP sanction/license transfer between the two has
been verified; separate source identity `copenhagen_2003` is used,
**not** an invented historical Beijing Series. Before 2003, Copenhagen
Tournament years remain unverified in this Package.

The Canadian Masters in 2003 had Montreal as its played host; 2004
was Toronto. The 2003 Masters Cup was in Houston, and Shanghai was a
regular International Series 2003/2004, **not** the city of the 2003
year-end Finals. Existing source histories preserved.

This raises the category-census coverage to **23 consecutive actual
played years, 2003–2025**. Still source-only, no per-round historic
point matrices, Draw/Edition/Result objects, Run Apply/Save or production
Package adapter. **1990–2002 remain incomplete; 2026 provisional.**


## ATP 2002 Tour-only played original tier roster — source audit 2026-11-02

**Played main ATP Tour 2002:** 9 Tennis Masters Series,
9 International Series Gold, **43 International Series** and one
separate Tennis Masters Cup (Shanghai): **62 source Series identities**.
The four Grand Slams, the World Team Cup in Düsseldorf, Davis Cup
and Challenger/ITF are excluded. This difference from 2003's 44
International Series is **real**, not silently completed by carrying
2003's Metz or Shanghai regular Tour event into 2002.

Sources:
- [ATP official actual played Results Archive 2002](https://www.atptour.com/en/scores/results-archive?year=2002)
- [Historical 2002 Category/calendar cross-check](https://de.wikipedia.org/wiki/ATP_Tour_2002)
- [Mallorca venue/licence → Valencia 2003, contemporary ATP board decision](https://as.com/masdeporte/2003/03/24/polideportivo/1048460403_850215.html)
- [ATP-authorised Tashkent President's Cup → Bangkok 2003](https://www.sports.ru/tennis/2875657.html)
- [2002 Hong Kong Salem Open finale and proposed Beijing move](https://www.scmp.com/article/392880/juan-last-hurrah-curtain-falls-open)
- [Official ATP report of the 2002 Tennis Masters Cup in Shanghai](https://www.atptour.com/en/news/nitto-atp-finals-50th-anniversary-shanghai-feature)

The 2002 Mallorca ATP International Series is **not** the separate
post-2021 Mallorca grass Tour event. It is attached to Valencia's
historically continuous licensed source identity `brussels`. Similarly,
`bangkok_2013` had the 2002 Tashkent ATP Tour event as its authorised
licence predecessor.

**Hong Kong name collision:** The `hong_kong` source played **in
Chennai, India** in 2002. The concurrent Salem Open was played **in
Hong Kong**; it uses a separate year-specific source
`hong_kong_salem_2002`. Do not link the two. Contemporary plans
to move the Salem Open to Beijing in 2003 did **not** result in
a played ATP 2003 Beijing edition; a 2004 legal connection is not
asserted without direct evidence.

**Archive correction:** Toronto hosted the 2002 Canadian Masters,
not Montreal as described in some secondary 2002 calendar summaries.
The 2002 Tennis Masters Cup was played in Shanghai, separately
from the Shanghai regular ATP International Series played 2003–04.

**24 consecutive source-reconciled played Tier rosters (2002–2025)**.
1990–2001 are incomplete, 2026 provisional. These are source data
only and do not import real annual Editions, draws, per-round points,
or production Apply/Save to Squash Engine. Keep the PR Draft.


## ATP Tour 2001 original played levels — source audit 2026-11-02

2001 actual Tour-only main tiers: **9 Tennis Masters Series,
9 International Series Gold, 46 International Series**, plus separate
Tennis Masters Cup in Sydney: **65 annual ATP-only Series identities**.
Four Grand Slams, ATP World Team Cup, Davis Cup, Challenger/ITF excluded.

Sources: ATP official results archive https://www.atptour.com/en/scores/results-archive?year=2001 ;
historical original ATP Category annual listing https://de.wikipedia.org/wiki/ATP_Tour_2001 ;
contemporary 2001 Stuttgart Masters → Madrid 2002 licence transfer
https://www.emol.com/noticias/deportes/2001/12/20/74392/tenis-masters-series-de-stuttgart-se-muda-a-madrid.html ;
2001 Roddick first title at Atlanta Verizon Challenge
https://www.upi.com/Archives/2001/04/29/Roddick-wins-first-pro-title/1182988516800/ ;
2001 Bogotá tournament and 2002 ATP cancellation for safety
https://www.eltiempo.com/archivo/documento/mam-1352814 .

Original source identities: `stuttgart_indoor_masters` played the
2001 indoor Masters, while the `stuttgart` Mercedes Cup was a distinct
outdoor clay International Series Gold concurrently played in 2001.
2002 Madrid Masters is a separate historic host identity `madrid`
with sourced Stuttgart transfer metadata, respecting existing reference
design and preventing a fictitious played 2001 Madrid event.

Two separate played 2001 US Tour events were Atlanta's clay Verizon
Challenge (`atlanta_verizon_2001`, final edition) and Indianapolis
(`atlanta`, original Indy licence). Bogota `bogota_colombia_2001`
was played then its planned 2002 Tour event cancelled for security;
Challenger fixtures are excluded.

The ordinary Shanghai Heineken Open was played in 2001 and again
2003–04 under `bangalore_2008`, while the 2001 year-end Finals were
held in Sydney. 2002 Shanghai hosted the Masters Cup instead of
Shanghai regular Tour, not a double-counted simultaneous fixture.

**25 played ATP-only original/rebranded tier rosters 2001–2025** have
year-count validation gates. 1990–2000 incomplete; 2026 provisional.
These remain source-only Category/Series, not playable historical
Edition objects, ranking rules, or production Run Apply/Save.

## ATP Tour 2000 — played original categories and licensing (2026-11-02)

The played original-category ATP Tour 2000 included **9 Tennis Masters
Series, 11 International Series Gold and 44 International Series**,
plus the year-end singles Tennis Masters Cup at **Lisbon, Portugal**.
This represents **65 distinct ATP-only historical source Series
identities for the 2000 calendar**. Separately organized Grand Slams,
Sydney Olympic tennis, Davis Cup, World Team Cup and Challengers/ITF
do not belong in this scoped source package.

Sources:
- Official played ATP Results Archive, year 2000:
  https://www.atptour.com/en/scores/results-archive?year=2000
- Actual original-category ATP annual event calendar:
  https://de.wikipedia.org/wiki/ATP_Tour_2000
- Contemporary provisional ATP 2000 fixture calendar:
  https://www.record.pt/modalidades/tenis/detalhe/calendario-atp-tour-para-2000

The **2000 London AXA Cup** was a played **International Series Gold**
indoor event, distinct from the simultaneously played **Queen's Club**
grass International Series. The indoor tournament license returned
from London to its Milan owners for **Milan Indoors 2001** (then a lower
International Series tier). The one historical reference identity
is source ID sofia, with year-specific original Category references.
Independent contemporary license report:
https://www.independent.co.uk/sport/tennis/london-loses-atp-tour-event-to-milan-637139.html

There are three further year-effective Category differences:
- 2000 Washington was Gold; 2001 Washington was International Series.
- 2000 Indianapolis was Gold; 2001 Indianapolis was International Series.
- 2000 Dubai was International Series; 2001 Dubai was Gold.

Original 2000 cities carried forward with the same historical sanction
or competition identity: Mexico City to Acapulco in 2001; Orlando
U.S. Men's Clay Court Championship to Houston in 2001;
Chile Open Santiago to Viña del Mar in 2001; Dutch Open Amsterdam to
Amersfoort in 2001. See original year archive and Orlando played draw:
https://www.stevegtennis.com/draw-results/atp/U.S.%20Men%27s%20Clay%20Court%20Championships%20-%20Orlando/2000

Three additionally played source Series in 2000 are introduced
separately: **San Marino**, **Toulouse**, **Brighton**. None is fabricated
as a 2001 event. The 2000 Toulouse ATP event was its last:
https://en.wikipedia.org/wiki/2000_Adidas_Open_de_Toulouse

Year-end separation is crucial: Singles Tennis Masters Cup in
**Lisbon**, and doubles World Championships in **Bengaluru**.
The source atp_finals represents singles only, not a fictitious
2000 Bengaluru singles event. Source:
https://en.wikipedia.org/wiki/2000_Tennis_Masters_Cup_and_ATP_Tour_World_Championships

The 2000 main Tour category census is deterministically validated in
the year resolver. **26 consecutive played original/rebranded ATP Tour
Tier rosters (2000–2025)** are now included. **1990–1999 incomplete**,
2026 provisional. References are source-only, not historical match
Edtions, draw/result payloads, points tables, Package Catalog importer,
or native Squash Engine Apply/Save. Keep Draft pending CI and review.


## ATP Tour 1999 — original Super 9 / Championship / World Series (2026-11-02)

In 1999 the real main ATP Tour used its original native tier labels, **not**
the 2000 Masters/International split nor modern ATP 1000/500/250. The
**played** 1999 men's ATP Tour census is **9 ATP Super 9, 11 ATP
Championship Series, 45 ATP World Series**, plus the single separate
singles ATP Tour World Championships in **Hannover**. There are therefore
**66 Tour-only annual source Series identities**. 1999's Grand Slam Cup,
the four majors, the World Team Cup, Davis Cup, Hopman Cup and
doubles-only Worlds in Hartford are outside this singles Tour roster.

Original sources:
- Official 1999 ATP played archive: https://www.atptour.com/en/scores/results-archive?year=1999
- Historical 1999 original-tier tournament listing: https://de.wikipedia.org/wiki/ATP_Tour_1999
- 1999 ATP tier aggregates / calendar: https://en.wikipedia.org/wiki/1999_ATP_Tour
- ATP original 1999 singles World Championships at Hannover:
  https://www.atptour.com/-/media/23da5115363646fd89d16716e5b35a2e.pdf
- 1999 separate year-end doubles at Hartford:
  https://www.atptour.com/-/media/08887c4b3be347dd8a2d701c23fcd587.pdf

**1999 historic source identities:** `singapore_1999` is the 1999
Heineken Singapore indoor **Championship Series** (not World Series
and not a played 2000 Singapore). `prague_1999`, `merano_1999`,
and `boston_1999` are played **World Series** events: Prague was
cancelled for 2000 because organisers did not deposit the ATP-required
financial guarantee; this is not a fictional 2000 ATP Czech Open.
- ATP Singapore original edition: https://www.atptour.com/en/tournaments/singapore/326/overview
- ATP Prague 1999: https://www.atptour.com/en/tournaments/-/379/overview
- Contemporary Prague 2000 Tour cancellation:
  https://cesky.radio.cz/zpravy-pondeli-03-cervence-2000-8056454
- ATP Merano 1999: https://www.atptour.com/en/tournaments/crans-montana/473/overview
- ATP Boston 1999: https://www.atptour.com/en/tournaments/boston/80/overview

One material licence move: the 1999 **Bournemouth Samsung Open** was
played on **green outdoor clay**, then transferred as the **same ATP
Tour Series identity** to **Brighton 2000**, played indoors on hard.
The `brighton_2000` source now holds BOTH years with host/surface
history; there must not be a duplicate 1999 Brighton or 2000
Bournemouth annual Series.
- Original tournament history: https://en.wikipedia.org/wiki/Brighton_International

The 1999 London indoor **Guardian Direct Cup** was a Championship
Series tournament under historical `sofia`; the distinct grass
**Queen's Club** was World Series. In 2000 the London indoor AXA Cup
became International Series Gold; the historical source licence
eventually returned to Milan 2001 and later Zagreb/Sofia. Historic
year-effective Category transitions are intentional, not a score
or points equivalence.

**27 consecutive played ATP Tour source tier rosters 1999–2025** are
now gated with historical category names. 1990–1998 remain incomplete;
2026 is provisional. This reference data does not create playable
historical Edtions, draws, results, points, or native Package Apply/Save.
Keep existing owner-only Draft PR until latest-head CI and review.


## 2026-11-03 — 1998 full played ATP Tour original-category roster

The new verified 1998 single-season census completes **28 consecutive played ATP main Tour tier rosters (1998–2025)**; 1990–1997 remain **unverified/incomplete**, and 2026 stays a provisional calendar rather than final played results. The canonical 1998 year source contains **9 ATP Super 9**, **12 ATP Championship Series**, **52 ATP World Series**, and **one ATP Tour World Championships singles Final** in Hannover: **74 ATP-only source Series identities**. The four majors, ITF and team tournaments are excluded. This is reference metadata, **not** native playable Editions, results, rankings or imported sporting rules.

Sources: [official 1998 ATP Results Archive](https://www.atptour.com/en/scores/results-archive?year=1998), [original 1998 ATP Tour tier totals](https://en.wikipedia.org/wiki/1998_ATP_Tour), [independent 1998 tier/location crosscheck](https://tennis-db.com/tournaments?season=1998), [ATP Finals historical official PDF](https://www.atptour.com/-/media/23da5115363646fd89d16716e5b35a2e.pdf), [Mexican Open 1998 Mexico City→2000 Mexico City→2001 Acapulco history](https://www.atptour.com/-/media/0c8acad38fa341ad9237f9197986ebac.pdf).

Seven new historical-only source IDs are introduced when no safe existing identity existed: `split_1998`, `antwerp_1998`, `philadelphia_1998`, `bologna_1998`, `new_haven_1998`, `ostrava_1998`, `santiago_1998`. All other 1998 played Tour entries reuse already established Series IDs and receive explicit year-specific categories and ATP archive hosts. 1998 New Haven Championship and Long Island World Series were distinct simultaneous events; do not collapse them into the later Winston-Salem licence chain.

**Cross-source corrections:** third-party display aliases can be anachronistic. The official 1998 ATP archive lists **Split** (not Geneva), **Lyon** (not Montpellier) and **Singapore** (not Brisbane). The persistent source Series `montpellier` was hosted in Lyon in 1998, `brisbane` in Adelaide, and `singapore_1999` in Singapore. Rotterdam was 1998 World Series and 1999 Championship Series; the Mexico City 1998 original World Series predates its 2000 Gold tier and eventual Acapulco host. 1998 Toronto and 1999 Montreal are separate years of one Canadian top-tier Series.

`PRE_2000_PLAYED_TIER_COUNTS` now gates 1998 against the original 9/12/52 totals; tests assert the original-tier vocabulary, distinct 1998 events and year-host continuity, and reject falsified played-tier classifications or cancellations. The 37 annual source snapshots remain deterministic. **These verification counts are not per-match/results evidence, nor a mandate to auto-Apply a package to any Run.**


## 2026-11-03 — 1997 played original ATP categories, 29-year consecutive run

The reconstructed **1997** main ATP Tour source tier roster includes **9 ATP Super 9**, **12 ATP Championship Series**, **53 ATP World Series** and **one year-end ATP Tour World Championships in Hannover**, **75 ATP-only singles tournament identities** total. Grand Slam events (four), the non-ATP Grand Slam Cup, ITF/Challengers and team tournaments are out of scope. This extends *year-level Category/Series* completed coverage to **1997–2025** (29 consecutive played years); **1990–1996 remain incomplete**, and 2026 remains provisional.

Evidence: [1997 ATP official played results archive](https://www.atptour.com/en/scores/results-archive?year=1997), [1997 ATP Tour original-tier schedule](https://en.wikipedia.org/wiki/1997_ATP_Tour), [independent historical categories](https://tennis-db.com/tournaments?season=1997), [ATP 1997 year-end Hannover Finals archive](https://www.atptour.com/-/media/23da5115363646fd89d16716e5b35a2e.pdf). Independent modern display aliases are never allowed to overwrite original tournament venue.

Historical identities explicitly reconciled:
- **Croatian Indoors: Zagreb 1997 → Split 1998** in one historical `split_1998` source identity, rather than fictitious parallel 1998 Zagreb and Split. 2006 Zagreb licensing is not asserted to follow from 1998.
- **Marbella 1997 → Mallorca 1998** shares the historic Valencia Open `brussels` source identity, later transferred to Valencia. [Venue lineage](https://newikis.com/en/Valencia_Open).
- **Milan 1997** Championship Series shares `sofia` history, distinct from **Zagreb 1997** World Series. The modern venue/name Sofia must never backfill 1997.
- **Coral Springs 1997** is the actual host of the modern Delray Beach event identity; independent historical display sometimes backfills the later Delray host. [Original 1997 event](https://en.wikipedia.org/wiki/1997_International_Tennis_Championships) and [ATP player bio](https://www.atptour.com/en/players/Jason_Stoltenberg/S331/bio).
- **1997 Beijing** Nokia Open is source ID `beijing_1997` separate from modern China Open, which ATP calls inaugural in 2004, until verified transfer/continuity evidence is found. [ATP historical profile](https://www.atptour.com/en/tournaments/beijing/7307/overview), [2004 new China Open release](https://www.atptour.com/en/news/beijing-2024-20-years-on).
- **Grand Prix de Lyon 1997** is hosted in Lyon, regardless of later Montpellier brand; **Canadian Open 1997 Montreal / 1998 Toronto** and other year-specific actual locations are recorded.

The deterministic `PRE_2000_PLAYED_TIER_COUNTS` gate now validates 1997's 9/12/53 played roster with original names. New tests assert Category, annual host evidence and fail-closed false tier/cancellation. Source only: **no imported played Editions, scores, points, licence rights, Package Catalog or Run Apply/Save**.


## 2026-11-03 — 1996 original ATP Tour played category roster

**1996** is source-reconciled as **9 ATP Super 9 + 11 ATP Championship Series + 57 ATP World Series + one ATP Tour World Championships (singles, Hannover)**, a total of **78 ATP-only source identities**. This achieves **30 consecutive original played-category seasons, 1996–2025**, without retrofitting 2009 or 2026 category labels to the 1990s. **1990–1995 remain incomplete**, and 2026 is a provisional not final played season.

Sources:
- [ATP 1996 official results archive](https://www.atptour.com/en/scores/results-archive?year=1996) (cross-check played single-year host/results)
- [1996 original tier schedule](https://de.wikipedia.org/wiki/ATP_Tour_1996) (explicit original Championship and World Series categories)
- [1996 independent edition inventory](https://tennis-db.com/tournaments?season=1996) (83 editions including four non-ATP Grand Slams and Atlanta Olympics, rather than 83 ATP-only events)
- [ATP 1996 Finals tournament history](https://www.atptour.com/-/media/83956b6ae89248d3a2a632428df04269.pdf), singles hosted Hannover; doubles separately held Hartford

Five narrowly scoped World Series source identities were added because no established equivalence was supported: `jakarta_1996`, `bermuda_1996`, `seoul_1996`, `porto_1996` and `tel_aviv_1996`. The earlier 1996 Seoul and Tel Aviv licences are not assumed to equal the temporary 2022 Tour events. Every existing 1996 ATP Series receives its actual year-specific original Category and city, using stable source IDs rather than duplicating relocated tournaments.

Verified era-correct continuity:
- **New Delhi (1996) → Chennai/Madras (1997)**: same Gold Flake Tour licence inherited by current `hong_kong` source family. [Contemporary 1997 report](https://www.indiatoday.in/magazine/sport/story/19970430-as-gold-flake-open-proved-life-on-tennis-tour-is-often-hard-and-unforgiving-831328-1997-04-29).
- **Pinehurst (1996) → Orlando (1997)**: U.S. Men's Clay Court Championships, same `houston` source family; [contemporary relocation report](https://www.sportsbusinessjournal.com/Daily/Issues/1996/09/03/Leagues-Governing-Bodies/WALT-DISNEY-TO-HOST-US-CLAY-COURT-TITLE-OPEN-NEWS-NOTES/), [tournament historical record](https://www.mensclaycourt.com/web/DATA/2024%20US%20Clay%20Media%20Guide.pdf).
- **Marbella (1996–1997) → Mallorca (1998)**: one `brussels` source family; [Valencia Open venue history](https://en.wikipedia.org/wiki/Valencia_Open).
- **Zagreb (1996–1997) → Split (1998)**: historic Croatian Indoors continuity, not parallel 1998 duplicate; **Singapore 1996 World Series → 1997 Championship Series** is a category transition; **1996 Rotterdam World Series** must not be retro-labelled Championship from 1999.
- **1996 Lyon** was the Lyon indoor tournament in the eventual Montpellier licence and **1996 Marseille** was a separate event in the `lyon` source family. **1996 Adelaide** and **1996 Singapore** were separate tournaments despite modern name aliases.

A deterministic `PRE_2000_PLAYED_TIER_COUNTS[1996]` gate now requires 9/11/57. Tests verify category hierarchy, original historical hosts, five new identities and exclusions, and reject fabricated cancellations or recategorisation.

**Not a playable tennis or squash calendar:** no scores, draw size contracts, licence rights, ranking matrices, sport rules, tournament Editions or Run Package Apply/Save were created. All 37 yearly views are still a history-derived reference, and no 1990–1995 absence is interpreted as a tournament not existing.


## 2026-11-03 — completed original 1995 ATP main Tour played roster

The 1995 played source census is **9 ATP Championship Single-Week (Super 9), 11 ATP Championship Series, 59 ATP World Series and one ATP Tour World Championships singles Final in Frankfurt**. This totals **80 ATP-only source Series**. Exclude four independently run Grand Slams, separately staged ATP year-end doubles event in Eindhoven, ITF Grand Slam Cup, team tournaments, Challengers and pre-1990 events. These are source identities, not historical playable Editions or results.

**Consecutive completed original-era roster range now 1995–2025 (31 seasons)**; **1990–1994 still source-incomplete**, 2026 is provisional. Six distinct source IDs were necessary: `stuttgart_indoor_feb_1995`, `tokyo_indoor_1995`, `johannesburg_1995`, `bordeaux_1995`, `montevideo_1995`, `buenos_aires_1995`.

Historically significant:
- **Vienna 1995 was World Series**, not Championship Series, unlike its 1996 classification. Some summary-year tables mislabeled it; the [original tournament edition](https://en.wikipedia.org/wiki/1995_CA-TennisTrophy) and original-tier overall 11/59 census agree with World. This is **not** historical ATP 250 point equivalence.
- **Tokyo April 1995 Japan Open and Tokyo Indoor October 1995** were distinct Championship Series tournaments, not duplicates; [1995 Tokyo Indoor](https://en.wikipedia.org/wiki/1995_Tokyo_Indoor).
- **Stuttgart February 1995 Championship**, **Stuttgart July 1995 Championship** and **Essen October 1995 Super 9** were three separate actual events. The top-tier Essen licence moved to Stuttgart for 1996; do not misidentify the February Stuttgart with that 1996 Super 9.
- **Nice 1995 → New Delhi 1996 → Chennai 1997** is the same documented ATP licence, now source-scoped as `hong_kong`; [contemporary 1997 report](https://www.indiatoday.in/magazine/sport/story/19970430-as-gold-flake-open-proved-life-on-tennis-tour-is-often-hard-and-unforgiving-831328-1997-04-29).
- **Pinehurst 1995–1996 → Orlando 1997** remains the U.S. Men's Clay Court Championships `houston` identity; 1995 Valencia→1996 Marbella→1998 Mallorca stays one `brussels` Series. 1995 Kuala Lumpur→1996 Singapore stays a source family, never two 1995 played events.
- 1995 Buenos Aires and Johannesburg are not automatically assumed the same licensed tournaments as later restarts. Finals 1995 singles were in **Frankfurt**, contrasting with Hannover 1996–1999. [ATP history PDF](https://www.atptour.com/-/media/23da5115363646fd89d16716e5b35a2e.pdf).

Sources: [official 1995 ATP Results Archive](https://www.atptour.com/en/scores/results-archive?year=1995), [1995 source-tier season summary](https://en.wikipedia.org/wiki/1995_ATP_Tour), [1995 independent tournament listing](https://tennis-db.com/tournaments?season=1995), [1995 Vienna World Series](https://en.wikipedia.org/wiki/1995_CA-TennisTrophy), [1995 Tokyo Indoor Championship](https://en.wikipedia.org/wiki/1995_Tokyo_Indoor). The independent list has 84 editions with four non-ATP Grand Slams (not 84 ATP-only).

The deterministic `PRE_2000_PLAYED_TIER_COUNTS[1995]` gate uses 9/11/59, supported by regression and adversarial tests and the 37-year stable JSON derived snapshot. These documents **do not** create native Category/Series adapters, played Editions, original ranking-point matrices, results, Package Catalog or Run Apply/Save support.


## 2026-11-03 — complete original 1994 ATP main-Tour played Category roster

**1994** had **9 ATP Super 9, 12 ATP Championship Series, 63 ATP World Series and one singles ATP Tour World Championships** at Frankfurt (**85 ATP-only source Series identities**). This extends original-year played-tier coverage to **32 consecutive seasons (1994–2025)**. **1990–1993 remain unverified/incomplete**. The 2026 source remains a provisional, non-final calendar. The documented [1994 ATP Tour category totals](https://en.wikipedia.org/wiki/1994_ATP_Tour) reconcile against the [ATP 1994 official results archive](https://www.atptour.com/en/scores/results-archive?year=1994), [independent 1994 original tier data](https://tennis-db.com/tournaments?season=1994) and [German 1994 year-host archive](https://de.wikipedia.org/wiki/ATP_Tour_1994). TennisDB reports 89 main-tour singles events including four Grand Slams, which are deliberately excluded from this ATP-only package.

**Nine source IDs introduced**: Oahu, Zaragoza, Osaka, Birmingham Alabama, 1994 Madrid clay Grand Prix, Florence, Schenectady, Athens and Sydney Indoor 1994. All retain original year-only evidence. Historic Madrid **clay World Series** is not automatically assigned to the **2002–2008 Madrid indoor Masters** licence without legal continuity evidence. 1994 Florence is not auto-equal to the temporary 2022 Florence fixture.

Original-year separation and provenance:
- 1994 **Stuttgart February Indoor Championship**, **Stuttgart July clay Championship** and **Stockholm October Super 9** were three separate played Tour competitions, as were **Tokyo April Japan Open** and **Tokyo October Indoor**, both Championship Series.
- 1994 **Sydney January World Series** and **Sydney October Indoor Championship** were separate ATP-only fixtures, not a duplicated October/January Edition.
- **Birmingham Alabama 1994** U.S. Men's Clay Court Championships and **Pinehurst 1994** USTA Clay Court Classic are *different coexisting US events*, confirmed by the [contemporary German annual listing](https://de.wikipedia.org/wiki/ATP_Tour_1994); TennisDB geographically mislabels Birmingham as in the UK. The legal licence chain into later Pinehurst/Orlando/Houston remains evidence-limited, so the two original 1994 fixtures are never collapsed into one. Coral Springs 1994 was also an additional separate World Series, sometimes anachronistically named Delray Beach.
- 1994 Vienna was **World Series** rather than Championship; the German Wikipedia annual table labels it Championship, but the historical original-tier 12 Championship / 63 World season counts and [independent original-tier tournament record](https://tennis-db.com/tournaments?season=1994) support World. Thus original-year data are not modernized into post-2009 winner-points/tier labels.
- 1994 **Manchester** (later Nottingham/Eastbourne), **Lyon** (later Montpellier), **Kuala Lumpur** (1995 same host, Singapore from 1996), **Sun City** (1995 Johannesburg) and **1994 Frankfurt Finals singles** use their contemporary city, not present-day brand. Jakarta year-end doubles Finals are separate and excluded.
- 1994 **Stockholm** was the ninth Super 9 (1995 moved to Essen, 1996 to Stuttgart indoors), not an additional World Series; 1994 Frankfurt singles Finals are not merged with Jakarta doubles Finals.

`PRE_2000_PLAYED_TIER_COUNTS[1994]` enforces 9/12/63 with original vocabulary, rejects category mutation or fabricated cancellations, and regenerates the source-derived season map without altering any other year. This remains source-only Category/Series metadata: no player/results data, ranking points, native Run Apply/Save, playable historic FAX Editions, licence rights, or Tour gameplay added.


## 2026-11-03 — 1993 ATP original played tiers, 33-year consecutive coverage

Year **1993** reconciles to **9 ATP Super 9, 12 ATP Championship Series, 62 ATP World Series and one Frankfurt singles ATP Tour World Championship** = **84 ATP-only men’s singles source identities**. This extends completed played category source rosters to **33 consecutive years, 1993–2025**. The full [independent 1993 tournament list](https://tennis-db.com/tournaments?season=1993) has 88 events including four Grand Slams, which are **outside** the ATP-only source scope. **1990–1992 remain incomplete** and 2026 remains provisional. Sources: [1993 official ATP Results Archive](https://www.atptour.com/en/scores/results-archive?year=1993), [original 1993 Category totals](https://en.wikipedia.org/wiki/1993_ATP_Tour), [historic host change notes](https://de.wikipedia.org/wiki/ATP_Tour_1993), and [original 1993 statistics summary from contemporaneous sports guide](https://files.eric.ed.gov/fulltext/ED407914.pdf). Historical categories are never converted to 2026 ranking point values.

Three historical IDs were added: **January Kuala Lumpur 1993**, **Bolzano 1993** and **São Paulo 1993**. Crucially, **Kuala Lumpur held *two separate* ATP World Series events in 1993**, January and late September–early October. They are represented independently rather than collapsing into one event or claiming the later Kuala Lumpur/Singapore licence staged a single tournament. 1993 São Paulo does not automatically prove legal continuity with the 2001-onward Brasil Open.

Year-effective source identities and locations:
- **1993 San Francisco → 1994 San José** (one original tournament family), **1993 Genova → 1994 St. Pölten** (clay), **1993 Durban → 1994 Sun City** (South African Open).
- **1993 Charlotte → 1994 Birmingham Alabama** U.S. Men’s Clay Courts and **1993 Tampa → 1994 Pinehurst** USTA Clay Court Classic were two distinct *concurrently played* original ATP World Series licences, not the same tournament. Modern Birmingham UK labels are historically incorrect.
- **1993 Vienna was World Series**, distinct original-year Championship Series tournaments remain **Stuttgart February indoor and July clay, Tokyo April and October indoor, and January Sydney World Series vs October Sydney Indoor Championship**.
- **1993 Frankfurt singles Finals** is not the separate **Johannesburg doubles-only Finals**; four majors, Davis/team events, Grand Slam Cup and Challenger Tour excluded.
- Other 1993 historical hosts retained without anachronistic current names: Coral Springs, Marseille, Manchester, Lyon, Kuala Lumpur, Nice, Durban, Frankfurt and San Francisco.

Added 1993's deterministic **9/12/62** original-tier played-roster gate, the canonical 1993 derived yearly snapshot, tests rejecting fabricated cancellations/wrong categories and audit documents. This is historical Category/Series source metadata only, not operational ATP/FAX gameplay, results, ranking points, playable Editions or Run Apply/Save.


## 2026-11-03 — 1992 original ATP Tour tiers, Olympic year boundary

Year **1992** originally consisted of **9 ATP Super 9, 12 ATP Championship Series, 56 ATP World Series and one Frankfurt singles ATP Tour World Championships**, hence **78 ATP-only source singles identities**. [Full independent season listing](https://tennis-db.com/tournaments?season=1992) has 83 events but that number includes **four non-ATP Grand Slams** and **1992 Barcelona Olympics**; Olympic tennis was not ATP Tour and awarded **no ATP ranking points**, as also stated by the [German original-year source](https://de.wikipedia.org/wiki/ATP_Tour_1992). This is **34 consecutive complete original-tier played source rosters 1992–2025**; **1990–1991 are unverified/incomplete** and 2026 is provisional. Sources: [ATP 1992 official results archive](https://www.atptour.com/en/scores/results-archive?year=1992), [original categories for 1992](https://en.wikipedia.org/wiki/1992_ATP_Tour), [German annual event locations](https://de.wikipedia.org/wiki/ATP_Tour_1992), [independent 1992 tournament list](https://tennis-db.com/tournaments?season=1992), [official ATP year-end Finals historical PDF](https://www.atptour.com/-/media/254456cd5274468ea5f4ac3ac7387bb1.pdf).

Nine new historical source IDs: 1992 **Wellington, Maceió, Brussels Championship, Singapore spring, Cologne clay, Brisbane autumn, Taipei, Guarujá and Búzios**.

Important coexistence:
- **January 1992 Adelaide** and **September 1992 Brisbane** are different *actual* ATP World Series in the same calendar year; modern Brisbane International title/alias must not collapse two sources.
- **1992 Milan World Series** vs **1992 Brussels Championship** are distinct; Milan was *promoted to Championship for 1993*. Historic 1992 Antwerp World Series also separate from Brussels.
- **1992 Singapore spring** World Series was played in its own historical season, with future licence continuity to the 1996+ Singapore/1994–95 Kuala Lumpur series not assumed without proof.
- **1992 Tampa** USTA Clay Court Classic and **1992 Charlotte** US Men's Clay Court Championship were separate ATP World Series, later Pinehurst/Birmingham respectively; historical 1992 tennis season must not have only one US clay identity.
- **1992 Cologne** clay World Series follows the historic Geneva-to-Cologne venue move, *not* proven same as revived Geneva 2015+ event. **1992 Johannesburg** preceded Durban 1993, Sun City 1994, Johannesburg 1995 in South African Open venue history.
- **1992 Prague** was still in **Czechoslovakia (CSK)**, not the Czech Republic created in 1993. Preserve the correct year-host country even when the Source Series persists.
- Brazil hosted multiple distinct original 1992 World Series (**Maceió, Guarujá, Búzios and São Paulo**) rather than one interchangeable Brazilian event. Other unique sources retain their individual year: Bolzano, Taipei, Brussels and Wellington.

Added `PRE_2000_PLAYED_TIER_COUNTS[1992]` exact 9/12/56 gate, full year-derived source snapshot, adversarial category/cancellation tests, and historical reference documentation. The source contains **no Olympics**, no Grand Slams, no ATP-only false licencing, no playable FAX Editions, ranking matrices, tournament results, Catalog adapter or Run Apply/Save mutation.


## 2026-11-03 — 1991 ATP original played tour tiers and Guarujá correction

**1991** original men's singles ATP Tour contains **9 ATP Super 9, 12 Championship Series and 54 World Series**, plus one **Frankfurt ATP Tour World Championship singles**, totaling **76 ATP-only source identities**. Four Grand Slams, the separate Johannesburg doubles-only year-end Finals, Grand Slam Cup and team events do not enter the ATP-only Category/Series Packages. 1991 reference now extends completed year-category coverage **1991–2025 (35 consecutive played Tour seasons)**. **1990 remains incomplete**; 2026 provisional. Sources: [ATP official Results Archive](https://www.atptour.com/en/scores/results-archive?year=1991), [original 1991 year Category roster](https://en.wikipedia.org/wiki/1991_ATP_Tour), [German original 1991 calendar](https://de.wikipedia.org/wiki/ATP_Tour_1991), [independent TennisDB 1991 calendar](https://tennis-db.com/tournaments?season=1991).

**Missing-event finding:** TennisDB's 1991 index of 79 entries (including four majors) omits the **February Guarujá Chevrolet Classic (Patrick Baur singles winner)**. ATP official archive explicitly records **Guaruja-1** Feb 4–10 and **Guaruja-2** Oct 21–27 (Javier Frana winner), both World Series. Both also appear in original German/English historical calendars. Their **licence lineages differ**: 1991 February Chevrolet Classic moved to **February 1992 Maceió** (existing `maceio_1992`); 1991 October Philips Open continued to **October 1992 Guaruja** (existing `guaruja_1992`). The two source IDs remain distinct: don't create fictitious extra licences when the source already has a documented annual successor. [Contemporaneous Guaruja tournament history](https://de.wikipedia.org/wiki/ATP_Guaruj%C3%A1) confirms both 1991 dates and the 1992 split.

Five new year-scoped World Series identities: `chicago_1991`, `orlando_1991`, `brasilia_1991`, `berlin_1991`, `birmingham_indoor_1991`. **1991 Birmingham was in England**, while the **1994 Birmingham Alabama U.S. clay** licence played in **Charlotte** in 1991 and must never be conflated. 1991 Orlando hard vs 1991 Tampa clay vs 1991 Charlotte US clay are three distinct Tour World Series.

Year-specific hosts preserve 1991 Czechoslovakia (Prague, code CSK), Soviet Union (Moscow, code SUN) and Yugoslavia (Umag, code YUG), without retroactively adopting the post-independence state code. The 1991 Vienna tier is original World Series (conflicting historic German annual summary is rejected in favor of original 12 Championship total and independent event data); 1991 Milan World Series wasn't promoted to Championship until 1993. January Sydney World and October Sydney Indoor Championship as well as April Tokyo Japan Open and October Tokyo Indoor Championship are distinct events, not duplicate year records.

Added deterministic `PRE_2000_PLAYED_TIER_COUNTS[1991]` **9/12/54** count gate, 37-year canonical derived source season view, adversarial wrong category and fictitious cancellation tests. No results, ranking matrices, scored Editions, native Package Catalog, FAX Apply/Save or sporting rules were introduced.


## 2026-11-03 — 1990 first-year played ATP Tour source census completed

The original **1990 IBM ATP Tour**, its first season, contained **9 ATP Championship Single-Week (future Super 9), 12 ATP Championship Series, 53 ATP World Series and 1 ATP Tour World Championships singles final in Frankfurt**, amounting to **75 ATP-only individual men's singles Series**. The independent [1990 tournament inventory](https://tennis-db.com/tournaments?season=1990) shows 79 played events including four independently organized Grand Slams, which are excluded from this ATP-only source. The [original 1990 full year event calendar](https://en.wikipedia.org/wiki/1990_ATP_Tour), [German historic calendar with original tier/venue](https://de.wikipedia.org/wiki/ATP_Tour_1990), [ATP 1990 results archive](https://www.atptour.com/en/scores/results-archive?year=1990) and [official ATP Finals history](https://www.atptour.com/-/media/254456cd5274468ea5f4ac3ac7387bb1.pdf) corroborate original tiers and finalists.

Historical played-tier Category/Series reference coverage is therefore **36 consecutive complete past seasons 1990–2025** with **164 persistent source Series identities** (after the independent 2014–2015 sanction audit) in the 37-year 1990–2026 bounded source. **2026 remains provisional**, not a final played calendar. This is *not* a source of exact played Edition IDs, tournament draws/results, ranking point matrices, historic source rankings, native FAX rules, Run Apply/Save or import adapter.

Five narrow historical source IDs were added: `toronto_indoor_1990`, `rio_carpet_1990`, `san_remo_1990`, `itaparica_1990`, `wembley_1990`. Historical Rio carpet World Series 1990 must not be equated with the modern Rio 500 clay licence launched in 2014; the other four historically played source identities have no invented future Editions or licence assertions.

1990 historical distinctions:
- **Toronto Indoor Championship February** and **Canadian Open Super 9 at Toronto July** were two separate same-city tournaments. Toronto Indoor is not the Canadian Masters.
- **January Adelaide World Series** and **September Brisbane World Series** were two independent played ATP tournaments, even though a later Brisbane-era Series ID sources the Adelaide lineage.
- **1990 Kiawah Island U.S. Men's Clay Court Championships** (1991 Charlotte, 1994 Birmingham Alabama) and **1990 Guaruja February Chevrolet Classic** (Feb 1991 Guaruja, Feb 1992 Maceió) preserve documented source lineages. **1990 Orlando hard** stays distinct from the 1997 Orlando U.S. Clay event.
- **1990 Stuttgart February Indoor** and **July Stuttgart Clay**, **January Sydney World Series** and **October Sydney Indoor Championship**, **April Japan Open Tokyo** and **October Tokyo Indoor Championship** are distinct concurrent Tour Series.
- **Rosmalen grass 1990** is the actual historic host of the later 's-Hertogenbosch series. **Prague 1990 (CSK), Umag 1990 (YUG), Moscow 1990 (SUN)** use historical country codes. Pre-October reunification West German hosts use FRG in 1990, whereas November Frankfurt ATP Finals country code is DEU.
- **1990 Milan** is World Series not Championship, **Memphis** is World Series not later Championship/Gold, and **Stockholm** is original Super 9 (later shifted to Essen, then Stuttgart indoors).
- Four majors, ITF Grand Slam Cup, Davis/World Team events and separately held doubles Finals remain out of scope.

Added `PRE_2000_PLAYED_TIER_COUNTS[1990]` exact **9/12/53** original-category roster gate, derived 37-year source snapshot and adversarial tests rejecting fabricated 1990 non-played fixtures or category changes. No production sporting consumption has changed.

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
with Category (11), Series (164) and Calendar (1929 entities at the current
source revision, comprising 37 provenance-coverage entities and 1892 dated
occurrences). The whole source is fingerprinted; Read-only Preview and
all-or-nothing Confirm use existing Run Package CAS; **Save remains explicit**.

## 1991 original ATP Tour — complete canonical date coverage (76/76)

The official [ATP Tour 1991 results archive](https://www.atptour.com/en/scores/results-archive?year=1991) dates all **76** original ATP singles main Tour/Frankfurt World Championships year-effective Series. The original [ATP Finals historical results](https://www.nittoatpfinals.com/en/heritage/results-1970-1999) independently agree on Frankfurt **12–17 November 1991**. The original dual Guarujá, Sydney, Tokyo and Stuttgart events, 31 December 1990 Adelaide/Wellington ISO 1991/W01 and September Brisbane are preserved. Now canonically stored: **1,892** dated occurrences plus **37** coverage entities = **1,929** Calendar source entities, **30 of 37** year source cohorts dated. See [complete 1991 dates and caveats](ATP_TOUR_1991_COMPLETE_DATE_REFERENCE.md). All playable FAX sporting commands and Run clock remain separate.

## 1992 source-date backfill (78/78 staged; not canonical)

All **78** original ATP Tour year-effective parent Series for 1992 have officially published event-date candidates, including **Adelaide and Wellington 30 December 1991–5 January 1992**, separately held **Brisbane in September–October 1992**, separate Tokyo/Sydney/Stuttgart editions and the original ATP Tour championships. The [official ATP 1992 archive](https://www.atptour.com/en/scores/results-archive?year=1992) includes **Frankfurt Finals 16–22 November**, while [official ATP Finals history](https://www.nittoatpfinals.com/en/heritage/results-1970-1999) and the ITF record date actual competition **17–22 November**. The year is staged only, with a centrally blocked source-date conflict. See [1992 evidence and constraints](ATP_TOUR_1992_DATE_EVIDENCE_AND_CONFLICT.md). **1992 remains undated in canonical Calendar.**

## 1993 source-date backfill (84/84 staged; not canonical)

The original 1993 ATP year-effective parent roster contains **84 original Tour and Frankfurt Finals source Series**. All **84 date candidates** have now been staged from the official [ATP 1993 yearly results archive](https://www.atptour.com/en/scores/results-archive?year=1993), preserving historical distinct Kuala Lumpur-1/2, Sydney-1/2, Tokyo-1/2, Stuttgart-1/2, Manchester, Durban, Genoa and Frankfurt. However, **the annual archive dates the Frankfurt Finals 15–21 November, while the separately authoritative [ATP Finals history](https://www.nittoatpfinals.com/en/heritage/results-1970-1999) and [ITF record](https://www.itftennis.com/en/tournament/atp-finals/ger/1993/m-csr-ger-01a-1993/draws-and-results/) date actual competition 16–21 November**. This conflict remains explicit and blocks entire-year promotion. See [1993 evidence and source conflict](ATP_TOUR_1993_DATE_EVIDENCE_AND_CONFLICT.md). No 1993 canonical Calendar, Run Calendar, or FAX sporting mutation is made.

## 1994 original ATP Tour (complete source date roster)

All **85** 1994 original Tour + Frankfurt World Championships year-effective Series have been dated from the official ATP results archive, retaining exact historic hosts, original categories, published date windows and ISO week spans. The distinct Sydney-1/Sydney-2, Tokyo-1/Tokyo-2, Stuttgart-1/Stuttgart-2, Atlanta/Indianapolis, Manchester and Hilversum cases are preserved. See [1994 complete evidence report](ATP_TOUR_1994_COMPLETE_DATE_REFERENCE.md). Canonical Calendar includes **1,816 dated occurrences + 37 year coverage records**; this confirms the known parent roster, **not** independent legal licence lineage or playable tennis/squash scheduling. Official Finals date-window differences for 1997–1999 and 2003 remain unresolved.

## 2004 archive coverage

All **63 played 2004 ATP Tour / Tennis Masters Cup historical source Series** are dated from the [ATP 2004 results archive](https://www.atptour.com/en/scores/results-archive?year=2004), with independent corroboration for specific venues (e.g. [ITF Palermo 2004](https://www.itftennis.com/en/tournament/palermo/ita/2004/m-is-ita-02a-2004/draws-and-results/)). Olympic tennis in Athens is **excluded**, as are Grand Slams, World Team Cup and Davis Cup. The original historical host and 2004 week arrangement, including *September Delray Beach*, Shanghai (`bangalore_2008` lineage), 2004 March Scottsdale (`las_vegas_2008`), Sopot (`warsaw_2008`), Amersfoort, St. Pölten, Memphis and autumn Madrid are preserved. **2004 Masters Cup start-date discrepancy:** official ATP year results archive shows **15–21 Nov 2004**, while [ATP Finals heritage](https://www.nittoatpfinals.com/en/heritage/results-2000-2023) records **13–21 Nov**. Stored year-source date follows the original ATP yearly archive, pending date-definition reconciliation. This is not independently a complete annual event census beyond the 2004 parent roster.

## 2005 archive coverage

All **63 named 2005 ATP main Tour + Tennis Masters Cup Series** are dated against the original [ATP 2005 results archive](https://www.atptour.com/en/scores/results-archive?year=2005). The edition was still in the original ATP International Series / Gold / Masters Series era. Chronological original host aliases include Adelaide (`brisbane`), Chennai (`hong_kong`), Milan (`sofia`), Viña del Mar (`cordoba`), San José (`dallas`), Memphis (`rio`), Scottsdale (`las_vegas_2008`), St. Pölten (`poertschach_2008`), Ho Chi Minh City (`bangalore_2008`), Palermo, Sopot, Amersfoort, New Haven, Valencia and Lyon. The official ATP year-results archive lists the 2005 Tennis Masters Cup at **14–20 Nov**, but the [ATP Finals tournament-history archive](https://www.nittoatpfinals.com/es/heritage/results-2000-2023) dates it **13–20 Nov**. We retain the official year archive's exact label as the Calendar source while documenting the conflicting contemporaneous season start; this is an unresolved provenance conflict rather than a certified date. No independent complete ATP tournament census is claimed beyond the source roster.

## 2006 archive coverage

All **63 originally played source Series** in the 2006 ATP Tour and Tennis Masters Cup historical roster have been dated from the [official ATP 2006 results archive](https://www.atptour.com/en/scores/results-archive?year=2006). In particular, the last Palermo (`palermo`) tournament was **25 Sep–1 Oct 2006**, while the Mumbai (`bangalore_2008`) and Amersfoort (`belgrade_2012`) host identities are retained. Other historical lineages: Adelaide (`brisbane`), Chennai (`hong_kong`), Viña del Mar (`cordoba`), San José (`dallas`), Memphis (`rio`), Costa do Sauípe (`sao_paulo`), Nottingham (`eastbourne`), Los Angeles (`los_cabos`), Sopot (`warsaw_2008`), Lyon (`montpellier`). The 2006 nine Masters Series events retain their original historical category, with Hamburg and autumn Madrid. Grand Slams, World Team Cup and Davis Cup remain excluded. The coverage is complete against the established source roster, but does not prove an independent complete tournament census.

## 2007 archive coverage

All **62 named source Series in the 2007 ATP Tour + Tennis Masters Cup** are individually dated from the original [ATP 2007 results archive](https://www.atptour.com/en/scores/results-archive?year=2007). Era-specific site records are preserved: Adelaide (`brisbane` lineage), Mumbai (`bangalore_2008`), Sopot (`warsaw_2008`), Amersfoort (`belgrade_2012`), Pörtschach, Nottingham (`eastbourne` lineage), Memphis (`rio`), Valencia (`brussels`) and Lyon (`montpellier`). The tour also included Hamburg and indoor Madrid **Tennis Masters Series**, not their modern ATP 500 / Madrid clay chronology. Grand Slams, team events and Davis Cup are not imported.

## 2008 archive coverage

The **61 played, named 2008 ATP International Series, International Series Gold, Tennis Masters Series and Tennis Masters Cup source Series** have their [official original ATP 2008 results-archive dates](https://www.atptour.com/en/scores/results-archive?year=2008), while 2008 Bangalore (`bangalore_2008`) is separately recorded as **not held**, with no fabricated tournament interval. Original dates include 31 Dec 2007–6 Jan 2008 for Adelaide (`brisbane` lineage), Amersfoort (`belgrade_2012`) in July, Kitzbühel in July, April Valencia (`brussels`), May Hamburg **Tennis Masters Series** and October Madrid **Tennis Masters Series**, Pörtschach, Warsaw, Las Vegas, and the season-ending Tennis Masters Cup. Excludes the Beijing Olympics, Grand Slams, team competitions and Davis Cup; preserves the original historical Category rather than backfilling 2009 ATP tiers.

## 2009 archive coverage

All **61 named source Series** for the inaugural 2009 Masters 1000 / ATP 500 / ATP 250 era and ATP Finals are dated against the [official 2009 ATP results archive](https://www.atptour.com/en/scores/results-archive?year=2009). The history is specifically year-effective: 2009 Kitzbühel ran **17–24 May** (not its later summer week), Indianapolis (`atlanta`) preceded Atlanta, Lyon (`montpellier`) preceded Montpellier, Viña del Mar (`cordoba`), San José (`dallas`), Memphis (`rio`), and the two Belgrade/Bucharest events remain separate. Excludes the World Team Cup, Grand Slams and Davis Cup. Original 2009 results-archive date intervals are persisted, not inferred from neighbouring calendars.

## 2010 archive coverage

All **61 named 2010 ATP Tour + ATP Finals source Series** are dated against the original [official ATP 2010 results archive](https://www.atptour.com/en/scores/results-archive?year=2010). Former host identities are preserved: Johannesburg, Santiago, Zagreb, San José, Memphis, Casablanca, Belgrade versus Bucharest, New Haven (`winston_salem`), Montpellier's original autumn slot, Los Angeles, Kuala Lumpur and Valencia. Brisbane starts on 3 January 2010 — **ISO 2009/W53**, not 2010/W01; the W53 label is retained and not projected silently onto the game's W52 clock. World Team Cup, Grand Slams and Davis Cup remain outside the ATP Tour reference package. This describes all 2010 source roster IDs, not necessarily a new complete census beyond the parent historical roster.

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

## 1995 canonical archive coverage

**1995: 80/80 historical ATP played main-tier and Finals source Series now
have exact date intervals in the canonical Calendar.** This includes
two separate **Tokyo** events (April outdoor / October indoor), two
**Stuttgart** events (February indoor / July clay), and the historical
October **Essen Masters**. The original Frankfurt ATP Tour World
Championship ran **14–19 November 1995** in both
[ATP annual archive](https://www.atptour.com/en/scores/results-archive?year=1995)
and [official ATP Finals history](https://www.nittoatpfinals.com/en/heritage/results-1970-1999).
The original Nice and Hong Kong tournaments are separate source Series.
For exact host labels and licence-evidence caveats, see
[`ATP_TOUR_1995_COMPLETE_DATE_REFERENCE.md`](ATP_TOUR_1995_COMPLETE_DATE_REFERENCE.md).
No playable FAX events or ATP results were created.

## 1996 canonical archive coverage

**1996: 78 / 78 original played ATP Tour source Series have dated records
in the canonical Calendar.** These come from the
[ATP 1996 year results archive](https://www.atptour.com/en/scores/results-archive?year=1996).
The year-end World Championship was held **19–24 November 1996**, matching
the [ATP Finals historical record](https://www.nittoatpfinals.com/en/heritage/results-1970-1999).
The year includes historic **Jakarta, Zagreb, Shanghai, New Delhi and Hong Kong
as two different played Series**, Bermuda, Seoul, Porto, Tel Aviv,
Pinehurst and Coral Springs. The 1996 Atlanta Olympics were excluded.
These are source-only reference dates; the parent Series lineage has not
been independently legally certified. See
[`ATP_TOUR_1996_COMPLETE_DATE_REFERENCE.md`](ATP_TOUR_1996_COMPLETE_DATE_REFERENCE.md).

## 2000–2002 canonical archive coverage

The 2000, 2001 and 2002 ATP original-tier source cohorts were promoted into the
canonical `calendar_dates_v1.json` and regenerated immutable `calendar.json`
in November 2026. **2000: 65 / 65; 2001: 65 / 65; 2002: 62 / 62**.
Event-specific archived dates and original venue aliases are retained, including
2001 Amsterdam / Sopot / Montreal and the separate Stuttgart indoor Masters,
and the 2002 December 2001 opening three tournaments whose ISO labels belong
to 2002/W01. The 192 new references are not playable FAX sporting events.

The automatic regeneration was compared to the old complete calendar: **all
pre-existing event entities and all coverage records for other years stayed
byte-equivalent after canonical serialization**. That verifies unchanged
source content, *not* historical legal licence identities. For dated inventory
and remaining evidence limitations see
[`ATP_TOUR_2000_COMPLETE_DATE_REFERENCE.md`](ATP_TOUR_2000_COMPLETE_DATE_REFERENCE.md),
[`ATP_TOUR_2001_COMPLETE_DATE_CANDIDATES.md`](ATP_TOUR_2001_COMPLETE_DATE_CANDIDATES.md)
and
[`ATP_TOUR_2002_COMPLETE_DATE_CANDIDATES.md`](ATP_TOUR_2002_COMPLETE_DATE_CANDIDATES.md).

Year **2003 is still not canonically dated**: 63 dated historical candidates are
staged, but the official annual ATP archive's 10–16 November Tennis Masters Cup
interval conflicts with a separate ATP tournament history's 8–16 November
interval. The import is deliberately blocked until the date convention is
reconciled. Historical years **1990–1994 and 1997–1999** remain undated.

## Source-only historical candidates blocked by official date conflicts

In addition to 1,731 already canonical date-bearing ATP occurrences, **278
additional source-date candidates** have been transcribed for years not yet
promoted into Calendar:

| Year | Original parent Series identities matched | Source state |
| --- | ---: | --- |
| 1997 | 75 / 75 | Staged; original ATP Finals week differs from historical Finals |
| 1998 | 74 / 74 | Staged; original ATP Finals week differs from historical Finals |
| 1999 | 66 / 66 | Staged; original ATP Finals week differs from historical Finals |
| 2003 | 63 / 63 | Staged; historical Finals start differs by two days |

**The source files are not playable, not canonically dated, and not
independently licence-lineage-certified.** Merely counting all original
source Series IDs is *roster reconciliation*, not proof that all ATP played
events or rightsholder chains are independently verified.

The read-only `audit_atp_calendar_backfill.py --year <year> --json` reports
`roster_reconciled=true` and a nonempty `unresolved_date_conflicts` for
the four affected years. Its `ready_for_whole_year_promotion` is
correctly **false** until the conflict has been adjudicated. Both the
read-only audit and canonical promoter use one shared conflict registry
to prevent mismatched acceptance signals.

See
[`ATP_TOUR_1997_DATE_EVIDENCE_AND_CONFLICTS.md`](ATP_TOUR_1997_DATE_EVIDENCE_AND_CONFLICTS.md)
and
[`ATP_TOUR_1998_1999_DATE_EVIDENCE_AND_CONFLICTS.md`](ATP_TOUR_1998_1999_DATE_EVIDENCE_AND_CONFLICTS.md).
The annual archives are the source of the published historical date
windows; ATP Finals heritage separately reports the competition windows.

## Current actual date coverage

| Year(s) | Source status | Dated Series | Undated |
| --- | --- | ---: | ---: |
| 1990–1994 | No canonically dated source Series yet | 0 | Explicit missing IDs for every year |
| 1995 | ATP played archive and official Frankfurt Finals date | **80 / 80** | 0 |
| 1996 | ATP played archive, all original main-tier dates and Finals | **78 / 78** | 0 |
| 1997–1999 | Source candidates available; conflicting official Finals date windows | **0 / 215 canonical** | 215 |
| 2000 | Official played ATP archive, original 2000 host and tier dates | **65 / 65** | 0 |
| 2001 | Original ATP annual archive; 65 historical source identities | **65 / 65** | 0 |
| 2002 | Original ATP annual archive; 62 historical source identities | **62 / 62** | 0 |
| 2003 | 63 staged candidates; unresolved ATP Finals source conflict | **0 / 63 canonical** | 63 |
| 2004 | ATP played results archive, 2004 original year/host dates; Finals evidence conflict | **63 / 63** | 0 |
| 2005 | Official ATP archive, 63 named editions; Finals start date conflict | **63 / 63** | 0 |
| 2006 | Official played ATP archive, original host and tier dates | **63 / 63** | 0 |
| 2007 | Official results archive, historical host continuity | **62 / 62** | 0 |
| 2008 | Official archive, original ATP tiers; Bangalore not held | **61 / 61 played** | 0 |
| 2009 | Official ATP results archive, year-specific historical hosts | **61 / 61** | 0 |
| 2010 | Official ATP results archive, all named source Series | **61 / 61** | 0 |
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
1731 unique year/Series occurrences currently have original *date* sources.
The other historical years will be sourced individually, not filled by
inventing dates or extrapolating 2025/2026 patterns.

Source links:

- [1995 original ATP results archive](https://www.atptour.com/en/scores/results-archive?year=1995).
- [1995 official ATP Finals historical record](https://www.nittoatpfinals.com/en/heritage/results-1970-1999).
- [1996 original ATP results archive](https://www.atptour.com/en/scores/results-archive?year=1996).
- [1996 Nitto ATP Finals historical record](https://www.nittoatpfinals.com/en/heritage/results-1970-1999).
- [2000 original ATP results archive](https://www.atptour.com/en/scores/results-archive?year=2000).
- [2001 original ATP results archive](https://www.atptour.com/en/scores/results-archive?year=2001).
- [2002 original ATP results archive](https://www.atptour.com/en/scores/results-archive?year=2002).
- [2004 official results archive](https://www.atptour.com/en/scores/results-archive?year=2004).
- [2004 Tennis Masters Cup alternative start date](https://www.nittoatpfinals.com/en/heritage/results-2000-2023).
- [2005 official results archive](https://www.atptour.com/en/scores/results-archive?year=2005).
- [2005 Tennis Masters Cup alternative start date](https://www.nittoatpfinals.com/es/heritage/results-2000-2023).
- [2006 official results archive](https://www.atptour.com/en/scores/results-archive?year=2006).
- [2007 official results archive](https://www.atptour.com/en/scores/results-archive?year=2007).
- [2008 official results archive](https://www.atptour.com/en/scores/results-archive?year=2008).
- [2009 official results archive](https://www.atptour.com/en/scores/results-archive?year=2009).
- [2010 official results archive](https://www.atptour.com/en/scores/results-archive?year=2010).
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

The work is **not complete for 1990–1994, 1997–1999 or 2003**. Source-year coverage must be
upgraded year by year using original contemporaneous calendars and/or official
ATP results archives. 2026 final validation remains pending.

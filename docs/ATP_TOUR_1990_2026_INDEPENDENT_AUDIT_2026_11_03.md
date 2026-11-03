# Independent ATP Category / Series source audit — 2026-11-03

**Scope:** independent historical source audit within reference Package
PR #1731 against `buuk` in `Jasmetk0/squash-tour-beta`. This document
evaluates **historical Category/Series source provenance**, not a playable
ATP Tour Calendar, ranking points or sporting implementation. A separate
opaque Run-owned reference Setup adapter with Preview/Confirm/explicit Save
was added later in this same PR; that integration has its own tests and
documentation in `ATP_TOUR_1990_2026_REFERENCE_PACKAGES.md`.
**Release/merge status:** Draft; owner alone merges. Passing source integrity
checks must not be described as full independent historical certification.

## 1. Inventory and deterministic integrity

| Item | Independently enumerated |
| --- | ---: |
| Category entities | 11 |
| Persistent Series identities | 164 |
| Annual derived source snapshots (1990–2026) | 37 |
| Historical Category intervals attached to Series | 1,983 |
| Year-effective Series memberships across 37 snapshots | 2,431 |
| Explicit historical host-year records | 1,455 |
| Active membership-years without a *separate* explicit host-year record | 976 |
| Series periods citing an ATP-domain URL | 1,832 / 1,983 |
| Series periods citing the general ATP results archive, year-filtered | 1,716 / 1,983 |
| Series periods citing non-ATP pages | 151 / 1,983 |

The audit enumerated the **entire source JSON**, independently reconstructed
every annual Series-to-Category map from effective history periods, and compared
all 37 source snapshot dictionaries and cancellation lists. Findings:
- **0** duplicate Series IDs, overlapping same-ID effective years, out-of-era
  category references, mismatched derived annual snapshots, non-held entries
  outside a Series' effective years, duplicate historical host-year records,
  historical hosts outside effective Series years, or mismatched 2026
  active-category/current-host values.
- All 36 retrospective seasons (1990–2025) pass the builder's **declared**
  original-era played-tier count constraints. 2026 remains provisional, not a
  completed 2026 played-event census.
- General ATP year-index pages support **year-level checking**; they are **not**
  proof of a particular legal tournament licence transfer. A source-period URL
  cannot by itself justify historical identity equivalence across venue moves.
- `historical_host_change` is sparse and optional by design; the 976 missing
  *individual host-year entries* are an evidence/coverage limitation, **not**
  976 missing tournament categories or proof of wrong locations.

## 2. External source sanity checks (bounded, not exhaustive)

Cross-checks were made against:
- [ATP 2026 official calendar](https://www.atptour.com/en/news/what-is-the-2026-atp-tour-calendar/)
  for the 9 Masters 1000 / 16 ATP 500 / 29 ATP 250 planned roster and its
  unresolved **TBD** ATP 250 slot; no fake persistent `TBD` Series was invented.
- [ATP 2025 calendar](https://www.atptour.com/en/news/what-is-the-2025-atp-tour-calendar),
  [ATP 2025 results archive](https://www.atptour.com/en/scores/results-archive?year=2025)
  and [ATP 500 category upgrade announcement](https://www.atptour.com/en/news/2025-atp-tour-calendar-announced)
  for the 2025 ATP 500 expansion to 16 and contemporary tour identities.
- [1990 original-season competition categories](https://en.wikipedia.org/wiki/1990_ATP_Tour)
  and [1999 original-season competition categories](https://en.wikipedia.org/wiki/1999_ATP_Tour)
  for the respective 9/12/53 and 9/11/45 historical top-three-tier counts.
  These Wikipedia examples are *independent cross-checks*, not official
  proof for each event identity, category and host across 36 years.

**This is not a full external row-by-row verification of all 2,431
year-effective source identities**. The project must not infer that mere
matching aggregate tier counts establishes correct identities, cancellation
policy, legal licences or historical venue data. Event substitutions within
one tier could evade a count-only gate.

## 3. Defects resolved during review

1. **2013 Los Angeles source false venue:** source formerly represented
   a Los Angeles 2013 ATP 250, despite the [ATP-approved December 2012
   transfer to Bogotá](https://www.tennis.com/news/articles/atp-finalizes-sale-of-l-a-tournament-to-bogota).
   The historical source `los_cabos` now carries the same licence from
   Los Angeles through 2012, Bogotá 2013–15 and Los Cabos from 2016;
   no duplicate 2013 Series created. Source identities fell 167 → 166;
   aggregate tier counts unchanged.
2. **Next Gen 2026 stale host:** official [September 9, 2026 ATP release](https://www.nextgenatpfinals.com/en/news/reggio-calabria-to-host-2026-next-gen-atp-finals)
   establishes **Reggio Calabria, ITA** as the December 2026 host,
   replacing the old unresolved/TBC calendar entry. One 2026 metadata
   and hosted venue record was updated, not the Category or Edition count.
3. **Belgrade 2025 venue missing:** ATP's [August 4, 2025
   announcement](https://www.atptour.com/en/news/belgrade-athens-announcement-august-2025)
   establishes that the **2024 Belgrade Open** ATP 250 moved to the **Athens
   Hellenic Championship in 2025**. A continuous `belgrade` Series now
   records 2024 Belgrade / 2025 Athens, separate from original 1994 Athens.
4. **2024–2026 Canada Masters:** official results show the alternating
   men's Canadian Masters 1000 city **Montréal 2024 → Toronto 2025 →
   Montréal 2026**, not an implied permanent 2026 host. Dated host
   records were added to one unchanged `canadian_open` Series. See
   [ATP 2025 archive](https://www.atptour.com/en/scores/results-archive?year=2025)
   and [ATP Montreal 2026 results](https://www.atptour.com/en/news/montreal-2026-results).
5. **Source integrity gates:** builder rejects missing/duplicate Finals
   identities; malformed cancellation years; mismatched 2026 effective
   category/current host; false, duplicate or out-of-scope historical
   venue evidence. Added adversarial/negative regression cases.

All corrections preserve historic year-effective original categories. None
copies ATP match, ranking, player or prize-money data into FAX.

### ATP licence transfer audit — two genuinely independent 2013→2014 Series

Contemporary primary-industry reporting confirms that **the Memphis 500 sanction
was sold and moved to Rio de Janeiro for 2014**, while **the San José 250
sanction was moved to Memphis in 2014**. These were not a promotion/demotion
of a single Memphis source licence. Sources: [2012 ATP board decision
report](https://www.sportsbusinessjournal.com/Daily/Issues/2012/04/24/Leagues-and-Governing-Bodies/ATP/),
[contemporaneous detailed tennis report](https://www.tennis.com/news/articles/san-jose-atp-tourney-to-close-rio-gets-event),
[2014 licence ownership follow-up](https://www.tennis.com/news/articles/usta-buying-memphis-tournament),
[ATP 2014 results](https://www.atptour.com/en/scores/results-archive?year=2014).

The historical 1990–2013 **Memphis** Tier/host timeline was moved to
`rio`, leaving 2014+ Rio Category membership as previously recorded.
Historical **San Francisco → San José 1990–2013** membership moved into
`dallas`, which owns **Memphis 2014–17 → New York 2018–20 → Dallas 2022+**.
Obsolete `san_jose_2013` identity removed; 166 → **165 Series** at that correction checkpoint. The independent Düsseldorf/Geneva correction below reduces the current total to **164**.
All original-era 1990–2025 Category played-tier totals and 2,431
year-effective memberships stay unchanged. Independent adversarial
regressions verify the 2008 **Memphis Gold** versus **San José International**
distinction, the 2013/2014 cross-transfer and later Dallas 2025 upgrade.

The newly added deterministic `scripts/audit_atp_reference_provenance.py`
is a **read-only diagnostic**, not a new data source. It inventories every
Series/year, highlights generic archive URLs, sparse host-years and
multi-host source IDs without explicit licence proof, and separately
records the **2026 ATP 250 announced-summary/TBD ambiguity**. It neither
auto-fetches webpages nor claims legal or sporting certification.
Use `python scripts/audit_atp_reference_provenance.py` for summary or
`--output FILE.json` to export the full per-Series/per-year evidence queue.

### Confirmed 2014 Düsseldorf → 2015 Geneva ATP 250 licence

The **2013–14 Düsseldorf ATP 250** and **2015+ Geneva ATP 250** were
previously kept as separate source identities because legal provenance
was unresolved. Now [WELT reporting an ATP announcement in November
2014](https://www.welt.de/print/welt_kompakt/duesseldorf/article134566672/Aus-fuer-ATP-Turnier-besiegelt.html),
[contemporaneous DIE ZEIT reporting](https://www.zeit.de/news/2014-11/19/tennis-kuenftig-in-genf-aus-fuer-atp-turnier-im-rochusclub-perfekt-19193604)
and the [Geneva organiser's original history](https://gonetgenevaopen.ch/le-tournoi/)
confirm the same sanction was transferred by its licence owners.

2013–2014 Düsseldorf source periods and new dated host records are now
included in `geneva`. The redundant `duesseldorf_2014` ID is removed,
**165 → 164** unique Series. The separate 1990/1991 Geneva World Series
moved to Cologne in 1992 remains `cologne_1992_clay`.
The Category counts and 2,431 year-effective membership records do not
change; no played Edition or ranking score is added.



## 2026-11-03 follow-up — six independently sourced relocation links

The source Registry now explicitly attaches **specific supporting publications**
to six already represented one-ID transitions; neither annual tier membership
nor any played total was changed. Independent source articles:

| Source Series | Specific documented transition | Evidence |
| --- | --- | --- |
| `hangzhou` | Zhuhai 2023 → Hangzhou 2024 | [ATP 2024 press conference](https://www.atptour.com/en/news/hangzhou-press-conference-2024-june), explicitly states Zhuhai relocation |
| `almaty` | Astana 2023 → Almaty 2024 | [ATP calendar update](https://www.atptour.com/en/news/2024-atp-calendar-update-gijon-almaty); [Kazakh federation approval](https://ktf.kz/en/tournaments/ktt/news/?id=8708) |
| `brussels` | Valencia 2015 → Antwerp 2016 → Brussels 2025 | [ATP 2016 calendar announcement](https://www.atptour.com/en/news/atp-announces-2017-2018-calendars); [ATP 2025 move](https://www.atptour.com/en/news/antwerp-brussels-relocation-2025) |
| `lyon` | Marseille 2025 → Lyon 2026 | [ATP-approved 2025 announcement](https://www.atptour.com/en/news/marseille-lyon-relocation) |
| `sofia` | Zagreb 2015 → Sofia 2016 | [ATP 2016 calendar announcement](https://www.atptour.com/en/news/atp-announces-2017-2018-calendars) |
| `chengdu` | Kuala Lumpur 2015 → Chengdu 2016 | [Contemporary June 2016 report quoting ATP approval](https://www.denik.cz/tenis/teniste-uz-nebudou-hrat-v-kualu-lumpur-turnaj-se-stehuje-do-ccheng-tu-20160629.html) |

The Zhuhai/Hangzhou Series also contained three truncated ATP article URLs
(`/en/news/to`); all were replaced with a verifiable ATP article. Regression
tests pin host-year identities, the documented links and fail-closed source
evidence shape. **One publication supporting one venue transition does not
certify every historical move within that Series.**

As of **3 November 2026**, the official [ATP published 2026 calendar](https://www.atptour.com/en/news/what-is-the-2026-atp-tour-calendar/)
still includes a November ATP 250 `TBD` entry. The official
[ATP tournament index](https://www.atptour.com/en/tournaments/) does not
establish a substitute identity for that slot. Therefore the 2026 reference
remains explicitly provisional. No future edition, winner or historic
ranking point is inferred.

## Additional ATP host-context classification (read-only evidence audit)

The initial licence-continuity queue used *any distinct historical city string*
as an unresolved licence transfer. That was overbroad: legal ownership, host
location, temporarily moved event, surface label and metropolitan-city alias
are **different facts**. The source now contains 13 explicitly scoped
`historical_host_context_sources` records. They are validated HTTPS citations
with one of seven nonlegal `kind` classifications. This distinct field is
deliberately **not** merged into `historical_licence_source_urls`.

| Series | Context evidence type | Independently identified supporting source |
| --- | --- | --- |
| Miami | Site transition | [ATP Miami 2019 Miami Gardens history](https://www.atptour.com/en/news/atp-50-moments-longform-part-1) |
| Canadian Open | Alternating host | [ATP Canada official overview](https://www.atptour.com/en/tournaments/canada/421/overview) |
| Cincinnati | Temporary site, 2020 | [USTA official New York announcement](https://www.usopen.org/en_US/news/articles/2020-06-17/2020_us_open_western_southern_open_to_be_held_in_new_york.html) |
| Acapulco | Site transition, 2001 | [ATP 50 host-city history](https://www.atptour.com/en/news/atp-50-locations-longform) |
| Brisbane | Adelaide-to-Brisbane context | [ABC's contemporary 2006 report](https://www.abc.net.au/news/2006-07-07/brisbane-to-host-mens-hard-court-champs-from-2009/1796818) |
| Delray Beach | Site transition, 1999 | [Local Delray Beach historical account](https://www.i-love-delray-beach.com/tennis-championships.html) — not official legal documentation |
| Houston | Site transitions, through 2001 | [ATP Houston history](https://www.atptour.com/en/tournaments/orlando/717/overview) |
| Marrakech | Casablanca-to-Marrakech, 2016 | [ATP official tournament overview](https://www.atptour.com/en/tournaments/casablanca/360/overview) |
| Stuttgart | Surface description (not new city) | [ATP Stuttgart official history](https://www.atptour.com/en/tournaments/stuttgart-1/321/overview) |
| ’s-Hertogenbosch | Rosmalen / city-name alias | [ATP Rosmalen / ’s-Hertogenbosch overview](https://www.atptour.com/en/tournaments/rosmalen/440/overview) |
| Eastbourne | Nottingham / Eastbourne venue shifts | [ATP history of both venues](https://www.atptour.com/en/tournaments/-/741/overview) |
| Estoril | Historical context, **not legal continuity** | [ATP Estoril 2015 new tournament overview](https://www.atptour.com/en/tournaments/estoril/7290/overview) |
| ATP Finals | Rotating host venues | [ATP Finals city history](https://www.atptour.com/en/news/atp-50-locations-longform) |

**Current coverage accounting:** among 46 source Series with more than one
recorded city string, 31 still lack a separately labelled *licence evidence*
URL (unchanged), but **13 of those** now have concrete, nonlegal, typed host
context, leaving **18 without either kind of explicit contextual source**.
Some of the 18 include mere spelling differences, but they are not
automatically upgraded to certified transfers. Not all cited context pages
verify every individual historical year or legal ownership: the 1997 Miami
city label, for example, cannot be interpreted as a legal or venue move just
because the ATP documents a later 2019 Miami Gardens move. The Estoril
2014/2015 organiser boundary must not be automatically treated as an
identical ATP membership.

`audit_atp_reference_provenance.py` now publishes both separately counted
coverage types and the **per-Series machine-readable unresolved queue**;
its complete year-effective values and deterministic 1990–2026 snapshots
stay unchanged. The builder rejects invalid context kinds, malformed URLs
and duplicate sources; PR-critical tests cover the distinction. This improves
traceability but **does not claim the entire original 1990–2025 legal
licence chain has been certified**.

## 4. Review and merge boundaries

**Technically verifiable now:** source documents parse under the existing
Package model; deterministic builder `--check` and scoped PR critical
backend CI are the regression gates; independent enumeration validates
the recorded annual values. Final-head CI must be green **after all edits**.

**Not yet proven:** independent *per-event* verification of every pre-2000
and 2000–2025 identity/lineage against original ATP event records;
all 976 sparse venue-year gaps; licence/legal reuse rights; complete
2026 played season (late 2026 schedule still includes TBD); the general
dynamic source Catalog for arbitrary non-World Packages; full sporting
lifecycle, result histories, point distribution, and a playable Calendar.
The dedicated ATP source catalog, Run reference Setup, Preview, explicit
Confirm/Save and Czech/English Apply UI are now implemented and tested;
they do not close the independent historical provenance gaps.

**Recommendation:** keep PR #1731 a **Draft** until the owner approves
the explicitly **provisional historical-provenance boundary**. Technical
integrity checks and passing Fast CI do **not** justify marking every
historical source as independently certified. The current reference-only
Package integration is not a promise of a playable ATP Tour or FAX Calendar.
Owner makes any merge decision.

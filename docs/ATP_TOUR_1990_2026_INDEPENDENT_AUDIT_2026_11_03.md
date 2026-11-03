# Independent ATP Category / Series source audit — 2026-11-03

**Scope:** isolated, source-only reference Package PR #1731 against `buuk` in
`Jasmetk0/squash-tour-beta`. This is **not** a review of a playable ATP Tour
Calendar, Run import/Apply/Save, ranking points or any sporting implementation.
**Release/merge status:** Draft; owner alone merges. Passing a source integrity
check must not be described as full independent historical certification.

## 1. Inventory and deterministic integrity

| Item | Independently enumerated |
| --- | ---: |
| Category entities | 11 |
| Persistent Series identities | 166 |
| Annual derived source snapshots (1990–2026) | 37 |
| Historical Category intervals attached to Series | 1,983 |
| Year-effective Series memberships across 37 snapshots | 2,431 |
| Explicit historical host-year records | 1,445 |
| Active membership-years without a *separate* explicit host-year record | 986 |
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
- `historical_host_change` is sparse and optional by design; the 986 missing
  *individual host-year entries* are an evidence/coverage limitation, **not**
  986 missing tournament categories or proof of wrong locations.

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
4. **Source integrity gates:** builder rejects missing/duplicate Finals
   identities; malformed cancellation years; mismatched 2026 effective
   category/current host; false, duplicate or out-of-scope historical
   venue evidence. Added adversarial/negative regression cases.

All corrections preserve historic year-effective original categories. None
copies ATP match, ranking, player or prize-money data into FAX.

## 4. Review and merge boundaries

**Technically verifiable now:** source documents parse under the existing
Package model; deterministic builder `--check` and scoped PR critical
backend CI are the regression gates; independent enumeration validates
the recorded annual values. Final-head CI must be green **after all edits**.

**Not yet proven:** independent *per-event* verification of every pre-2000
and 2000–2025 identity/lineage against original ATP event records;
all 986 sparse venue-year gaps; licence/legal reuse rights; complete
2026 played season (late 2026 schedule still includes TBD); native Package
Catalog inventory and Run Apply; full sporting lifecycle, result histories,
point distribution, and a playable Calendar.

**Recommendation:** keep PR #1731 a **Draft** pending an independent
year-by-year source/identity provenance review. Technical integrity checks
and passing Fast CI do **not** justify marking every historical source as
fully independently certified. Owner makes any merge decision. Any future
Catalog/Run integration belongs in its own explicit approved vertical slice.

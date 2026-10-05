# Earth sport histories — implementation and research boundary

Status: historical-rating foundation merged in #1126; this branch adds the
research-provenance layer required before populated FIFA Earth / ATP Earth data.

## Accepted scope

The owner requested project-official FIFA Earth and ATP Earth packages, representing
football and men's tennis environments. Each must cover every year **1955–2026**
for all countries in the existing Earth catalogue. A real-world year is the same
engine year. These are project estimates, not federation-endorsed products.
The six attributes keep their existing meanings on an explicit 1–10 scale with
at most one decimal. Court Count is outside pre-alpha. Population/geography are
separate inputs. Innate potential rarity must remain independent of nationality.

## Current implementation status — 5 October 2026

This section is the authoritative current summary; dated batch sections below are
preserved as implementation history.

- FIFA Earth has **29 / 250** complete 1955–2026 country/territory histories,
  covering all six attributes. Its canonical research bundle resolves **69 datasets
  and 1,449 normalized observations**.
- The latest FIFA batch adds **FRA and ESP**, another **864 annual attribute ratings**. France is dimensionally anchored by official FFF technical/development history plus the 2006 participation and 2023 professional checkpoints; Spain combines the 1909 RFEF foundation, 2003 Ciudad del Fútbol and 2026 talent-development process. Big Count remains popularity/access evidence, Professional 2023 remains competition/elite-ecosystem context, and neither programme existence nor federation age is a direct score formula.
- The KOR/THA ATP batch has been re-audited against the same scale: 9+ remains world-leading, current programme/calendar facts are separated from confidence in the authored estimate, and tests now enforce temporal evidence rather than hard-coded high confidence.
- ATP Earth has **44 / 250** complete histories: CZE, DEU, USA, AUS, ESP, SRB,
  FRA, GBR, ARG, JPN, CAN, ITA, NED, SWE, SUI, CRO, POL, CHN, NOR, GRE, BEL, ZAF,
  DEN, FIN, NZL, PRT, IRL, HUN, ROU, SVN, SVK, ISR, BGR, AUT, TUR, CYP, BRA, CHL, COL, MEX, ECU, IND, KOR and THA. Its canonical bundle resolves **147 datasets and 431 normalized observations**.
- The latest ATP batch adds **KOR and THA**, another **864 annual attribute ratings**. Korea combines 1945/1948/1968 institutional continuity, the 1971 Jangchung complex and 1989 ITF men's circuit milestone with a current 16-branch/6-federation network and broad 2026 U10-to-adult calendar. Thailand combines its 1926 association, National Tennis Development Centre and a current nationwide development/competition system spanning regional U8-U18 events, national-team selection, national championships and ITF J200/J300 events.
- The preceding ATP batch adds **ECU and IND**, another **864 annual attribute ratings**. Ecuador combines 1899/1905 tennis roots and the 1967 federation with current National Tennis Centre, CEJ and JTI child-development structures. India combines deep 1880s/1910/1920 institutional history with the 1996 National Stadium and 2026 HPC/ACE 2032/coaching/junior-pipeline reforms.
- The preceding ATP batch adds **COL and MEX**, another **864 annual attribute ratings**. Colombia combines its 1932 federation history with 2025 Interligas/training-site evidence and 2026 national affiliation/child-circuit structures. Mexico combines 1894-era club history and the 1963 FMT foundation with a nationwide state-association network, ~30k current affiliates and strongly documented 2025/2026 junior competition layers.
- The preceding ATP batch adds **BRA and CHL**, another **864 annual attribute ratings**. Brazil combines the 1955 CBT foundation and pre-CBT state-federation context with current affiliated-player scale, national junior/Tennis 10s rules and a formal coach-graduation system. Chile combines 1880s/1890s roots, its 1920 federation and 1927 ITF affiliation with 2025 JTI reach and 2026 junior-circuit decentralisation, zonal qualifying and development grants.
- The preceding ATP batch adds **TUR and CYP**, another **864 annual attribute ratings**. Turkey combines 1923/1953 institutional anchors with current national training centres, coach education, a broad 2026 competition calendar and a multi-province club network. Cyprus combines 1900/1913/1951 history, 1984 ITF/Tennis Europe membership, the 1999 National Tennis Centre and current development/tournament structures while retaining partial-association territorial caution.
- The preceding ATP addition is **AUT**, adding **432 annual attribute ratings**. Austria has unusually strong current structural evidence: ~210k federation members, ~1,750 clubs, ~95k championship players, 11,369 teams, 450 tournaments and 3,000+ coaches/instructors, plus 2025 ITF WTT and five 2026 ATP/Challenger events.
- The preceding ATP batch adds **ISR and BGR**, another **864 annual attribute ratings**. Israel combines the 1950 federation and early Davis Cup continuity with current nationwide development and multi-level youth competition structures; Bulgaria combines 1896/1911/1925/1930 historical anchors with 128 current clubs, a nationwide child-entry programme and the 2026 competition framework.
- The preceding ATP addition is **SVK**, adding **432 annual attribute ratings**. Pre-1990 Slovak ratings use true historical anchors from current Slovak territory (1899 clubs and the 1924 Banská Bystrica international tournament); independent-era STZ, Challenger, NTC, active-athlete and league evidence is gated from its actual dates.
- The preceding ATP addition is **SVN**, adding **432 annual attribute ratings**. Slovenia preserves pre-1991 tennis institutions as Yugoslav-territory context rather than pretending independent statehood, while current registered scale, WTT pathway and Tutor development evidence stay temporally gated.
- The preceding ATP batch adds **HUN and ROU**, another **864 annual attribute ratings**. Hungary combines federation history with current national player-support and a dense 2026 international-event calendar; Romania combines federation mandate, National Tennis Centre, coach-licensing structure and national junior competition evidence.
- The preceding ATP batch adds **PRT and IRL**, another **864 annual attribute ratings**.
  Portugal combines federation/national-championship continuity from 1925 with current
  broad participation, junior competition and national-camp evidence. Ireland keeps
  Tennis Ireland's all-island remit explicit: club/player/pathway evidence is partial
  Earth IRL context rather than a Republic-only census.
- The preceding ATP batch adds **DEN, FIN and NZL**, another **1,296 annual
  attribute ratings**. Denmark uses its long official membership trajectory and current
  national-championship structure; Finland combines current member/junior activity with
  its high-performance system; New Zealand combines deep championship lineage with a
  current club-to-regional-to-national/international pathway. Modern evidence remains
  temporally gated and mixed/child-limited observations keep their actual scope.
- The preceding ATP batch adds **NOR, GRE, BEL and ZAF**, another **1,728 annual
  attribute ratings**. Norway and Greece preserve modern elite spikes without turning
  star-player results into participation evidence; Belgium marks Flemish tennis/padel
  scale as partial-country combined-sport evidence; South Africa separates deep tennis
  tradition and the Anderson peak from current access/development constraints.
- The preceding ATP batch added **SUI, CRO, POL and CHN**, another **1,728 annual
  attribute ratings**. Switzerland separates current federation scale from elite
  outcomes; Croatia preserves pre-1992 Yugoslav territory context; Poland preserves
  the 1951 governance break and gates modern youth support; China keeps its large
  modern youth-development system separate from weaker current men's elite output.
- The preceding ATP batch added **CAN, ITA, NED and SWE**, another **1,728 annual
  attribute ratings**. Canada separates 2025 mass participation from the 2007 NTC
  pathway; Italy preserves the Formia development lineage and current decentralized
  junior system; Netherlands keeps combined tennis/padel membership explicitly
  non-tennis-only; Sweden preserves elite historical dominance without pretending its
  current competition quality still matches the 1980s.
- The preceding ATP batch added **FRA, GBR, ARG and JPN**, another **1,728 annual
  attribute ratings**. Great Britain explicitly preserves the LTA/United Kingdom
  territory mismatch instead of treating LTA participation as a synthetic UK census;
  Japan preserves the 2001 national-training-base setback and 2008 recovery;
  Argentina gates current federation/DETA evidence to 2026; France uses DTN and
  high-performance milestones independently from Davis Cup outcomes.
- The latest FIFA batch adds **WSM (Samoa), TON (Tonga) and VUT (Vanuatu)**,
  another **1,296 annual attribute ratings**. It preserves Samoa's 2010–11 governance
  discontinuity, Tonga's rugby-leading national context and Vanuatu's 2008 academy
  pathway instead of smoothing the three Pacific environments into one template.
- Neither `config/world_packages/fifa_earth/` nor
  `config/world_packages/atp_earth/` is installed yet. The builder intentionally
  refuses to publish an incomplete 250-country research bundle, so absence of those
  directories is expected until coverage is complete.
- Coverage and provenance must be measured through
  `load_earth_research_bundle()`, because sources, manifests and country histories
  may live in shards rather than only in the root JSON.
- Historical profiles are not yet a fully closed player-lifecycle feature: quantity
  paths can use historical cohort ratings, while generated-player development still
  uses the requested season environment. Ordinary World Library editing/persistence
  of the full historical profile remains an integration boundary.

## Implemented foundation

- Explicit `country_ratings_1_10.v2`; unversioned legacy data retains its 1–5
  validation, formulas and serialized payload. No automatic historical migration.
- `country_rating_history.v2` stores per-year six-attribute histories with
  territorial interpretation, exact source and observation references, rationale,
  confidence and interpolation/backcast/carry-forward/derived provenance.
- `derived_estimate` is explicit and requires a `calibration_model_id`; modelled
  lag/ramp years are therefore not mislabelled as observed interpolation.
- `earth_source_observations.v2` defines normalized research facts independently
  of game ratings: source entity, Earth/historical identity, time scope,
  measurement semantics, sex/age/competition scope, value/unit, collection method,
  coverage/comparability, territory mapping and quality flags.
- `earth_sport_research.v2` registers content-addressed observation dataset
  manifests. Every rating observation reference must resolve to a registered
  dataset whose source is also cited by that rating.
- Directory storage, snapshot serialization and API contracts preserve history.
  `GET /world/packages/{world_id}/countries/{code}?rating_year=2000` resolves a year
  without changing the source. Nearest authored year is used outside coverage;
  earlier wins ties. After 2026 this is a frozen last observation, not a forecast.
- Initial-pool quantity and weekly intake use birth-cohort-year population and
  ratings. Annual talent planning uses its requested year; player generation uses
  the requested season environment. Existing non-history behavior is preserved.
- New-country UI authors v2 tenths; Court Count no longer appears in the World
  Library table/detail/editor. Old inert Court Count data survives old contracts.
- Builder refuses incomplete country/year coverage and refuses to overwrite an
  existing package. Source catalogue, observation dataset manifests and history
  metadata participate in package identity. Persisted validation checks declared
  years, source references and observation-dataset references independently of
  the saved coverage report.

## Not implemented or not proven

- **Neither official Earth directory exists yet.** FIFA currently has 27 complete
  histories and ATP has 22; neither reaches the required 250-country all-or-nothing
  build threshold. No fabricated neutral profiles are shipped to satisfy coverage
  mechanically. See the current-status section above for authoritative counts.
- FIFA Big Count 2006 now has five canonical normalized
  `earth_source_observations.v2` datasets (all players, registered, unregistered,
  clubs and officials/staff). FIFA Professional Football Report 2023 adds two
  canonical datasets (men's professional players and professional clubs). Other files directly under
  `config/earth_research/observations/` remain raw/source-specific inputs until
  explicitly normalized.
- Observation manifests are content-addressed provenance declarations.
  `load_earth_research_bundle()` resolves their relative files and fail-closes on
  dataset/source/count/input-artifact/semantic-hash mismatch before audit/build.
- FIFA association→Earth identity is a separate typed transform, not a mutation of
  source observations. `earth_observation_identity_resolutions.v1` binds every
  resolved/manual observation to its input dataset hashes, reviewed override hash
  and Earth identity catalogue hash; aggregate members and manual-review cases remain
  explicit instead of being silently collapsed.
- Historical ratings in an editable copy require versioned import/API authoring;
  the flat World Library editor deliberately disables Save for a history-bearing
  profile. A dedicated per-year/evidence editor is still required.
- Generic built-in World Package cloning is now available (merged #1127), including
  package-owned history/provenance files. This still does not prove a complete Earth
  Run lifecycle or 50-season acceptance.
- Initial player development uses the season-start environment; it does not yet
  integrate every year of a player's pre-start development path.
- Country pipeline coefficients remain provisional. No measured realism result
  or completeness assertion follows from passing schema/tests.

## Research already stored

`config/earth_research/fifa_earth.json` and `atp_earth.json` are
`earth_sport_research.v2` catalogues whose root records are extended by sharded
sources, observation manifests and country histories. FIFA currently resolves 27
complete histories. ATP currently resolves 44 complete histories (CZE, DEU, USA, AUS, ESP, SRB, FRA, GBR, ARG, JPN, CAN, ITA, NED, SWE, SUI, CRO, POL, CHN, NOR, GRE, BEL, ZAF, DEN, FIN, NZL, PRT, IRL, HUN, ROU, SVN, SVK, ISR, BGR, AUT, TUR, CYP, BRA, CHL, COL, MEX, ECU, IND, KOR and THA); its evidence now
combines ITF national snapshots, federation histories/participation records, Davis Cup
outcomes and country-specific development/support evidence. Root-JSON contents alone
must not be used as the coverage count.

Current evidence includes:

1. FIFA Big Count 2006: the checked-in 208-association all-player extract is retained
   as raw input and normalized into five content-addressed v2 datasets. The normalized
   facts are mixed-sex; missing club cells remain missing; row-level direct-vs-
   statistically-supplemented flags cannot be recovered from this legacy extract.
2. FIFA Professional Football Report 2023: 211 national pages are retained as raw
   input and normalized into 112 non-null men's professional-player observations and
   135 professional-club observations. Page 38 remains a distinct KUWAIT/Kyrgyzstan
   identity anomaly; extracted national sums remain intentionally different from the
   published global headline rather than being silently adjusted.
3. ITF 2019 Czech/German participation, clubs and coach counts. Edition/report
   timing is distinct from the underlying observation date, and mixed-sex
   participation must not be presented as men's participation.

Reproduce the current source-specific FIFA PDF extraction with:

    python scripts/extract_fifa_2023_observations.py REPORT.pdf OUTPUT.json

PyMuPDF is an offline research dependency only. The output records the source PDF
SHA-256 and aggregate discrepancies; the PDF is not redistributed in the repo.

Audit research coverage:

    PYTHONPATH=src python scripts/build_earth_sport_package.py config/earth_research/fifa_earth.json
    PYTHONPATH=src python scripts/build_earth_sport_package.py config/earth_research/atp_earth.json

Only complete, reviewed research may be built by adding `--output NEW_DIRECTORY`.
The builder's `coverage_complete` is structural; `realism_validated` stays false.

## Required data completion

Continue normalizing source observations before calibration. Big Count v2 is the
first completed slice, but it is not sufficient for men's FIFA Earth on its own.
Do not infer that similarly named counts share the same definition across federations:
membership, registered player, active player and modelled/casual participation are
distinct measurements. A richer Big Count re-extraction should recover country-level
male/female and source statistical-processing metadata where the original material
supports it.

Use the canonical observation identity-resolution layer before calibration. The
current FIFA source slices now resolve every normalized Big Count / Professional
2023 observation exactly once, while reviewed ambiguous cases stay manual. Extend
this same mechanism to historical polities and later source families (including
USSR, Yugoslavia, Czechoslovakia and colonial territories). Population must not be
duplicated when a predecessor has several successors. Collect independent evidence for participation/access, development,
competition, elite support and tradition; ranking outcomes alone cannot measure
all six. Author period anchors with uncertainties, preserve documented structural
breaks, and use explicit `derived_estimate` provenance for calibrated ramps/lags.
Label sparse early years as estimates and 2026 as incomplete through the stated
cutoff. Then compare intake/development distributions with held-out sporting
observations in Test Labs.


## Structural evidence layer

Structural football milestones are stored as canonical source observations rather
than as direct rating deltas. Federation/league foundations, academies, technical
centres, infrastructure milestones and governance discontinuities preserve their
actual dates, including pre-1955 history.

The current structural layer contains 57 events: 43 review events plus 14 explicitly
held-out validation events. The held-out set (Germany, Brazil, Iceland and San
Marino) is excluded from model fitting by policy.

Structural dimension summaries may report timeline coverage, first/last evidence
year, pre-1955 evidence and source-conflict groups. They must not infer a quality
score from event count or treat absence from the curated seed as evidence of
non-existence.


> The dated sections from this point record how coverage evolved. They are retained for
> audit/history and do not override the current-status summary above.

## Seeded canonical-history progress — 4 October 2026

The first actual country histories are CZE and SVK in FIFA Earth. Their values reuse
the reviewed prototype trajectories only after re-grounding every annual attribute
on exact normalized observation IDs. They are stored as `derived_estimate` rather
than pretending the game ratings were measured by FIFA/UEFA/FAČR/SFZ. Weak evidence
families remain low confidence, and validation-only ranking outcomes are not used as
automatic authoring inputs.

ATP Earth has begun canonical normalization with CZE and DEU ITF 2019 player, club
and coach facts. The edition/report date is retained separately from observation
year; the checked-in raw extract does not establish a separate observation year, so
the normalized facts intentionally keep `observation_year=null`. Mixed-sex player
counts are not represented as men's participation, and coach counts are not treated
as development quality.


## ATP canonical-history progress — 4 October 2026

ATP Earth now has its first two complete country histories: CZE and DEU. Both cover
all 72 years and all six attributes. The numerical values are explicit project
estimates under `atp-earth-cze-deu-seed-model.v1`; source facts remain separate
normalized observations.

Germany has unusually strong longitudinal popularity/access evidence through selected
checkpoints from the DTB membership series. Before reunification this evidence covers
West Germany only and is therefore marked as partial current-territory context. Czech
early participation/access remains much less certain. Davis Cup outcomes are used for
competition/tradition context only, while current development/support ratings use the
documented Czech talent-centre framework and German federal high-performance-centre
system. Court count remains excluded.


## FIFA canonical-history batch 2 — 4 October 2026

FIFA Earth now contains six complete country histories: CZE, SVK, JPN, IND, MAR
and SEN. The second batch adds 1,728 annual attribute ratings across JPN, IND, MAR
and SEN, all stored as `derived_estimate` values with exact canonical observation
references.

The batch deliberately preserves evidence asymmetry. Japan has long structural
JFA evidence; India separates absolute participation scale from organised access;
Senegal's modern academy/youth/professional pathway is much better evidenced than
its 1955 pre-independence backcast. Morocco retains both conflicting FIFA academy
timing observations (2009 establishment and 2019 opening) instead of manufacturing
a false resolution. Outcome rankings remain validation data rather than automatic
authoring inputs, and court count remains outside pre-alpha.


## FIFA canonical-history batch 3 and sharding — 4 October 2026

FIFA Earth now resolves nine complete histories: CZE, SVK, JPN, IND, MAR, SEN,
FRO, USA and ZAF. The third batch adds 1,296 ratings for FRO, USA and ZAF and
completes the original nine-country prototype set.

Country history storage is now optionally sharded under
`config/earth_research/countries/<world_id>/CODE.json`. The loader merges those
histories before the existing `EarthSportResearch` validation, rejects duplicate
inline/sharded codes and validates every sidecar through `CountryRatingHistory`.
This keeps the research contract unchanged while avoiding an impractical 100+ MB
monolithic research document at full 250-country coverage.

The batch preserves meaningful discontinuities: Faroe Islands' artificial-turf
breakpoint primarily changes access/development; the United States retains the NASL
collapse before MLS recovery; and South Africa's apartheid-era exclusion is treated
as an institutional/international-competition disruption rather than absence of
domestic football culture.


## FIFA canonical-history batch 4 — held-out validation countries

Brazil, Germany, Iceland and San Marino are now authored as complete 1955–2026
country-history shards. These countries were previously held out from calibration
fitting, so their 2023 FIFA ranking observations remain an independent outcome check
and are explicitly forbidden from rating provenance.

The batch intentionally separates dimensions. Brazil combines world-leading
popularity/tradition with less-than-maximal organised access. Germany has extremely
strong access/development/support but pre-1991 current-territory coverage is marked
partial. Iceland has near-top access with smaller absolute competition depth. San
Marino likewise has excellent local access and long tradition while maintaining
modest competition quality; missing professional-report fields remain missing rather
than becoming zero.


## FIFA canonical-history batch 5 — source/manifest sharding and four new countries

The Earth research loader can now merge sharded source records and observation
dataset manifests before the existing `EarthSportResearch` validation. Together
with country-history sharding, new research can be added without rewriting the
multi-megabyte root research JSON. Duplicate identifiers fail closed and every
normalized dataset still passes the existing semantic SHA, source, record-count and
observation-ID integrity checks.

The first batch using the complete sharded research path adds Argentina, Mexico,
Australia and New Zealand. Argentina enters 1955 with mature professional competition;
Mexico separates very high popularity from more mixed access evidence; Australia
preserves federation, league and confederation discontinuities; and New Zealand
keeps strong modern access/development investment distinct from football's lower
relative cultural dominance in a rugby-led sporting environment.


## FIFA canonical-history batch 6 — sparse Oceania

Fiji, Papua New Guinea, Solomon Islands and Cook Islands are now complete
1955–2026 country-history shards. This batch deliberately tests the rule that
participation/access density is not a universal football-strength score.

Cook Islands has extremely dense 2006 registration and club evidence but remains
small in competition and elite-support depth. Fiji combines strong organised access
with a small explicit professional ecosystem and current infrastructure investment.
Papua New Guinea's difficult geography is preserved as direct access/development
context. Solomon Islands maps to Earth code `SLB` and can carry very high cultural
popularity while still having materially lower competition depth.

Missing FIFA Professional 2023 values for PNG, SLB and COK remain missing, never
synthetic zeros. Sparse pre-association periods are authored only as explicit
low-confidence backcasts bounded by the first documented association structures.


## FIFA canonical-history batch 7 — association identity in Oceania

American Samoa, Tahiti/French Polynesia and New Caledonia are now complete
1955–2026 country-history shards.

The key rule in this batch is that football-association identity is independent from
political sovereignty. Tahiti observations map to Earth `PYF`, New Caledonia to
`NCL`, and American Samoa to `ASM`. Tahiti and New Caledonia never inherit
metropolitan France evidence; American Samoa never inherits United States football
evidence.

American Samoa explicitly preserves the 2005–07 governance normalisation rather
than interpolating smoothly across it. Tahiti receives modern development anchors
for the 2023 artificial pitch and 2025 FIFA Talent Academy without backcasting
those facilities into earlier decades. New Caledonia preserves federation and
league history from 1928 while treating full FIFA/OFC membership in 2004 as a later
institutional transition rather than the beginning of football.

The batch also refreshes full-suite FIFA evidence totals after the preceding
Oceania expansion so global exact-count tests track all sharded datasets and
observations.

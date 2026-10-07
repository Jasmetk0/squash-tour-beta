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

## Liechtenstein / Gibraltar research batch — 7 October 2026

Baseline: `buuk` at `90279b3df104a0c78400adf6b9a3f94af83f8f19`.
This candidate adds LIE and GIB to FIFA Earth and ATP Earth: four complete 1955–2026 histories (1,728 authored annual attribute ratings).

- FIFA: 187 -> 189 authored histories; expected 241 datasets / 1,926 records.
- ATP: 187 -> 189 authored histories; expected 417 datasets / 894 records.
- Liechtenstein football uses UEFA-dated membership/infrastructure milestones through the September 2026 LFV Campus opening.
- Gibraltar football preserves its 1895 association history while gating UEFA membership to 2013 and FIFA membership to 2016.
- Tennis remains conservative: early values are explicit project assumptions and current structure is not backdated.
- All numeric ratings remain low-confidence project estimates, not measured federation values.

## Andorra / Montenegro research batch — 7 October 2026

Baseline: `buuk` at `f91b10f9eed9bd45bb2c2ba144510ba1e11eb79d`.
This candidate adds AND and MNE to FIFA Earth and ATP Earth: four complete
1955–2026 histories, 1,728 authored annual attribute ratings.

- FIFA: 185 -> 187 authored histories; 238 datasets / 1,916 records.
- ATP: 185 -> 187 authored histories; 415 datasets / 890 records.
- All new values are explicitly low-confidence project estimates, not measured
  FIFA/ATP ratings. Structural sources, project assumptions and numeric models
  remain separate; early assumptions cite the project rather than a federation.
- Football evidence gates federation/affiliation, competition and training/stadium
  milestones to their actual years. Montenegro retains territorial continuity
  without inheriting Yugoslav or Serbian national totals.
- Tennis uses documented Andorran men's competition from 2000, Montenegro's
  regional membership from 2006, 2021 grant eligibility and April 2026 junior
  development opportunities. Eligibility is not receipt; it causes no rating jump.
- Tests exercise all 72 years, six dimensions, source/observation integrity,
  dated-evidence gating, country identity and the non-measurement of early priors.

**Completion boundary:** 187 is the authored-history count, not 187 fully matched
Earth catalogue countries. The audited baseline still contains six FIFA and eleven
ATP sport-code aliases requiring a separate identity correction (e.g. ANG/AGO,
CRO/HRV). This candidate's AND/MNE codes already match the Earth catalogue.
The complete 250-country package build, final realism calibration and pending
integration repairs are not claimed completed by this data PR.

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

- **Neither official Earth directory exists yet.** FIFA and ATP each currently have 113 complete histories; neither reaches the required 250-country all-or-nothing build threshold. No fabricated neutral profiles are shipped to satisfy coverage
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


## FIFA canonical-history batch — ITA/NLD/BEL/PRT empirical calibration (5 October 2026)

Italy, Netherlands, Belgium and Portugal are now complete 1955–2026 FIFA Earth
country-history shards. The batch adds **1,728 annual attribute ratings**, taking
FIFA Earth to **33 / 250 complete histories**.

This slice intentionally reuses the already-normalized FIFA Big Count 2006 and
FIFA Professional Football Report 2023 datasets instead of manufacturing extra
historical observations from weak secondary pages. Before 2006, every rating is
low confidence and explicitly described as a calibration backcast toward the first
direct participation/club checkpoint. From 2006 onward, Big Count remains historical
participation/access context rather than a current census.

Professional 2023 evidence is temporally gated: no pre-2023 rating cites the
professional-player or professional-club datasets. From 2023 onward those observations
inform only development/competition/elite ecosystem scale. They do not directly
measure match quality, federation spending, academy outcomes or popularity.

The calibration keeps 9.0+ exceptional, does not use held-out rankings or title
outcomes, and records that tradition values in this batch are conservative continuity
estimates from observed organised-football footprint rather than mechanically converted
federation-foundation dates.


## FIFA canonical-history batch — AUT/DNK/SWE/CHE comparable evidence (5 October 2026)

Austria, Denmark, Sweden and Switzerland now have complete 1955–2026 FIFA Earth
histories, adding **1,728 annual attribute ratings** and taking FIFA Earth to
**37 / 250 complete histories**.

This batch is calibrated from the same canonical Big Count 2006 and Professional
Football Report 2023 families as the preceding ITA/NLD/BEL/PRT slice, with explicit
population-normalised context. The measured signals are not collapsed into one
football-strength score: Denmark and Sweden's dense club networks primarily strengthen
organised access, while Sweden's high 2023 professional-player density strengthens
professional competition/elite ecosystem context without becoming a direct ranking
or outcome score.

Pre-2006 annual values are low-confidence backcasts toward the first direct checkpoint.
Professional 2023 observations are cited only from 2023 onward. No held-out rankings,
trophy counts or tournament outcomes are used for calibration.


## FIFA canonical-history batch — NOR/FIN/HRV/SVN structural governance (5 October 2026)

Norway, Finland, Croatia and Slovenia now have complete 1955–2026 FIFA Earth
histories. The batch adds **1,728 annual attribute ratings**, taking FIFA Earth to
**41 / 250 complete histories**.

Four UEFA national-association profiles are normalized into 14 structural observations.
The evidence is used as dated chronology rather than as automatic rating deltas.
Norway and Finland provide long-running institutional anchors; Finland's currently
described regional centres of excellence are cited only in 2026 development/support
ratings.

Croatia and Slovenia deliberately exercise successor-state handling. Pre-independence
years describe football on the current Earth territory within Yugoslav governance,
without assigning Yugoslavia-wide participation, professional counts or outcomes to
the successor state. The 1991 political/competition transition is represented as a
real discontinuity, with FIFA and UEFA memberships gated to their documented later
years.

Big Count 2006 is never cited before 2006 and Professional Football Report 2023 is
never cited before 2023. High access density, professional ecosystem depth and
institutional tradition remain separate dimensions, and held-out rankings/titles are
not calibration inputs.


## FIFA canonical-history batch — POL/ROU/UKR/LTU transitions (5 October 2026)

Poland, Romania, Ukraine and Lithuania now have complete 1955–2026 FIFA Earth
histories, adding **1,728 annual attribute ratings** and taking FIFA Earth to
**45 / 250 complete histories**.

The batch adds twenty direct UEFA structural observations. Poland and Romania
provide long institutional continuity with dated reorganisation/infrastructure
anchors. Ukraine and Lithuania exercise Soviet-successor handling: current-territory
football is represented inside USSR governance without inheriting USSR-wide
participation, professional counts or outcomes.

Ukraine's 1991 autonomous-association/independence break and 1992 independent league
are explicitly gated. Lithuania likewise separates restored independence in 1990,
FIFA readmission in 1991 and UEFA membership in 1992. The authoring does not smooth
those governance changes away.

For Ukraine, the 2023–2026 access/development/support trajectory also remains below
the pre-2022 path rather than assuming operating conditions were unaffected.
Professional 2023 evidence remains a dated ecosystem observation, not proof that
the wider environment was unchanged. Big Count definition anomalies reduce confidence
rather than mechanically determining a rating.


## ATP canonical-history batch — Kazakhstan (5 October 2026)

Kazakhstan now has a complete 1955–2026 ATP Earth history, adding **432 annual
attribute ratings** and taking ATP Earth to **45 / 250 complete histories**, level
with FIFA Earth.

The historical model deliberately separates current-territory tennis from state
identity. Pre-1991 values describe documented Kazakh tennis activity inside Soviet
governance; USSR-wide participation, rankings or competition outcomes are not
assigned to KAZ. Kazakhstan NOC material anchors organised tennis in 1933 and the
first Almaty city-wide competition in 1935.

Independent-era competition begins with the President's Cup from 1991. KTF's own
retrospective describes the 1990s and 2000s as a difficult underfunded period with
limited international travel, so development and elite-support remain constrained
through 2009. The 2007 President's Cup Challenger/ITF upgrade marks a genuine
competition-system step.

Current 2026 evidence is strictly gated: KTF reports 14 regional branches, a
children/regional/coaching/referee development portfolio, a broad hosted competition
ladder, and a current infrastructure network of 39 high-performance centres and
394 courts. These are capacity/opportunity observations rather than direct player
outcomes, so modern KAZ remains below the 9+ world-leading threshold.


## Baltic dual-world canonical-history batch — Latvia and Estonia (5 October 2026)

Latvia and Estonia now have complete 1955–2026 histories in **both FIFA Earth and
ATP Earth**, adding **1,728 annual attribute ratings**. Coverage is now balanced at
**47 / 250 FIFA histories** and **47 / 250 ATP histories**.

For FIFA, official UEFA timelines preserve the pre-war associations, Soviet-era
governance and restored independent competition systems. Latvia's 1991 independence
and 1992 Virsliga/UEFA transition are separately gated. Estonia preserves the 1940
interruption, 1988 EFA re-formation, 1991 FIFA return and 1992 UEFA/Meistriliiga
restart. Big Count 2006 and Professional 2023 evidence are never cited early.

For ATP, the histories are deliberately independent from the football ratings.
Latvia is anchored by documented 1904 organised competition, the 1929 Latvian Tennis
Union foundation and 1937 ITF admission, with the amateur league entering only from
2013 and current LTS/ITF capacity only in 2026. Estonia uses its 1913 birth tournament,
1921 tennis section, 1922 federation foundation and official evidence of the Estonian
SSR Tennis Federation in 1968 before adding current ETL governance/development
capacity in 2026.

Across both worlds, current-territory Baltic sport during Soviet rule does **not**
inherit USSR-wide participation, player-strength or outcome evidence. Structural
milestones are chronology/capacity evidence, not automatic rating bonuses.

### Monaco + Kosovo reviewed batch (2026-10-07)
MCO and XKX now have complete 1955–2026 histories in both FIFA Earth and ATP Earth. Project-authored numeric priors remain explicit low-confidence estimates separate from external structural observations. Kosovo jurisdiction is represented in historical-entity labels, Monaco football evidence does not imply FIFA/UEFA membership, and current ITF member-association evidence enters only in 2026.

### Hong Kong + Macau reviewed batch (2026-10-07)
HKG and MAC now have complete 1955–2026 histories in both FIFA Earth and ATP Earth. Hong Kong uses British Hong Kong before 1997 and HKSAR afterward; Macau uses Portuguese Macau before 1999 and MSAR afterward. External football milestones remain dated, current ITF evidence enters only in 2026, and numeric ratings remain explicit low-confidence project estimates.

### Taiwan + DPR Korea reviewed batch (2026-10-07)
TWN and PRK now have complete 1955–2026 histories in both FIFA Earth and ATP Earth. Taiwan/Chinese Taipei naming and association milestones are explicitly dated, DPR Korea is kept distinct from Korea Republic, current federation-directory evidence is not backdated, and numeric ratings remain low-confidence project estimates.

### Guam + Curacao reviewed batch (2026-10-07)
GUM and CUW now have complete 1955–2026 histories in both FIFA Earth and ATP Earth. Guam federation/confederation milestones are explicitly dated; Curacao keeps pre-2011 Netherlands-Antilles context separate from its successor identity. Current ITF evidence is not backdated and numeric ratings remain low-confidence project estimates.

### Timor-Leste + Somalia reviewed batch (2026-10-07)
TLS and SOM now have complete 1955–2026 histories in both FIFA Earth and ATP Earth. Timor-Leste's colonial/transition/independent identities and 2002–2005 football milestones are explicit; Somalia's 1951/1962/1968 federation milestones are dated. Current ITF evidence is not backdated and numeric ratings remain low-confidence project estimates.

### Central African Republic + DR Congo reviewed batch (2026-10-07)
CAF and COD now have complete 1955–2026 histories in both FIFA Earth and ATP Earth. CAF federation milestones are dated from the current CAF profile. COD preserves historical state identities and the official CAF profile's internal chronology tension (created 1997, affiliated FIFA/CAF 1964) rather than silently reconciling it. Current ITF 2026 association evidence enters only in 2026.

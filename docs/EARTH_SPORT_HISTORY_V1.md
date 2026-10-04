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

- **Neither official Earth directory exists yet. Both research `countries` maps
  remain empty.** Registering future IDs does not display nonexistent packages.
  No fabricated neutral profiles are shipped to satisfy coverage mechanically.
- FIFA Big Count 2006 has five canonical normalized datasets and FIFA Professional Football Report 2023 adds two more. The review set has 25 source-specific structural-event datasets containing 43 dated institutional/development/tradition facts; a separate held-out validation seed adds 7 datasets / 14 events for Germany, Brazil, Iceland and San Marino. Other files directly under
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
`earth_sport_research.v2` catalogues. FIFA Earth now registers **39 canonical observation datasets / 1,342 observations**: five Big Count datasets, two Professional 2023 datasets and 25 structural-event datasets. Both country-rating maps remain empty.

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
3. FIFA structural-event evidence: 43 dated facts for the nine-country review set plus 14 separately labelled held-out validation facts for Germany, Brazil, Iceland and San Marino. Evidence includes pre-1955 institutional/competition history, academy/training-centre milestones and governance breaks. Relevance tags support development/tradition review but are never numeric effect sizes; the Morocco academy timing conflict remains unresolved by design.
4. ITF 2019 Czech/German participation, clubs and coach counts. Edition/report
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

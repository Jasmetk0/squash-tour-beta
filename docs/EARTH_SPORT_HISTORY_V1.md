# Earth sport histories — implementation and research boundary

Status: implementation candidate on top of `buuk` `7d2e120253cc3bea0c6e20113bcb1aec1a826df4`.
This is the historical-rating foundation, **not delivery of the two populated Earth packages**.

## Accepted scope

The owner requested project-official FIFA Earth and ATP Earth packages, representing
football and men's tennis environments. Each must cover every year **1955–2026**
for all countries in the existing Earth catalogue. A real-world year is the same
engine year. These are project estimates, not federation-endorsed products.
The six attributes keep their existing meanings on an explicit 1–10 scale with
at most one decimal. Court Count is outside pre-alpha. Population/geography are
separate inputs. Innate potential rarity must remain independent of nationality.

## Implemented in this candidate

- Explicit `country_ratings_1_10.v2`; unversioned legacy data retains its 1–5
  validation, formulas and serialized payload. No automatic historical migration.
- Per-year six-attribute histories with territorial interpretation, source IDs,
  rationale, confidence and interpolation/backcast/carry-forward provenance.
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
  existing package. Source catalogue and history metadata participate in identity.
  Persisted validation checks declared years and source references independently
  of the saved coverage report.

## Not implemented or not proven

- **Neither official Earth directory exists yet. Both research `countries` maps
  are empty.** Registering the future IDs does not display nonexistent packages.
  No fabricated neutral profiles are shipped to satisfy coverage mechanically.
- Historical ratings in an editable copy require versioned import/API authoring;
  the flat World Library editor deliberately disables Save for a history-bearing
  profile. A dedicated per-year/evidence editor is still required.
- The existing Custom World clone route is FAX-specific; generic Earth source
  cloning is still required before shipping these built-ins. Run source snapshots
  serialize Country history, but this candidate does not prove a complete Earth
  Run lifecycle or 50-season acceptance.
- Initial player development uses the season-start environment; it does not yet
  integrate every year of a player's pre-start development path.
- Country pipeline coefficients remain provisional. No measured realism result
  or completeness assertion follows from passing schema/tests.

## Research already stored

`config/earth_research/fifa_earth.json` and `atp_earth.json` contain source catalogues.
The observations directory contains facts, **not game attributes**:

1. FIFA Big Count 2006: 208 association rows, all-player participation, registered
   and unregistered players, clubs and officials. This survey is not men-only.
2. FIFA Professional Football Report 2023: 211 national pages with professional
   player/club totals. The extraction preserves nulls and source page numbers.
   Page 38 is labelled KUWAIT but shows a Kyrgyzstan flag/emblem: identity remains
   unresolved. Extracted national totals (129,388 / 3,997) differ from the published
   global summary (128,694 / 3,986). These facts are quarantined from calibration
   until reconciled, not silently corrected.
3. ITF 2019 Czech/German participation, clubs and coach counts, with exact source
   pages. Edition date is distinct from unknown observation year. The mixed-sex
   survey cannot be presented as men's participation. Coach count is not quality.

Reproduce the PDF extraction with:

```sh
python scripts/extract_fifa_2023_observations.py REPORT.pdf OUTPUT.json
```

PyMuPDF is an offline research dependency only. The output records the source PDF
SHA-256 and aggregate discrepancies; the PDF is not redistributed in the repo.

Audit research coverage:

```sh
PYTHONPATH=src python scripts/build_earth_sport_package.py config/earth_research/fifa_earth.json
PYTHONPATH=src python scripts/build_earth_sport_package.py config/earth_research/atp_earth.json
```

Only complete, reviewed research may be built by adding `--output NEW_DIRECTORY`.
The builder's `coverage_complete` is structural; `realism_validated` stays false.

## Required data completion

Map sporting associations and historical polities explicitly to the Earth country
catalogue (including UK associations, USSR, Yugoslavia, Czechoslovakia and colonial
territories). Population must not be duplicated when a predecessor has several
successors. Collect independent evidence for participation/access, development,
competition, elite support and tradition; ranking outcomes alone cannot measure
all six. Author period anchors with uncertainties, preserve documented structural
breaks, and interpolate only between defensible anchors. Label sparse early years
as estimates and 2026 as incomplete through the stated cutoff. Then compare
intake/development distributions with held-out sporting observations in Test Labs.

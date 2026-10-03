# Country Game Attributes V1

**Status:** `[DECIDED FOR V1]` attribute structure; exact calibration remains open.  
**Decision date:** 10 Aug 2026; scale and Court Count scope revised 3 Oct 2026 (Master v74).  
**Scope:** World Package country model and first-version player-pipeline semantics.

## 1. V1 principle

A country does **not** author the innate talent quality of people born there.

Country state affects the sporting pipeline around that talent:

`population → squash participation/access → prospect pool → development/competition/support → professional conversion`

A small or weak squash country must retain a non-zero chance of producing a generational player. A strong squash ecosystem should produce elite players more repeatedly because it samples more squash participants and converts more of its available talent, not because nationality creates genetically better players.

## 2. Authored Country Game Attributes

All six pre-alpha game attributes are finite numeric ratings on the inclusive **1 to 10** scale, with at most one decimal place (step **0.1**). Whole numbers are valid. This is the Master v74 target contract; the current runtime still validates 1–5 and requires a separate coordinated migration. Invalid inputs must not be silently rounded or clamped.

| Attribute | V1 meaning |
|---|---|
| `squash_popularity` | How strongly the population tends to actively participate in squash. |
| `squash_access` | How easy it is to play squash regularly: practical court/club access and affordability. |
| `development_quality` | Quality of coaching, talent identification, junior pathway and player development. |
| `competition_quality` | Quality and availability of meaningful competitive matches and tournament opportunities. |
| `elite_support` | Ability to support an elite junior/prospect through the transition to professional squash: funding, travel, physio and international opportunities. |
| `squash_tradition` | Long-term squash culture, know-how, role models and institutional continuity. |

The exact quantitative calibration of the scale is intentionally **OPEN**. No fixed meaning for each decimal increment has been decided.

## 3. Factual country data, not ratings

These remain factual/configuration data rather than game-strength ratings:

- `population_by_year` / effective population,
- `area_km2`,
- `region`,
- `travel_region`,
- `timezone_area`,
- country identity/name/flag/notes.

`Travel Region` and `Timezone Area` are independent geography layers in Master v45: Travel Region represents coarse physical travel burden, while Timezone Area represents biological time shift / jet-lag topology. They must not be collapsed into one field.

The repository now has a dedicated Timezone Area registry/assignment layer (see the implementation note below). It must not fake missing assignments by reusing `region` or `travel_region`.

**Deferred beyond pre-alpha (Master v74):** `court_count` is not an active pre-alpha input, editor field, new-package requirement or simulation factor. `squash_access` directly represents practical access. Existing stored court counts may survive only as inert compatibility data; their later use to derive/validate access is not yet specified.

## 4. Derived values — never authored as Country V1 ratings

The engine may derive concepts such as:

- Effective Squash Pool,
- Competitive Depth,
- Talent Discovery Rate,
- Professional Conversion Rate,
- Current Country Strength.

These must come from country data, authored V1 attributes and the actual simulated world state. In particular, **Competitive Depth** should reflect how many strong players actually exist in the country at that time rather than being a static authored country rating.

## 5. First implementation baseline

For the first implementation slice:

- initial-pool, annual-intake and weekly-intake country volume use effective population together with `squash_popularity` and `squash_access`,
- very large populations use diminishing-return weighting where a fixed global cohort is allocated,
- innate potential / quality-band rarity is global rather than increased by country development ratings,
- country-scoped history balancing such as the pre-V1 Recent Greatness Dampener may remain readable for audit but must not modify innate quality-band probabilities in V1,
- country strength does not create national style, personality, technical or mental DNA,
- `development_quality`, `competition_quality`, `elite_support` and `squash_tradition` describe the environment in which potential is realised,
- exact numerical weights are implementation calibration values, **not canon**.

Future calibration may change the formulas without changing this product model.

## 6. Superseded V1 country fields

The previous active model exposed:

- `wealth_support`,
- `system_quality`,
- `competition_density`,
- `federation_quality`,
- `style_dna`.

They are not active Country Game Attributes V1.

Backward-loading bridge for pre-V1 World Packages:

- legacy `wealth_support` → initial `squash_access`,
- legacy `system_quality` → initial `development_quality`,
- legacy `competition_density` → initial `competition_quality`,
- legacy `federation_quality` → initial `elite_support`,
- existing `squash_popularity` and `squash_tradition` keep their semantic identities; their numeric scale must still be interpreted from the source version.

This mapping is a deterministic migration bridge only; it does **not** claim semantic equivalence. It only fills a V1 field when an actual legacy source exists; missing authored V1 ratings are not silently invented and invalid legacy ratings are rejected rather than clamped.

`style_dna` / national play-style predispositions are deferred beyond V1. They must not bias first-version player style, personality or innate potential by nationality.

## 7. Migration/storage rule

**Master v74 migration requirement (not implemented by this documentation change):** version the rating scale explicitly across packages, imports/exports and Run snapshots. Coordinate domain/API validation, editor bounds/step and every normalization/formula currently assuming a maximum of 5. Never infer the scale from a value alone: 3 is valid in both scales. Do not rewrite historical snapshots or change historical replay semantics. The exact numerical conversion and calibration must be explicit and tested; this decision does not prescribe a formula.

Built-in read-only World Packages authored with legacy attribute files remain readable through the compatibility loader. New countries and edited custom-package countries are written only in the canonical V1 attribute format currently supported by the repository.

This avoids a noisy mechanical rewrite of every built-in country while ensuring all new mutable game-attribute data converges to V1. `Timezone Area` is a factual geography field from Master v45 and now has dedicated canonical package registry/assignment storage; legacy absence remains explicit.

## Timezone Area geography foundation (implemented after Country V1)

World Packages can now author a dedicated, ordered `timezone_areas` registry and a separate optional factual `timezone_area` country assignment. The order is a deterministic circular topology: first and last are adjacent, and topology queries preserve forward/backward direction while representing exact even-ring ties neutrally. This layer is never inferred from Region or Travel Region. Legacy packages without the registry remain readable and explicitly report the layer as not yet authored.

The Official FAX area count, codes, display names, boundaries, country assignments, UTC-offset interpretation, and all biological jet-lag magnitude/effect rules remain **[OPEN]** product/data decisions; this infrastructure does not decide or fabricate them.

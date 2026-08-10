# Country Game Attributes V1

**Status:** `[DECIDED FOR V1]` attribute structure; exact calibration remains open.  
**Decision date:** 10 Aug 2026.  
**Scope:** World Package country model and first-version player-pipeline semantics.

## 1. V1 principle

A country does **not** author the innate talent quality of people born there.

Country state affects the sporting pipeline around that talent:

`population → squash participation/access → prospect pool → development/competition/support → professional conversion`

A small or weak squash country must retain a non-zero chance of producing a generational player. A strong squash ecosystem should produce elite players more repeatedly because it samples more squash participants and converts more of its available talent, not because nationality creates genetically better players.

## 2. Authored Country Game Attributes

All six V1 game attributes are integer ratings from **1 to 5**.

| Attribute | V1 meaning |
|---|---|
| `squash_popularity` | How strongly the population tends to actively participate in squash. |
| `squash_access` | How easy it is to play squash regularly: practical court/club access and affordability. |
| `development_quality` | Quality of coaching, talent identification, junior pathway and player development. |
| `competition_quality` | Quality and availability of meaningful competitive matches and tournament opportunities. |
| `elite_support` | Ability to support an elite junior/prospect through the transition to professional squash: funding, travel, physio and international opportunities. |
| `squash_tradition` | Long-term squash culture, know-how, role models and institutional continuity. |

The exact quantitative meaning of ratings `1 / 2 / 3 / 4 / 5` is intentionally **OPEN** until calibration against simulation output.

## 3. Factual country data, not ratings

These remain factual/configuration data rather than game-strength ratings:

- `population_by_year` / effective population,
- `area_km2`,
- `region`,
- `travel_region`,
- `court_count` where known,
- country identity/name/flag/notes.

`court_count` may later help derive or validate access, but it is not itself a V1 quality rating.

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

- prospect/intake country volume uses effective population together with `squash_popularity` and `squash_access`,
- very large populations use diminishing-return weighting where a fixed global cohort is allocated,
- innate quality-band rarity is global rather than increased by country development ratings,
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
- existing `squash_popularity` and `squash_tradition` remain directly usable.

This mapping is a deterministic migration bridge only; it does **not** claim semantic equivalence.

`style_dna` / national play-style predispositions are deferred beyond V1. They must not bias first-version player style, personality or innate potential by nationality.

## 7. Migration/storage rule

Built-in read-only World Packages authored with legacy attribute files remain readable through the compatibility loader. New countries and edited custom-package countries are written only in the canonical V1 attribute format.

This avoids a noisy mechanical rewrite of every built-in country while ensuring all new mutable data converges to V1.

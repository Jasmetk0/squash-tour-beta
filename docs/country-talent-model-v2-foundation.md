# Country Talent Model V2 Foundation (merge-safe slice)

## New canonical country model

Countries are now modeled with a compact editable schema:

- `code`, `name`, `flag_asset`, `region`, `population`
- four integer simulation factors (`1..5`):
  - `wealth_support`
  - `squash_popularity`
  - `squash_tradition`
  - `system_quality`

This is intentionally simpler than the previous float-heavy model so tuning dozens of countries stays operationally manageable.

> Note: current `the retired global countries seed` values are a temporary seed/demo dataset, not finalized project world content.

## Annual talent class planner

`AnnualTalentClassPlanner` creates a deterministic yearly plan from `(year, seed, countries)`:

1. computes total global cohort size for the year,
2. allocates talent counts to countries,
3. assigns quality bands to each country allocation,
4. emits deterministic `TalentSeed` values for downstream player generation.

Typed output models:

- `AnnualTalentClassPlan`
- `CountryTalentAllocation`
- `TalentSeed`
- `TalentQualityBand`
- `CountryGenerationBiasProfile`

### Allocation drivers

- **Volume (count):** nonlinear population (`log10`) + strong popularity signal, with smaller support from system quality and wealth.
- **Quality (bands):** primarily system quality + tradition, secondarily wealth + popularity.

### Rarity

Quality bands explicitly include a `generational_talent` top tier with extremely low probability; stronger countries increase odds but do not guarantee outcomes.

## Foundation-only scaffold included

- `RecentGreatnessDampener` interface is now present.
- `NeutralRecentGreatnessDampener` currently returns neutral multipliers (`1.0`) and keeps planner behavior unchanged.
- This creates a safe architectural insertion point for future commissioner/history-aware dampening.

## What is intentionally not rewired yet

- Full runtime player creation flow is not replaced by this slice.
- Existing generators still run; compatibility properties preserve current behavior while migration continues.
- Tabular user authoring is handled by a bridge workflow (`scripts/countries_tabular_tool.py`) until an in-engine editor is built.

## Next slice

1. Wire annual plan consumption into player generation runtime.
2. Persist annual plans/snapshots with `config_version` traceability.
3. Connect non-neutral dampener to commissioner/manual-override history.
4. Incrementally replace compatibility aliases in legacy generator paths.

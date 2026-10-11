# InitialWorld exact country quotas — pre-alpha V1 slice

Target: approved Master v78 §9.6. **Scope:** the single first-season 2000/01 Run-owned World generation batch with an explicitly specified total (Admin UI 1–1000). This is not a generic constraint solver.

## Supported contract

- `generation.country_quotas` is an optional, sorted list of unique `{country_code, count}` records. Counts are nonnegative **integers**. A missing/empty list preserves historical generation/fingerprint semantics.
- Each count is **exact across the full batch**, not extra players. Example: total 100, `CZE:20`, `SVK:10` gives exactly 70 other eligible countries. `CZE:0` explicitly excludes CZE.
- The remainder is allocated through the **existing Run-owned World population-weighting kernel** over eligible non-quota countries only. This does not change ability/talent rarity or attempt to calibrate it.
- Global country/geographic/travel-region/age hard conditions continue to apply to **every** player. Quota-country membership is checked against the same selected saved World and typed region constraints.
- Overbooking, duplicate/unsorted country codes, unavailable/ineligible country, noninteger/negative counts, Keep-preserved counts exceeding exact quotas, and nonzero remainder without an eligible non-quota country fail explicitly. No changing quotas to hints, rerolling a kept player, or silently dropping a constraint.
- Keep replays against the exact original reviewed input/fingerprint. Preview is read-only; Adopt recomputes the real source and checks the reviewed fingerprint and Save remains a separate manual action. Saved proposal payload stores and restores the same quota input without regenerating on Open.
- Frontend independently verifies full returned player membership and exact counts before enabling Adopt. Form changes invalidate the previously reviewed proposal. It displays total / explicit / automatic counts and highlights conflicts.

## Limitations

- Distinct sport country identities make this quota slice disjoint; overlapping potential-tier/handedness groups, arbitrary nested groups, Automatic **total** from partial quotas, general existing-player additions and future-season generation remain unsupported.
- `country_quotas` is absent from historical source fingerprints when not used. InitialPool source player numeric scale is still 1–99, not canonical 57-field/0–200 attributes.
- The entire 50-season release gate remains separate from scoped Fast CI and real browser checks.

## Verification

Focused backend deterministic, exact/zero/remainder, Keep/Adopt, fingerprint compatibility and fail-closed tests; frontend component quota/editor tests and real 1000-player browser regression run on the latest PR head. See the PR checks for actual outcomes.

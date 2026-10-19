# Native Tour Signed prospect intake preflight v1

This is a **read-only**, Admin-only integration step. A new endpoint:
`GET /admin/runs/{run}/branches/{branch}/calendar-tour/prospect-intake/preflight`
authenticates the current Saved HEAD/Run/Branch, existing sporting checkpoint and
the Run-owned prospect source against exact Saved Revision bytes and live SQLite.

Its source-aware pure planner computes the **next real Run Week** (W=52/61/80,
including W→next Season Week 1 and the Run's offset), derives each prospect's
actual 15th birthday from immutable birth year/year-week, independently checks
stored cohort week, year/week and age, and validates due canonical 57-attribute
sporting profiles and source countries. Identity collisions and unsupported
source/sporting identities fail closed. It returns stable due IDs/labels/country,
source/HEAD/checkpoint fingerprints, blockers and a deterministic preflight hash.

The new endpoint is *not a Save, transition, activation, simulation or readiness
gate*. No transition guards were removed. It explicitly returns
`native_activation_supported=false`, even with a complete cohort, because
native Tour lifecycle/sporting/Health/ranking atomic insertion and Signed replay
remain unavailable. This prevents operator misunderstanding while supplying
accurate birthday-boundary evidence for the next integration slice.

Old FAX 61-week intake generators are untouched; they are not reinterpreted as
52/80-week sources, and no old Saved hash/schema is rewritten. The source must
already have been Saved and must still match the Run's shared rows.

Tests cover W52/O1, W52/O35, FAX W61/O37, W80/O15, season rollover,
missing sources, future/past cohorts, age/calendar corruption, foreign
identity and missing/mismatched canonical profile. Production HTTP integration
and authenticated cross-Branch Saved source failure are subsequent acceptance
gates, not claimed by pure tests.

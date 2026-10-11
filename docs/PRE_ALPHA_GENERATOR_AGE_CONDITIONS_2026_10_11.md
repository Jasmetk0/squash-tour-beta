# Single Run generator — hard age constraints (2026-10-11)

Status: stacked implementation candidate on top of #1370; **not** a replacement for its country/region checks. Once #1370 is merged, retarget this PR to `buuk` and rerun/verify final HEAD; user alone merges.

## Contract

Run → Players → Generate accepts an optional **minimum age** and/or **maximum age** in whole years, within **15–45**. Either blank means no bound on that side. Age means a player's age at the **first week of 2000/01**, not a forecasted age and not a match-week projection. Minimum above maximum or values outside bounds are explicit errors, with Preview disabled.

Both limits flow through the existing `RunWorldInitialPoolPreviewRequest`, into the **same production InitialPlayerPoolGenerator**. The production algorithm does not generate then discard whole players, loop/retry indefinitely, or silently decrease the requested count. When bounds are present, each original career-stage weight is multiplied by the fraction of its age interval allowed by the constraints; one stage is then drawn from these *conditioned* weights and the exact age from its eligible ages. This retains the existing stage↔age correlation and avoids fabricating styles/skills by nationality. **Unconstrained inputs take the original two RNG draws unmodified**, with established identities, potential and deterministic output.

Hard country/region conditions from #1370 still apply to the entire cohort, and can be combined with age. User choice is included in request and preview fingerprints; changing the age requires a new full preview. Frontend verifies every generated player's first-season age and existing country/region restrictions before permitting Adopt. Existing Run/Branch/Saved HEAD/draft/World guards, separate staged component and explicit manual Save remain unchanged. Historical time and overwriting saved InitialWorld remain disallowed.

### Evidence

- `tests/domain/test_initial_pool_age_conditions.py`: original default generation preserved, deterministic replay and stage consistency under 15/15, 18–25, 45/45, single-ended bounds; invalid bounds fail closed.
- `tests/api/test_earth_world_run_acceptance.py`: genuine FIFA/ATP Earth source, country+region+18–25 bound and deterministic result.
- `web/src/api/runInitialWorldSetup.test.ts`: explicit bounds and per-player verification.
- `web/src/components/RunInitialWorldSetupPanel.test.tsx`: blocked invalid limits, actual reviewed request, stale review rejection and out-of-range preview refusal.
- `scripts/admin_first_tournament_smoke.py`: Chromium age selectors and reset, followed by established complete manual Save/tournament/replay workflow.

## Explicit scope limits

This is a **first-cohort age selection**, not a calibrated new player age/potential model, an annual intake generator, midseason regeneration, or a full 0–200 OVR model. The world's effective population country-allocation weighting stays on its currently implemented full-birth-cohort basis; this change *conditions the individual stage/age draw*, without claiming age-conditioned population volume calibration. Group overlap, unassigned remainder, independently edited preview players, permanent locks and Player Package serialization remain unresolved or outside this slice.

Do not confuse fast PR checks with the full internal pre-alpha regression/release gate.

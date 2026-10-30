# Exact continuation of a copied-FAX probe

## Reproduced defect

The first actual copied-FAX probe freezes a durable Full Simulation parent and
pauses at a real preparation checkpoint. Repeating that exact probe request used
to call `preview_full_simulation` again. That reader correctly refuses a second
parent while the first is pending, so the probe incorrectly replaced its real
checkpoint and execution evidence with `full_simulation_preview_unavailable`.
The same failure persisted after an API/SQLite restart.

## Correction

Before creating a new review, the probe asks the production driver's existing
pending-parent inspector for this Run/Branch. That inspector validates the stored
command scope, request fingerprint and reviewed contract. If this exact command
ID exists, the probe:

- requires the same normalized operator, audit reason and Run/Branch identity;
- verifies the complete original review against the command's frozen preview hash;
- refuses a retargeted/shortened or precise-boundary parent instead of silently
  reinterpreting it as the original full reference range;
- supplies the **entire original command** to the normal execution method.

No sporting writer, task ownership rule, lease, manual Save boundary, control state
or persisted schema changes. A paused parent remains paused; only the existing
explicit operator Resume can change that. A different command ID cannot replace
an already pending parent. Corrupt persisted evidence fails closed. There is no
new receipt/cache/authority, automatic Save, Entry validation or native dispatch.

## Verification

`test_pre_alpha_fax_probe_continuation_api.py` uses the real copied FAX source,
1,000 generated players, 80 Editions, HTTP API, Full Simulation and SQLite. It
checks identical retry reports and original parent bytes, changed-audit rejection,
rejection of a competing parent, actual API/SQLite reopen, explicit Pause/Resume,
and an explicitly retargeted parent rejection without mutation. Original Saved
Revision bytes/hash and source hash remain intact. Its explicit qualification
awards are isolated test inputs, not FAX product rules.

The same regression test was run against original `buuk`
`edd237b7a2d5e1d69cf96aafce13799bf428253b` and failed on the second probe's
checkpoint/preview/execution fingerprints. It passes with this application adapter
correction. Separate mocked contract tests exercise damaged reviews, audit/scope
mismatches and changed targets; those are not substitutes for the actual API case.

The actual API case completes locally in approximately 16 seconds; Fast CI selects
it as a changed `pr_critical` module. No existing expensive acceptance was shortened
or replaced. Required hosted evidence must match the final candidate SHA.

## Limits and coordination

This slice concerns pending legacy FAX probe continuation only. Completed or
abandoned/terminal parents are not reopened, retargeting belongs to the normal
Full Simulation controls, and server-task-owned parents still require their task
continuation endpoint. It does not prove a played reference season, actual native
reference migration, the required 50 seasons or release readiness.

It changes no files owned by #1662, #1670 or the reference-points preparation
candidate #1671. That candidate independently fixes empty/incomplete points
snapshots; this test authors complete isolated inputs for compatibility with that
correction. Both target `buuk`; no owner merge is performed by this workflow.

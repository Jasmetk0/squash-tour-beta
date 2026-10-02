# Pre-alpha checkpoint — 2 October 2026

## Verified baseline and review scope

Repository: `Jasmetk0/squash-tour-beta`; integration branch: `buuk`.
Audited commit: `aceb144d79924a985ada34b9eefaec53f548cf1c`, merge of #1093.
Previous Master: v69, #1074; Master blob `21a0391ce3f1a48c1fabfe579ca742b60751e154` was identical locally and on GitHub.
GitHub comparison from #1074 to the audited commit: ahead by 163 commits, behind by 0.
No open PR was returned at this checkpoint.

Review covered every new PR's metadata, changed-file patch inventory, final-head hosted Fast CI and inline review comments; no inline review comments were returned. Targeted source review examined Viewer projection/migration boundaries, Talent Intake materialization and quality derivation, Calibration Lab V1–V3, schemas and tests. This is a checkpoint review, not a claim of exhaustive line-by-line verification of every historical file or full release acceptance.

Local git transport was unavailable. Current changed sources were read through the GitHub connector at the immutable audited SHA. The local working tree was not presented as a fresh full checkout. No production data or protected built-in Run/Package was modified.

## PR inventory

| PR | Change | State | Final PR-head hosted check |
|---|---|---|---|
| [#1075](https://github.com/Jasmetk0/squash-tour-beta/pull/1075) | Move H2H sporting metadata to canonical Saved-Revision sources | merged | success; [Fast CI 2111](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36767401987) |
| [#1076](https://github.com/Jasmetk0/squash-tour-beta/pull/1076) | Add canonical Saved-Revision Viewer Players and Countries | merged | success; [Fast CI 2112](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36769185110) |
| [#1077](https://github.com/Jasmetk0/squash-tour-beta/pull/1077) | Move Viewer people lists, search and H2H samples to canonical APIs | merged | success; [Fast CI 2120](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36771183641) |
| [#1078](https://github.com/Jasmetk0/squash-tour-beta/pull/1078) | Move Viewer Player and Country details to canonical Saved-Revision people | merged | success; [Fast CI 2126](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36824891237) |
| [#1079](https://github.com/Jasmetk0/squash-tour-beta/pull/1079) | Move Viewer Tour hub to canonical Saved-Revision sources | merged | success; [Fast CI 2130](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36831152955) |
| [#1080](https://github.com/Jasmetk0/squash-tour-beta/pull/1080) | Retire dead Viewer snapshot compatibility surfaces | merged | success; [Fast CI 2131](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36848440656) |
| [#1081](https://github.com/Jasmetk0/squash-tour-beta/pull/1081) | Move legacy Race snapshot source context to canonical Viewer authorities | merged | success; [Fast CI 2133](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36849256250) |
| [#1082](https://github.com/Jasmetk0/squash-tour-beta/pull/1082) | Move Viewer Tournament and Week details to canonical Product Run authorities | merged | success; [Fast CI 2136](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36851035140) |
| [#1083](https://github.com/Jasmetk0/squash-tour-beta/pull/1083) | Restore current-base main-entry provenance recovery coverage | merged | success; [Fast CI 2140](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36851829405) |
| [#1084](https://github.com/Jasmetk0/squash-tour-beta/pull/1084) | Separate expected talent output from generated yearly result | merged | success; [Fast CI 2143](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36852770218) |
| [#1085](https://github.com/Jasmetk0/squash-tour-beta/pull/1085) | Connect Talent Intake to run-scoped cohort season preview | merged | success; [Fast CI 2144](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36853240291) |
| [#1086](https://github.com/Jasmetk0/squash-tour-beta/pull/1086) | Add reviewed Talent Intake materialization workflow | merged | success; [Fast CI 2145](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36853521115) |
| [#1087](https://github.com/Jasmetk0/squash-tour-beta/pull/1087) | Inspect materialized Talent Intake prospect output | merged | success; [Fast CI 2147](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36854109102) |
| [#1088](https://github.com/Jasmetk0/squash-tour-beta/pull/1088) | Centralize provisional talent quality rarity weights | merged | success; [Fast CI 2149](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36920146440) |
| [#1089](https://github.com/Jasmetk0/squash-tour-beta/pull/1089) | Integrate weekly 15yo cohorts with deterministic talent quality bands | merged | failure; [Fast CI 2150](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36920985858) |
| [#1090](https://github.com/Jasmetk0/squash-tour-beta/pull/1090) | Fix Talent Intake quality test scope after merged #1089 | merged | success; [Fast CI 2152](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36976699426) |
| [#1091](https://github.com/Jasmetk0/squash-tour-beta/pull/1091) | Add deterministic Talent Calibration Lab | merged | success; [Fast CI 2158](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36982698386) |
| [#1092](https://github.com/Jasmetk0/squash-tour-beta/pull/1092) | Add candidate potential policy sandbox to Talent Calibration Lab | merged | success; [Fast CI 2162](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36989865723) |
| [#1093](https://github.com/Jasmetk0/squash-tour-beta/pull/1093) | Add multi-seed robustness analysis to Talent Calibration Lab | merged | success; [Fast CI 2167](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/36994968407) |

#1089 was merged with failed Fast CI #2150. #1090 repairs the ambiguous frontend quality-band assertion and the final-head CI for #1090 and subsequent PRs is green. This incident does not justify merging future red/pending heads.
#1083 carries the current-base replacement for stale #951; no old PR needs reopening.

## Findings and remaining gaps

### F1 — historical quality labels depend on today's global policy (priority 1)

`src/beta_engine/application/api_services.py` derives `quality_band` when listing persisted prospects using `talent_quality_band_from_seed(record.potential_seed)`.
`run_prospect_materialization_service.py::summarize_materialized_talent` does the same and calculates expectations using current global rarity weights.
`talent_quality_policy.py` reads the current module-level weights and policy ID; neither API read resolves a historical policy from that record.

An immutable seed alone is insufficient: editing the policy or its ID can relabel existing players and change historical summaries. A controlled, isolated 100-seed probe changed only the weights to a deterministic all-Generational policy, then restored the in-memory values; 100/100 labels changed. This is a reproduction of the policy dependency, not evidence that production data has already been damaged.

Required next boundary: frozen/replayable policy identity and values, deterministic historical resolution, safe legacy provenance migration, and Saved Revision/fork/restore preservation. Do not choose new rarity numbers or band→potential mapping.

### F2 — review confirmation is not bound to the reviewed scope (priority 1)

`web/src/pages/TalentIntakePage.tsx` resets the checkbox for intake/growth edits, but the Run ID input only calls `setRunIdInput`. A checked confirmation can survive switching from Run A to Run B.
The mutation captures the current Run ID and numeric controls; it sends no reviewed world/cohort fingerprint or explicit reviewed season. The server re-builds the preview in `materialize_15yo_cohort`, so `overwrite: false` alone does not establish that the confirmed target is the reviewed target.
Static reproduction path: review A → tick checkbox → switch Run ID to B → wait for B preview → confirmation remains enabled. Add UI scope invalidation and server-side stale-preview validation with no partial writes.

The page also still describes itself as not creating players although it now has a materialization command. Correct that explanation with the workflow fix.

### F3 — Expected vs Generated is only a conditional rarity diagnostic (functional gap)

The current summary multiplies the already-materialized country count by current global band weights and includes only countries that have persisted records. It cannot demonstrate whether the number generated by a country deviated from a pre-generation forecast, and a zero-output country disappears.
Keep this useful conditional diagnostic truthfully labelled. The confirmed product needs a stored, historically versioned pre-generation expectation, complete country scope including zero outcomes, partial/complete cohort state, and comparison after the generation period finishes. Country pool size and rarity distribution are different quantities.
Run intake also uses `get_simulation_run`; its connection to the canonical Product Run/Branch must be explicit before claiming complete branch-aware integration.

### F4 — Calibration candidate ranges are silently floored by current OVR (priority 2)

The production kernel computes `potential_ovr = max(current_ovr, rolled_potential)`.
A candidate with all five ranges `0..0`, seed 5 and sample_count 20 returned effective Potential OVR 65..105 in the isolated current-service probe.
The Lab currently calls the submitted values “Candidate potential ranges” without explaining this effective floor. Preserve the production kernel; clarify sampled vs effective values and report adjusted sample counts or an equivalent explicit diagnostic. Do not silently change potential semantics to fit a UI label.
A baseline-equivalent multi-seed probe (seeds 5–6, 20 prospects each, all ranges 110..190) correctly returned 40/40 unchanged.

### F5 — optional Viewer projection exposes internal potential (release-boundary issue)

#1076's `viewer_people_read_model.py` copies `sporting_player.potential_ovr`, current Form and fatigue directly into Viewer DTOs. #1077/#1078 render those values; no explicit reveal-policy check is present at this projection boundary. The Master distinguishes public information from Admin truth, and its Potential OVR is hidden by default.
The Viewer is outside the first pre-alpha acceptance scope; further Viewer expansion has no priority. If these pages remain accessible, audit or conservatively gate internal fields rather than treating all Saved Revision data as public. Current-state-only profiles also do not prove historical time-machine support.

### Scope still required by Master v70

- A copied FAX test template with at least 1,000 non-retired pre-start players and a reference 80 World Tour Editions; lower Tours abstract.
- Three testable pre-start ranking modes; no final FAX canon selected.
- Global Match/Tournament Lab with portable replayable scenarios, shared execution kernels, compatibility diagnostics and Run-copy/draft boundaries. Talent Calibration Lab is a useful additional diagnostic, not a substitute for these Labs.
- Actual availability/travel and scenario-based discipline replace a universal Week Tournament Lock.
- Country imports remain independent editable Run snapshots; no live Woorld FAX dependency.
- CZ/EN Admin, history/recovery and complete season/empty-Run acceptance remain obligations.
- Fairness and numeric calibration remain explicit test work, not automatic canon inherited from source constants.

## Validation actually performed

- GitHub live metadata, complete changed-file patch retrieval for #1075–1093, CI results at each final PR head, empty open-PR inventory and inline-review inventory.
- Current Master source hash match and branch comparison; targeted source review and isolated Python kernel probes described above.
- No local full backend/frontend suite or application browser acceptance was run. Local pytest was unavailable; importing it raised `ModuleNotFoundError`. Existing hosted green CI is evidence of its own configured checks only.
- Documentation validation: complete PAQ-001–157 with no duplicate/missing identifiers; 57 resolved / 97 open or partial / 3 outside first pre-alpha. Check document diff/whitespace before publishing.

## Chosen continuation

1. Execute the one prepared task in `docs/CODEX_NEXT_TALENT_INTAKE_HISTORY_V1.md`: freeze Talent Intake history and bind Review→Confirm to the exact scope. This addresses data trust before any calibration changes.
2. Repair the explicit diagnostic gaps (forecast vs realized output, effective potential floor, future-cohort visibility) using the same authority boundary; no further arbitrary Lab expansion.
3. Complete the global Match/Tournament Lab and a realistic copied FAX season path, using existing shared kernels.
4. Re-run focused checks per slice and the full internal-release acceptance only when the integrated path is ready. Decide calibration/fairness from measured cases at that point.

This is a technical work ordering under the user's authorization. It does not close open sporting mechanics or automatically authorize merging this documentation PR.


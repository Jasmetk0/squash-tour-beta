# Admin Edition Entry timing — CS/EN

Frontend consumer of merged backend contract #1675. No backend sporting rules, Saved ownership, or ranking authority are changed.

## Scope

The editor appears only in present Run Admin planned Edition detail with explicit matching Branch and Calendar Package. Parent verifies an active writable Product Run, matching Saved head / clean Working Draft for mutation, matching Run-owned Calendar projection, Package state and Edition identity. A dirty Draft after confirmation is displayed read-only. Historical/foreign handoff cannot write. Run calendar metadata must be the actual explicit v1 record, with no inferred FAX 61/50/2000 defaults.

## Review and Save separation

1. GET Entry timing distinguishes loading/errors, missing plan and existing plan; explicit retry is available.
2. A new plan pre-fills only Main=2 and Q=1 durations. Main opening Season Index / Week is always explicit. Optional Final Commitment and ranking publication override send null when unchecked, never zero or latest-ranking fallback.
3. POST preview is read-only and displays server before/after, inclusive Main/Q windows, final commitment, completed ranking-data week and distinct publication label, source, blockers and fingerprints. Main 13–14 / Q 15 uses data after week 13 and publication labelled 14.
4. Operator label and audit reason precede explicit POST confirm using the server preview fingerprint. The complete original command payload and ID are retained for user-triggered exact retry after ambiguous failure. Edits invalidate the preview; language switch preserves it.
5. Confirm stages only the Working Draft and possibly the exact published Ranking Snapshot binding. It never triggers Save, adoption of another ranking, simulation, players, fields, draws or publication. A **separate checkbox and Save button** use the existing Working Draft Save API only after fresh server checks verify Run, Branch, prior Saved head, dirty Draft version, and exact Package fingerprint. No automatic Save takes place. The owner still controls merging.

## Honest readiness

missing_prerequisite is not confirmation. A valid future plan may still be confirmed without an existing publication only when the server explicitly reports can_confirm_configuration=true. ready_for_explicit_confirmation and bound are distinct. timing_and_ranking_ready covers current Working Draft configuration only and is not Saved or player eligibility. automatic_eligibility_status=not_implemented is visible. unsupported_execution does not authorize sporting operations.

## Test boundary

web/src/components/RunEditionEntryTimingPanel.test.tsx contains mocked React/API-boundary tests for empty plan, CS/EN, preview invalidation, blockers, missing future ranking, explicit confirm/exact retry, no auto-Save and disabled/foreign context. These are not real Chromium, production HTTP or SQLite integration evidence. #1675 separately has backend HTTP/SQLite tests. The final head needs TypeScript/Vite and relevant hosted checks; skipped Draft acceptance is not a pass.

Known limitation: historical Run records without explicit v1 Run calendar metadata intentionally fail closed. The existing general planned-event page still has separate legacy-only projection assumptions. Automatic sporting Entry validator and real browser Save/reopen acceptance remain outside this slice.
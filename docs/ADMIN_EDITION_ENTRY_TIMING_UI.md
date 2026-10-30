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

Mocked tests in web/src/components/RunEditionEntryTimingPanel.test.tsx verify empty/existing review, CS/EN persistence, preview invalidation, blockers, future missing ranking, exact confirm/retry, Save safeguards and delayed/foreign contexts. web/src/api/runEditionEntryTiming.test.ts verifies the exact encoded HTTP request/response boundary; web/src/pages/PlannedEventDetailPage.test.tsx exercises verified Admin wiring. These are not real Chromium, production HTTP or SQLite integration evidence. #1675 separately has backend HTTP/SQLite tests. The final head needs TypeScript/Vite and relevant hosted checks; skipped Draft acceptance is not a pass.

Known limitation: historical Run records without explicit v1 Run calendar metadata intentionally fail closed. The existing general planned-event page still has separate legacy-only projection assumptions. Automatic sporting Entry validator and real browser Save/reopen acceptance remain outside this slice.
## 30-point continuation — incremental implementation (30 October)

- **Implemented/improved:** #1 progress across local/preview/Draft/Saved; #2 explicit Run/Branch/Edition/Calendar Package context; #5–7 hints, calendar-specific season labels, ranges and input error association; #8–11 local restore, independent edit status, explicit 2+1 and advanced grouping; #23–25 concise confirmed receipt and technical disclosure; #27 concrete Saved ID and existing Run Management link; #28–29 CS/EN and narrow-screen ID wrapping.
- **Retained from existing PR:** #3–4 no-plan/existing-plan, #14–22 server-only ranking/window/readiness/blockers, #24 exact retry and #26 separate guarded Save. No additional backend or sporting authority.
- **Still open for verified follow-up:** #12 selecting an actual ranking publication from an existing Run/Branch list, #13 compact changed-field diff, #18 explicit operation impacts of every blocker, #27 exact Saved Revision route (unverified), #30 final-head checks and real browser/HTTP/SQLite acceptance. These must not be marked done from mocked tests.
- Added mocked React tests for restore, audit-only changes and exact field bounds; no real backend or browser is claimed. Last-head CI and Sonar gates must be checked independently. Keep Draft.

- Follow-up: #13 frozen server before/after fields and disclosed unchanged values added. Accessible field error text is now outside labels. The actual execution, save and ranking boundaries remain unchanged.

- #12 integrated existing Run/Branch/Edition published Official Ranking options API as an optional dropdown, loaded only when override is enabled. Displays pending/empty/error separately; selection changes local week only and never binds, confirms or Saves. Mocked UI tests cover real-shaped options and empty history.
- #18/#20 now distinguish server-permitted preparation from blocked confirmation and from unsupported sporting execution. No new authority is inferred.

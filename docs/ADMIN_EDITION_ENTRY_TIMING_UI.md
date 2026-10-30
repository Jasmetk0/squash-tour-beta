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
## Checklist of 30 continuation tasks (30 Oct 2026)

_Status is evidence-scoped: **Implemented/Improved** = frontend code added, **Retained** = pre-existing behavior preserved, **Partial** = verified dependency remains. Mock tests are not real browser/HTTP/SQLite acceptance._

| # | Status | Evidence / remaining dependency |
|---:|---|---|
| 1 | Improved | Verified data-based Local / server Preview / confirmed Draft / Saved receipt step |
| 2 | Partial | Exact IDs Run/Branch/Edition/Calendar Package shown; source provenance needs separate verified parent metadata |
| 3 | Retained | Missing plan explained; no zero/ready fallback |
| 4 | Retained | Actual Run clock; before/after existing Entry values; no 61/50/2000 assumption |
| 5 | Improved | Main, duration and advanced fields explained; no invented sporting validation |
| 6 | Improved | Real W and season-count validation; season label depends on Run offset |
| 7 | Improved | Per-field season/week/duration aria-invalid and error text; frontend validates syntax only |
| 8 | Implemented | Restore loaded plan locally, preserving operator/reason; no command |
| 9 | Improved | Local dirty, preview, confirmed Draft and Saved distinguishable |
| 10 | Implemented | Explicit 2+1 duration button preserves other fields and does not POST |
| 11 | Implemented | Collapsible advanced options; disabled override serializes as null |
| 12 | Implemented | Existing Run/Branch/Edition publication list; load/error/empty state; selection fills fields only |
| 13 | Implemented | Frozen server before/after differences, unchanged disclosed |
| 14 | Retained | Main/Q/Final server-resolved windows with season index |
| 15 | Retained | Completed-data and publication week displayed separately, not recalculated |
| 16 | Retained | Default versus explicit ranking source and exact fingerprint |
| 17 | Retained | missing_prerequisite / ready_for_explicit_confirmation / bound are separate |
| 18 | Improved | Backend blockers exposed; confirm-permitted versus blocked shown; blocker-specific remediation not exhaustive |
| 19 | Retained | Server-approved future plan can confirm without ranking publication |
| 20 | Improved | Allowed Package prep is explicitly distinct from unsupported sporting execution |
| 21 | Retained | Draft-only timing/ranking readiness; eligibility not_implemented |
| 22 | Retained | Edits invalidate actual preview; audit-only edits and CS/EN do not; no read-induced write |
| 23 | Retained | Explicit command ID, operator, reason, preview fingerprint and duplicate submission fence |
| 24 | Retained | Original command/payload held for exact retry; old scope responses suppressed |
| 25 | Improved | Confirmed Draft version and action shown; technical command/fingerprint under disclosure |
| 26 | Retained | Independent consented Save and fresh Run/Branch/Draft/fingerprint reads |
| 27 | Partial | Exact Saved ID and existing history link; no verified per-revision deep-link route |
| 28 | Improved | New UI messages and state labels CS/EN; audit text and preview preserved |
| 29 | Partial | Field label/aria associations and wrapping improved; real browser/mobile keyboard audit pending |
| 30 | Partial | Mocked component tests added for local restore, preview audit, diff, publication options, empty state. Hosted final-head CI and real browser/HTTP/SQLite acceptance still required |

### Verification boundary

- All edits are in this single Draft PR #1676; no backend, Master or sporting rules changed. The simultaneously open #1677 is untouched.
- Mocked tests in RunEditionEntryTimingPanel.test.tsx test local restore, CS/EN preview persistence, exact retry, server windows, optional explicit fields, guarded Save, changed-field display and real-shaped ranking list responses; they cannot prove a browser/database integration.
- **Must not merge on stale results:** run latest-head frontend tests and TS/Vite build; check actual hosted status, Sonar new-code gate and focused real browser + HTTP/SQLite Save/reopen. Skipped Draft workflows do not count as acceptance.
- Known limitation: older Runs without explicit v1 clock still fail closed, and the generic planned event page has unrelated legacy projection assumptions. This UI does not implement automatic Entry eligibility.

## Exact retry safety regression

An uncertain Confirm response freezes the form and the server Preview button until the original command is explicitly retried. A second preview must not clear the immutable `command_id` and payload, because the original Confirm may already have reached the server. The component regression verifies the preview remains disabled across CS/EN switch and that only the original payload is resubmitted. This is mocked frontend evidence, not a real connection-loss/SQLite test.

## Stable list identity regression

Season option keys use stable calendar-derived season labels. Server blockers retain all entries even when their code and explanation are identical: keys are based on each content identity plus occurrence within that identity rather than list position. A mocked React test checks duplicate blockers render without duplicate-key warnings or premature confirm.

## Preserving backend blocker diagnostics

Known blocker codes now show a CS/EN next action alongside the existing translated explanation. Their original, unmodified server detail is retained behind disclosure rather than silently replaced; unknown blockers continue to display their exact server text. This is explanatory UI only. It never recalculates server readiness, bypasses can_confirm_configuration, or enables sporting execution.

## Nested API-contract hardening (follow-up)

On the HTTP read boundary, reject non-boolean ranking binding/readiness flags, unknown current-window values, a blank Saved HEAD identity and any existing `before` timing whose Run clock disagrees with the proposed timing. These fields are backend-owned; the UI must not reinterpret them or silently fabricate a fallback. Five malformed mocked responses are asserted to fail closed before rendering.

## Confirm receipt type hardening

Client rejects a Confirm receipt if the returned Working Draft version is not a positive safe integer, `already_applied` is not boolean, the optional ranking authority fingerprint is malformed, or the returned state is absent/not an object/foreign Branch. These checks are independent of the immutable command and preview fingerprint checks and cannot infer Save success. Five mocked HTTP regressions cover malformed receipt metadata.

## Post-Save stale-form lock

Once a Saved Revision receipt is accepted, keep the Entry form, new Preview and in-place re-read locked for that mounted editor, even if query cache still holds the pre-save state. The Run Management link remains available; entering a new context starts another verified editing session. The mocked Save test asserts the lock and absence of another preview call. Successful Save still cannot be undone by a cache refresh failure.

## Uncertain Save: no blind second write

The Working Draft Save route does not accept this UI's immutable Entry command ID. Once the Save POST has been attempted, a timeout, lost reply, or malformed success receipt might mean an actual immutable Saved Revision already exists. The panel now conservatively locks a repeated Save, keeps the existing Run Management/history link visible, does **not** claim a successful revision, and prompts inspection of Saved HEAD/history before a new editing session. A failure during preflight *before* POST remains an ordinary recoverable error. Mocked React regressions cover the lost reply, malformed receipt, CS/EN switch and preflight failure. Real HTTP/SQLite uncertainty must still be accepted independently.

## Published ranking picker input integrity

The shared HTTP client now validates every published ranking option before exposing it to the Entry override picker: exact Run/Branch/Edition identity and source, nonnegative safe count matching a real array, strictly valid publication week, SHA-256 fingerprint, nonnegative ranked count, positive Best N, nonempty policy ID, and no duplicate season/week key. Invalid/missing nested rows fail the read closed rather than producing a malformed or ambiguous select. The client mock suite covers valid response and nine corrupt response cases. No publication is automatically adopted by selecting it.

## Explicit re-read rehydration (31 October continuation)

A user-triggered successful inspection GET now replaces the local timing form with the newly fetched server plan (including new/removed plan and main/Q lengths), preserving manually written operator and audit reason. It invalidates an ordinary preview but never submits Confirm/Save. A stale scope, failed GET or foreign response cannot rehydrate. Re-read is disabled while the exact Confirm retry, confirmed Draft, uncertain Save, or Saved receipt is active, so those write decisions cannot be silently displaced. Mocked component regressions cover fresh server rehydration, audit retention, no automatic writes and retry preservation.

## Avoid stale preflight interpretation while locally editing

If timing inputs differ from the last inspected plan and there is no matching server Preview, prior GET blockers remain visible for provenance but are explicitly labelled as referring to the **previous** plan; the existing can-confirm status is suppressed until a fresh server Preview is accepted. This prevents stale readiness from being misread as permission for the locally edited timing. CS/EN mocked regression checks initial edits, preview restoration and subsequent invalidation.

## Pending GET read fence

While a manual or automatically triggered inspection GET is in flight, the Entry timing and audit form stays disabled, and updates are rejected at their event handler too. This prevents a delayed server GET from overwriting edits made after refresh started. On success the form uses the freshly inspected timing; on failure the existing fail-closed read path applies. A deferred-GET mocked regression covers disabled controls, attempted edits, empty server response and retained audit. No write is initiated.

## Canonical Run context identity

The frontend editing scope uses the actual Run calendar values in a fixed order rather than raw JSON object serialization. A caller that reorders an otherwise identical persisted clock object must not wipe a valid preview or operator/audit text. Changing any real clock field still creates a different editor scope and invalidates reviewed state. A mocked React rerender regression covers reordered metadata without a Confirm or Save write.

## Direct Saved Revision history navigation

The existing `/admin/runs/:runId/branches` route renders `SavedRevisionHistoryPanel` and allows an operator to select the intended Branch. After confirmed Draft and Saved/uncertain Save, the Entry UI now offers a direct CS/EN link to that real history page in addition to its original Run Management link. It does **not** fake support for direct per-revision navigation or assume that the first Branch is the requested one; the operator selects the Branch in history. Mocked component regressions verify the exact route after Confirm, successful Save and ambiguous Save.

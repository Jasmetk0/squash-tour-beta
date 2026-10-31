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

Mocked tests in web/src/components/RunEditionEntryTimingPanel.test.tsx verify empty/existing review, CS/EN persistence, preview invalidation, blockers, future missing ranking, exact confirm/retry, Save safeguards and delayed/foreign contexts. web/src/api/runEditionEntryTiming.test.ts verifies the exact encoded HTTP request/response boundary; web/src/pages/PlannedEventDetailPage.test.tsx exercises verified Admin wiring. These mocked suites remain separate from the actual Chromium/API/SQLite evidence below. #1675 separately has backend HTTP/SQLite tests. The final head needs TypeScript/Vite and relevant hosted checks; skipped Draft acceptance is not a pass.

Known limitation: historical Run records without explicit v1 Run calendar metadata intentionally fail closed. The existing general planned-event page still has separate legacy-only projection assumptions. Automatic sporting Entry validation remains outside this slice. Actual browser acceptance below covers future-plan configuration, not automatic eligibility or sporting execution.
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
| 29 | Improved | Exact select accessible names and scoped wrapping; actual CS/EN Chromium review at 390px without panel overflow. Full accessibility certification is not claimed |
| 30 | Improved | Focused mocked component/API suites plus actual Chromium/API/SQLite Confirm/retry/Save/restart. Final-head hosted acceptance must pass; full release remains separate |

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

## Immutable Confirm recovery after parent becomes non-writable

A lost Confirm response may mean the server already staged the local Calendar edit, making the parent page mark the current Working Draft read-only for *new* Entry modifications. The original exact command retry must still be allowed so the backend idempotent receipt can be recovered without creating a different command or forcing another preview. The UI separates a fresh Confirm (requires verified writable scope, current preview, audit inputs) from the frozen exact retry (requires the original timing, fingerprint, command ID, and audit to be unchanged in the same Run/Branch/Package/Edition/clock). No new Preview or Save is triggered. A mocked React rerender regression simulates the parent flipping `enabled` to false between the first lost response and the exact retry.

## Background inspection refresh invalidates ordinary review

An ordinary server Preview is now attached to the React Query inspection's `dataUpdatedAt` version. If a subsequent background GET delivers a newer inspected state, the prior Preview no longer grants Confirm, even when local text and timing have not changed; a new server Preview is needed. A GET that races an in-flight Preview also prevents that older response from being accepted after the read version changes. The immutable already-attempted Confirm retry is a separate recovery path and does **not** depend on this fresh-read check. Mocked background-refetch regression asserts the prior Confirm action disappears without creating another write.

## Saved Revision receipt identity must be a real string

The successful Save UI now requires a nonblank string revision ID and a matching clean Working Draft base in the server response; null/missing or non-string identity must not be rendered as a definitive Saved success. Such a response remains an ambiguous post-write result and the second Save stays locked. A mocked HTTP-boundary component regression rejects numeric revision IDs rather than coercing them into apparently valid saved history.

## Display authenticated Entry phase and correct season labels

The read-only review now displays the backend's `current_window` directly, with distinct CS/EN labels for not opened, Main, Qualification and all closed. A null server window is shown explicitly as **unknown**, not as a fictitious active or closed phase. The reviewed date labels use the actual Run clock's season-start offset: for a cross-year 2030/2031 season they show `2030/2031 · S0 W13`, not the incomplete `2030 / S0 W13`. Server-resolved weeks still are never recomputed as sporting rules. Added mocked React checks for known/null phases, locale switch, and cross-year labels.

## Fail closed on foreign Run clock and stale readiness panels

An otherwise internally valid, in-scope server inspection that embeds a different Run calendar from the verified parent must not populate an editable Entry form. The component now rejects it, shows a dedicated bilingual mismatch warning, and disables Preview/Confirm. It still permits explicit re-read for recovery. When the operator changes any timing field without a fresh matching Preview, it also suppresses the previous plan's before/after windows, ready-to-bind message and Working Draft readiness claims, retaining only accurately labelled previous-plan blockers. Mocked React regressions cover a genuinely different W52/W80 clock and the stale-ready display after a local edit. This changes no backend contract or sporting computation.

## Monotonic read-epoch proof for server Preview

React Query's `dataUpdatedAt` is a millisecond timestamp, not a unique read revision. Two very fast inspections can resolve in the same millisecond and mistakenly leave an old Preview eligible for a new Confirm. The form now increments an explicit local GET epoch at the start of each authoritative inspection request; a Preview is accepted and usable only against that exact epoch. A mocked React regression freezes `Date.now()` across multiple real query refetch calls and proves an older Preview cannot regain confirm authority. The immutable original Confirm retry remains independent of new GET epochs.

## Explicit GET recovery rejects different Run clock before rehydrating

Manual re-read now checks the inspected plan's embedded Run clock before replacing any local timing fields. A self-consistent W52 server record cannot overwrite the operator's W80 edit merely because the Run/Branch/Package/Edition IDs match. The clock mismatch warning remains visible and Preview/Confirm are blocked until a truly matching inspection is obtained. A mocked component regression preserves the local Main opening after a foreign-clock GET response.

## Independent integration review — 31 October 2026

The real browser exposed defects that isolated component mocks did not cover:

- A nested select inside its label included every option in its accessible name.
  Season and publication pickers now have separate explicitly associated labels.
- The generic multi-column `.grid` overflowed at a 390px viewport. A dedicated
  `RunEditionEntryTimingPanel.css` scopes sequential layout, shrinking controls
  and wrapping to this panel; no shared styles are changed.
- After actual Save, Branch HEAD and Draft requests finish independently. Their
  temporary mismatch previously unmounted the editor and erased the definitive
  Saved receipt. Mount identity now follows the verified Run/Branch/Edition; the
  existing complete HEAD/Draft checks still disable every new mutation. The
  receipt remains visible until navigation to a fresh editing context.

`scripts/edition_entry_timing_browser.py` creates an isolated Calendar through
real Package HTTP commands and starts a separate production backend process. It
uses Chromium on the normal Admin route, without fabricated API responses. It
proves missing plan -> explicit Main 13/Q defaults -> read-only server Preview,
CS/EN switch retaining review/audit, 390px layout, and no implicit writes. It
forwards the real Confirm to the server and drops only its network reply, then
requires the identical original command/payload to recover the committed receipt.
A separately consented Save produces a new immutable revision containing the exact
plan. Parent cache refreshes retain the successful receipt. A fresh backend
process physically reopens SQLite; the complete Saved payload and Entry timing
remain identical and a page reload performs no writes.

Reproduce with a fresh directory:

```sh
python scripts/edition_entry_timing_browser.py --root work/entry-timing-browser
```

The dedicated `Edition Entry Timing` Ready/manual workflow runs this exact proof.
Existing relevant acceptance workflows remain unchanged. Initial development
attempts exposed an incorrect test origin (CORS), accessible-name and mobile
failures, then the real post-Save receipt loss; these are not counted as passes.
No browser claim is made for ranking adoption, automatic eligibility, full
sporting continuation, all calendars or the 50-season release.

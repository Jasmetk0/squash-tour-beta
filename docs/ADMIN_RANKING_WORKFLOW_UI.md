# Admin Ranking Workflow — local CS/EN presentation

## Authority and isolated scope

This PR starts at `buuk` `3f9af67435f68aa6322ee05e6efda3e62850249c`, independently of candidate read-only history PR #1644. The only production edits are `RankingPreparationPanel.tsx`, `RankingResultCorrections.tsx`, `RankingSavePanel.tsx` and the local, display-only `rankingWorkflowText.ts`. Existing component tests are adapted to mount `LanguageProvider` and focused `RankingWorkflow.csen.test.tsx` adds contract coverage.

Existing `LanguageContext` selects English/Czech. Changing the language changes only visible copy: the form and its key stay mounted, so its controlled values, stable tie-break tokens, zero changes, corrections, audit fields, reviewed checkbox, preview object and exact saved command ID remain unchanged. Query keys and requests do **not** contain the language; switching languages does not refetch or execute a mutation. Display labels for `completed` / `abandoned` and ranked/unranked decisions are translated but HTML `option.value`, TypeScript request enums and API payloads stay exactly as before. Unknown server error text and user/audit/source identifiers remain unmodified. Numeric 0, null and missing fields are not coalesced by this display layer.

## Covered user-facing workflow

| # | Panel | CS/EN content / contract |
|---|---|---|
| 1 | Preparation | Initial/next preparation headings and explicit buttons |
| 2 | Preparation | Legacy target week and season boundary; original 50 × 61 calendar untouched |
| 3 | Preparation + Save | Candidate is unpublished; separate recoverable Saved Revision and Official Ranking are not conflated |
| 4 | Preparation | Policy reference and Best N |
| 5 | Preparation | Roster count and empty-roster message |
| 6 | Preparation | Player ID and immutable token field text |
| 7 | Preparation | Tour entry season/week and retirement checkbox |
| 8 | Preparation | Add/remove player labels with unique numbered remove buttons |
| 9 | Preparation | Disciplinary zero section and context of decisions |
| 10 | Preparation | Player selector, duration, source reference of new zero |
| 11 | Preparation | Review duration changes and visible unchanged original start |
| 12 | Preparation | Operator label, reason and audit instructions |
| 13 | Preparation | Required reviewed-checkbox text and explicit Calculate preview |
| 14 | Preparation | Previous inputs loading, errors and explicit retry |
| 15 | Preparation | Preview summary, counts, ranking table, empty result |
| 16 | Preparation | Confirm, edit/recalculate and same-command retry |
| 17 | Corrections | Explicit source loading, empty/error states, manual retry |
| 18 | Corrections | Corrected qualification/main points, ranked flag, terminal status, provenance and original publication/validity |
| 19 | Save | Explicit review entry, loading, unchanged/ready/blocked states, API error and refresh |
| 20 | Save | Explicit Save button, pending status, success and error recovery guidance |

## Failure messages and recovery (CS/EN)

All ranking workflow error surfaces now add a locally translated, static description
of the failed **operation**: loading prior preparation inputs, computing the preview,
confirming the prepared candidate, loading stored result sources, reviewing Save,
and performing an explicit Save. The existing `formatApiError` diagnostic remains
visible unchanged and is never rewritten or treated as a translated request value.
Changing CS/EN neither refetches failed reads nor retries a failed mutation.

The original buttons and gates remain: previous-input/source read retries require
an explicit click, confirm retries the **same** frozen command and preview,
and a failed Save refetches its review under the existing error callback. A
further write still requires explicit Save. Tests assert the raw diagnostic,
localized static context and zero implicit writes across language switches.

## Preserved behavior and gates

- **Never automatic:** preparing, confirming and saving remain explicit independent commands. A preparation candidate is not a saved revision or a publication. Neither browsing nor switching locale calls an API write.
- The preparation command builder, `crypto.randomUUID()` command/zero IDs, `previewRankingCommand`, `confirmRankingCommand`, `saveRankingPreparation`, preview/confirm mutation lifetimes, exact retry and frozen payload references are unchanged.
- The required reviewed checkbox, preview gating, Save `can_save` condition, error-triggered review refresh, initial/next weeks and season termination are unchanged. Corrections still use verified stored predecessor fingerprint and keep original validity timing. No API/schema/calendar/backend/Viewer/global i18n modifications.
- `RankingPreparationPanel.test.tsx` and `RankingSavePanel.test.tsx` retain their prior English checks under an explicit English LanguageProvider. The new CS/EN mocked-component tests cover draft form and audit retention, preview retention, exact retry after lost response, stored corrections and terminal `option.value`, future stored roster dates, explicit Save and source error retry without implicit write/read refresh.
- Mocked `useQuery` and mutation API calls do **not** prove real browser / HTTP / SQLite behavior. The final PR head still requires successful focused Vitest, TypeScript/Vite production build and all applicable Fast CI / CodeQL checks. Draft-only skipped acceptance is not an executed pass. The 50-season release gate is separate.

No commits from #1644 and no work to Viewer, backend, CalendarTourPanel, Full Simulation, Labs, Packages, shared styling/translations, dependencies, CI or Master are included.

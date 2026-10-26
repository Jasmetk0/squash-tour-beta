# Admin Ranking Candidates — CS/EN read-only history

## Scope and authority

This vertical slice only changes the two historical candidate display components,
their focused tests, and the page-local copy/identity utility. It does **not**
change ranking calculations, calendar limits, API request contracts, persistence,
the ranking Preparation/Save controls, publication or simulation.

An **unpublished candidate** (publication_status = candidate_only) is never
represented as a published Official Ranking. Opening the page, switching language,
expanding details, and manually refreshing candidates / sources / frozen inputs
are **read-only**. Existing separate preparation and save controls are unchanged
and still require explicit user action; Viewer selection is untouched.

## Localized display

LanguageContext controls the English and Czech copy for titles, table headings,
status indicators, input-history explanation, tie-break reasons, disciplinary zero
decision provenance and source results. The helper is intentionally local to
these pages; shared translations and styles are not edited. Persisted IDs,
fingerprints, source values, policy references, operator labels and audit reasons
remain byte-for-byte untranslated. The legacy 61-week candidate week format
remains unchanged; only the visible word "Week" changes to "Týden".

Numeric **0** is rendered as zero; explicit **null** is rendered as "None"/
"Žádná hodnota", and an absent tie value as "Missing"/"Chybí". A zero
result_slot is printed rather than suppressed.

## Reading and recovery

- Candidate history remains scoped by Run + Branch, with optional selected season/week
  in the URL. Manual refresh does not navigate.
- The response and nested candidate Run/Branch, candidate_only publication
  status and usable fingerprints are checked before rendering.
- Input and source responses are separately matched against the selected Run,
  Branch, exact season/week, candidate fingerprint and candidate_only
  publication status. Source version and disciplinary input owner identities
  are also checked. An untrusted response is an error, not verified evidence.
- complete_manifest requires stored roster/results; a
  legacy_without_manifest response must have manifest: null. Legacy,
  empty-but-verified, loading, error and non-empty verified states remain separate.
- Queries are keyed by the full applicable identity. Delayed results from a
  previous Branch, week or fingerprint cannot appear under the newly selected
  context. Old content is hidden during refresh and after a failed refresh.
- Every loaded read section has an explicit Refresh control and a recovery Retry
  action after errors. Refreshes preserve selected URL week and mounted native
  details while within the same candidate identity. A different candidate
  fingerprint remounts detail sections and invalidates their old identity.
- Source selection and opening frozen inputs are still opt-in. They only make
  GET/read calls; no client preparation, persistence or publication API is
  invoked by opening a section.

## Focused verification

The component tests cover legacy/no candidate, exact week selection, CS/EN,
source and input lazy loading, provenance, historic ties and disciplinary zeros,
foreign identities, delayed previous-Branch delivery, zero/null display,
manual refresh and error recovery, and absence of automatic preparation / save
calls. Mocked API responses establish **component contracts only**, not real
production HTTP/SQLite/browser acceptance.

Before the owner merges, verify the **final commit** with frontend Vitest,
TypeScript/Vite build and every relevant hosted gate that actually executes.
A skipped Draft-only browser gate or pending check is **not** a green acceptance.
No changes to the existing browser scripts, CI, shared i18n or API client are
made here. Full pre-alpha release certification is outside this change.

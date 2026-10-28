# Admin Diagnostics CS/EN

## Scope

- Localized `AdminDiagnosticsPage` to Czech/English using existing `LanguageContext`.
- Kept page role as launcher/triage (not consolidated scan), preserving the split between linked tools and planned areas.
- Preserved filter values and counts (`All / Linked tools / Planned`, `6 / 3 / 3`).
- Preserved existing routes and safe `encodeURIComponent` handling for remembered Run IDs.
- Continued hiding last-run links when remembered Run ID is missing or whitespace-only.
- Kept raw remembered Run ID content unchanged in link labels.

## Tests added/updated

- Wrapped page tests in `LanguageProvider`.
- Added CS rendering assertions for headings/status/filter label.
- Added EN switch assertions and filter persistence after language change.
- Added link assertions for encoded complex remembered Run ID in both shortcuts.
- Kept absence checks for missing and whitespace-only remembered Run IDs.

# World Package cloning: CS/EN result handoff

Scope: frontend presentation of the existing built-in World Package clone flow. This change deliberately does **not** touch cloning commands, payloads, API schemas, server implementation, stored defaults, global language infrastructure or simulation.

## UI behavior

- `CloneResultCard` reads the existing `LanguageContext` and displays CS/EN labels, status explanations, file listings, package counts, validation headings and the created-package detail link.
- A dry-run result is always identified as **preview**, including its package/file headings. A write-success banner and navigation link require an `ok && !dry_run` response.
- Failure remains visibly distinct from a confirmed creation. Source/target IDs, paths, package fields, fingerprints, raw validation status and server error field/message values are never translated.
- The adjacent confirmation review's accessibility label follows the selected language. The stored default clone description remains the original stable English string.
- No mutation, form reset, review re-approval, or data fetch is driven by a language toggle; the existing source-fingerprint, late-response, explicit confirmation and unsaved-navigation safeguards remain unchanged.

## Focused verification

- `cd web && npm run test -- src/pages/WorldLibraryPage.test.tsx src/pages/WorldPackageValidation.test.tsx`
- `cd web && npm run build` (TypeScript project build + Vite production build)
- PR Fast CI also runs the existing frontend critical baseline and changed-file/colocated tests, followed by the production build.

Targeted clone tests cover CS/EN switching while reviewing, dry-run vs confirmed response, identical request content and default description, preservation of server diagnostics, and protection against changed source fingerprints. These are component-level mocked API checks, **not** real HTTP/SQLite or browser acceptance.

Final-head hosted checks must be inspected separately. Skipped Draft-only acceptance checks are not passes; full pre-alpha release validation remains separate.

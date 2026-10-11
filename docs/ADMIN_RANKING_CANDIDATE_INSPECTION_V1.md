# Admin ranking candidate inspection V1

The application now exposes two read-only routes:

- `GET /admin/runs/{run_id}/branches/{branch_id}/ranking-candidates`
- `GET /admin/runs/{run_id}/branches/{branch_id}/ranking-candidates/{season_index}/{week}`

Season index is 0–49 and week is 1–61. History is complete and oldest-first;
the detail route requests an exact stored week, with no current-week fallback.
Responses explicitly identify `publication_status: candidate_only`, include the
persisted snapshot (policy, rows, counted result provenance), its fingerprint and
associated command IDs. A bootstrap or older-path candidate can have no receipt.
No candidate is presented as a published Official Ranking.

The public repository read boundary uses a single explicit SQLite read transaction
for scope, candidate lineage and receipt validation. Both routes validate the
complete local history and all scoped receipts before returning any data. Missing
Run/Branch or week is 404; invalid numeric coordinates are 422; corrupt data or
unsupported fork ancestry is 409 with `ranking_history_unavailable`. An existing
scope without candidates returns an empty history. Read-only scopes are readable.

The routes use the existing application's Admin namespace/runtime; they do not
introduce an authentication system or change its deployment/access model. No
Viewer route or mutation endpoint is added. Reads never recalculate ranking,
inspect current award JSON, change Viewer selection, advance time or write data.

Receipt checks detect a missing/altered referenced candidate, including a deleted
tail when its receipt survives. They do not authenticate data or validate the
original request against its unavailable serialized input. Coordinated deletion
of candidates and receipts, source completeness, and shared fork ancestry remain
outside this local inspection contract. These are ranking preparation records,
not fully revision-integrated published history. UI presentation and full Week
Transition publication remain separate work.

Tests use the real registered FastAPI routes, runtime/repository and a file-backed
SQLite database with persisted candidates/receipts. They check nonzero points and
result detail, chronology and rollover, scope isolation, empty/missing/invalid
requests, absence of write/Viewer routes, read-only access, corrupt payload/receipt,
deleted tail and fork rejection. Complete SQL dumps before/after successful and
failed reads confirm non-mutation. No endpoint is mocked. The fixtures seed stored
records rather than simulate a full season.

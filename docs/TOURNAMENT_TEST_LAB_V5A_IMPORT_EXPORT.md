# Tournament Test Lab V5A — explicit session import/export

## Scope

This slice adds an explicit portable transport boundary for persisted Tournament Test Lab Sessions.

It deliberately does **not** implement Run → Lab historical Tournament copy or Lab → Run draft/application behavior. Those remain separate reviewed boundaries.

## Export contract

`GET /admin/labs/tournament/sessions/{session_id}/export` returns `tournament_test_lab_session_export.v1`.

The envelope freezes:

- the complete isolated Test Session payload,
- the exact Session fingerprint,
- the exact Scenario fingerprint,
- an export-envelope fingerprint over all reviewed transport data.

Export is read-only. It does not mutate the Test Session, Product Run, Branch or Saved Revision state.

## Import contract

`POST /admin/labs/tournament/sessions/import` requires:

- the complete validated export envelope,
- the exact reviewed export fingerprint,
- an optional new display name.

Import always creates a **new** isolated Tournament Lab Session with a new generated Session identity and version 1. The source Session remains unchanged and is not live-linked.

The Scenario payload and its existing source provenance are preserved exactly. Import does not reinterpret a built-in or future Run-snapshot source as a new authority.

## Fail-closed integrity

Import fails before persistence when:

- the caller's reviewed export fingerprint is stale or wrong,
- the embedded Session fingerprint does not match the embedded Session,
- the embedded Scenario fingerprint does not match the Scenario,
- the export-envelope fingerprint does not match the complete envelope.

Existing persisted Session integrity checks remain unchanged.

## Tests

PR-critical service/API coverage proves:

- export fingerprints match the reviewed persisted Session,
- import creates a new identity and keeps the original Session unchanged,
- later edits to the imported copy do not mutate the source Session,
- stale reviewed export fingerprints are rejected without creating a copy.

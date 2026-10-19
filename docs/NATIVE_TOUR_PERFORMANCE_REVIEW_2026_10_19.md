# Native Tour performance review — 19 October 2026

Scope: #1542 over #1541, starting at 4ee5b826. Owner alone merges.

## Reproduced defects

- Final-head W80/1000 browser job 117808901826 failed the first cold
  calendar-tour response at 120 seconds. API acceptance passed but consumed
  more than 20 minutes. Fast CI was already short; it was not the bottleneck.
- Four concurrent real service inspections of a valid copied W80/1000 Saved
  database with 14 revisions caused 45 full revision validations. The baseline
  took 168.43s. A bounded single-flight reduced this to exactly 14 checks;
  the first diagnostic took 68.81s with identical checkpoint/Tour fingerprints.
  These two diagnostic runs overlapped partly; do not treat them as an isolated
  benchmark or general latency SLA. Final-head CI remains the acceptance gate.
- Live and Saved checkpoint JSON were semantically identical but disagreed
  in insertion order of sets_won keys. The former byte-string fast path fell
  back to repeated full parsing. Canonical hashing of the actual decoded live
  content preserves its exact fingerprint while accepting harmless key order.

A chronological-walk experiment did not provide the required improvement and
was discarded. No changes to lineage ordering or historical schema remain.

- A third HTTP regression reproduced full verification happening again in
  the Save response immediately after commit, although the exact captured
  source had just passed full verification. Publish its existing metadata-only
  exact-byte proof only after successful transaction exit. Explicitly validate
  all remaining ranking/package components, scope and signed content before
  earning that proof. Future reads still rehash actual SQL bytes and owners.
  Controlled commit failure publishes nothing; tampering after success fails.

## Repair and invariants

Single-flight locks are bounded and protect the existing exact-byte validation
cache, which retains metadata only. Every caller hashes its actual stored bytes;
only complete successful validation can populate a proof. Failure is never cached.
Independent response payloads and live owner validation remain mandatory.
No new persistent trust cache, timeout increase, reduced population, fake match
result or skipped integrity validation is introduced.

Browser acceptance now prints operation durations and preserves failure details,
blocked backend thread stacks and the disposable SQLite files in CI artifacts.
The full W52/W61/W80 matrix and real HTTP/SQLite acceptance remain mandatory.

## Validation

58 focused backend tests passed: concurrent cold proof sharing and failure,
post-proof corruption, reordered mapping content and live tampering, existing
component proof scope, Save lineage, history, restore/fork and historical hashes.
An additional real HTTP/SQLite regression covers the native Save fold count,
commit failure, successful retry and changed stored bytes after publication.
The concurrency failure was separately reproduced against the unmodified source
outside pytest's automatic src-path override.

Required workflow checks on the final repair head must finish before handoff.
Full pre-alpha release gates and unsupported sporting mechanics are unchanged.

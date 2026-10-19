# Native Tour performance review — 19 October 2026

Scope: #1542 includes #1541 and targets buuk, starting at 4ee5b826. Owner alone merges.

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

- Unsaved live Tour inspections also rebuilt their entire old sporting history
  instead of anchoring it to the just-authenticated previous Saved source.
  Apply the existing guarded prefix verifier here too: validate every new event,
  compare the complete successor and fall back to full replay on divergence.
  Real HTTP regression reproduces the missing prefix, verifies a subsequent
  weekly transition and rejects a rehashed forged live successor.

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

58 focused backend tests and 15 original Tour integration regressions passed: concurrent cold proof sharing and failure,
post-proof corruption, reordered mapping content and live tampering, existing
component proof scope, Save lineage, history, restore/fork and historical hashes.
An additional real HTTP/SQLite regression covers the native Save fold count,
commit failure, successful retry and changed stored bytes after publication.
The concurrency failure was separately reproduced against the unmodified source
outside pytest's automatic src-path override.

Required workflow checks on the final repair head must finish before handoff.
Full pre-alpha release gates and unsupported sporting mechanics are unchanged.

## Follow-up from the complete consolidated check set

Head `fd8dbb41` passed 12 of 14 workflows. The real Native Tour API acceptance
passed in about 14 minutes; the reviewed original run took 22+ minutes.
W52/W61 passed; W80 reached Week 6 after both actual Editions and restart, but
the unchanged 18-minute process bound expired during final evidence reads.
Do not treat that failed large browser gate as green.

Further bounded optimizations:

- Checkpoint event union dispatch now selects the one disjoint required shape
  before validation. Every event model still validates its fields, schema,
  rally logs and hashes. Historical omitted default version tags still work.
  A copied real W6/1000 checkpoint preserved its exact fingerprint; ordinary
  union parsing took roughly 2.5–3s versus 1.4–1.9s with direct dispatch in
  local diagnostics. This is not a general latency SLA.
- Already authenticated played roots may be reused only after hashing the
  actual decoded live row and checking every physical identity/hash column.
  Changed content/metadata falls back to strict parsing. Reordered map keys
  remain harmless. No parsed payload cache survives the current request.
- Reuse locally computed checkpoint hashes inside the decoder and the single
  inspection response. A profiled repeated inspection of the same earlier
  copied W5/1000 state fell from 7.8s to 6.5s, with identical source hashes.

The other failure was the existing Server Tasks browser. Trace showed its pause
fetch unresolved, while backend logs showed `database is locked` in the control
writer and heartbeat. The harness released its genuine next-child gate directly
after clicking, before waiting for the pause commit. Await the actual HTTP 200
`pause_requested` ACK before release, preserving the real pause, continuation,
page-close and SIGKILL assertions. No production control or lease fence is weakened.
Final-head browser verification remains mandatory after this harness repair.

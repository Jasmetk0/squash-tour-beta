# Native sporting inspection: bounded read-cost reduction

Base: owner-merged #1547, `buuk`
`93a3f946e86af8265b8e7539d6c6ffcd174f3282`. This is a read-only
performance change; no new sporting capability or Master decision.
It is independent of the records and CI-selection PRs #1548/#1549.

## Removed work

Opening knockout inspection, canonical-input preview and checkpoint-player
inspection now consume the live/Saved sources returned by their existing
`_context(..., _include_sporting_sources=True)` inside the same explicit SQLite
read transaction. Previously inspection loaded the live match and checkpoint
again and performed another full Saved match fold after the context had already
authenticated them. The context and all of its actual-byte, hash, owner, Saved
lineage, live/Saved-root and unsaved-suffix checks remain unchanged.

Opening output reuses its already computed fingerprints. Continuation output
hashes each distinct authenticated object once per read and builds temporary
fingerprint membership sets instead of nested `any(...)` loops. Match membership
keeps its original ledger-position comparison. Closure labels retain tournament
IDs, while Saved flags still compare full fingerprints, not merely IDs.
Neither decoded objects nor hash/proof entries survive a request.

Commands, MatchEngine calls, RNG, schemas, Saved bytes, manual Save, chronology,
Viewer boundaries and restore validators are unchanged.

## Evidence

On one genuine Saved SQLite population (8 players, W80/O80), alternating old and
new read methods behind the real HTTP router produced exactly equal complete
opening and continuation responses. The warm opening read measured 3.897 seconds
before and 1.732 seconds after locally. Continuation on this short, no-followup
fixture measured 0.999 vs 0.980 seconds; this is too small to claim a meaningful
end-to-end gain. No hosted SLA or full-Tour test speedup is inferred from these
local measurements.

Loader instrumentation on the genuine opening read changed live match/checkpoint
reads from 2/2 to 1/1 and eliminated the extra Saved match read. In a separate
synthetic presentation-only history with 80 entries in each category, digest
calls fell from 19,925 to 642 with identical output. These synthetic objects are
not signed sporting authority and are not integration evidence.

35 focused tests passed locally in 78.84 seconds:

- Real HTTP/SQLite W52 and W80: empty/canonical preview, unsaved/signed opening,
  one-read source use, checkpoint-player inspection, stale proof rejection,
  unchanged database on GET, tampered live bytes with both old and recomputed
  hashes, rejection without repair, and exact recovery after restoring bytes.
- Read-model contract tests: empty, unsaved, Signed and separately prepared
  points, mismatched roots, context rejection without fallback, distinct/shared
  object digests, new digest derivation on a later request, 1/20/80-entry histories,
  unchanged match-order semantics and non-Saved flags despite matching IDs.
  Context mocks in these tests are explicitly not integration evidence.
- Existing exact component/owner/live-byte/restore proof-scope regressions.

The digest-cost regression was reproduced against the original read method
before verifying the optimized path. Matched HTTP responses also verify the
original output contract independently of those counters.

The existing matched W52/W80 eight-match HTTP/SQLite profile, native Tour API,
native Chromium matrix and relevant Fast CI remain the final-head gates.
The profile now cancels superseded PR runs, retaining its fixture, matrix and
20-minute deadline. Hosted checks are pending until recorded in the PR; this
document is not a pre-alpha release or a claim that all long CI is solved.

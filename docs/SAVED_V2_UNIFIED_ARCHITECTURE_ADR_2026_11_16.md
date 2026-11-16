# ADR candidate: One authenticated Saved v2 Merkle store for long native Runs

**Status:** FOR WORK DESIGN DECISION — proposal, not approved, not implemented.  
**Date:** 16 November 2026.  
**Base:** `buuk`; authoring only this file. Existing `run_saved_revision.v1` and all production DB bytes remain untouched.

## 1. Decision Work needs to make

**Recommend ONE generic Run-scoped content-addressed Merkle DAG for any future
`run_saved_revision.v2` Saved payload**, building on Claude's #1805 and its
original #1803 proposal. The sporting `events` ledger, Native Fork streams,
`player_lifecycle.states`, Health, Tour receipts/rankings, player arrays and
rally evidence should all be expressed as typed, verifiably reconstructed
subtrees **within that one DAG**, not as three competing authoritative formats.

- **#1803** remains the independent v1 cold-read optimization. Existing
  A–B–B–A [#1817](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/43931906798)
  measured 98.652 s old vs 54.949 s on the same actual W12/256 Saved source
  (**−44.30% cold inspection median**), identical canonical response and
  lower peak RSS. This is *not* a full-season speedup; requires Work approval
  of its correctness and broader regression coverage.
- **#1805** is the strongest generic v2 storage specification and physical-node
  prototype. Do not replace it with #1821 or #1811 as a second production format.
- **#1811** demonstrates append-only Merkle deltas for *different*
  Native Fork source arrays; use it as an adversarial append experiment, not a
  separate authoritative Native Fork database format.
- **#1821** demonstrates original-calendar-Tour `GlobalCompetitionCheckpoint.events`
  corruption checks, exactly reconstructed real sporting histories and
  Run/Branch binding; use its tests and failure gates, but do not ship its
  separate `experimental_sporting_event_*` tables as production v2.
- **#1818, #1816, #1822** are diagnostic only; **#1819** is a narrow optional
  v1 writer serialization optimization, not a v2 storage or disk-size fix.

**Work must explicitly approve the following contract before any live v2
writer/reader PR is merged.** This ADR is a proposed decision for that review,
not a unilateral approval.

## 2. Quantified problem; keep workload and evidence honest

| Source/workload | Genuine observation | What it does NOT prove |
| --- | --- | --- |
| #1820, real HTTP/SQLite, 1,000 initial players | W2 52.89 s; W3 69.77 s; W4 352.56 s; W5 586.25 s; W6 1,133.34 s; at W6 ~1.085 GB SQLite and 3.56 GiB peak RSS (reported telemetry) | Not a finished five-season benchmark; W4–6 contain more tournament work and test-harness GETs, so cannot attribute all growth to Saved history |
| #1816, genuine 256-player/8 played Edition/24 real match, 46-Saved W12 | cProfiled cold GET 114.35 s; SQL cursor-execute 1.20 s; JSON/Pydantic and lineage replay dominate | Does not measure full actual SQL fetch, player sport, later-season complexity, or uninstrumented execution |
| #1817 matched W12 A–B–B–A | #1803 cold GET median 54.949 s vs original 98.652 s; same complete response SHA-256 | Not a claim that whole simulated week or season is 44.3% faster |
| #1818 physical W12 v1 Saved | 46 revision payloads: 742,677,941 B; `calendar_player_sporting_checkpoint` 586,070,200 B; `events` 566,039,006 B over 39 snapshots | Nested canonical component byte sums are not disjoint SQLite file savings |
| #1818 exact historical event reconstruction | 15 true unique event JSON objects 39,026,296 B; 39/39 arrays exact; all 38 observed adjacent lists preserve prefix; 93.103% *event-array text* hypothetical reduction | Append-only is proven only in this source. No production conversion, fork/restore, or whole database gain yet |
| #1818 finer nested player values | 12,288 player record occurrences / 22,457,260 B vs 3,955 unique / 7,225,081 B; 67.827% repeated player-object bytes | This duplication is **inside** the unique event bytes, not additive to 93.103% event-array result |
| #1805 generic Merkle threshold trial on those 15 original events | 4KB nodes 29,215,309 B / 2,141 nodes; 1KB nodes 24,914,276 B / 11,712; 512B nodes 22,110,151 B / 24,365; all 15 rebuild exactly | In-memory prototype only; no SQLite rows/indices, semantic replay, real Save performance |

**Consequence:** performance work must reduce both the *quadratic bytes* stored
across complete snapshots and the *quadratic verification/decoding* on cold
reads. Merely compressing SQLite or replacing the hash with a cached declared
value cannot solve the correctness/performance combination.

## 3. Proposed physical format and authority chain

### One versioned Saved envelope

- Existing `branch_saved_revisions` **v1 remains immutable**, including
  `payload_json`, canonical original `content_hash`, parent, status,
  sequence, Run/Branch owner and all recorded audit/source/replay semantics.
  Never rehash or auto-migrate prior rows.
- **Opt-in v2 only for explicitly configured new Runs**, version recorded in
  immutable Run creation metadata. A physical v2 Saved row contains a small
  explicitly versioned canonical envelope with the existing identity fields
  and one authenticated `content_root` pointer. Freeze the exact hash
  envelope/key ordering and schema version in a compatibility fixture **before
  writing** a production insert.
- `content_hash_v2 = SHA256(canonical_envelope_with_run_branch_parent_sequence_kind_content_root_change_summary)`.
  The canonical envelope commits to the Merkle root, whose full descendant
  graph commits to the original materialized JSON content. Hashing just a
  self-described root with no verified Saved envelope is **not** authority.
- One insert-only Run-scoped node table, conceptually
  `saved_revision_nodes(run_id TEXT, digest CHAR(64), body_json TEXT,
  PRIMARY KEY(run_id,digest))`. Every digest is SHA-256 of the **actual
  canonical stored body**, including explicit children refs, schema/version
  and payload. No cross-Run node sharing. Branch ownership and allowed
  ancestor reachability are checked against the source Saved revision lineage,
  even if a shared Run-scoped node's hash is identical.
- Explicit references (as #1805's `{"mj":1,"r":[...],"v":...}`) preserve
  arbitrary JSON literals that otherwise resemble a reference. Validate
  reference path type, null placeholder, canonical serialization, list index
  bounds, duplicated paths, cycles, depth and total materialization size.

### Physical verification before semantic reuse

A reader opens **one consistent SQLite snapshot**, authenticates the current
physical Saved envelope and **every reachable** v1/v2 parent/owner/source edge,
rehashes the actual reachable node bytes in that snapshot, then checks all
expected fingerprints and source provenance using the existing independent
domain replay rules. A declared digest or stored manifest self-hash never
authorizes bytes.

- Memoize a decoded node or a *semantic result* only after the actual
  physical DAG has passed verification in that snapshot. Reuse by
  `(run_id,digest,verified_source_context)`, not merely by textual event
  equivalence, when the value has branch/season/source-dependent meaning.
  Per-revision owner, saved-head ancestry, sequence, source references, audit,
  closure and terminal sporting checks must still run for every revision.
- **No persistent "verified" flag**: physically tampering any node or ancestor
  after a prior successful warm read must make the next read fail closed.
- A read of 100 Saved revisions should verify unique physical nodes once in
  its current consistent snapshot, not decode/replay identical immutable
  sporting sources 100 times. Determine what may be reused using explicit
  verified domain equivalence, not a blanket skip of MatchEngine or source
  validation.
- Exports and API projections materialize **exactly the same original canonical
  values**, player records, ranking points, real match/rally evidence and
  chronological history as the corresponding v1 source.

## 4. Incremental writer without O(full-history) work

A v2 writer must not merely call #1805's full-snapshot encoder on a
multi-gigabyte `payload` after each week. It must operate from the fully
verified previous Saved head and the resulting authorised command change:

1. Within `BEGIN IMMEDIATE`, authenticate the physical Run/Branch current head,
   expected head and all dependencies; reject stale concurrent head with 409.
2. Apply the actual approved Tournament/MatchEngine/WeekTransition command,
   without changing the current deterministic sporting algorithm.
3. Derive **verified changed subtrees** from the authorised state transition
   (or from an independently checked exact old/new structure comparison for
   an initial conservative implementation); never trust client-supplied
   `delta = [...]` or a claimed append length without checking old bytes.
4. Reuse unchanged already-verified child node digests. Hash/serialize and
   insert *only* new/changed subtree nodes, constructing a copy-on-write path
   to the new root. For truly append-only arrays, add new authenticated
   chunk(s) and new small root/manifest; unchanged prefix nodes stay physical
   once. If a valid reset, edit, fork, historical correction or restore
   changes a prefix, use generic COW/fallback to a fully verified new
   snapshot, **not rejection of legitimate sport or silent truncation**.
5. Insert physical new nodes and the v2 Saved row (including its committed
   DAG root, ancestry, audit) and update the branch head **in one transaction**.
   Any exception rolls back every insert/branch-head write. On duplicate digest,
   physically compare body bytes, not just declared digest. No readers may
   observe a future node whose Saved parent isn't yet committed.
6. After Save, independently authenticate the **actually stored** new row and
   reachable physical nodes. Preserve manual Save and idempotency rules.

The four full 256-player rosters in each genuine native-week event
(`completed`, `developed`, `recovered`, `target`) are part of the
sporting evidence. Do **not** delete them or replace them with an unauthenticated
player-state delta. Fine-grained child node reuse may share exact immutable
player objects while reconstructing all four full views. Later validated
incremental-player diff is optional and must prove full replay and
source-provenance equivalence.

## 5. Explicit thresholds, choices, and version gates

- **Do not silently change Claude's 4096 B default** on the prototype. Use
  an explicit benchmark-configurable threshold. 1024 B looks promising for
  source W12 sporting objects, but 11,712 nodes vs 2,141 at 4KB affects
  SQLite indexes, cursor fetches, RSS, WAL and writer latency. Compare
  4096/2048/1024/512 B on a *physical SQLite* node table under cold and
  warm reads, with independent integrity/semantic validation; retain
  original byte counts as ground truth. Work chooses versioned default
  only after end-to-end measurements.
- **Do not introduce parallel production stores** from #1811 or #1821. Their
  adversarial tests become gate fixtures for one canonical generic DAG.
- A v2 Save must still allow a mixed v1 ancestor/v2 descendant if Work
  approves an explicit migration path. Branch forks can share original
  Run-scoped verified physical nodes but must retain source Saved IDs,
  Branch ownership and reachable-ancestor checks. A cross-Run node reference
  must fail even if a digest matches.
- Do not change deterministic Saved revision IDs or original Run RNG
  as part of storage v2 without a separate provenance/regression decision.

## 6. Exact test order and release blockers

**Stage 0 — Work architectural signoff** (this ADR). Confirm unified
generic DAG, exact v2 envelope, node owner scope, version flag, read snapshot
and replay cache rules, generic COW fallback, threshold measurement plan.
Until then **no production writer**.

**Stage 1 — physical writer/reader behind default-off flag** on new Runs only.
Dedicated PR. Existing `run_saved_revision.v1` code path and stored SQLite
must have byte-identical behavior. Add a dual-mode fixture with deterministic
Saved identities and materialized value comparison. No giant CI required yet.

**Stage 2 — independent security and concurrency review**. Negative tests for
missing/corrupt/foreign-run/reordered/duplicate/truncated/cyclic node; changed
physical bytes *after* a successful warm request; forged but self-consistent
node+manifest; fake ancestry, source reachability and owner; rollback after
every insertion phase; concurrent Save same head; conflicting race 409; WAL
visibility. Include an explicit normal fallback for valid non-prefix history.

**Stage 3 — semantic equality**. Identical inputs for v1/v2 across Entry,
Draw, all real rounds of 4/8 and supported larger formats, MatchEngine
rally logs, ranking, lifecycle/health, signed cohorts, week/season
transitions, end-season archive, manual Save, branch fork, restore, mixed v1/v2,
cold restart, historical revision GET and cross-Run comparisons. Verify all
original complete DTO values/semantic hashes as applicable; never fabricate
matches or World Championships not executable in the tested Native Tour.

**Stage 4 — authenticated performance A–B–B–A**. Same machines/cases, independent
SQLite copies and source identities. Report wall/CPU by inspect,
preview, execute, MatchEngine, ranking/lifecycle/health, JSON/Pydantic,
physical query execute AND fetch, postwrite validation and manual Save;
current/peak RSS, WAL, SQLite and new physical node bytes, revision count,
actual matches and exact resulting sport. Execute W6/W12 first, then signed
W52, W61/W80 multiple seasons; compare native Calendar Tour separately from
Native Fork v2. Monitor growth *slope* per week, not only one final number.
The benchmark-harness extra GET and idempotency POST work isolated by
diagnostic #1822 must be reported separately, not mislabelled as an
engine-only speedup.

**Stage 5 — larger authentic acceptance**. Only after Stage 4 pass, run 1,000+
players, progressively increasing actual 4/8 tournament load; then 50-season
reference when feasible. User-requested 16–128/Q/World can only be claimed
once those formats have genuinely executable authorized FAX/ATP sources.
Existing running #1820 is never edited or interrupted.

## 7. Decisions and required Work review outcome

| Decision | Proposed answer | Needs Work approval |
| --- | --- | --- |
| Single authoritative v2 format? | Yes: Claude #1805 generic Merkle JSON DAG, refined by #1821/#1811 tests | **YES** |
| Node physical namespace? | `(run_id,digest)`, branch reachability validated through Saved lineage | **YES** |
| Original v1 historical bytes? | Immutable, no auto-upgrade/re-sign | **YES** |
| Current snapshot and all ancestor source checks? | Required; node digest alone never proves owner or history | **YES** |
| Append-only vs rewrites? | Authenticated append optimisation + generic COW/snapshot fallback | **YES** |
| Internal node threshold? | Measure physical SQLite 4K, 2K, 1K, 512B; choose afterward | **YES** |
| First production change? | Stage 1 default-OFF v2 storage with exact v1/v2 differential tests | **YES** |
| Integrate independent experimental stores directly? | **NO**; they are diagnostics and threat-model evidence | **YES** |
| Is a 5-year Main16–128/Q full ATP simulation currently proven? | **NO** | **YES** |

Once Work approves the contract, split the implementation into small
coherent Draft PRs. **Only Radim merges**. This document should remain an
unmerged design proposal until acceptance; it is not a release note.

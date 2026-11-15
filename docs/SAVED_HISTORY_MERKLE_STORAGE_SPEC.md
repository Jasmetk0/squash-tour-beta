# Saved history as content-addressed JSON nodes (specification + prototype)

Status: **specification and measuring prototype only** (16 November 2026). No
production path reads or writes this format; no migration, re-signing or schema
change is made. It refines the component-storage proposal of Draft #1803
(`docs/NATIVE_SAVED_COMPONENT_STORAGE_PROPOSAL.md`) with measurements.

## Problem (measured)

Every v1 Saved Revision stores the complete Run state. On the actual two-season
final databases (W52/W61/W80 built by the #1803 acceptance runs):

| History | Revisions | v1 database | Unique whole components | Unique subtrees ≥ 4 KB |
| --- | ---: | ---: | ---: | ---: |
| W52 | 127 | 1,636 MB | 180 MB | 44 MB |
| W61 | 145 | 2,042 MB | 239 MB | 53 MB |
| W80 | 183 | 2,832 MB | 388 MB | 73 MB |

Deduplicating whole components (the #1803 proposal's first step) gives only 7–9×:
the checkpoint (`events`), Tour (`receipts`, `rankings`, `transitions`), lifecycle and
health `states` are all append-only lists re-stored whole. Splitting large subtrees
gives 37–39×, and each later revision adds only 0.3–0.5 MB.

## Design

1. **Nodes.** Every dict/list whose canonical encoding is ≥ 4 KB is stored once as
   the canonical JSON of `{"mj": 1, "r": [[path, digest], ...], "v": value}`;
   referenced children are `null` placeholders at explicit one-step paths, so no
   ordinary value can alias a reference. Smaller values stay inline.
2. **Addressing.** `digest = SHA-256(node text)`; a parent commits to its children's
   digests (Merkle), so a revision's root digest commits to its complete payload.
3. **Table.** `saved_revision_nodes(run_id, digest, body)`, primary key
   `(run_id, digest)`, insert-only, Run-scoped (no cross-Run sharing or ownership
   question). Written in the Save transaction: rollback removes exactly its nodes.
4. **Revision envelope `run_saved_revision.v2`.** `payload_json` holds the envelope
   (Run/Branch/identity fields unchanged) plus `"content_root": <digest>`; the
   revision `content_hash` covers that envelope, i.e. the whole content through the
   Merkle commitment. v1 revisions keep their bytes, hash and reader.
5. **Reading.** A reader hashes every node's ACTUAL stored text before use, once per
   read snapshot (the #1803 rule: nothing trusted because it is declared or cached in
   the same database). Missing, changed, non-canonical, malformed, foreign-Run or
   cyclic nodes fail closed for every revision that references them.
6. **Validation once per unique value.** Semantic validation (component replay,
   origins, terminal results) is keyed by a verified node digest within a process;
   a component unchanged across 100 revisions is validated once. Per-revision checks
   (identity, lineage, sequence, ownership, source reachability) still run for every
   revision on small envelopes.
7. **Compatibility.** Writer version chosen per Run at creation (recorded in Run
   metadata); existing Runs never change format silently; a lineage may mix v1
   ancestors and v2 descendants; forks share nodes within their Run; exports
   reconstruct v1-identical payload bytes.

## Prototype results (actual runs, this host)

`scripts/prototype_merkle_saved_history.py SOURCE.db --work DIR` re-stores a real
history (source opened read-only) into a fresh SQLite node table, then in a new
process authenticates every revision cold, reconstructs HEAD and checks every
revision's exact canonical bytes:

| History | v1 file | node file | write (all revisions) | cold authentication of all revisions | HEAD reconstruction | exact |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| W6 | 232 MB | 17.7 MB | 22.5 s | 0.47 s | 0.41 s | 34/34 |
| W52 | 1,636 MB | 43.8 MB | 185 s | 1.55 s | 0.85 s | 127/127 |
| W61 | 2,042 MB | 53.0 MB | 232 s | 2.28 s | 1.14 s | 145/145 |
| W80 | 2,832 MB | 72.6 MB | 317 s | 2.33 s | 1.14 s | 183/183 |

For comparison, a v1 cold read of the same W80 history is ~105–111 s on #1803's
repaired head (226 s on `buuk`) because it decodes and validates every full snapshot.
The prototype measures storage and authentication only; it does not yet run the
semantic validators on nodes, so it is not a like-for-like read time.

Prototype limits: the writer re-encodes the full payload for each revision
(1.7 s per W80 revision); a production writer must reuse digests of unchanged
subtrees (the previous HEAD is already verified in the Save transaction). The
measurement process's peak RSS (3.4 GB for W80) comes from reconstructing all 183
full payloads for the equality check, not from authentication.

## Projection (not a test)

At the measured 0.3–0.5 MB of new nodes per revision, 50 W80 seasons (~4,600
revisions) would store a few GB instead of the v1 quadratic growth (~2.8 GB per two
seasons today, growing with every snapshot). This is an extrapolation only; no
50-season Run has been executed.

## Plan (each step its own reviewable PR, after #1803 is merged)

1. Node table + v2 envelope writer/reader behind a Run-level format flag; v1
   untouched; differential tests: same commands produce identical public DTOs,
   fingerprints, replay results and archive/comparison responses on v1 and v2 Runs.
2. Negative tests: changed, missing, foreign-Run, truncated, duplicated nodes; a
   digest not matching actual bytes; corruption after successful warm reads;
   rollback/savepoint; concurrent Saves inserting the same node.
3. Incremental writer (reuse verified subtree digests), then node-keyed validation.
4. Mixed v1/v2 lineage, fork, restore, extension.
5. Re-run W52/W61/W80 two-season acceptance and a growing-horizon benchmark, then
   the 50-season reference run.

Related determinism defect (separate decision): random Saved revision IDs enter
component values, so identical commands produce different bytes on every run;
deterministic IDs would also improve node sharing across forks.

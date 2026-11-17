# Proposal: content-addressed Saved components (remaining engineering work)

Status: **proposal only**, written for Work's review in Draft #1803 (14 November 2026).
Nothing here is implemented, migrated or approved. It is the engineering answer to
the measured limit that long native Runs re-validate their complete history from
full snapshots; it is not a product rule change.

## Why

Every Saved Revision stores the complete Run state. A two-season W52 native Run
with 8 players already has 127 revisions and 1.61 GB of Saved text; each later week
is larger than the previous one. Reads reread and hash every ancestor once; a cold
process also decodes, canonically re-encodes (content hash) and validates every
revision. Data and cold validation therefore grow quadratically with the number of
weeks. The Master's reference FAX 50-season release test (31.28) has about 3,000
revisions; that cannot meet the 120 s per-read bound with full snapshots.

## Design

1. **New payload schema `run_saved_revision.v2` for new writes only.** Its `content`
   maps each component key to a reference `{"sha256": <digest>, "bytes": <n>}`
   instead of the component body. Everything else in the envelope (Run, Branch,
   identity, sequence, parent, kind, change summary) is unchanged.
2. **Immutable component store** `saved_revision_components(run_id, digest,
   body_json)`, primary key `(run_id, digest)`. `digest` is SHA-256 of the canonical
   JSON of the body. Rows are insert-only (a writer inserts if absent), never
   updated or deleted, and Run-scoped: no cross-Run sharing.
3. **Append-only histories as segments.** Components that grow by appending
   (sporting checkpoint events, lifecycle/Health histories, Tour receipts) are
   stored as a chain of segment bodies; a revision references the chain head, whose
   body names its previous segment digest. An unchanged prefix is stored and
   validated once. The assembled component value is byte-for-byte the v1 body.
4. **Integrity.** The revision `content_hash` covers the envelope with the
   component digests (a Merkle commitment). A reader recomputes SHA-256 over the
   ACTUAL stored component bytes it uses, in every read snapshot, exactly as today
   for whole revisions; a digest is never trusted because it is declared, and no
   proof is persisted in the database. A missing, foreign-Run or changed component
   fails closed for every revision that references it.
5. **Validation once per unique component.** Strict decoding, canonical-form check
   and component replay are keyed by the verified digest within one read snapshot,
   so a component shared by 100 revisions is decoded and validated once. Per-revision
   checks (identity, lineage, sequence, owners, source reachability, receipts,
   terminal results, closures) still run for every revision.

## Compatibility (non-negotiable)

- Existing v1 revisions keep their bytes, hashes, fingerprints and reader; they are
  never migrated, re-signed or rewritten. Historical replay uses their original
  semantics.
- A lineage may mix v1 ancestors and v2 descendants; each revision is validated
  under its own schema. Forks share ancestors exactly as today.
- Public API/DTOs, exports, seeds, RNG hierarchy, MatchEngine and sporting rules are
  unchanged: readers assemble the same component values.
- Writer choice is explicit and versioned (for example only for Runs created after
  the change, recorded in the Run's metadata); an existing Run never changes format
  silently.

## Expected effect (to be measured, not claimed)

Stored bytes and cold validation become proportional to the unique data actually
saved (roughly linear in weeks). Two W80 seasons would read and validate on the
order of the last revision's size plus per-revision metadata instead of ~2.6 GB of
repeated snapshots.

## Work plan and tests

1. Writer/reader for v2 behind a Run-level format flag; v1 untouched.
2. Differential tests: v1 and v2 Runs built from the same commands yield identical
   public DTOs, fingerprints, replay results and archive/comparison responses.
3. Negative tests: changed, missing, foreign-Run, truncated or duplicated component
   rows; a declared digest that does not match actual bytes; a segment chain cycle;
   corruption after successful warm reads.
4. Mixed-lineage, fork, restore, extension and rollback tests.
5. Re-run the W52/W61/W80 two-season acceptance and a growing-horizon benchmark on
   identical commands for v1 and v2; then the 50-season reference run.

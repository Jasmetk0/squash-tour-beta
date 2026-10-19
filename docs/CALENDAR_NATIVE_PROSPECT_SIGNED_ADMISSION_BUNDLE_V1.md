# Native W-aware 15yo admission — Signed lifecycle / sporting / Health bundle v1

## Implemented (read-only staging)

Following merged #1552–1554, the Admin prospect-intake preflight now prepares a
**complete, hash-bound three-owner admission bundle** from the exact authenticated
Signed Run prospect source and configured Tour predecessor. The same W/O-aware
birthday event supplies every proposed athlete to:

- the separate `player_lifecycle_calendar_state.v4` successor, preserving
  previously published retirement/first Entry identity and chronological age;
- complete canonical **57-attribute sporting records**, preserving every prior
  player and the original newborn potential/attributes without rerolls; and
- complete proposed Health profiles, preserving every pre-existing health fact
  byte-for-byte and creating **empty injury, illness and consequence history**
  for each newly arriving 15-year-old.

`calendar_prospect_admission_bundle.v1` owns the exact new population in all
three projections. It checks sorted unique identities across all three and
matches each new sporting profile to its exact seeded birth evidence. The Health
projection retains the authenticated source Health fingerprint, source week,
full original and proposed health rosters, and **the same birth event**. Its
validator refuses any dropped/modified original injury or invented newborn
health record. No artificial healing or pre-run facts are generated.

The preflight displays the proposed Health fingerprint and population count,
alongside previously available lifecycle/sporting proofs, plus one
`admission_bundle_fingerprint` that binds all authorities together. It does
not send the hidden 57 attributes, full Health history or other raw source
payload to the UI.

## Scope and safety boundary

This is **not** Tour activation. The existing
`intake_source_requires_native_calendar_materialization` guard is still
present. No SQLite/Saved Revision/Tour/Health/ranking/Entry write is performed
by the new projection. A non-empty source continues to block the real
Week/Season Transition until a single transaction and fully versioned
cross-domain replay can consume this evidence.

The baseline Health verifier still rejects a non-Saved/unsaved Health component.
Active health conditions and permanent consequences remain unsupported in this
intake adapter: failing closed is preferable to silently treating them as
healed. The bundle deliberately declares `tour_signed_writer_supported=false`
and `ranking_and_entry_adoption_supported=false`.

The next production step must give Sporting checkpoint and Health persistence
their own historical-compatible intake schema, reconcile genuine end-of-week
development, deterministic ranking inclusion and Entry eligibility, integrate
Saved replay/fork/restore and only then switch on atomic birth adoption.

## Verification

Focused `pr_critical` tests cover W52/O1, W52/O35, W61/O37, W80/O15,
W80/O80 and actual Year/Season rollover, exactly equal lifecycle/sporting/
Health player sets and fingerprint determinism, preserving original byte
evidence, missing/foreign/future Health rejection, fabricated newborn injury,
forged source roster, tampered sporting 57 attributes and stale Signed head
fingerprint. Real HTTP/SQLite Save and restart demonstrates that the new
bundle appears for a due 15-year-old without admitting anyone.

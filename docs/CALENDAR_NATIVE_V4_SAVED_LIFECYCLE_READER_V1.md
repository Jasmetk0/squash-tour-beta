# Native 15-year-old v4 lifecycle — real Saved reader and adversarial gate

## What this adds to the actual persistence path

The production `player_lifecycle_state.py` Saved decoder now recognizes
`player_lifecycle_calendar_state.v4` as a distinct validated subclass rather
than trying to parse it as a legacy state. This allows real Signed reader,
SQLite row decode and Saved component hash validation to understand a
versioned birth receipt without modifying older v2/v3 bytes.

**A Saved chain containing even one v4 birthday is admitted by the
component verifier only after all of these pass:**

- Authentic initial World is already loaded and matches the unchanged
  initial v2 population identity and lifecycle policy.
- The full Saved lifecycle-component hash is recomputed over all states.
- The Saved Tour owner is present and its real model passes schema checks.
  The final lifecycle week/fingerprint must equal the Tour owner.
- The saved Run-scoped prospect source is present, has a correct canonical
  fingerprint and belongs to the same Run. It is parsed from the immutable
  *revision being verified*, never from arbitrary current SQLite rows.
- The #1556 full-history native replay checks every W/O birthday, source
  profile seed, 57-attribute identity, provenance, lifespan/retirement, and
  every actual first Entry from the Saved Tour's own Edition submissions.
  Old non-birth v3 weeks stay v3 and preserve their exact signatures.
- For an entire history without v4, the *unchanged* historical
  `calendar_lifecycle_history` replay applies. No new branch or calendar
  reinterpretation is introduced for old revisions.

Forking a v4 lifecycle with the old generic branch-remapping shortcut now
**fails closed**. Its event references the old Branch and predecessor hash;
a future authenticated fork writer must rebuild those references, not
rewrite the enclosing `branch_id` and pretend the event is signed.

The new acceptance tests exercise the actual `load_saved_lifecycle`,
`_parse_lifecycle_json` and saved Run-prospect-source component reader,
with a canonical actual `CalendarTourState` object and minimal trusted
InitialWorld fixture. They test W52/W61/W80, compatible run offsets,
JSON equality, unchanged Saved input, source omission, a bad source hash,
full re-signed source substitution, extra due player, forged Tour head,
forged lifecycle hash, foreign branch and modified newborn identity.

## Explicit remaining production boundaries

- This is a **read-side capability**. No new Tour Week Transition writer is
  authorized; the existing Run-prospect guard is unchanged.
- Sporting and Health persistent snapshot migration, genuine end-of-week
  source count verification, ranking/Entry publication, transaction rollback,
  full Saved restart/fork/restore, and 50-season acceptance are outstanding.
- The production Saved component verifier still requires a matching Tour
  owner: standalone unsaved v4 imports must not acquire authority.
- Do not mark native birth activation complete until actual atomic writer
  commits can round-trip through this verifier together with the compatible
  checkpoint/Health/ranking/event authorities.

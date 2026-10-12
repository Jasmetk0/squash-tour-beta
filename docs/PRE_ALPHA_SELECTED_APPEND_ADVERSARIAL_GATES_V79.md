# F79-08 — Selected-append adversarial authority gates

Extension of the already merged F79-06 Add Selected operation. **No change to
existing player IDs, generation mechanics or historical ranking contents.**

## Why this is necessary
A pristine Week-1 player snapshot and absent official ranking are necessary
but not sufficient. Run/Branch-specific historical authority can exist before
a published ranking or after a legitimate edit has been independently audited.
The initial population may not be rewritten after any such history.

Before committing a selected append, the existing SQLite BEGIN IMMEDIATE
transaction therefore refuses a run/branch once any of the following exists:

- Official ranking candidate or published official ranking;
- historical Official Ranking result/zero version, adopted tournament ranking
  source or tournament ranking-snapshot authority;
- authoritative world clock, world event or Week Transition receipt;
- completed-week sporting context;
- a Player Health Admin Edit receipt, even if a later data change would leave
  an apparently pristine Week-1 health state;
- a Tour entry trigger, even before a first Official Ranking publication;
- a Week-2-or-later lifecycle/sporting/health projection;
- any valid but non-bootstrap edit of the three Week-1 projections.

These are *blocking evidence*, not data to be deleted or recalculated by Add.
An unrelated Run/Branch should not trigger this scoped check.

## Other historical CAS requirements (unchanged but adversarially tested)
- Active writable custom Run/Branch only.
- Exact expected Saved HEAD and clean Working Draft version.
- Live and Saved World Package fingerprint both match the reviewed input.
- Exact live and Saved InitialWorld fingerprint must match the reviewed source.
- The source player IDs must be new, unique and explicitly selected.
- Every rejection leaves original InitialWorld bytes, all Week-1 projection
  bytes and every existing Saved Revision identifier/hash/payload unchanged.

## Verification limits
The added tests operate against the real repository, SQLite transaction and
Saved Revision lineage. Only the unrelated World Package provisioning lookup
is stubbed using the established scoped InitialWorld test fixture. This test
does not claim a full internal pre-alpha release or support for adding players
mid-season.

The separate F79-07 production Chromium/SQLite/restart gate proves the
ordinary successful Add Selected path; this PR exercises failure modes that
must never mutate a saved Run.

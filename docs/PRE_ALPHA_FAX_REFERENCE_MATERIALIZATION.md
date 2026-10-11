# Copied-FAX pre-alpha reference materialization

## Purpose

Create one disposable editable Product Run from reviewed FAX source inputs using only existing production Run, Package, InitialWorld and Working Draft boundaries.

The workflow is explicit **Preview → Materialize**. Preview is read-only and freezes the source fingerprints plus the acceptance-scale counts. Materialization rejects a stale preview before creating a Run.

## Materialization sequence

1. Create a canonical empty 50-season Product Run.
2. Copy the selected World Package document into Run-owned Package state and Save.
3. Copy the reviewed 2000/2001 Calendar Package document into Run-owned Package state and Save.
4. Generate and adopt at least 1,000 InitialWorld players from the Run-owned World snapshot.
5. Save InitialWorld through the normal Working Draft boundary.
6. Re-run the machine-readable FAX long-acceptance input gate and fail closed if the new Run does not pass it.

Each durable component uses the ordinary Saved Revision path; the bootstrap does not create a parallel persistence model.

## Content boundary

The materializer requires exactly 80 first-season `WORLD_TOUR` Calendar Editions before it mutates anything. It does **not** define their eventual FAX names, locations, categories or format canon. Those remain explicit source/template content.

The current integration test therefore uses an explicit provisional 80-Edition test Calendar only to prove persistence and scale. It must not be cited as final FAX sporting content.

## API

- `POST /run-containers/pre-alpha/fax-reference/preview`
- `POST /run-containers/pre-alpha/fax-reference/materialize`

The materialize request includes the exact preview fingerprint.

## Next

Author the reviewed 80-Edition copied-FAX Calendar source, use this bootstrap to create the persisted 1,000-player release fixture, then start the mandatory 50-season acceptance harness and fix the first canonical preparation blocker encountered.

# F79-03 — Temporary country + serial generator names

**Product authority:** Master v79 §9.6. Newly generated players receive
temporary names based on their World country's display label and a deterministic
country-local sequence (e.g. `Česko 1`, `Česko 2`, `Slovensko 1`).
Realistic first/last-name databases are not part of this slice.

## Versioning and replay

`RunWorldInitialPoolPreviewRequest.naming_policy` is optional, with supported
explicit value `country_serial.v1`. New first-cohort **Run Admin** previews
send this value; unchanged pre-existing preview and proposal requests do not.

The absent value uses the original personal-name generator exactly and is
omitted from the request's canonical fingerprint payload. This preserves exact
old initial preview, two-pass Keep, session V2 and saved-proposal fingerprints.
No existing Run/Branch/World, saved proposal, imported player or published
player is renamed. An old saved request replays using its original name
generation, not the new policy.

A new player in the opted-in generator is named
`{country.name} {sequence}`. The country name is resolved from the
**authoritative stored World country**, not from a browser value. The sequence
is the numeric suffix of the immutable existing player identity
`P-{season_start_year}-{country_code}-{sequence:04d}`, making numbering
independent of table sort, filters, Keep/replay and display localization. The
name is purely display data; `player_id` is always authoritative.

The previous name-selection RNG draws are still consumed before assigning the
new display name to preserve the exact remaining player RNG stream and existing
generation fingerprints for equal seed/country/sequence. Other player fields,
age, potential, style, quotas and seed hierarchy are unchanged.

## Keep, next batch and limits

Keep preserves the entire original player object including its name. A new
generation stage skips reserved player IDs (existing preserved profiles)
and numbers each generated player according to its unique new ID. Expanding a
cohort while retaining all its prior profiles produces increasing names:
`Česko 1–3` followed by `Česko 4–5`. Gaps from intentionally discarded
non-Kept proposals may be reused in the replacement preview: the generator
does not create an independent persistent global serial registry.

An authoritative append to an **already saved InitialWorld** is still a
separate future feature; this PR does not pretend to implement the general
selected-profile Add workflow. On that feature, Run-owned existing IDs must
be supplied as reserved identities so per-country serials continue without
collision and imported/manual names remain untouched.

Serial scope in this initial-player generator is the season start year and
country code of the generation request; two Branches replay independently,
while the stable ID remains the true identity. Shared World country display
names do not replace or mutate country codes, nor do names define a global
identity registry.

## Evidence

Focused tests cover old vs opted-in requests, identical non-name player fields,
deterministic round-trip, exact quotas, repeated Keep and V2 edit, adoption,
country-name accents, continuation with preserved players, and invalid policy
rejection. The disposable Chromium initial-tournament acceptance also asserts
serial display before two Keep passes, proposal restore and Save. This is not a
full season, future-year intake or release/realism certificate.

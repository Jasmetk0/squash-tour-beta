# Authenticated generation session V2 — implementation boundary

V2 is opt-in for the existing Run-owned first-season production generator.
Unchanged legacy (no-session, one-pass and repeated Keep) request fingerprints
and stored proposals retain their prior normalization. This slice does **not**
implement the canonical 57 attributes / 0–200 OVR.

## Request and operation authority

A V2 request preserves an exact, typed `session_origin_request` with the
`session_origin_fingerprint` of its independently regenerated authoritative
preview, plus ordered `session_steps`. Each step has an operation kind
(`edit` or `keep`), the fingerprint of the immediately preceding verified
preview, its resulting seed, complete supported source field-lock snapshot
and (for Keep) sorted selected player IDs. No client-supplied player snapshots
are accepted or used. Source fingerprints are verified by server-side replay
from the Run-owned World Package on every preview, proposal verification and
Adopt. Edits must preserve origin world, season, total, exact country quotas,
age, country/region, and original legacy Keep ancestry.

A field edit retains the current seed and replays the authoritative stage
before applying its complete supported lock snapshot. Keep requires a new
seed, a nonempty proper subset, and preserves selected source players only.
Keep cannot quietly introduce or change locks: its lock snapshot is exactly
the prior locks restricted to selected IDs. Removed players' preview locks
do not survive their replacement. Kept identities remain stable; session
locks do not become career locks in InitialWorld.

V2 step limit: 48 operations, with at most 17 V2 Keep steps (the frontend
also applies its stricter total Keep limit across legacy and V2 history).
Existing independent proposal limit and preview field limit remain.

## Safety, limitation and follow-up

This is a read-only preview and authenticated-input extension: Adopt stages
InitialWorld only on explicit confirmation, and manual Run Save remains a
separate operation. Existing Run/Branch/World/Saved HEAD/Draft guards in
`admin_players.py` still apply. Stored proposals keep the complete validated
request, previews and fingerprints; exact reopening does not generate.

**Known limitation:** An Automatic field reset inherits the last authoritative
Keep stage's pre-edit source profile. If a manual value was already inherited
as part of a whole-player Keep before V2 began, Automatic cannot recover a
pre-Keep source generation value from that field alone. Distinguish removing
a current-stage lock from undoing historical whole-player Keep; the latter
requires a later explicit history-aware reset operation. Do not describe
this as canonical source model or full session Undo.

Focused backend/frontend tests are the PR gate. Full season/release/realism
certification remains governed by `docs/PRE_ALPHA_TEST_POLICY.md`.

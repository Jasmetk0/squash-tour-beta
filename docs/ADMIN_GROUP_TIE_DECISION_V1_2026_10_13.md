# Real Admin unresolved group tie decision — 13 October 2026

## Scope
After a pure-groups tournament's actual matches finish, its immutable
Group Standings authority can still be blocked by an unresolved sporting tie.
This change makes that previously API-only decision usable in the Run-owned
Event Admin view. It does **not** change the order of the sporting tie-breaks.

## New workflow
- The existing Group Standings panel obtains the exact unresolved case,
  including the server-computed `unresolved_case_fingerprint`, from the
  authority-bound `GET group-standings/tie-resolution` endpoint.
- The Admin reviews the complete player list in the case, moves those players
  up/down into a deliberate order, records a nonempty audit reason (max 1000
  characters), and checks a separate confirmation.
- The UI submits exactly that reviewed player permutation plus the backend
  fingerprint, scoped to the selected Run/Branch/Event; no other players can
  be inserted and the client cannot generate its own case identity.
- The server commits an immutable audited Group Tie Resolution only for the
  still-current unresolved case. Stale/foreign cases remain HTTP 409, and
  the browser clears its confirmation and re-reads live authority before any
  retry.
- A recorded tie decision is not a final table. Existing explicit generation
  of the completed table is available only after **every** remaining unresolved
  tie has been resolved; Simulation Save still freezes the resulting revision.
- Read-only, historical, unverified Run/Branch, missing or malformed case
  fingerprint, incomplete player order, or missing audit reason all block writes.

## Acceptance boundaries
- Python `pr_critical` exercises the exact serialized server-side case digest.
- Frontend tests cover positive and negative scope validation, exact response
  matching, explicit reordering and confirmation, edit-after-confirm invalidation,
  audit reason, disabled contexts and stale 409 handling.
- This does not create mock sporting receipts, fabricate ranking points or seed
  an unearned tie-break. Genuine unresolvable ties may not occur in a short
  six-match random tournament, so dedicated UI tests provide deterministic
  coverage for the review controls.

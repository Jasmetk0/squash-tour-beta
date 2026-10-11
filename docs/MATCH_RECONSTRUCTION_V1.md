# Canonical Match Reconstruction v1

## Scope

This slice implements the minimum pre-alpha Match Reconstruction contract from
Master §§17.9 and 31.3 on the canonical Run/Branch simulation path.

It is deliberately **not** the final probability-search architecture. The supported
hard constraints are:

- winner player identity,
- exact match score in frozen Player A / Player B order,
- exact game scores in frozen Player A / Player B order.

Admin chooses a requested candidate count from 1 to 20. The engine searches a bounded
deterministic stream of natural scenarios and returns every scenario that satisfies all
supplied hard constraints until the requested count is reached or the bounded search is
exhausted.

## Non-authoritative preview

Preview uses the same canonical Simulation Slot executor and Match Engine as normal
sporting execution. It does not maintain a second reconstruction simulator.

The server may materialize the adopted tournament authority and current Simulation Slot
inside the preview transaction. Every candidate attempt executes inside a nested
savepoint and is rolled back before the next attempt. The outer preview transaction is
rolled back as well. Therefore candidate generation does not persist:

- adopted tournament authority,
- Simulation Slots,
- match-group receipts,
- player effects,
- tournament result / point / ranking sources,
- command receipts.

Candidate order is discovery order. Every candidate exposes a compact winner / match
score / game-score summary and the complete read-only canonical Match Result detail.

If the bounded natural search cannot fill the requested candidate count, preview returns
the candidates it did find plus an explicit warning. It does not silently force a
result or reinterpret probability.

## Commit

Only an explicitly selected candidate can become authoritative history.

Commit runs under the existing writable Run/Branch transaction boundary and revalidates:

- current FAX week,
- current canonical Position fingerprint,
- Saved Revision head,
- current eligible match group,
- reviewed preview fingerprint,
- selected candidate fingerprint.

The server then re-derives the reviewed candidate set and executes the selected seed
through the normal canonical Simulation Slot match path. The committed result fingerprint
must equal the reviewed candidate result fingerprint exactly.

The committed match-group receipt stores reconstruction provenance:

- preview fingerprint,
- selected candidate fingerprint,
- exact hard constraints,
- operator label,
- audit reason.

Normal match effects and tournament close / ranking-source logic remain owned by the
existing canonical executor. Exact command retry reuses the stored command receipt.

## Intentionally unresolved

This slice does **not** define or infer:

- candidate probability estimates,
- p / δ / α acceptance mathematics,
- forced reconstruction,
- nearest-match / relaxed-constraint search,
- the complete future constraint catalog,
- reconstruction-session retention,
- final compact-card or dedicated Reconstruction-page design.

Those remain product / simulation-policy work and must be specified before a later
implementation promotes them to canon.

# Individual preview field locks — supported production V1 slice

Date: 11 October 2026. Authority: Master v78 §§9.6, 27.20, 31.33.

## Exact boundary

The current real first-cohort generator exports nine numeric **source-model** fields (1–99): current and potential ability and `technique`, `movement`, `physical`, `mental`, `consistency`, `clutch` and `recovery`. The inspector offers a right-side player editor, explicit **Lock field**, **Automatic** and **Apply field locks to preview** actions; the editor holds position in the list. It is not a 57-field/OVR editor. Height/weight and other as-yet unmodeled canonical physical fields are unavailable instead of being silently fabricated or written to an incompatible schema.

The server accepts only sorted, unique typed `field_locks` with valid player IDs and supported numeric 1–99 values. It generates from the exact saved World snapshot and returns a concrete conflict if locked identities disappear or if edited current/potential values violate the existing generator model or hidden potential ceiling. It never silently modifies or unlocks a requested value. Each edited player's source fingerprint and aggregate generator fingerprint are recomputed. The browser verifies **every** proposed locked value against returned authoritative InitialWorld state before enabling explicit Adopt. Unapplied changes block adoption.

A same-seed field edit recalculates the full preview but leaves the Run alone. For a new-seed regenerate, field locks remain explicit hard constraints and mismatched IDs or profile values cause a conflict. The next-seed action is available from the editor for the initial review before whole-player Keep; repeatable Keep + evolving locks needs a separate verified integration slice. Legacy no-lock fingerprints preserve their hashes.

On explicit Adopt, edited numeric values and their provenance become part of the InitialWorld Working Draft; user must separately Save. The ephemeral field locks do **not** install a persistent player lock or freeze subsequent career development. The production browser smoke tests a modified technique field before whole-player Keep and full tournament Save/restart replay, while focused backend and component tests cover conflicts and approval guard.

This PR does not settle any [OPEN] generator mathematics, quotas, repeated Keep/lock conflicts, height/weight physical calibration, general player creation or Player/Hybrid Package schema.

# Signed-native 15yo sporting preflight — explicit-seed Admin HTTP review

## Implemented

`POST /admin/runs/{run_id}/branches/{branch_id}/calendar-tour/prospect-intake/sporting-preflight`

JSON body (all fields required):
```json
{
  "expected_saved_head": "<existing Saved Revision ID>",
  "expected_checkpoint_fingerprint": "<64 lowercase hex hash>",
  "expected_tour_fingerprint": "<64 lowercase hex hash>",
  "seed": 927
}
```

The POST operation is **read-only**; it calls the same live, Signed-verified
native Tour context and saved Run-scoped prospective-source validation as
the existing Admin `GET .../prospect-intake/preflight`, in **one database
read transaction**. It rejects unsaved/changed Tour/checkpoint, stale HEAD,
non-integer/boolean seed, missing newborn source, unsupported policy and
bad due cohort, without a SQLite/Working Draft/Save mutation.

For each due native 15th birthday, the endpoint calculates #1555's exact
lifecycle + full Health + 57-attribute signed candidate and #1557's actual
old-player weekly sporting development, including end-of-completed-week
Form/sharpness/fatigue effects. Its `played_counts` come exclusively from
verified opening/continuation/Tour MatchEngine events in the real sporting
checkpoint, not client-provided numbers. The development policy comes
exclusively from the actual effective calendar Tour authority, not from a
request override.

The Admin receives an explicitly seeded review with:
- the current/target Run week, current/next population counts and source HEAD;
- genuine played-participant count and hash of the canonical play count data;
- verified policy and seed;
- old-player developed/recovered and complete new-player sporting fingerprints;
- the bound Health/lifecycle/sporting **combined admission-week fingerprint**;
- unchanged `blocked=true`, `native_activation_supported=false`
  and `signed_writer_supported=false`.

The existing GET response is unchanged; POST only adds
`sporting_week_projection` and recalculates its overall preflight fingerprint.

## Boundary

This is now a real seeded and Signed-verified **review endpoint**, not
activation. The future actual Tour Week Transition must use the same
command seed, completed match facts and season-effective policy, then install
a new versioned sporting/Health/lifecycle owner and ranking in one atomic
transaction. It cannot treat this POST response as a permission to write.
No previous v1–v10 Saved checkpoint/event bytes are reinterpreted.

## HTTP/SQLite regression

The existing real 8-player Signed Run source acceptance now tests:
1. manual source Save with an authentic due 15yo profile;
2. explicit seed and current verified HEAD/Tour/checkpoint;
3. correct 8 → 9 target population and deterministic replay;
4. different seed changing the exact review fingerprint;
5. stale HEAD/checkpoint/Tour returning HTTP 409;
6. booleans, string seeds and extra JSON fields returning HTTP 422;
7. unchanged GET preflight, Saved revision hashes and Tour live state;
8. **physical SQLite restart** preserving identical seeded review bytes.

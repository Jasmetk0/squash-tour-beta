# Match Lab: paired two-scenario comparison (API V1)

Status: production Match Lab backend/API candidate, not an authoritative Run match.

## Purpose

The existing Match Test Lab can simulate one isolated scenario and multiple seeds,
and preserve standalone Lab sessions. The new endpoint compares **two scenarios
on precisely the same seeds**, preserves the identity of each source, and rejects
stale Session fingerprints before invoking MatchEngine.

## Endpoint and source contract

POST /admin/labs/match/compare returns match_lab_paired_comparison.v1.

Each side (baseline and candidate) chooses exactly one:

- Inline: a complete existing match_test_lab_scenario.v1 in a scenario field.
- Saved Session: session_id plus expected_session_fingerprint (64 lowercase hex).

batch_seeds is an explicit list of 1–12 distinct signed 64-bit integers shared
by both arms. Invalid seed batches return HTTP 422, a missing Session 404,
and a changed Session or mismatched scenario rules/identities 409.

## Portable example (schematic only)

Request fields: baseline.scenario, candidate.scenario, batch_seeds: [11,12,13].
Or replace either side with a saved Session reference, for example:

    baseline: {session_id: <your real Lab Session ID>,
               expected_session_fingerprint: <the exact current 64-hex hash>}

The HTTP response includes immutable provenance fingerprints, exact original
winner, sets, rally count and elapsed duration per seed and side, result hashes,
winner flip counts, and observed paired deltas. No session or Run is saved.

## Pair validity and safety

The two arms require the same match_id, player IDs on the same A/B sides,
best_of, games_to, win_by, upset_variance, and retirement rule. The intended
difference can be a player attribute or one of the existing participant
modifiers. No auto-tuning or sporting policy is introduced.

Same seed means only the same initial RNG state: control-flow changes can
cause different downstream draws. Paired results are descriptive and cannot
be described as scientific proof of calibration or a causal confidence bound.
Lab Sessions are read and fingerprint-checked at request time; the two reads
are not an atomic snapshot of the whole database. Historical Run source
equivalence is NEVER claimed from a Session copy.

The service invokes the existing production MatchTestLabService.run and
MatchEngine.simulate in both arms. It does not alter MatchEngine, existing
session persistence, Run/Branch/Viewer, calendars, Saved history, or Master.

## Verification

    python -m pytest -q tests/application/test_match_lab_paired_comparison.py
    python -m pytest -q tests/api/test_match_lab_paired_comparison_api.py

The application tests cover replay, arithmetic, pinning, corruption and
adversarial input handling. The HTTP tests use genuine FastAPI + SQLite,
actual MatchEngine matches, no session mutation, and a physical DB restart.
These are scoped tests, not 80 played FAX Editions or 50-season release proof.

No CS/EN frontend is included in this PR; it can be implemented independently
against the new API after the owner merges this bounded backend contract.

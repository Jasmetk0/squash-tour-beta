# Prepared points from actual later-week native knockouts

Implementation scope following merged #1535; Master remains v85. This is a
practical scored-*exhibition* sporting operation, NOT an Official Tour Edition
or official ranking release. The existing saved v5 opening knockout and at
least one saved sporting-week advance remain prerequisites.

## Distinct opt-in command

Existing POST `/calendar-continuation/knockouts/simulate` stays untouched
and writes historical `calendar_followup_knockout.v1`.

New POST `/calendar-continuation/knockouts/simulate-scored` requires all
original source-bound knockout command fields **plus**
`point_policy` (category label, champion/finalist/semifinal non-increasing
integer points, positive W-validity) and literal
`explicit_point_confirmation: true`.

It runs the same three real MatchEngine matches atomically under one
`BEGIN IMMEDIATE` SQLite transaction, with finalist load effects and
the current 57 canonical sporting inputs. Nothing may partially commit.

The new `calendar_followup_knockout.v2` event embeds frozen policy and
four awards derived exclusively from semifinal losers, final loser and
final winner. Every award includes the exact (policy-independent)
sporting tournament fingerprint and policy fingerprint. A changed winner
or point value, even with recomputed outer component hash, must fail
validated full-event replay. The old v1 serializer drops new fields and
its original hashes/receipts stay unchanged.

## Checkpoint, Save and replay

A scored event makes the player-owner schema
`calendar_sporting_checkpoint.v5`, while all earlier schemas v1–v4
are retained byte-for-byte. An unscored later knockout after a scored
event retains v5; an additional sporting-week advance also retains v5.
Neither re-signs earlier evidence.

All nested MatchEngine logs, sources, unique command identities,
signed lineage, entire population and authoritative weekly effects
are reconstructed by existing checkpoint verification. Source HEAD and
checkpoint must both be Saved. The new result itself requires a
separate manual Save before another sporting command. Exact retry,
later weekly progression, restart, replay, historical restore and
compatible horizon extension preserve original results.

The normal Admin continuation view exposes immutable points beside
the actual winner and saved status. UI requires an independent
confirmation for prepared scoring; score edits revoke the consent.
Operator-authored amounts are provisional, not a configured
Category/Edition point source. They never auto-count in Official
Ranking, Race or public timeline. Tour Entry, Edition provenance,
official result publication, lifecycle/Health, real nine-stage
Week Transition and Season Transition remain separately guarded.

## Targeted acceptance

- W52/W80 real production HTTP/SQLite scored knockout and three matches.
- Explicit consent, W-bound policy, three-stage placement and award
  fingerprint guards; wrong inputs rejected without mutation.
- V1 old serialization preserved, v2 tamper rejection even with
  an outer re-hash, scorer receipt exact idempotence.
- Manual immutable Save, next week six real participation counts,
  saved v5 schema, cold restart/replay, backward/forward restore.
- CS/EN form and frontend receipt guards for changed awards.
- Latest-head Fast CI and relevant browser workflows must be green
  before the owner is told the PR is merge-ready.

This is significant sporting history/point preparation, but it is
not a claim to have completed Official Tour or Full Simulation.

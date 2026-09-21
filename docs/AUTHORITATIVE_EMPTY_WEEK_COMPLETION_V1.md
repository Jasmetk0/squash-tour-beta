# Authoritative Empty Week Completion V1

## Purpose

This slice closes one concrete whole-season continuity gap from Master §31.3:
an Official Run can reach a RankingWeek with no competitive tournament work, but
the canonical sporting transition must never infer **zero matches** merely because
rows are absent.

`POST /admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation/empty-week/complete`
creates explicit Run/Branch-owned `CompletedWeekSportingContext` evidence for that
case.

## Commit contract

The command is CAS-guarded by:

- exact current `RankingWeek`;
- exact authoritative Position fingerprint;
- exact Branch Saved Revision head;
- unique `command_id`.

The command fails closed unless all of the following are true:

- the Run/Branch is writable and active;
- a season Calendar authority exists;
- no Calendar Event interval covers the current week;
- no executable tournament package exists for the week;
- no adopted tournament authority exists;
- no Week Schedule exists;
- no Entry/WC global Simulation Slot exists;
- no authoritative match slot/group history exists;
- no completed tournament ranking source exists for the week;
- lifecycle and sporting snapshots both exist;
- no different completed-week sporting context already exists.

The Calendar snapshot plus week identity is fingerprinted and stored as the sole
source fingerprint of the explicit zero-match context. Every player in the current
sporting roster receives competitive match count `0`.

## Downstream behavior

Once the explicit context exists, authoritative Position no longer requires a
match Week Schedule or terminal match checkpoint for that genuinely empty week.
The normal persisted Ranking Transition Authority, Saved Revision and Week
Transition path remains unchanged. Development and Between-Week State Update read
the same `CompletedWeekSportingContext` contract used after played matches.

The existing `player_sporting_state` Saved Revision component already serializes
both sporting snapshots and completed-week contexts, so the evidence uses the
normal save/restore projection rather than a separate checkpoint format.

## Deliberate boundaries

This command does **not** decide or infer:

- tournament cancellation policy;
- Entry/WC eligibility;
- Final Commitment or Week Tournament Lock placement;
- ranking or development policy;
- Match Reconstruction probability/forcing rules;
- a missing Calendar as an empty Calendar.

A Calendar Event covering the week blocks the empty-week command even if no
MatchPackage or Simulation Slot has been created. This keeps absence of generated
execution rows from becoming false sporting truth.

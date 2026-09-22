# Authoritative Next Week v1

## Purpose

`Next Week` is the first canonical simulation range that crosses a publication
boundary. It means: **finish every remaining canonical competitive slot in the
current Ranking Week and, once every Week Transition prerequisite is satisfied,
publish the existing canonical Week Transition into the next Ranking Week**.

It does not call the legacy branch simulation wrapper and does not hide a Season
Transition behind a weekly action.

## Reviewed scope

`POST .../authoritative-simulation/next-week/preview` is read-only. The Admin supplies
one durable parent command ID plus an audit label/reason. The server freezes:

- current and target Ranking Week;
- every remaining V2 competitive Simulation Slot in the current week;
- the exact Week Schedule fingerprint;
- current Saved Revision and Position fingerprints;
- the Ranking Transition Authority required by the target week.

If that Ranking Transition Authority already exists, the preview binds to it. If it
is absent and can be canonically derived, the preview derives its exact candidate
without persisting it. The commit adopts that exact authority before sporting
execution begins.

## Operation-scoped prerequisites

The wider action inherits every prerequisite of its contained narrower operations.

Known blockers that cannot be solved by ordinary sporting progress fail the preview
closed. Entry/WC process slots are never skipped. A dirty Working Draft, stale Saved
Revision, missing lifecycle/ranking truth, unresolved Week Tournament Lock, missing
V2 chronology, or another non-derived transition prerequisite blocks the wider
action without disabling narrower valid actions.

Expected in-progress blockers such as unfinished matches, missing tournament closure,
missing terminal sporting evidence, or the not-yet-persisted derived Ranking
Transition Authority are allowed because the reviewed operation itself is responsible
for reaching those boundaries.

Week 61 is deliberately excluded. It hands control to canonical Season Transition.

## Durable execution

`POST .../authoritative-simulation/simulate-next-week` creates one parent receipt.

Every remaining competitive slot is executed through the existing authoritative
`Next Slot` command with a deterministic child command ID. Child payloads are
persisted before execution, so an interrupted week resumes without rerolling matches.

After sporting work closes, Position is inspected again:

- if Week Transition is ready, the server derives the exact existing
  `AuthoritativeWeekTransitionCommand`;
- the transition is previewed outside the parent write lock;
- its exact request and expected ranking/lifecycle/sporting fingerprints are persisted
  into the parent receipt;
- the existing atomic `AuthoritativeWeekTransitionRunner` performs publication.

The Next Week parent does not create a second ranking, lifecycle, sporting, or world
publisher.

## Progressive stop / resume

A wider operation can reach a legitimate prerequisite checkpoint only after some
children have committed. In that case the endpoint returns
`authoritative_week_progress.v1` with `status=blocked`, exact transition blockers
and the reached Position while leaving the parent receipt pending.

After the required explicit action is resolved, the Admin retries the same reviewed
parent command. Already committed sporting children are exact retries.

The same rule covers response loss after Week Transition itself committed: the child
transition receipt is replayed exactly and the pending Next Week parent is finalized
without a second world-clock advance.

## Admin UI

The canonical Simulation Admin panel exposes:

1. operator label + audit reason;
2. **Review authoritative Next Week**;
3. reviewed current→target week, remaining slots, authority mode/fingerprint and
   current in-progress blockers;
4. **Simulate reviewed authoritative Next Week**;
5. if paused, the exact blocker list and **Retry reviewed authoritative Next Week**.

The command ID is intentionally preserved across progress checkpoints and commit
errors. Discarding the review is explicit.

## Scope limits

- Week 61 uses Season Transition.
- `Next Season` and `Full Simulation` remain wider follow-up ranges.
- Canonical empty-week evidence remains an explicit audited operation; Next Week does
  not invent zero-match evidence.
- Future long-running job UX (live progress, safe stop, immediate pause) remains a
  separate execution-surface layer above this deterministic resumable kernel.

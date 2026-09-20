# Tour-entry lifecycle boundary sealing v1

Formal Tour entry may happen inside a FAX week, while
`PlayerLifecycleWeekState` remains immutable week-opening history.

This slice closes the boundary between those two truths.

## Canonical boundary

For an ordinary Week Transition from completed week **W** to opening week **W+1**:

1. start from the persisted opening lifecycle snapshot for W;
2. perform normal age/retirement and birth-week prospect advancement into W+1;
3. overlay only first Tour-entry triggers with `trigger_week <= W`;
4. persist that result as the immutable W+1 lifecycle snapshot.

A trigger occurring inside W+1 is deliberately excluded from the W+1 opening
snapshot. It remains a current-world overlay until the following boundary.

## Shared ranking truth

The exact same target lifecycle resolver now supplies:

- Ranking Transition Authority derivation;
- authoritative ranking command validation;
- ordinary Week Transition preflight;
- ordinary Week Transition lifecycle persistence;
- Season Transition Week 61 → next-season Week 1 lifecycle staging.

Season Closing Ranking also overlays Tour-entry triggers effective through completed
Week 61, so a player who formally entered during Week 61 is not lost at the closing
ranking boundary.

This keeps current-world immediacy, immutable historical opening snapshots and the
next Official Ranking snapshot consistent with Master Vision §9.2.

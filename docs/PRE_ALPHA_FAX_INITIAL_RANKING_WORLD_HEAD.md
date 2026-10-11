# Copied-FAX initial ranking and world-head bootstrap

## Purpose

Complete the persisted copied-FAX fixture with the existing canonical Week-1 Official Ranking publication boundary before Full Simulation begins.

## Sequence

After World Package, Calendar Package and InitialWorld are Saved, the materializer:

1. derives ranking policy/players from the Run-owned InitialWorld,
2. previews the existing `RankingBootstrapCommand`,
3. commits the exact reviewed Official Ranking candidate,
4. Saves ranking state through the ordinary Working Draft boundary,
5. publishes the initial ranking through `InitialOfficialRankingPublicationService`.

That publication creates the canonical `PublishedOfficialRanking` for Week 1 and `AuthoritativeWorldState(current_ordinal=0)`.

InitialWorld adoption already invokes lifecycle and sporting bootstrap, so this slice deliberately does not duplicate either subsystem.

## Acceptance significance

The copied-FAX fixture now has all opening Position ingredients owned by existing production boundaries: InitialWorld, lifecycle, sporting Week 1, saved ranking candidate, published Week-1 ranking and authoritative world clock head.

The next acceptance step is to rerun the real Full Simulation probe and follow its next reported Ranking/Entry/Draw/Schedule checkpoint.

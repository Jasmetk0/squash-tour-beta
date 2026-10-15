# Explicit next-season Calendar preparation handoff (Master v81)

## Scope

When a **current**, nonterminal Full Simulation server task is `awaiting_operator` with a canonical Week or Season preparation checkpoint, Task Center now provides a *navigation-only* link to that task's exact Run / Branch in Run Management. The target calendar season is derived from the actual canonical task `current_week.season_index` (e.g. index 1 -> `2001-2002`). URL identity is encoded and the existing Branch selector independently validates the requested Branch.

Run Management accepts only a valid consecutive `YYYY-YYYY` season within the product's 2000/01–2049/50 timeline, and only for the matching selected Branch. It preselects the existing **Calendar copy** interface and exposes the requested season. Merely following the link makes **no API mutation**. The operator must separately author a source Calendar if absent, Preview the copy, explicitly Confirm to the Working Draft, and manually Save the independent Run/Branch Saved Revision. The old Full Simulation server task is then separately inspected and explicitly resumed; no automatic retry or second parent is created.

## Verified fact versus diagnosis

The real sparse hybrid #1484 acceptance reached Season 2001/02 Week 1 and then `week_preparation_required`. That alone is **not proof** of which exact source/configuration is absent. Earlier production HTTP acceptance demonstrates that a new season's Calendar must be explicit, and an absent source must not be treated as an empty week. This handoff **does not** claim that copying a calendar alone resolves all sport, rankings, schedule, Entry/WC or lifecycle requirements. Task Center's actual persisted driver `progress.detail` and `progress.blockers` remain primary evidence.

## Acceptance and limitations

Focused mock HTTP component tests verify exact Run/Branch/year prefill, wrong-Branch/invalid-year rejection, read-only navigation, source-not-found failure without applying a copy, and correct gating to current blocked tasks. Existing Fast CI and real server-task Chromium acceptance must remain green on final PR HEAD.

**Not yet proven:** a newly authored 2001/02 Calendar with more than one real Tournament Edition, complete MatchEngine sports in that new season, Week 2 publication, and continuation on the same server task. Those require a separate real SQLite/Chromium positive acceptance with no dummy sports or hidden Save.

## Next implementation slice

Extend the real #1484 season-boundary browser scenario with exact persisted blocker capture first. Prepare *genuine* new-season Calendar source (rather than assuming empty weeks), explicitly copy/Save through existing Admin, create multiple real Tournament Editions and play their matches via existing authorities, then resume the same original server task to a concretely verified next Week. Preserve original historical rankings, replay identities and immutable Saved Revisions, and add negative tests for genuinely missing configuration.

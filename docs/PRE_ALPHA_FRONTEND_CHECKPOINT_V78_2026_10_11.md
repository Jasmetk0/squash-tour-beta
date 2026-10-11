# Pre-alpha frontend checkpoint v78 — 11 October 2026

Audited integration baseline: `buuk 55a2e415d5d76b27017c5667280c1d5a7647fc33`, merge #1373, tree `8771e464af245b5f49441bd459428d65c1823425`. This supersedes the v77 active findings, while preserving its dated evidence. Master v78 is target product authority; this checkpoint records code, integration and hosted-check boundaries.

## Review method and evidence

Read all eight PR patches, relevant actual buuk code, feature-head workflow runs, branch comparison and selected real-browser job logs. No fresh local runtime/full release run and no screenshot inspection were performed. Every returned workflow on the final feature heads below was completed/success; a workflow not triggered is not an additional passed test. See linked PRs for full histories.

| PR | Final feature HEAD | Hosted workflow run IDs | Actual integration |
|---|---|---|---|
| [#1367](https://github.com/Jasmetk0/squash-tour-beta/pull/1367) | `d5b203b964fe6513478dc3579ec5bff0d96ed722` | 38135866485, 38135866511 | Present in buuk |
| [#1368](https://github.com/Jasmetk0/squash-tour-beta/pull/1368) | `4938d1ce7d68b251db4870f78a3a4e38d273518f` | 38137276616, 38137276615, 38137276621 | Present in buuk |
| [#1369](https://github.com/Jasmetk0/squash-tour-beta/pull/1369) | `d01ead2b2aa7eea72105d96ef007c4bd2666208b` | 38138579969, 38138579974, 38138579980 | Present in buuk |
| [#1370](https://github.com/Jasmetk0/squash-tour-beta/pull/1370) | `af6c6ab1beecaa9f6202065ffc003f4711defa81` | 38141104864, 38141104815 | Present in buuk |
| [#1371](https://github.com/Jasmetk0/squash-tour-beta/pull/1371) | `efeca8059351c5907e792a89ced8893091fd369e` | 38142497178, 38142497136 | Present in buuk |
| [#1372](https://github.com/Jasmetk0/squash-tour-beta/pull/1372) | `069df75f96d2b27516e133ca8c5ded4ddc8005b3` | 38144743220, 38144743204, 38144743157 | Intermediate branch; restored by #1373 |
| [#1373](https://github.com/Jasmetk0/squash-tour-beta/pull/1373) | `093df0afce48dbd332eed436e11d2d5a9abef408` | 38145460588, 38145460576, 38145460572 | Present in buuk |
| [#1374](https://github.com/Jasmetk0/squash-tour-beta/pull/1374) | `368f7198a91775dc98c26b8a0f470e20eccffeec` | 38146337223, 38146337234 | Absent from audited buuk; merged into intermediate branch |

## What improved

- #1367: production data router/useBlocker protects links, imperative navigation and Back/Forward. Accepted-URL restoration and guarded invalid Branch selection address the previous deep-link findings. Global World Apply protects local edits and target context, retains a server draft, and offers explicit reopen/Save. Shell job 114459475738 reports `run_history_cancel_accept`, `global_apply_guard_and_draft_recovery` and no browser errors.
- #1368: `saved_players_inventory.py` reads selected Run/Branch immutable Saved Revision with pagination/filters and fail-closed identity checks. Legacy Explorer is separate. Profile Overview/Attributes/Career Results reuse existing saved ranking/match replay.
- #1369: one Players Generate route uses real Run-owned World/production InitialPool → InitialWorld preview, exact fingerprints and explicit adoption into a Working Draft followed by separate Save. Saved Replay job 114467483270 passed.
- #1370/#1371: saved-source country/region and first-week age conditions are binding; impossible combinations fail. Age-stage sampling is conditionally weighted and preserves the old path when no age bounds are specified.
- #1372/#1373: full-cohort statistics/table/filter/sort inspector now actually exists in buuk. Filters are display-only and do not alter adoption. Legacy source abilities are honestly labelled 1–99. Shell job 114487733211 and its Saved Replay workflow passed.
- #1374 feature code: preserves exact server-resolved whole players for one new-seed regeneration, verifies source seed/fingerprint and strips temporary locks before adoption. Tests include deterministic equality, same IDs/source fields, invalid IDs/seed/fingerprint and adoption without permanent locks. Saved Replay job 114490381878 passed. This remains feature-branch evidence.

## Findings and limitations

### F1 — integration blocker: merged #1374 is absent from buuk

#1374 targeted `fix/integrate-generated-player-review-buuk-20261011`, not buuk. #1373 merged into buuk at 15:36:24 UTC; #1374 merged into that intermediate branch at 15:36:34 UTC. Its merge is `73acefee89dccde3a20d247a7ef48eaae0fc3743`. Compare buuk → that merge reports diverged (ahead 13, behind 1), merge base `093df0afce48dbd332eed436e11d2d5a9abef408`, eight delta files. Current buuk preview request, InitialWorld panel and inspector have no Keep fields. Repair with a new integration PR against freshly verified buuk; use the exact verified delta, preserve later changes and test actual integrated behavior. Do not merge/reset the entire stale intermediate tree.

#1372 had the same base-branch problem and #1373 repaired it. Require base=buuk for ordinary slices, and confirm merged code/ancestry after the user's merge rather than trusting the merged badge.

### F2 — geographic semantics: Region and Travel Region are conflated

`admin_players.py:get_run_world_generation_options` builds one `regions` set from both `c.region` and `c.travel_region`. `run_world_initial_pool_preview_service.py` accepts a country when the chosen region equals either `country.region` or `country.effective_travel_region`. Distinct geographic layers can share a label and incorrectly include another country's travel-region match. Use an explicit typed condition or distinct selectors/predicates; maintain snapshot/replay compatibility. Regression must deliberately use a same-label cross-layer collision. No new travel mechanics are authorized.

### Bounded capability, not proof of completion

- Generator UI/adoption is first season 2000/01 only and 1–128, despite preview model accepting up to 2,000. FAX requires at least 1,000 opening players. Need the whole review/adopt/Save/restart path, not just a larger input max.
- #1374 supports one Keep pass only; repeated chains, field editing/locks and resumable exact proposals are not implemented.
- Whole-batch country/region/age conditions are not arbitrary groups, simultaneous partial constraints, exact quotas/remainder, presets or all-attribute solving.
- Players inventory is present-only. Current age and canonical current/Potential OVR are unavailable; all prospect-source records use one opt-in rather than complete reveal/birth/time classification. Full future-layer semantics and no-future-leak integration need a separate slice.
- Source 1–99 abilities do not complete the canonical 57 attributes/0–200 OVR or shared older-player development model. No numerical conversion should pretend otherwise.
- New country/population/rating/intake editors, rating interpolation runtime migration, Player/Hybrid schema and general append-to-existing-pool are still outside these PRs.
- These checks do not establish realism, 80 World Tour editions, 50-season continuity or pre-alpha release readiness.

## Next action

First integrate #1374 and fix geographic semantics as distinct coherent PRs. Next prove ≥1,000 first-cohort review/adoption/Save/restart with complete persisted readback and normal ranking/tournament continuity. Then build a versioned generation proposal/session for repeated Keep, individual editor/locks, exact saved proposals and the approved page layout, followed by explicit-total/group/quota/remainder rules. Implement temporary naming without touching old/imported identities. Continue World/future-profile editors afterwards. Refresh buuk/open PRs before every slice; user owns merge. Product decisions: Master §§9.4–9.6, 27.19–27.20, 31.32–31.33. Do not silently settle remaining OPEN mechanics.

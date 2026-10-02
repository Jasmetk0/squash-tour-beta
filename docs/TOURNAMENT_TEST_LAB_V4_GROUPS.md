# Global Tournament Test Lab V4 — groups and groups→knockout

V4 extends Tournament Test Lab over the existing group-stage and hybrid Tournament authorities.

## Shared authority path

Pure groups and groups→knockout use the production domain chain:

- `TournamentGroupRulesPolicy`;
- `TournamentFormatAuthority`;
- `TournamentTopologyAuthorityBuilder`;
- `TournamentGroupMatchScheduleBuilder`;
- production `MatchEngine.simulate`;
- `TournamentGroupStandingsBuilder`;
- for hybrid formats, `TournamentHybridKnockoutEntrantsBuilder`;
- for hybrid formats, `TournamentHybridKnockoutBracketBuilder`.

The Lab does not invent a second group draw, schedule, standings table or hybrid crossing engine.

## Scenario contract

Group-based Tournament Lab scenarios explicitly carry:

- `group_count` and `group_size`;
- `seeded_slots_per_group`;
- exact `group_seed_placements`;
- explicit group BO3/BO5;
- deterministic `topology_seed`;
- for groups→knockout, `advancing_per_group` and exact `knockout_crossings`.

The existing `seed_order_player_ids` remains the frozen participant order. Group seed placement is
explicit because the Master does not define one universal automatic seed-layer rule for every
group format.

Group formats currently require one fully resolved participant field: no Qualification/WC/BYE
reservations are silently folded into groups.

## Group execution

The Lab builds immutable group topology from the frozen field and format, then materializes the
canonical round-robin Match Day schedule.

Every scheduled match runs through the production Match Engine. Completed receipts feed directly
into `TournamentGroupStandingsBuilder`, so group points and tie-break behavior are exactly the same
authority used by normal tournament execution.

If the production standings authority reaches a tie that requires explicit Admin resolution, the
Lab fails closed for that batch run with `GROUP_STANDINGS_UNRESOLVED_TIE`. It does not fall back to
player ID, random order, Ranking or Race.

Likewise, a group result whose table effect is still unresolved in the Master (for example a RET
case not covered by decided group scoring) produces `GROUP_STANDINGS_RESULT_UNSUPPORTED` rather
than fabricating table points.

## Pure groups

For `format_kind=groups`, final group standings complete the Lab tournament run. There is no
fabricated global champion. A champion assertion is therefore `not_evaluated`; ordinary
played-match assertions still run.

## Groups→knockout

For `format_kind=groups_knockout`:

1. all groups complete;
2. final standings freeze group positions;
3. `TournamentHybridKnockoutEntrantsBuilder` resolves the exact configured crossings;
4. `TournamentHybridKnockoutBracketBuilder` creates the standard winner-feeder elimination tree;
5. every knockout match runs through the same production Match Engine.

There is no Ranking/Race reseeding between groups and knockout.

`stop_after_round` applies to the hybrid knockout stage after the group stage is fully resolved.
Stopping early never fabricates a champion.

## Built-in baselines

V4 adds:

- `two-groups-of-four`: two four-player round-robin groups;
- `two-groups-to-four-player-knockout`: the same group field with two advancers per group and
  explicit A1-vs-B2 / B1-vs-A2 first-round crossings.

The crossing definition is stored as scenario data, not promoted into a universal automatic rule.

## Remaining Tournament Lab work

Still open:

- explicit scenario import/export UX;
- Run → Lab historical tournament copy;
- Lab → Run compatibility-preview draft bridge;
- withdrawals, WC/LL and replacement windows;
- tournament ranking consequences / close effects;
- any future group rules not yet decided in the Master.

Copied-FAX full-season acceptance remains a separate later track.

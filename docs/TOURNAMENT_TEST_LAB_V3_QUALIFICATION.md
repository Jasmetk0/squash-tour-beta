# Global Tournament Test Lab V3 — canonical Qualification progression

V3 extends the persistent Tournament Test Lab with real canonical Qualification topology and progression.

## Shared authority path

Qualification uses the same production authorities as a normal tournament:

- `TournamentEntryFieldCapacity`;
- `canonical_classic_seed_count`;
- `canonical_qualification_seed_count`;
- `TournamentDrawInputAuthority`;
- `TournamentDrawAuthorityBuilder(idealized_seed_tiers.v2)`;
- production `MatchEngine.simulate`.

The Lab does not create a second Qualification draw algorithm.

## Scenario additions

A `tournament_test_lab_scenario.v1` may now optionally include:

- `qualification_draw_size`;
- `qualifier_spots`;
- `qualification_player_ids`.

When those fields are absent/empty they are excluded from serialization, preserving the exact
fingerprint shape of older no-Qualification Tournament Lab scenarios and persisted V2 sessions.

The complete participant list remains the portable player-data envelope. `qualification_player_ids`
partitions that list into Qualification and direct-Main entrants. `seed_order_player_ids` remains
the single frozen ordering source; direct Main and Qualification seed pools are derived from it.

## Validation

Structured diagnostics fail closed for:

- incomplete Qualification geometry;
- unequal Q section geometry;
- non-power-of-two Q section capacity;
- duplicate Qualification players;
- Qualification players outside the participant field;
- too few players to resolve every Q section;
- Qualification field exceeding configured capacity;
- direct Main + qualifier places exceeding Main Draw capacity.

No invalid Qualification draft receives a fabricated draw/result.

## Progression

The canonical Draw authority materializes equal Q sections `Q1…Qn` plus matching Main Draw
qualifier placeholders.

For each batch run:

1. every Qualification section is played to completion;
2. its winner is frozen for that run as the section winner;
3. `Q1…Qn` winners are resolved into the exact canonical Main Draw placeholder slots;
4. the Main Draw then runs with the same Match Engine kernel.

The report stores per-section winner, played-match count, BYE advances and detailed match results.
Tournament-level played-match and BYE counts include both Qualification and Main Draw.

`stop_after_round` remains a Main Draw stepping boundary in V3. Qualification is fully resolved first,
because the Main Draw cannot legitimately start before qualifier identities exist.

## Built-in baseline

`qualification-two-sections-to-eight-main` provides a deterministic baseline with:

- 8-player Main Draw;
- 2 qualifier places;
- 8-player Qualification field;
- two equal 4-player Q sections;
- six direct Main entrants;
- expected total of 13 played matches.

## Remaining Tournament Lab work

Still open:

- explicit scenario import/export UX;
- Run → Lab historical tournament copy;
- Lab → Run compatibility-preview draft bridge;
- groups and groups+knockout;
- withdrawals, WC/LL and replacement windows;
- ranking consequences and tournament-close effects.

The copied-FAX full-season acceptance track remains separate.

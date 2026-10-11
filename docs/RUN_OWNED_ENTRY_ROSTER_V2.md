# Run-owned Entry roster projection v2

## Purpose

Authoritative simulation must not depend on the mutable global
`config/simulation/season_active_players.json` registry.

The Entry subsystem and the remaining legacy tournament-award compatibility builder
still consume the old `SeasonActivePlayer` DTO. This document defines the read-only
adapter that projects current Run/Branch-owned player truth into that DTO without
making the DTO authoritative.

## Authoritative inputs

For one `Run / Branch / RankingWeek`, the projection reads:

1. **Player lifecycle week state**
   - decides which identities are active;
   - owns current age, birth identity, retirement state and Tour-entry identity.
2. **Player sporting week state**
   - owns the current canonical 57 attributes;
   - owns current/potential sporting ability and development timing.
3. **InitialWorld**
   - supplies stable display/country/career metadata for original players.
4. **RunProspect metadata**
   - supplies stable identity/display/country/profile provenance for later generated
     prospects;
   - its persisted canonical sporting profile must validate before projection.
5. **Published Official Ranking for the same week**, when present
   - supplies current ranking points used by the legacy Entry ordering contract.

The projection never reads or writes `season_active_players.json`.

## Current-player compatibility projection

The old Entry engine accepts seven `1..99` attributes while authoritative sporting
state stores 57 `0..200` attributes. V2 therefore uses one explicit technical
compatibility policy: `run-owned-entry-roster-projection.v2`.

The adapter derives:

- technique from the mean Technical group;
- movement from the mean Move group;
- physical from the mean Physical group;
- mental from the mean Mental group;
- consistency from canonical Consistency;
- clutch from Composure + Confidence + Toughness;
- recovery from Endurance + Durability.

Every value is scaled deterministically from `0..200` to `1..99`.

This is **not** a second sporting model. The 57-attribute state remains authoritative.
The seven values exist only so still-legacy consumers can run while migration
continues.

Original InitialWorld players retain their stable display identity, nationality,
play-style/archetype labels and hidden career traits, but their current ability and
seven compatibility attributes are rebuilt from the current sporting snapshot. Entry
AI therefore no longer sees frozen season-2000 ability after players develop.

## Prospect projection

An active lifecycle/sporting identity that is not in InitialWorld must resolve to one
RunProspect row.

The adapter fails closed unless:

- Run/prospect identity exists;
- prospect birth identity matches lifecycle;
- persisted canonical prospect sporting profile validates across profile/development/
  potential evidence.

Prospects use `source_generation=annual_intake`.

Prospect trait JSON is still deliberately unresolved product scope. For the legacy
Entry AI only, v2 derives deterministic `0..1` compatibility trait values from the
already-owned immutable `trait_seed`. These values are versioned adapter input and
must not be interpreted as finalized player-career canon.

## Consumers migrated in this slice

### Authoritative Entry decision flow

Both Entry modes consume the Run-owned roster:

- deterministic AI Entry preview/commit;
- explicit Admin-reviewed Main/Qualification Entry decision slots.

Both produce the same `RunEntryDecisionSlotAuthority` downstream.

### Legacy-topology authoritative tournament close

The legacy result/award compatibility builder can receive an explicit
Run-owned active-player service. The authoritative simulation driver always supplies
it, so legacy-topology tournament close no longer needs the global active-player
registry.

Canonical Draw tournament close already uses Run-owned canonical result/award
authorities and does not need this compatibility layer.

## Audit surface

`GET /admin/runs/{run}/branches/{branch}/authoritative-simulation/entry-roster`

returns the current projected roster and summary for inspection. It is read-only.

## Deliberate boundaries

This slice does not:

- make `SeasonActivePlayer` canonical;
- finalize prospect hidden-trait product rules;
- define Race points as a canonical player-state aggregate;
- replace every legacy non-authoritative screen/service that may still read the old
  active-player registry;
- change the canonical 57-attribute sporting model.

Future migration should remove consumers from this compatibility DTO rather than grow
it into a second player authority.

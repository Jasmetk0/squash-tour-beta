# Empty Run standalone match acceptance v1

This slice implements only the second mandatory pre-alpha acceptance flow already
decided in Master Vision §31.3 / PAQ-003 and PAQ-005:

> empty Run -> manually add two players -> add one match -> simulate it safely
> without requiring a Calendar.

## Scope

The flow is deliberately operation-scoped. It requires only a writable product
Run/Branch plus exactly two complete manual player payloads. It does **not** create or
require:

- World Package attachment;
- Calendar or Tournament Edition;
- Tournament Ranking Snapshot, Entry Field or Wild Card authority;
- Draw Input, Draw authority or Week Simulation Schedule;
- Official Ranking publication or Week Transition.

Before simulation, the two players live in a small Run/Branch-owned authoring
workspace. The workspace accepts at most two players, requires explicit stable
player IDs and reuses the existing validated manual-player payload rather than
inventing a second player schema.

## Atomic sporting freeze and match commit

StandaloneMatchService.simulate(...) owns one BEGIN IMMEDIATE transaction.

At commit it:

1. revalidates writable Run/Branch scope and the reviewed workspace fingerprint;
2. fails closed if InitialWorld, Simulation Slots, Tournament authority or a Week
   Simulation Schedule already occupies the scope;
3. freezes the two reviewed players into a Run/Branch-owned InitialWorldState with
   manual_standalone.v1 provenance;
4. bootstraps canonical Week-1 lifecycle and 57-attribute sporting truth through the
   same existing lifecycle/sporting adapters used by the ordinary canonical flow;
5. creates exactly one canonical global Simulation Slot with one direct-player match;
6. executes that match through AuthoritativeSlotMatchExecutor and the normal Match
   Engine/effects path;
7. removes the mutable authoring workspace only after the canonical match commit;
8. persists an exact command receipt so identical retry returns the same result and a
   conflicting reuse of command_id fails closed.

The standalone match therefore shares canonical Match Engine input protection,
result/effect fingerprints and terminal sporting checkpoints with normal authoritative
match execution. It does not create fake tournament containers merely to satisfy an
API prerequisite.

## Save/load boundary

After the match commits, the normal authoritative simulation Save captures the
resulting InitialWorld, lifecycle state, sporting state, Simulation Slot/group and
command receipt into the Saved Revision. No standalone-only sporting history format is
introduced.

The pre-match authoring workspace is intentionally transient in this minimum slice; the
required acceptance contract is safe save/load of the completed standalone match.
Persisting a partially authored two-player workspace as user-visible Saved Revision
content is not claimed here.

## Acceptance coverage

tests/application/test_standalone_match_acceptance.py is pr_critical and proves:

- a canonical empty product Run can host the flow while still in working status;
- exactly two manual players are reviewed before execution;
- one standalone competitive match completes and exact retry is idempotent;
- InitialWorld, lifecycle, sporting state, one Simulation Slot and one match group are
  created;
- Tournament/Entry/WC/Draw/Week-schedule authority counts remain zero;
- the completed state is accepted by the existing authoritative simulation Save and
  all canonical sporting components are present in the resulting Saved Revision.

## Deliberately not inferred

This slice does not decide any still-open global Start gate, Package requirement,
Calendar design, tournament policy, AI entry behavior, automatic player generation,
ranking policy, or broader standalone multi-match workflow. It is the minimum
operation-scoped proof required by Master §31.3.

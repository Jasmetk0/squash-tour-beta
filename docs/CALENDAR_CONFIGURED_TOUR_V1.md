# Configured native Tour integration (candidate, Master v85)

Base: owner-merged #1540, `44c782870391d45d39b05cf00fa1edd6e938e6a6`.
This is an implementation contract, not a change to the Master or release acceptance.
Verification evidence below must be completed before a merge-ready handoff.

## Authority map

| Concern | Existing authority / integration |
| --- | --- |
| Run/Branch, HEAD, Saved Revision, recovery | `SimulationPersistenceRepository`, ordinary immutable revision Save and restore coverage |
| Run time | `RunCalendar` / `RunWeekPosition`; native sporting checkpoint and coupled Tour clock; no `RankingWeek` cast |
| Edition/configuration | Run/Branch-owned `CalendarTourState` component and SQLite row; frozen `CalendarTourEdition` before Entry/draw/play |
| Entries / first formal entry | Production `TournamentApplicationSubmissionStore`, batch writer and first-entry triggers; explicit native v2 dates |
| Approved field / draw | Existing `TournamentEntryFieldResolver`, `TournamentDrawInputAuthorityBuilder`, `TournamentDrawAuthorityBuilder` with frozen native ranking binding v2 |
| Matches / player state | Existing winner-fed followup executor, injected RNG, actual MatchEngine; explicit configured event v5 and full-population checkpoint v9 |
| Lifecycle | Existing `PlayerLifecycleWeekStateModel` and Saved lifecycle component: unchanged native bootstrap v2 followed by consecutive native v3 snapshots |
| Results / points | Actual match placements and frozen Edition point table/validity, independently confirmed before activation |
| Ranking | Existing W-aware Official ranking calculator; Tour transition owns historical policy, sources and publication snapshots |
| Public events | Transition-owned announcement and publication records; Saved-only Viewer API with historical filtering |

The legacy fixed-calendar Edition/Entry/ranking stack remains supported. New native
Entry and ranking bindings are explicit versions of its existing contracts. The
adapter does not insert native dates into legacy ordinal columns. Historical
exhibitions stay exhibitions and never acquire a configured Edition identity.
The broader Category/Series/Edition Plan package hierarchy, all formats and general
scheduler remain incomplete; this does not claim that entire Master subsystem.

## Supported production path

On an editable local Run with Saved v2 population, native fresh/recovered Health,
opening full-population sporting owner and sporting Week 2 or later, open Admin
Tour → Editions. Initialize the Tour owner, then manually Save. Initialization
materializes factual lifecycle history from the original Saved birth identities;
it creates no retrospective tournament results or first Tour entries.

Create future Editions with native dates, explicit announcement, chronological
slots, full field size, point table and validity. The schema supports general
sizes through 128; this executor supports full main-only 4/8-player knockouts.
The Admin offers those supported sizes. Announcement becomes public only through
its actual Week Transition and must precede operations by a complete week.

Submit validated applications through the production writer, Save, approve the
canonical field, Save, build the seeded canonical draw, Save, play the actual
MatchEngine tournament, Save, independently confirm results, and Save again.
Every new operation reviews exact HEAD, sporting and Tour inputs and requires
explicit consent. There is no automatic Save. The last match feeds its actual
winner into subsequent rounds. Original rally logs, projected 57-attribute sources
and actual terminal player effects remain authoritative and replayable.

Each Edition freezes point values and validity before play. Ranking sources bind
Edition/field/draw/played-event/award hashes; a subsequent policy or another
Edition's table cannot rewrite an earlier award. Only independently confirmed
configured results can activate. Prepared exhibition awards cannot enter this path.

## Week Transition and publication

Preflight requires a Saved predecessor, all due Editions terminal, chronological
slots, coherent Health/lifecycle/source ownership and supported scope. It stages:
completed-week development using 1/W and that week's policy; weekly form/load
recovery; target policy activation; actual birthdays/retirement/first Entry;
result activation/expiry and Best N; one Official ranking calculation; public
announcements/publication; final validation and one SQLite commit. Retired players
retain their stored sporting state. Development never reads planned next-week
matches. A target-week ranking policy applies immediately; a target-week
change to development first governs that week's later completed-week update.

Working publication remains a candidate until an independent manual Save signs
the coupled sporting, lifecycle, Tour, Entry and ranking data. Viewer reads the
selected Viewer Branch's Saved revision, never the current working candidate.
The historical API refuses ungenerated future weeks and hides unannounced plans.

No silent unsupported steps: season rollover, unresolved numeric Health/healing,
owned Run prospects needing native calendar materialization, and due staged
external correction/disciplinary sources block with concrete reasons. The bounded
path consumes the existing owned population and has no new prospect source. This
is not full demographic intake, Financial Level, general medical progression,
Season Transition or Full Simulation completion. These remain pre-alpha work;
adding their required authority must not be replaced by a successful no-op.

## Integrity and recovery

All command writes, including nested MatchEngine results and lifecycle/Entry
writers, share one `BEGIN IMMEDIATE` transaction. A late failure rolls back the
whole transition. Exact retry authenticates current owners and returns the
original receipt; same ID with another payload/confirmation conflicts. New stale
HEAD or changed input invalidates preview consent. UI epochs cover Run/Branch/HEAD
changes, input changes, delayed responses and A→B→A switching.

Save uses the existing immutable revision boundary and restore coordinator.
Lifecycle and Tour components participate in capture and restore; pre-play Saved
draw origins must belong to the reachable selected timeline. Existing protected
Run and unsupported match-fork guards remain. Old v1–v8 sporting schemas and v1
Entry/ranking bindings preserve their original serialization and hashes.

Performance work is bounded: one shared result provenance hash per derivation;
exact original-match/component/prefix proofs reused only inside one lineage walk;
batched intermediate tournament states strictly validated before the final write.
Raw revision bytes, hash, scope, ancestry, source fold and live owner checks remain.
No runtime HTTP timeout is increased and no SQL/hash repair is part of acceptance.

## Verification status

Candidate tests: native date/version/expiry contracts, canonical field/draw rebuild,
source ownership, immutable policy, W52/FAX W61/W80 birthdays/retirement, unchanged
historical hashes, one-walk proof isolation, UI consent/late responses, real
HTTP/SQLite two-tournament flow with policy activation, late rollback, exact retry,
restart and bidirectional restore. The dedicated Chromium acceptance drives every
new Tour mutation through Admin and physically restarts the backend between two
real tournaments. CI matrix includes W52, FAX W61 offset 37 and W80/1,000 players.

Actual final-head results and measured timings are still pending. Mocked component
tests are not browser evidence. No full pre-alpha release acceptance is implied.

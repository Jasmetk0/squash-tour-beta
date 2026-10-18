# Saved native eight-player knockout — first playable 8-draw vertical slice

Based on merged #1536 and current Master v85. This **does not** grant official Tour, Entry, Ranking, public time, Season Transition or Full Simulation capability.

## Actual play

Existing four-player `/calendar-continuation/knockouts/simulate` and point-prepared `/simulate-scored` are unchanged in command, schema and historical bytes.

New `POST /calendar-continuation/knockouts/simulate-eight` accepts an exact Signed Saved HEAD, checkpoint fingerprint, a full list of eight **distinct existing** population player IDs in seed/draw-position order, a deterministic seed, command/tournament identity and operator audit reason. It requires at least one manually Saved sporting advance to Week 2 or later and an unchanged, fully authenticated full-population 57-attribute owner.

One SQLite `BEGIN IMMEDIATE` transaction plays seven **actual** MatchEngine matches. Bracket order:
1. qf1 positions 1–2, qf2 3–4, qf3 5–6, qf4 7–8.
2. sf1 winners qf1/qf2 and sf2 winners qf3/qf4.
3. final winners sf1/sf2.

Every match consumes the current stored records, projects the same 57 canonical attributes and Form/sharpness/fatigue into the existing MatchEngine, and writes authoritative rally, timeline, stamina, projection and frozen-Health evidence. Previous semifinal/quarterfinal effects are retained for later games involving the winner. Other population records stay unchanged. These matches are explicitly sequential, one after another within one operator-created event, rather than a claim of concurrent Simulation Slot execution or a real Tour timetable.

`calendar_followup_knockout.v3` holds eight entrants, seven ordered nested continuation v2 matches and frozen source/identity/fingerprint. Its reconstructed round wiring must use actual winners. The complete population owner upgrades to `calendar_sporting_checkpoint.v6`. Historical knockout v1/v2 and checkpoint v1–v5 **retain their exact serialization and hashes**. Only the new event enables v6.

The operation either persists all seven matches and terminal player states together or rolls back. Exact retries reconstruct the original receipt after other Saved operations. A distinct command or changed source must fail closed. The new owner requires a **separate manual Save**, after which a following match/tournament or sporting advance is allowed. This same Saved lineage supports cold restart, exact replay of each nested match, backward/forward restore, horizon extension and weekly fatigue/development; next week's played counts include all **14 player participations**.

## User experience

Admin CS/EN adds an independent 8-position bracket selector, explicit consent for seven real matches and saved tournament history showing field size and winner. Its existing Save review and replay links work with the seven match records. Client checks frozen source/HEAD, all 8 positions, seven match IDs/sequences and winner-fed semifinal/final pairing. It rejects forged Official publications or scored labels. The existing 4-person and prepared-point controls remain usable.

## Intentionally not implemented

Eight-player events are **unscored exhibitions** in v3. Four-player operator-prepared awards remain under historical v2. Eight-player configured point distributions, canonical Edition/Entry/Draw sources, Official Ranking, lifecycle/Health healing, simultaneous tournament scheduling and true Week/Season Transition are still outstanding. Protected World/Package sources are never mutated. Match-containing cross-Branch fork retains its existing guard.

## Verification scope

Focused W52/W80 production HTTP/SQLite tests cover 7 actual MatchEngine results, complete winner-fed bracket, nested replay, tamper rejection even with recomputed outer component fingerprints, exact retries, no partial writes, manual Saved v6, weekly 14 participations, cold restart and backward/forward restore. Frontend source/lineage and component tests cover independent consent and Save boundary. Relevant Fast CI and browser workflows should be verified on the final PR head before merging; user may explicitly defer those checks, but the PR is not labelled verified until they pass.

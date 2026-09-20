# Ranking completion evidence

Status after the owned tournament-source bridge. Rankings are **not
complete**. This is an implementation checklist, not a new product contract. Master
v64 and subsequent explicit decisions remain authoritative; open product questions
must not receive invented defaults.

| Area | Implemented evidence | Remaining integration |
| --- | --- | --- |
| Official calculation | `domain/rankings/official.py`: Best N, Q/main result components, expiry, lifecycle eligibility, tie-breaks, deterministic immutable candidates | Full discipline and authoritative roster/token lifecycle |
| Historical inputs | Stored result versions, corrections, receipts, complete input manifests, and immutable Run/Branch-owned snapshots for supported completed main draws | Full branch ancestry and identity remapping; Q/WC/LL and abnormal sources remain guarded |
| Preparation commands | Audited API supports explicit adoption of a fingerprint-bound persisted main-draw result/award package in the same transaction as ranking preparation, plus real preview and guarded confirmation | Authoritative world roster/policy resolution, full-world Week/Season Transition and publication |
| Inspection | Admin candidate, source and input APIs/UI, with verified equal-point tie explanations and historical zero decision evidence | Public historically faithful Viewer ranking path |
| Recovery | Versioned bundles include owned tournament evidence, Closing Ranking archives via `ranking_revision_state.v6`, ordinary Season Transition World Events via `ranking_revision_state.v7`, independent explicit Save, reload and guarded saved-component restore | Complete sporting-world snapshot/recovery and ranking-bearing forks |
| Season Closing Ranking | `season_closing_ranking.v1` calculates the archived Week-61 snapshot under the outgoing policy; seasons 0–48 persist Week-61 sources against next Season Week 1, while 2049/50 uses Closing-only owned source v6 with a post-final boundary ordinal and no fictional Week 1. Final 2049/50 has an atomic closure command. Ordinary rollover has `season_transition_configuration.v1`, cross-season sporting/lifecycle/Week-1 Ranking staging and an atomic Saved-Revision-backed commit writer: W61 Closing Ranking + closure package, W1 sporting/lifecycle/Official Ranking, publication, world-head advancement and season-transition event commit together or roll back together; preflight also fingerprints the read-only Closing Ranking candidate. Target-week prospects still fail closed, and non-empty future reset catalogs require a real adapter | Register future authoritative season-scoped statistic components and implement the prospect/Tour-entry canonical sporting-profile bridge; implement the prospect activation/canonical player-state bridge; prospect-free ordinary rollover already has reviewed Admin execution |
| Disciplinary changes | Versioned zero decisions resolve by week, reserve Best N slots, expire independently and survive Save/Restore | Automatic sanction issuance policy and point deductions; exact tariff/duration calibration must remain explicit |
| Protected Ranking | Master 18.4 defines a separate entry value and versioned case policy | Verify/implement policy snapshots, absence, activation/use and entry integration; unresolved seeding/LL questions are not implicit defaults |
| Race and downstream consumers | Legacy paths exist but are not proof of completion of the new Official path | Audit and integrate Race, Finals qualification, entries and seeds with authoritative historical snapshots |

Completion requires a tested user flow through preparation, Save, actual transition,
public historical ranking, downstream consumers and recovery, including expiry,
corrections, season boundaries and supported discipline/lifecycle scenarios. Pure
calculation tests or a green PR alone do not establish this. A complete user-facing
explanation of the final rules should be written from the finished implementation,
with explicit distinctions for features intentionally deferred or still undecided.

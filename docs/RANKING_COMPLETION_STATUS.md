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
| Recovery | Versioned bundles include owned tournament evidence, Closing Ranking archives via `ranking_revision_state.v6`, independent explicit Save, reload and guarded saved-component restore | Complete sporting-world snapshot/recovery and ranking-bearing forks |
| Season Closing Ranking | `season_closing_ranking.v1` calculates the archived Week-61 snapshot under the outgoing policy; ordinary-season resolver/staging derives it from canonical Week-61 state and `ranking_revision_state.v6` preserves/restores the archive against its exact publication | Closure marker/season summary, full atomic Season Transition and the dedicated final-season source adapter; final season must not create Week 1 of season 51 |
| Disciplinary changes | Versioned zero decisions resolve by week, reserve Best N slots, expire independently and survive Save/Restore | Automatic sanction issuance policy and point deductions; exact tariff/duration calibration must remain explicit |
| Protected Ranking | Master 18.4 defines a separate entry value and versioned case policy | Verify/implement policy snapshots, absence, activation/use and entry integration; unresolved seeding/LL questions are not implicit defaults |
| Race and downstream consumers | Legacy paths exist but are not proof of completion of the new Official path | Audit and integrate Race, Finals qualification, entries and seeds with authoritative historical snapshots |

Completion requires a tested user flow through preparation, Save, actual transition,
public historical ranking, downstream consumers and recovery, including expiry,
corrections, season boundaries and supported discipline/lifecycle scenarios. Pure
calculation tests or a green PR alone do not establish this. A complete user-facing
explanation of the final rules should be written from the finished implementation,
with explicit distinctions for features intentionally deferred or still undecided.

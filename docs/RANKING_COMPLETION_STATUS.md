# Ranking completion evidence

Status after audited Admin preparation API (follow-up to #717). Rankings are **not
complete**. This is an implementation checklist, not a new product contract. Master
v64 and subsequent explicit decisions remain authoritative; open product questions
must not receive invented defaults.

| Area | Implemented evidence | Remaining integration |
| --- | --- | --- |
| Official calculation | `domain/rankings/official.py`: Best N, Q/main result components, expiry, lifecycle eligibility, tie-breaks, deterministic immutable candidates | Full discipline and authoritative roster/token lifecycle |
| Historical inputs | Stored result versions, corrections, receipts and complete input manifests | Full branch ancestry and identity remapping |
| Preparation commands | Audited Admin bootstrap/weekly API and atomic internal tournament/result/zero batches | Preparation form, scoped tournament-source adapter, full-world Week/Season Transition and publication |
| Inspection | Admin candidate, source and input APIs/UI, with verified equal-point tie explanations and historical zero decision evidence | Public historically faithful Viewer ranking path |
| Recovery | Versioned bundles, Save capture, independent explicit Save, guarded saved-component restore | Complete sporting-world snapshot/recovery and ranking-bearing forks |
| Season Closing Ranking | Master 18.5.1 requires a separate archived closing ranking including Week 61 under outgoing policy | Dedicated calculation, persistence, closure marker and season summary; final season must not create Week 1 of season 51 |
| Disciplinary changes | Versioned zero decisions resolve by week, reserve Best N slots, expire independently and survive Save/Restore | Sanction issuance/editor and point deductions; exact tariff/duration calibration must remain explicit |
| Protected Ranking | Master 18.4 defines a separate entry value and versioned case policy | Verify/implement policy snapshots, absence, activation/use and entry integration; unresolved seeding/LL questions are not implicit defaults |
| Race and downstream consumers | Legacy paths exist but are not proof of completion of the new Official path | Audit and integrate Race, Finals qualification, entries and seeds with authoritative historical snapshots |

Completion requires a tested user flow through preparation, Save, actual transition,
public historical ranking, downstream consumers and recovery, including expiry,
corrections, season boundaries and supported discipline/lifecycle scenarios. Pure
calculation tests or a green PR alone do not establish this. A complete user-facing
explanation of the final rules should be written from the finished implementation,
with explicit distinctions for features intentionally deferred or still undecided.

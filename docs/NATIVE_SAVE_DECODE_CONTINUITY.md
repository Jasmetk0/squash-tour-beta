# Native checkpoint decoding after manual Save

## Problem and implementation

Merged baseline `fbe8e00c346b1de6de6d3144509a92592dec38d0` contains #1657.
Its native command reader retains strict v13 checkpoint decode data by complete
actual component plus Run/Branch. The successful Save coordinator only primed
its older whole-Saved-payload DTO key. Consequently the very first native read
after a committed sporting change still structurally parsed the checkpoint.
A real HTTP/SQLite regression test reproduced that miss on the merged baseline.
The normal `save_tour` test helper cannot detect it because its trailing GET
warms the component cache itself; the new case deliberately inspects immediately
after the actual POST acknowledgement.

After the original successful transaction exit, committed-append proof and
whole-payload DTO handoff, the coordinator also primes the existing component
representation from the same strictly captured models. It uses the existing
complete-value fingerprint check, Run/Branch binding, defensive copies and
shared 64 MiB/four-entry ceiling. Oversize whole-payload data may be bypassed or
evicted while a fitting checkpoint is retained. Oversize checkpoint behavior
remains ordinary strict decoding; no retention is promised beyond the budget.
Legacy/non-v13 handling remains on its original route.

This is decode data only. Nothing runs before commit and no physical, owner,
ancestry, dependency, sporting math or post-write verification is replaced.
Manual Save, audit, immutable revision hashes, command receipts and all sporting
outcomes keep their existing contracts. No cache size, schema, CI selection
exception, scenario size or acceptance timeout is introduced.

## Verification

The new genuine HTTP/SQLite test captures an actual MatchEngine change and POSTs
manual Save. It forbids structural decoding on the immediate next component
read, compares the entire returned model with the actual persisted state and
checks nested/caller isolation. A second case lowers the shared budget so the
whole Saved envelope cannot fit but its checkpoint can; retention must remain
within that same byte limit. The existing adversarial append/ancestor case also
checks that a rejected late-write Save does not publish its uncommitted
checkpoint to this handoff. Existing complete captured-DTO reuse, stale/retry,
rollback, rehashed-source and metadata checks remain.

The original baseline failed the immediate-read guard. Focused tests and hosted
acceptance on the final PR commit are recorded in the PR; no mocked UI test or
skipped Draft job is presented as production integration. This change makes no
percentage speed claim and does not certify full pre-alpha/50-season release.

# Native sporting PR audit — 18 October 2026

Review scope: every new PR since #1532, namely #1533–1539, all already merged
by the owner. Repair base: `4df7580c5548fbb27b0f7ee1a28ce6b3af5f71bd` (`buuk`).
Master remains v85. This is correctness/verification work, not new product policy.

## Reviewed changes and original checks

| PR | Runtime change | Original final-head workflow evidence |
| --- | --- | --- |
| #1533 | Reuse validated ancestry inside one Save/review transaction | [Fast CI green](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/39117378034) |
| #1534 | Three-match four-player later-week knockout | Nine workflows green; [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/39119185007) |
| #1535 | Logged match winners follow scored sets / retirement | [Fast CI green](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/39120713605) |
| #1536 | Four-player prepared awards | Nine workflows green; [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/39122141534) |
| #1537 | Seven-match eight-player knockout | Nine workflows green; [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/39123570024) |
| #1538 | Eight-player prepared awards | Eight browser workflows green; [Fast CI failed](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/39127751386) |
| #1539 | Signed per-player native result closure; validation performance | Eight browser workflows green; [Fast CI](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/39132765526) was still running at audit start |

#1538's failed backend job `117676449651` reached the final W52 historical
restore, then exceeded the real HTTP client's 120-second request timeout.
Its test ran 1376.23 seconds. This was a recovery latency failure, not a
failed point-value assertion. #1539 removes redundant validation, but its
PR-selected tests do not include #1538's scored-eight module; both modules
need explicit post-merge regression execution.

## Repairs

1. **Exact standalone retry after closure:** reconstruction previously folded
   weeks and matches but omitted closures. A valid later match therefore failed
   its predecessor fingerprint on retry. Apply closures at their original
   `source_week_event_count` before consuming later events; return the original
   match receipt, not a later checkpoint.
2. **Command identity collision:** a new tournament root could generate a nested
   command ID already used by a closure. Reserve every prior sporting command
   before MatchEngine work and enforce closure uniqueness in the pure reducers.
   Reject wrong-W prepared policy before playing as well.
3. **Client bracket authority:** the four-player guard accepted a swapped finalist
   and semifinalist when stage counts/point values still matched. Both bracket
   sizes now derive each placement from participant-valid, ordered winner-fed
   matches. Inspection applies the same checks before showing prepared awards.
4. **Closure availability:** a previous scored tournament remained actionable
   after a later exhibition/week even though the server rejects that action.
   Offer closure only while it is the latest sporting event in its played week.

## Verification and limits

The four-player client regressions were reproduced red before the repair:
swapped finalist awards and a non-participant semifinal winner both passed
the former guard. The focused frontend API/component suite and build validate
the repair without claiming a production browser journey.

The real result-closure API regression covers immediate retry, Save, a later
week, cold restart, exact rally replay and backward/forward restore of the new
post-closure exhibition. It also tests a nested-command/closure collision and
checks database rollback. Both W52 and W80 are required. The independent
scored-eight API module includes #1538's original failing restore scenario.

Focused historical checkpoint/hash, annual development, logged-result integrity
and same-transaction lineage regressions remain part of the audit. No persistent
verification cache or bypass of raw bytes, lineage, full sporting fold or live
owner checks is introduced.

Distinct adversarial review examines cross-kind command identities, source
fingerprints, closure timing, exact original receipts versus current HEAD,
tamper rejection, legacy schema serialization and partial transaction rollback.
Final repair-head workflow results are recorded in its PR; pending/red checks
are not merge-ready evidence. The owner alone merges.

Existing Shell/legacy browser workflows do not exercise these new later-knockout
and result-closure panels end to end. Native results/prepared awards still do
not implement configured Tour Edition/Entry, Official Ranking publication,
public Week/Season Transition or the complete pre-alpha release gate.

Next integration step: one canonical configured Edition/Entry bridge consuming
these authentic results, with an actual browser journey and preserved Save/replay
authority. Avoid adding another parallel native result wrapper first.

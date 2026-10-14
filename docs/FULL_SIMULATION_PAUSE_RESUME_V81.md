# Verified Full Simulation controls — 14 October 2026

Baseline: `buuk` `a5482935006728f9de04bec2261b7301aaa9ddc6`, merge #1464;
#1464 is merged and there were no open PRs at task start. This integration
candidate reuses the existing durable parent, controls, Task Center and lease.
It does not redefine the Master or declare a pre-alpha release.

## Behavior and evidence

- The original reviewed Full Simulation command, operator, reason, target and
  fingerprint remain immutable across pause, acknowledgement and resume.
- An actual synchronous production invocation commits sporting children before
  a concurrent HTTP control request asks for pause. The next SQLite writer is
  fenced; acknowledgement occurs after the child transaction exits. Existing
  results, original owners, MatchEngine seeds and pre-slot checkpoints persist.
- The Chromium adapter sends the actual control request to production FastAPI,
  allows SQLite to commit, then drops only the HTTP answer. The browser retries
  the same request ID/payload and receives `replayed=true`; one original pause
  audit event remains. Retrying the original Full Simulation while paused also
  creates no duplicate result or audit.
- A fresh browser page opens the global Task Center, switches to Czech, follows
  the exact Run/Branch link, explicitly authorizes resume, restores the original
  command and confirms continuation. The remaining genuine semifinals/final
  complete. A second ordinary operator pause bounds this test after three real
  matches, before executing the rest of the season.
- A competing Full Simulation in another actual Run receives HTTP 409 before
  any command receipt or sporting result exists there.
- Expiration now fences writes even before another owner takes over. Heartbeat
  renewal cannot resurrect an expired invocation. HTTP tests expire/reclaim a
  lease after a genuine child result, release the old executor and verify 409,
  no subsequent authoritative writes and no deletion of the new owner's lease.
- All six existing Saved Revisions and the Saved head are byte/hash-identical
  before, during and after the native browser flow. No Save occurs in this flow.
  The original saved state remains independently recoverable.
- CS/EN control labels, accessible names and pause guidance follow the selected
  language; an ordinary operator pause is informational. History's
  `Source Branch:` label is translated; IDs and authoritative JSON stay exact.

## Verification boundaries

| Layer | What was exercised |
| --- | --- |
| Deterministic backend / SQLite | Existing lease, final-boundary and Task Center tests plus three HTTP-flow cases; 44 focused tests pass. Three existing same-slot/order-independence tests also pass. |
| Production HTTP + SQLite | Real Uvicorn TCP requests and real production services, with disposable deterministic input fixtures; actual MatchEngine outputs are never inserted or mocked. A copied initial DB running the identical command without pause produces identical sporting receipts and slot snapshots. |
| React/client mocks | 228 tests in 13 focused/CI-baseline modules pass, including CS/EN pause retry, acknowledgement, explicit resume authorization, History translation, Task Center and its validator. These establish presentation/contracts, not engine execution. |
| Native Chromium | Real Admin forms create the Run, copy isolated source packages, generate/adopt/Save 64 players, bootstrap initial Ranking and prepare real Entry/Draw/Schedule. Real Full Simulation results grow **0 → 1 → 3**; controls, discarded HTTP answer, reconnect/Task Center navigation and Save non-mutation are verified. |
| Build / CI | TypeScript/Vite build, backend compile and `git diff --check` pass locally. Fast CI and the dedicated controls browser workflow must both complete successfully on the final PR head before handoff for merge. |

The test-only synchronization hook delays a writer **before BEGIN IMMEDIATE**,
letting the second HTTP request run predictably. It neither creates sporting
results nor changes RNG, transactions or rules. Its routes and evidence reader
exist only in the disposable acceptance process; the production application does
not import this adapter. Chromium saves `evidence.json`, screenshots and a trace;
the dedicated CI workflow uploads these together with server/frontend logs.

Reproduce the native browser gate (fresh disposable directory):

```sh
VITE_API_BASE_URL=http://127.0.0.1:8020 npm --prefix web run dev -- --host 127.0.0.1 --port 5173 --strictPort
python scripts/full_simulation_controls_browser.py --acceptance work/controls --port 8020 --base-url http://127.0.0.1:5173 --chromium /usr/bin/chromium
```

Install production dependencies, pytest and Playwright for this acceptance.

## Limits and next slice

Execution still belongs to explicit synchronous HTTP invocations. Browser polling
only reads receipts; an unexpired lease does not prove autonomous worker health.
The browser reconnect happens after safe acknowledgement; this does not prove
tab closure during active execution, process-restart recovery or an autonomous
server task lifecycle. A child transaction exceeding the renewable lease expiry
fails closed rather than authorizing an expired owner to commit; recovery requires
an explicit retry with the original command. Other simulation entrypoints are
not newly advertised as globally serialized by this Full Simulation lease.

This bounded three-match proof does not complete the original 50-season target,
mid-match immediate pause, target changes, termination, historical cross-Branch
comparison or the full pre-alpha release gate. Native Run Health, Entry and
Ranking prerequisites remain necessary; fixture tests do not waive them.

Recommended next PR: versioned effective Full Simulation target changes and safe
termination on the existing immutable parent, with explicit control identities,
HTTP/SQLite/Chromium retry evidence and no implicit Save. Keep original command
fingerprints/history; autonomous server lifecycle and active-tab reconnect follow
as distinct integration work.

# Cross-platform giant performance diagnostics (28 November 2026)

Owner decision: include Windows in regular long-load performance experiments; preserve Linux x64 and ARM64. This supplements `PRE_ALPHA_PERFORMANCE_MEASUREMENT_V1.md` and does not change Master §31.41 release acceptance or sporting rules. Draft implementation: `.github/workflows/cross-platform-giant-matrix.yml` and `scripts/observe_giant_portable.py`.

## Matrix and cost boundary

Use the three platforms (Windows x64, Linux x64, Linux ARM64). For each, run a previous-night exact control, optimized core without experimental worker PR, same optimized core plus pool implementation disabled, pool with 2 workers, pool with 3 workers. Fifteen cells, at most ten concurrently. Repeat across distinct hosts; never infer CPU architecture causation from a single host. No paid/larger runner or scheduled recurring expenditure is authorized by this procedure. For broader platform compatibility, consider macOS separately from reference performance, not as a substitute for Windows.

Push to the isolated diagnostic branch triggers only the bounded pilot (128 initial players, W5 completed and cold restart + history check). Full mode is explicitly selected; 1000 initial players, five W52 seasons, 60 compatible Main-only 4/8-player Editions/year, 80 arrivals/year, Saved v2, explicit Save, 315-minute simulation budget, 360-minute job cap, 120s HTTP. This is not a 16–128/Q acceptance test. For new nights refresh pins after review, keep the prior exact combination as control and preserve source tree hashes. Do not merge diagnostic combinations into buuk.

## Evidence and gates

Use one Python version (3.12.10 initially) across this matrix, platform-specific dependency hashes and recorded versions. This is a new benchmark series, not directly comparable to prior 3.11.18 timing. Run exact same-host W6 A/A on control or A/B against the previous-night control, with independent copies of a hashed fixture; require equal results and history. Fail closed on conflicts and mismatch. Workers must pass their independent fault-injection and process-teardown gate; timeout that step after 12 minutes rather than leaving a failed process running for six hours. Sequential core diagnostics do not contain the experimental pool code and therefore are not blocked by its gate. Do not describe pool-off or pool-on as accepted if their gate fails.

The portable observer only replaces the pinned harness's two Linux-specific peak-memory reads and associated import in a disposable copy, and observes urllib requests. It retains exact original and adapted harness hashes, host OS/CPU/memory, dependency versions, request counts/timing, process CPU, main process working set/RSS, DB/WAL bytes and progress. Linux I/O counters are null when unavailable on Windows. Main-process RSS is not total process-tree RAM; HTTP time is to response headers. Preserve full raw evidence, compare equal completed weeks/operations and hardware, report stopped-before-week versus completed-week separately. Pilot core restart fixtures are retained for seven days. Full-length intermediate W9/W12/W15/etc. snapshots still need to be ported; previous isolated long workflow remains historical evidence.

## Acceptance status

Pilot run [46128839331](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/46128839331) was queued on the implementation commit `8b057740`. Hosted results are pending at creation. Do not claim Windows giant portability, worker correctness or 1000-player full-load completion until evidence supports it. Workflow dispatch requires availability on the repository's default branch; the diagnostic branch push is the current isolated entry point. User owns merge decisions.

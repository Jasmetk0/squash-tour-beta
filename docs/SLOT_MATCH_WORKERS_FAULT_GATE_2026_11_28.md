# Worker fault test and the hung nightly preflight (28 November 2026, #1941)

Scope: the opt-in spawn worker pool of #1909, its fault tests and a bounded
wrapper for diagnostic CI steps. No sporting rule, seed, RNG draw, schema, hash,
Saved format, Save, Restore, replay authority, timeout value, cooldown, queue
bound, worker limit, workflow or Master change. Base: #1909 head
`b5e1ab34fd0574565224f28ac398b1a613cf4d18` (branch `claude/epic-shannon-zx6y13`).

## Failure being explained

Nightly matrix [46076041064](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/46076041064)
of #1936 (tree `5ee76e2ce92dbef237c4f70484befd2d3915fc13`): five of eight
optimized jobs failed `tests/api/test_slot_worker_faults_http.py::test_faulty_shared_pool_equals_sequential_over_http_saved_v2`
in the step `New optimization correctness gate` with `stats["timeouts"] == 2`
instead of 1, then the step ran until the 360-minute job cap. The runner's
final cleanup still found `python` (pytest), `tee` and one more `python` (the
spawn resource tracker) alive.

## Reproduction (x64, 4 vCPU, Python 3.11.18, lock `fast-ci-linux`)

The #1936 combination was rebuilt locally exactly as its workflow does
(cherry-pick of the two #1905 follow-ups, then `--no-ff` merges of the eight
pins). The tree is `5ee76e2c…`, identical to CI (commit ids differ only by
local merge metadata). The exact gate command (`PYTHONPATH=src:.:tests/api`,
same eleven files, `2>&1 | tee`, `set -o pipefail`) reproduced both symptoms
on the first run: the same assertion `assert (2 == 1)`, the summary was
printed after 13 min, and pytest then never exited (killed after 26 min, the
pipeline returned 143). An instrumented trace of the faulty scenario
(`scripts/trace_slot_worker_faults.py`) reproduced the second timeout and a
blocked manager thread in both valid trace runs on that tree, so both symptoms
appeared in all three runs of the scenario there (one gate, two traces).

### What waits after the summary (the 6 h step)

`py-spy dump --locals` of the hung pytest:

```
MainThread   Thread.join <- _python_exit (concurrent/futures/process.py:100) <- threading._shutdown
Thread-60    Connection._recv  size=534416 remaining=208896
             <- _ExecutorManagerThread.wait_result_broken_or_wakeup (process.py:424)
QueueFeederThread  idle
child        multiprocessing.resource_tracker (waits for its parent)
```

The hung trace process showed the same frame with `size=723987 remaining=200704`.
So pytest itself waits, at interpreter exit, for the manager thread of a
*retired* pool generation. That thread had read the length header and part of
a large result (a `MatchResult` JSON of ~0.5–0.7 MB) from a worker that our
retirement had terminated in the middle of `send_bytes`. The rest never comes,
and EOF never comes either, because the parent process itself still holds the
write end of the pool's result pipe (CPython 3.11–3.13 close it only in
`shutdown(wait=True)`). `concurrent.futures.process._python_exit` joins every
manager thread without a limit. `tee` waits only because pytest still holds
the pipe; the resource tracker only waits for pytest. pytest's block-buffered
tail (the `N failed` line is not printed at `-qq` anyway: `addopts = "-q"`
plus `-q`) also stayed in the hung process.

### The second timeout

Trace of the faulty scenario on the exact #1936 tree (times in seconds from
start; `g` = pool generation):

| t | batch | g | n | outcome |
| ---: | --- | ---: | ---: | --- |
| 71.70 | crash | 1 | 3 | BrokenProcessPool, g1 retired |
| 79.32 | duplicate | 2 | 3 | rejected after 1.06 s, **g2 retired** at 80.38 |
| 79.54 | missing | 2 | 4 | futures `RUNNING` ×4 until its own deadline: **TimeoutError after 7.00 s** |
| 83.15 | foreign | 3 | 3 | rejected, g3 retired |
| 86.09 | shuffled | 4 | 3 | accepted |
| 88.02 | (timeout) | – | 4 | declined: cooldown started by the *missing* batch |
| 90.31 | timeout | 4 | 3 | injected: TimeoutError after 1.00 s |

The barrier-synchronized concurrent step sends three `next-slot` requests;
two of their batches landed on the same generation. When one of them failed
and retired the generation, the other one was still waiting. One of its
workers was terminated mid-send, the generation's manager thread blocked as
above, so its futures never failed with `BrokenProcessPool`: the healthy
batch waited for its full deadline and was counted as a timeout, with a
cooldown. In CI the same race shows as `TimeoutError('3 (of 3) …')` /
`'2 (of 4) …'` beside the injected one; when no worker happens to be
mid-send, the waiting batch fails with `BrokenProcessPool` instead (also seen
in CI) and the test passes. Which faults share a generation depends on the
arrival order of the concurrent requests, hence the failure in sequential,
two- and three-worker matrix jobs alike (the test builds its own two-worker
pool) and not in all of them.

A second path to the same spurious timeout exists without any blocked
thread: futures that were still `PENDING` are cancelled by
`shutdown(cancel_futures=True)`, but `as_completed` yields only
`CANCELLED_AND_NOTIFIED` or `FINISHED` futures, so it never yields them.

Both are production pool defects (a request could wait up to the 30 s cap and
then cool the pool down for 30 s; a server process could not exit), not test
defects.

## Change (pool only)

- `ProcessBatch` observes completion through done callbacks (also fired by
  `cancel()`) plus a wake-up sent by retirement. Every other batch still
  waiting on a retired generation falls back at once with
  `GenerationRetired`: an ordinary sequential fallback, never a timeout of
  that batch, no cooldown, `stale_discards` as before.
- `_shutdown` captures the manager thread and result queue before
  `shutdown(wait=False)` drops them, terminates and joins the workers as
  before, then closes the parent's result write end (nothing can write any
  more) and joins the manager thread (≤ `join_seconds`). A thread still alive
  is counted as `stuck_manager_threads` and logged as an error.
- Deadlines (`min(30, 5 + 0.5 n)`), the cooldown, the queue bound, the live
  worker limit, generation compare-and-set, spawn, fallback and result
  validation are unchanged.

## Tests

- `tests/domain/test_match_worker_generations.py` (real spawn):
  - `test_a_retired_generation_wakes_every_other_waiting_batch_without_a_timeout`:
    X holds both workers, Y waits on the same generation, X fails. Y returns
    the sequential bytes before its deadline, `timeouts == 0`, no cooldown,
    the next batch uses generation 2. On `b5e1ab3` it fails with `timeouts == 1`.
  - `test_a_worker_killed_while_sending_its_result_never_blocks_the_manager_thread`:
    a worker writes a length header for 1 MiB and 1 KiB of it, then stalls
    (the exact state of a worker terminated mid-send). After retirement the
    manager thread has ended. On `b5e1ab3` the thread stays alive (the test
    unblocks it itself so the test process can still exit). POSIX only.
- `tests/api/test_slot_worker_faults_http.py`: the injected timeout keeps its
  own trigger (30 s sleep against a 1 s deadline). Every admitted batch is
  kept and every counted timeout is attributed to its batch: any timeout other
  than the injected one fails with its fault, generation and size, so an
  unexpected production timeout stays visible. Also asserts
  `stuck_manager_threads == 0` and no `_ExecutorManagerThread` left alive.
- `tests/tools/test_run_bounded_gate.py`: the wrapper below, with real
  processes: a failing command, a command that never exits after printing
  its summary while a descendant holds the pipe, and a successful command
  that leaves a process behind.

## Bounded diagnostic step

`scripts/run_bounded_gate.py --limit-seconds S --log FILE -- <command>` runs
the command in its own process group with unbuffered Python output, streams
it to the console and the log, and returns the command's exit code. At the
limit it dumps stacks with `py-spy` when installed, stops the whole group and
returns 124; a successful command that leaves processes behind returns 125.
It is meant for diagnostic steps only. Proposed use in a #1936-style workflow
(not applied to any running branch):

```yaml
      - name: New optimization correctness gate
        if: matrix.variant == 'optimized'
        timeout-minutes: 35          # outer guard only
        run: |
          set -euo pipefail
          root="$RUNNER_TEMP/giant-saved-v2-evidence"
          python scripts/run_bounded_gate.py --limit-seconds 1800 --log "$root/new-tests.log" -- \
            python -m pytest -q <the same eleven files>
```

The gate took 13.4–14.0 min here and 13.7 min on the CI x64 runner, so 30 min
is about twice the observed time. A non-zero exit fails the step and every
later step without `if: always()` (W6 A/B, the large simulation) is skipped;
the artifact step keeps the log.

## Evidence

| check | tree | result |
| --- | --- | --- |
| exact gate, `pytest \| tee` | #1936 `5ee76e2c` | `assert (2 == 1)`; summary at 13 min, then hung (killed at 26 min, rc 143) |
| trace of the faulty scenario, 2 runs | #1936 `5ee76e2c` | 2 timeouts each, blocked manager thread each (one hung and was killed, one rc 3) |
| new regressions | #1909 `b5e1ab3` | both fail (`timeouts == 1`; manager thread alive) |
| forced preflight failure through the wrapper (mid-send retirement, then a failing assert) | #1909 `b5e1ab3` | rc 124 at the 90 s limit, log with the assertion kept, 0 processes left |
| same | fix | rc 1 after 1.8 s, log kept, 0 processes left |
| exact gate through the wrapper, 3 runs | #1936 + fix `f442d2de` | rc 0 each, 802–839 s, no leftover process |
| exact gate, limited to 2 CPUs (`taskset -c 0,1`) | #1936 + fix `f442d2de` | rc 0, 813 s, no leftover process |
| trace of the faulty scenario | #1936 + fix `f442d2de` | 1 timeout (the injected one); `missing` falls back with `GenerationRetired` after 0.46 s; no manager thread left |

## Worker pilot (0 / 2 / 3)

Pending: running on the fixed tree; results follow in the next commit.

## Reproduction commands

```bash
# Exact #1936 optimized tree (5ee76e2c) in a separate worktree
git worktree add --detach ../combo 29784d51d01d9d747705be8abae30f0c82706c1e && cd ../combo
git cherry-pick -x ea9978fb3e41558fef5e9f00778f2cc18cf513ba dfb2e3a0d98bfca700ce1f9d801929ccec2544bf
for pin in 1372c31849e242cc2ca0f0a2d67cd73af04c816f 47beee7a2a999cce7d9fd71aea0412e95b1d56ac \
  091ac6c79852ddd1fc976c0fff808795703359f5 1935e53555c1f6d3d11481d3e83cb9687bceb3cd \
  18bf7156cb056e25a5fb22a306609597a2517fd0 b0f135fb83422b220f08ae1863f632e48f01bac6 \
  b5e1ab34fd0574565224f28ac398b1a613cf4d18; do git merge --no-ff --no-edit "$pin"; done
git rev-parse HEAD^{tree}   # 5ee76e2ce92dbef237c4f70484befd2d3915fc13
# Fixed tree: the same plus this branch
git merge --no-ff --no-edit <this branch head>   # tree f442d2de… for b5af417
# Per-batch trace (exit 3 = a blocked manager thread was left)
python scripts/trace_slot_worker_faults.py --root ../combo --out work/trace.jsonl
# Exact gate, bounded
PYTHONPATH=src:.:tests/api python scripts/run_bounded_gate.py --limit-seconds 1800 \
  --log work/new-tests.log -- python -m pytest -q <the eleven gate files>
# Stacks of a hung process
py-spy dump --pid <pid> --locals
```

## Limitations

- x64 only. No ARM64 machine was available to this session; Windows is not
  verified. On Windows the result pipe is message-mode, so the partial-message
  regression test is skipped there and the write-end close is unexercised.
- The fix uses `ProcessPoolExecutor` internals (`_executor_manager_thread`,
  `_result_queue._writer`, `_processes`, the last already used by #1909). They
  were read in the CPython 3.11.18 source and are present unchanged in the
  3.12 and 3.13 sources; only 3.11.18 was executed.
- A healthy batch that arrives on a freshly spawned generation still pays the
  spawn and import inside its unchanged deadline. Here such batches took
  ≤ 0.6 s against ≥ 6 s; on a much slower runner it would be a visible
  unexpected timeout, not a hidden one.
- A healthy batch on a generation retired by another batch is recomputed
  sequentially, as before; it now does so at once instead of after its
  deadline.
- The gate was not run on GitHub runners from this branch; the nightly
  five-season matrix was not run (as instructed).

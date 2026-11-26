"""Independent frozen slot matches: any executor, any completion order, same bytes.

Component tests of ``slot_batch`` and the real spawn pool. The production
HTTP/SQLite path with workers is in ``tests/api/test_slot_match_workers.py``.
"""

from __future__ import annotations

import dataclasses
import os
import random

import pytest

from beta_engine.domain.matches import slot_batch
from beta_engine.domain.matches.health import EffectiveMatchHealthSnapshot
from beta_engine.domain.players.health import PlayerHealthProfile
from beta_engine.infrastructure import match_workers
from scripts import benchmark_match_engine as bench

pytestmark = pytest.mark.pr_critical


def _healthy(context):
    return EffectiveMatchHealthSnapshot.from_profiles(
        player_a=PlayerHealthProfile(player_id=context.player_a.player.player_id),
        player_b=PlayerHealthProfile(player_id=context.player_b.player.player_id),
    )


def corpus(count=None):
    """Deuce, BO1/BO3/PAR-15, explicit and probabilistic retirement, injury, varied."""
    items = []
    for label, context, seed, health, _path in bench.edge_cases():
        if label.startswith(("lab-", "step-")):
            continue
        snapshot = (
            bench._health(context.player_a.player.player_id, context.player_b.player.player_id)
            if health == "injured" else _healthy(context)
        )
        items.append((context, seed, f"{len(items) + 1:064x}", snapshot))
    for match_id, a, b, best_of, seed in bench.match_set()[:4]:
        context = bench.context_for(match_id, a, b, best_of)
        items.append((context, seed, f"{len(items) + 1:064x}", _healthy(context)))
    return items[:count] if count else items


@pytest.fixture(scope="module")
def items():
    return corpus()


@pytest.fixture(scope="module")
def sequential(items):
    return slot_batch.simulate_batch(items)


def _bytes(results):
    return [r.model_dump_json() for r in results]


class InProcessExecutor(slot_batch.MatchBatchExecutor):
    """Runs the real worker body here; optionally shuffles/tampers responses."""

    def __init__(self, *, seed=0, mutate=None, fail=None):
        self.rng = random.Random(seed)
        self.mutate = mutate
        self.fail = fail
        self.discarded = 0
        self.batches = 0

    def run(self, requests):
        self.batches += 1
        if self.fail is not None:
            raise self.fail
        order = list(requests)
        self.rng.shuffle(order)
        responses = [slot_batch.run_encoded(r) for r in order]
        return self.mutate(responses) if self.mutate else responses

    def discard(self):
        self.discarded += 1


def test_the_corpus_contains_the_abnormal_states(sequential):
    reasons = {r.termination_reason.value for r in sequential}
    assert {"COMPLETED", "RETIREMENT"} <= reasons
    assert {r.best_of for r in sequential} >= {1, 3, 5}
    assert any(r.games_to == 15 for r in sequential)
    assert any(
        e.score_before.points_a >= 10 and e.score_before.points_a == e.score_before.points_b
        for r in sequential for e in r.rally_log.events
    )


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_random_completion_order_returns_identical_results_in_request_order(items, sequential, seed):
    executor = InProcessExecutor(seed=seed)
    results = slot_batch.simulate_batch(items, executor=executor)
    assert executor.batches == 1 and executor.discarded == 0
    assert results == sequential
    assert _bytes(results) == _bytes(sequential)
    assert [r.rally_log.input_snapshot_hash for r in results] == [i[2] for i in items]


def _swap_first_two(responses):
    a, b = responses[0], responses[1]
    return [dataclasses.replace(a, result_json=b.result_json),
            dataclasses.replace(b, result_json=a.result_json), *responses[2:]]


def _tamper_rally(responses):
    first = responses[0]
    raw = first.result_json.replace(b'"rally_number":1,', b'"rally_number":2,', 1)
    assert raw != first.result_json
    return [dataclasses.replace(first, result_json=raw), *responses[1:]]


def _tamper_score(responses):
    first = responses[0]
    raw = first.result_json.replace(b'"winner_games":11', b'"winner_games":12', 1)
    assert raw != first.result_json
    return [dataclasses.replace(first, result_json=raw), *responses[1:]]


@pytest.mark.parametrize("mutate", [
    lambda rs: rs[1:],                                              # missing
    lambda rs: [*rs, rs[0]],                                        # duplicate
    lambda rs: [dataclasses.replace(rs[0], index=99), *rs[1:]],     # foreign index
    lambda rs: [dataclasses.replace(rs[0], anchor="f" * 64), *rs[1:]],  # wrong anchor
    _swap_first_two,                                                # result of another match
    _tamper_rally,                                                  # broken rally chain
    _tamper_score,                                                  # score differs from log
    lambda rs: [object(), *rs[1:]],                                 # not a response
], ids=["missing", "duplicate", "foreign", "anchor", "swapped", "rally", "score", "type"])
def test_any_rejected_worker_batch_is_recomputed_sequentially(items, sequential, mutate):
    executor = InProcessExecutor(seed=7, mutate=mutate)
    before = slot_batch.batch_counters()["fallback_batches"]
    results = slot_batch.simulate_batch(items[:4], executor=executor)
    assert results == sequential[:4] and _bytes(results) == _bytes(sequential[:4])
    assert executor.discarded == 1
    assert slot_batch.batch_counters()["fallback_batches"] == before + 1


def test_executor_failure_falls_back_and_engine_errors_keep_their_meaning(items, sequential):
    executor = InProcessExecutor(fail=RuntimeError("worker died"))
    assert slot_batch.simulate_batch(items[:3], executor=executor) == sequential[:3]
    assert executor.discarded == 1
    # A genuine input error is not hidden by the executor: the sequential
    # recomputation raises the original MatchEngine error.
    context, seed, _anchor, health = items[0]
    broken = [(context, seed, "not-a-hash", health), items[1]]
    with pytest.raises(Exception) as worker_error:
        slot_batch.simulate_batch(broken, executor=InProcessExecutor())
    with pytest.raises(type(worker_error.value)):
        slot_batch.simulate_batch(broken)


def test_single_match_and_disabled_executor_use_the_original_call(items, sequential):
    executor = InProcessExecutor()
    assert slot_batch.simulate_batch(items[:1], executor=executor) == sequential[:1]
    assert executor.batches == 0
    assert slot_batch.simulate_batch([]) == []


def test_worker_count_configuration():
    assert [match_workers.resolve_worker_count(v) for v in ("", "0", "off", " 3 ")] == [0, 0, 0, 3]
    assert match_workers.resolve_worker_count("auto", cpu_count=4) == 3
    assert match_workers.resolve_worker_count("auto", cpu_count=16) == 4
    assert match_workers.resolve_worker_count("auto", cpu_count=2) == 0
    for bad in ("x", "-1", "33"):
        with pytest.raises(ValueError):
            match_workers.resolve_worker_count(bad)


def crash_worker(_request):
    os._exit(3)


class CrashingExecutor(match_workers.ProcessMatchExecutor):
    crash = True

    def run(self, requests):
        if self.crash:
            self.crash = False
            pool = self._ensure_pool()
            futures = [pool.submit(crash_worker, r) for r in requests]
            return [f.result(timeout=60) for f in futures]
        return super().run(requests)


def test_real_spawn_pool_matches_sequential_and_recovers_from_a_worker_crash(items, sequential, monkeypatch):
    # Workers deliberately get another hash seed than this parent process.
    monkeypatch.setenv("PYTHONHASHSEED", "424242")
    executor = CrashingExecutor(2, timeout_seconds=90)
    try:
        before = slot_batch.batch_counters()["fallback_batches"]
        crashed = slot_batch.simulate_batch(items[:4], executor=executor)
        assert crashed == sequential[:4]
        assert slot_batch.batch_counters()["fallback_batches"] == before + 1
        assert executor._pool is None  # broken pool discarded
        results = slot_batch.simulate_batch(items, executor=executor)
        assert results == sequential and _bytes(results) == _bytes(sequential)
        assert executor.pools_started == 2
        pids = executor.worker_pids()
        assert 1 <= len(pids) <= 2 and os.getpid() not in pids
    finally:
        executor.close()
    if os.path.isdir("/proc"):
        assert not any(os.path.exists(f"/proc/{pid}") for pid in pids)
    with pytest.raises(RuntimeError):
        list(executor.run([]))


def test_install_from_environment_is_bounded_and_does_not_replace_an_installed_executor(monkeypatch):
    previous = slot_batch.install_executor(None)
    try:
        assert match_workers.install_from_environment("0") is None
        first = match_workers.install_from_environment("2")
        assert slot_batch.installed_executor() is first and first.workers == 2
        assert match_workers.install_from_environment("3") is None
        match_workers.uninstall(first)
        assert slot_batch.installed_executor() is None
    finally:
        slot_batch.install_executor(previous)

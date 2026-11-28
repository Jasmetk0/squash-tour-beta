"""Order-independent batch execution of independent, already frozen matches.

A Simulation Slot freezes every simultaneous match before any of them is
played (Master 6.6). Each frozen match is a pure function of exactly four
values: its ``MatchContext``, its own seed, its log anchor and its effective
Health snapshot. This module runs a batch of such values and returns their
``MatchResult`` objects in request order.

The default is the original in-process sequential call. An optional executor
(for example the bounded spawn pool in
``beta_engine.infrastructure.match_workers``) may compute the same pure calls
elsewhere; it never receives a session, repository, Signed value or history and
can only return encoded results. The parent binds every returned value back to
its exact request and decodes it through the complete ``MatchResult`` validator
(rally log, timeline and stamina chains included). Any executor failure, a
missing, duplicate, foreign or invalid result discards the whole executor batch
and recomputes it here sequentially, which is the original behaviour, so a
worker can neither install a partial step nor change a sporting result.
Scheduling, completion order and worker count therefore cannot affect results.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches.health import EffectiveMatchHealthSnapshot
from beta_engine.domain.matches.match_engine import MatchEngine
from beta_engine.domain.matches.models import MatchContext, MatchResult

_log = logging.getLogger(__name__)

REQUEST_SCHEMA = "frozen_match_batch_request.v1"


@dataclass(frozen=True, slots=True)
class FrozenMatchRequest:
    """The exact pure inputs of one frozen match; nothing else crosses over."""

    index: int
    match_id: str
    seed: int
    anchor: str
    context_json: bytes
    health_json: bytes


@dataclass(frozen=True, slots=True)
class FrozenMatchResponse:
    index: int
    match_id: str
    anchor: str
    result_json: bytes


def simulate_frozen(context, *, seed, anchor, health):
    """The single authoritative call; sequential path and workers both use it."""
    return MatchEngine(DeterministicRng(seed)).simulate(
        context, log_anchor_hash=anchor, effective_match_health=health,
    )


def encode_request(index, context, *, seed, anchor, health):
    return FrozenMatchRequest(
        index=index,
        match_id=context.match_id,
        seed=seed,
        anchor=anchor,
        context_json=context.model_dump_json().encode(),
        health_json=health.model_dump_json().encode(),
    )


def run_encoded(request: FrozenMatchRequest) -> FrozenMatchResponse:
    """Worker body: decode exact inputs, simulate, encode. No I/O, no state."""
    context = MatchContext.model_validate_json(request.context_json)
    health = EffectiveMatchHealthSnapshot.model_validate_json(request.health_json)
    if context.match_id != request.match_id:
        raise ValueError("Frozen match request identity differs from its context")
    result = simulate_frozen(
        context, seed=request.seed, anchor=request.anchor, health=health,
    )
    return FrozenMatchResponse(
        index=request.index,
        match_id=request.match_id,
        anchor=request.anchor,
        result_json=result.model_dump_json().encode(),
    )


def bind_response(response, request, context):
    """Strictly decode one returned result and bind it to its own request."""
    if (
        not isinstance(response, FrozenMatchResponse)
        or (response.index, response.match_id, response.anchor)
        != (request.index, request.match_id, request.anchor)
        or not isinstance(response.result_json, bytes)
    ):
        raise ValueError("Worker result is not bound to its frozen match request")
    # Full validation: every rally/timeline/stamina chain is rebuilt from bytes.
    result = MatchResult.model_validate_json(response.result_json)
    log = result.rally_log
    if (
        result.match_id != context.match_id
        or (result.player_a_id, result.player_b_id)
        != (context.player_a.player.player_id, context.player_b.player.player_id)
        or (result.best_of, result.games_to, result.win_by)
        != (context.best_of, context.games_to, context.win_by)
        or log is None
        or log.match_id != context.match_id
        or log.input_snapshot_hash != request.anchor
    ):
        raise ValueError("Worker result differs from its frozen match identity")
    return result


class ExecutorUnavailable(Exception):
    """The executor declined a batch (full, closed, replacing, cooling down).

    Nothing was submitted; the batch is computed sequentially and nothing is
    retired.
    """


class MatchBatchExecutor:
    """Interface: iterate ``run_encoded`` responses of every request, any order."""

    min_batch = 2

    def run(self, requests):  # pragma: no cover - interface
        """Return an iterable of responses (may raise ``ExecutorUnavailable``)."""
        raise NotImplementedError

    def discard(self, batch=None):  # pragma: no cover - interface
        """Drop the possibly broken pool that served ``batch`` (and only it).

        ``batch`` is the value ``run`` returned, or ``None`` when ``run``
        itself raised.
        """


_executor_lock = threading.Lock()
_executor: MatchBatchExecutor | None = None
_counter_lock = threading.Lock()
_counters = {
    "executor_batches": 0, "executor_matches": 0, "fallback_batches": 0,
    "unavailable_batches": 0, "executor_seconds": 0.0, "max_executor_batch_seconds": 0.0,
}


def install_executor(executor):
    """Install a process-wide executor; returns the previous one."""
    global _executor
    with _executor_lock:
        previous, _executor = _executor, executor
        return previous


def install_executor_if_absent(executor):
    """Install ``executor`` unless one is installed; returns the installed one."""
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = executor
        return _executor


def uninstall_executor(executor):
    """Uninstall exactly ``executor`` (never a later replacement)."""
    global _executor
    with _executor_lock:
        if _executor is executor:
            _executor = None
            return True
        return False


def installed_executor():
    return _executor


def batch_counters():
    with _counter_lock:
        return dict(_counters)


def _count(**values):
    with _counter_lock:
        for name, value in values.items():
            if name.startswith("max_"):
                _counters[name] = max(_counters[name], value)
            else:
                _counters[name] += value


def _sequential(items):
    return [
        simulate_frozen(context, seed=seed, anchor=anchor, health=health)
        for context, seed, anchor, health in items
    ]


def simulate_batch(items, *, executor=None):
    """Return the MatchResults of ``(context, seed, anchor, health)`` items, in order."""
    items = list(items)
    executor = executor if executor is not None else _executor
    if executor is None or len(items) < max(2, executor.min_batch):
        return _sequential(items)
    requests = [
        encode_request(i, context, seed=seed, anchor=anchor, health=health)
        for i, (context, seed, anchor, health) in enumerate(items)
    ]
    started = time.monotonic()
    batch = None
    try:
        batch = executor.run(requests)
        # Responses may arrive in any order; each is decoded as soon as it
        # arrives (overlapping the remaining worker computation) and placed by
        # its own request index only.
        results = [None] * len(requests)
        for response in batch:
            index = getattr(response, "index", None)
            if not isinstance(index, int) or not 0 <= index < len(requests) or results[index] is not None:
                raise ValueError("Duplicate or foreign worker result")
            results[index] = bind_response(response, requests[index], items[index][0])
        if any(result is None for result in results):
            raise ValueError("Incomplete worker batch")
    except ExecutorUnavailable as error:
        # Declined before anything was submitted: nothing to retire.
        _count(unavailable_batches=1)
        _log.info("Match worker batch declined; computing sequentially: %s", error)
        return _sequential(items)
    except Exception as error:  # noqa: BLE001 - every failure takes the safe path
        _count(fallback_batches=1)
        _log.warning("Match worker batch rejected; recomputing sequentially: %r", error)
        try:
            getattr(batch, "close", lambda: None)()  # cancel unfinished work
            executor.discard(batch)  # only the pool generation that served it
        except Exception:  # noqa: BLE001
            _log.exception("Discarding the match worker pool failed")
        return _sequential(items)
    elapsed = time.monotonic() - started
    _count(executor_batches=1, executor_matches=len(items), executor_seconds=elapsed,
           max_executor_batch_seconds=elapsed)
    return results

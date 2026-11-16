"""Test-only A/B: complete Pydantic cohere validation without JSON round trip.

No production modules are patched. This measures the existing NativeForkRuntime
model built by the real input fixtures, extended with structurally valid
append-only journal evidence to simulate growing Saved history. It DOES NOT
measure real HTTP W52 or claim season speedup.
"""
from __future__ import annotations

import json
import statistics
import time

import pytest

from beta_engine.application.native_fork_runtime_reducer import cohere
from beta_engine.domain.native_fork_runtime import ForkRuntimeCommand, NativeForkRuntime
from tests.infrastructure.test_native_fork_runtime_format import runtime_root

pytestmark = pytest.mark.pr_critical


def _prepared(runtime, changes):
    result = runtime.model_copy(update=changes)
    return result.model_copy(update={"tour": result.tour.model_copy(update={
        "week": result.week,
        "checkpoint_fingerprint": result.checkpoint_fingerprint,
        "lifecycle_fingerprint": result.lifecycle.fingerprint,
    })})


def _candidate(runtime, changes, dump_mode):
    prepared = _prepared(runtime, changes)
    return NativeForkRuntime.model_validate(prepared.model_dump(mode=dump_mode))


@pytest.mark.parametrize("journal_count", [0, 64, 256])
def test_paired_cohere_roundtrip_modes_with_growing_history(journal_count, capsys):
    runtime, _ = runtime_root()
    # Make an unforgeable 'old' result by running exactly the production cohere.
    # journal does not alter checkpoint identity; ordinary runtime validator
    # still receives, parses and checks the complete growing journal.
    if journal_count:
        items = tuple(
            ForkRuntimeCommand(
                draft_version_before=index,
                request={"action": "transition", "id": f"tick-{index}"},
                result={"audit": "ž" * 1200, "week": index, "confirmed": True},
            )
            for index in range(journal_count)
        )
        runtime = runtime.model_copy(update={"journal": items})
    expected = cohere(runtime)
    assert expected.journal == runtime.journal

    modes = ("python", "json")
    compatible = {}
    for mode in modes:
        try:
            value = _candidate(runtime, {}, mode)
        except (TypeError, ValueError) as exc:
            compatible[mode] = {"ok": False, "reason": type(exc).__name__ + ": " + str(exc)[:300]}
            continue
        if value.model_dump_json() != expected.model_dump_json():
            compatible[mode] = {"ok": False, "reason": "Pydantic output JSON is different"}
        else:
            compatible[mode] = {"ok": True}
    methods = [("baseline", lambda: cohere(runtime))]
    methods += [(mode, lambda m=mode: _candidate(runtime, {}, m))
                for mode in modes if compatible[mode]["ok"]]
    samples = {name: [] for name, _ in methods}

    # Interleave and reverse order to avoid systematic first-call bias.
    for index in range(9):
        scheduled = methods if index % 2 == 0 else list(reversed(methods))
        for name, fn in scheduled:
            start = time.thread_time_ns()
            out = fn()
            samples[name].append((time.thread_time_ns() - start) / 1e6)
            assert out.model_dump_json() == expected.model_dump_json()
    medians = {name: round(statistics.median(xs), 3) for name, xs in samples.items()}
    with capsys.disabled():
        print("COHERE_REAL_MODEL_PAIRED_AB " + json.dumps({
            "source": "actual typed native runtime test fixture, synthetic growing journal",
            "journal_entries": journal_count,
            "baseline_json_bytes": len(expected.model_dump_json().encode("utf-8")),
            "validation_modes": compatible,
            "median_thread_cpu_ms": medians,
            "ratios": {k: round(v / medians["baseline"], 4)
                       for k, v in medians.items() if k != "baseline"},
            "outputs_equal": True,
        }, sort_keys=True), flush=True)


@pytest.mark.parametrize("case", ["foreign_owner", "empty_players"])
def test_invalid_runtime_would_still_fail_with_original_cohere(case, capsys):
    runtime, _ = runtime_root()
    if case == "empty_players":
        changes = {"players": ()}
    else:
        changes = {"lifecycle": runtime.lifecycle.model_copy(update={"branch_id": "foreign"})}
    with pytest.raises(ValueError):
        cohere(runtime, **changes)
    matches = {}
    for mode in ("python", "json"):
        try:
            _candidate(runtime, changes, mode)
        except (TypeError, ValueError):
            matches[mode] = True
        else:
            matches[mode] = False
    with capsys.disabled():
        print("COHERE_INVALID_A_B " + json.dumps({"case": case, "rejected": matches}), flush=True)

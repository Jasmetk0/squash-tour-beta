"""The projection cache is a bounded value cache, never a physical-row proof."""

from threading import Lock
from types import SimpleNamespace

import pytest

from beta_engine.infrastructure.db.native_fork_source_projection import (
    decoded_original_source,
)

pytestmark = pytest.mark.pr_critical


def repository():
    return SimpleNamespace(_revision_validation_lock=Lock())


def source(value=1, **fields):
    return SimpleNamespace(
        run_id="run",
        branch_id="branch",
        content_hash="same-declared-hash",
        payload={"content": {"value": value}},
        **fields,
    )


def test_exact_current_value_and_defensive_copies():
    repo = repository()
    calls = []

    def decode(src):
        calls.append(src.payload["content"]["value"])
        return SimpleNamespace(items=[{"value": calls[-1]}])

    first = decoded_original_source(repo, source(), decode)
    first.items[0]["value"] = "caller mutation"
    second = decoded_original_source(repo, source(), decode)
    second.items.clear()
    assert decoded_original_source(repo, source(), decode).items == [{"value": 1}]
    assert calls == [1]
    assert decoded_original_source(repo, source(2), decode).items == [{"value": 2}]
    assert calls == [1, 2]  # Same declared hash cannot hide different actual data.


def test_scope_repository_restart_and_failed_decode_are_independent():
    repo = repository()
    calls = []

    def decode(src):
        calls.append((src.run_id, src.branch_id))
        if src.payload["content"]["value"] == "bad":
            raise ValueError("invalid current input")
        return []

    decoded_original_source(repo, source(), decode)
    for _ in range(2):
        with pytest.raises(ValueError, match="invalid current input"):
            decoded_original_source(repo, source("bad"), decode)
    changed_owner = source()
    changed_owner.branch_id = "another"
    decoded_original_source(repo, changed_owner, decode)
    decoded_original_source(repository(), source(), decode)
    assert len(calls) == 5


def test_entry_and_byte_budgets_and_oversize_bypass(monkeypatch):
    from beta_engine.infrastructure.db import native_fork_source_projection as cache

    repo = repository()
    monkeypatch.setattr(cache, "MAX_SOURCE_BYTES", 100)
    for value in range(5):
        decoded_original_source(
            repo, source(value), lambda src: [src.payload["content"]["value"]]
        )
    assert len(repo._native_source_projection_cache) == cache.MAX_SOURCES
    assert sum(v[0] for v in repo._native_source_projection_cache.values()) <= 100
    before = dict(repo._native_source_projection_cache)
    decoded_original_source(repo, source("x" * 101), lambda src: [])
    assert repo._native_source_projection_cache == before
    decoded_original_source(repo, source("x" * 45), lambda src: [])
    assert sum(v[0] for v in repo._native_source_projection_cache.values()) <= 100

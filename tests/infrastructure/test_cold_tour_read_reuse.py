"""Walk-private reuse in the cold Tour read never crosses its own boundary."""

from threading import Lock
from types import SimpleNamespace

import pytest

from beta_engine.infrastructure.db import calendar_tour

pytestmark = pytest.mark.pr_critical


def test_walk_private_played_origin_values_are_never_retained_across_requests():
    repository = SimpleNamespace(_revision_validation_lock=Lock())
    projection_key = ("run", "branch", "revision", b"digest", False)
    proofs = {"_global_origin_inputs": {
        projection_key: (7, '{"run":{}}'),
        calendar_tour._PLAYED_ORIGIN_AUTHORITIES: (0, {("run", "branch", "revision", b"d", "e"): ("{}", object())}),
    }}
    calendar_tour.retain_origin_projection_values(repository, proofs)
    assert repository._origin_projection_values == {projection_key: (7, '{"run":{}}')}


def test_walk_origin_projection_budget_holds_the_played_head_working_set():
    cache = {}
    for index in range(40):
        calendar_tour._retain_origin_projection(cache, ("key", index), {"tour": "x" * (5 * 1024 * 1024)})
    # Seven Editions' played heads plus their predecessors (W9) fit; the bound
    # is still enforced.
    assert len(cache) >= 40
    total = sum(value[0] for value in cache.values())
    assert total <= calendar_tour._MAX_WALK_ORIGIN_PROJECTION_BYTES
    for index in range(40, 80):
        calendar_tour._retain_origin_projection(cache, ("key", index), {"tour": "x" * (5 * 1024 * 1024)})
    assert sum(value[0] for value in cache.values()) <= calendar_tour._MAX_WALK_ORIGIN_PROJECTION_BYTES
    assert ("key", 0) not in cache and ("key", 79) in cache

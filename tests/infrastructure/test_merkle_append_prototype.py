"""Differential and adversarial tests for non-production Merkle append deltas."""
import hashlib
import json

import pytest

from beta_engine.infrastructure.db.merkle_append_prototype import (
    AppendReader, MerkleAppendError, append, canonical,
)

pytestmark = pytest.mark.pr_critical


def test_week_by_week_exact_replay_without_recursion():
    store, head, events = {}, None, []
    for week in range(1, 82):
        item = {"week": week, "players": ["Žan", "😀"],
                "events": ["r" * 2500, {"score": week}]}
        head = append(store, head, [item], previous_count=len(events))
        events.append(item)
        assert AppendReader(store).history(head) == events
        assert AppendReader(store).history(head, reconstruct=False) == len(events)
    assert len(store) == 81


def test_forks_can_share_an_authenticated_prefix_without_cross_contamination():
    store = {}
    ancestor = append(store, None, [{"week": 1}], previous_count=0)
    left = append(store, ancestor, [{"week": 2, "side": "left"}], previous_count=1)
    right = append(store, ancestor, [{"week": 2, "side": "right"}], previous_count=1)
    assert AppendReader(store).history(left)[-1]["side"] == "left"
    assert AppendReader(store).history(right)[-1]["side"] == "right"
    assert len(store) == 3


def test_caller_cannot_mutate_values_after_insertion():
    store = {}
    original = [{"name": "žluťoučký", "list": [1]}]
    head = append(store, None, original, previous_count=0)
    original[0]["list"].append(2)
    assert AppendReader(store).history(head) == [{"name": "žluťoučký", "list": [1]}]


def test_corruption_after_warm_read_still_rejected_by_reader_and_writer():
    store = {}
    parent = append(store, None, [{"a": "before"}], previous_count=0)
    head = append(store, parent, [{"a": "after"}], previous_count=1)
    reader = AppendReader(store)
    assert reader.history(head) == [{"a": "before"}, {"a": "after"}]
    store[parent] = store[parent].replace("before", "tampered")
    with pytest.raises(MerkleAppendError, match="corrupted"):
        reader.history(head)
    with pytest.raises(MerkleAppendError, match="corrupted"):
        append(store, head, [{"a": "next"}], previous_count=2)


def test_missing_actual_ancestor_and_wrong_count_fail_closed():
    store = {}
    parent = append(store, None, [0, 1], previous_count=0)
    head = append(store, parent, [2], previous_count=2)
    with pytest.raises(MerkleAppendError, match="count"):
        append(store, head, [3], previous_count=999)
    del store[parent]
    with pytest.raises(MerkleAppendError, match="Missing"):
        AppendReader(store).history(head)


@pytest.mark.parametrize("node", [
    {"v": 1, "prev": None, "count": 3, "items": [1]},
    {"v": 1, "prev": None, "count": True, "items": [1]},
    {"v": 1, "prev": None, "count": 1, "items": [1], "extra": 5},
    {"v": 1, "prev": None, "count": 1, "items": []},
    {"v": 1, "prev": "wrong", "count": 2, "items": [2]},
])
def test_forged_but_self_consistently_hashed_bad_nodes_rejected(node):
    raw = canonical(node)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    with pytest.raises(MerkleAppendError):
        AppendReader({digest: raw}).history(digest)


def test_invalid_input_and_empty_history_fail_closed():
    assert AppendReader({}).history(None) == []
    assert AppendReader({}).history(None, reconstruct=False) == 0
    for items in ([], (), {}, None):
        with pytest.raises(MerkleAppendError):
            append({}, None, items, previous_count=0)
    with pytest.raises(MerkleAppendError):
        append({}, None, [1], previous_count=1)
    with pytest.raises(MerkleAppendError):
        append({}, "0" * 64, [1], previous_count=0)
    with pytest.raises(MerkleAppendError):
        append({}, None, [object()], previous_count=0)


def test_long_history_remains_iterative_and_checks_old_physical_bytes():
    store, head = {}, None
    for week in range(1, 125):
        head = append(store, head, [week], previous_count=week - 1)
    first = next(iter(store))
    store[first] += "\n"
    with pytest.raises(MerkleAppendError):
        AppendReader(store).history(head)


def test_canonical_unicode_and_signed_bytes():
    store = {}
    head = append(store, None, [{"utf8": ["ž", "😀"], "f": -0.0}], previous_count=0)
    node = json.loads(store[head])
    assert canonical(node) == store[head]
    assert head == hashlib.sha256(store[head].encode()).hexdigest()

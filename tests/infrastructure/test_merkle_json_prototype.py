"""Merkle JSON prototype: exact reconstruction and fail-closed authentication."""

import hashlib
import json
import random

import pytest

from beta_engine.infrastructure.db import merkle_json_prototype as mj

pytestmark = pytest.mark.pr_critical


def history(weeks):
    """A growing value like a Saved checkpoint: events append, other fields change."""
    return {
        "content": {
            "checkpoint": {"fingerprint": f"f{weeks}", "state": {
                "events": [{"week": i, "log": "r" * 3000, "n": [i, i * 1.5]} for i in range(weeks)]}},
            "small": {"note": "x" * (weeks % 3)},
        },
        "run": {"run_id": "run", "weeks": weeks},
    }


def test_exact_reconstruction_and_sharing_across_revisions():
    store = {}
    roots = []
    sizes = []
    for weeks in range(1, 12):
        root, stats = mj.encode(history(weeks), store, threshold=1024)
        roots.append(root)
        sizes.append(stats["new_bytes"])
    for weeks, root in zip(range(1, 12), roots):
        assert mj.canonical(mj.decode_root(root, mj.Reader(store))) == mj.canonical(history(weeks))
    # Each later revision stores only the new event and changed small nodes.
    assert max(sizes[3:]) < 5000
    reader = mj.Reader(store)
    for root in roots:
        reader.verify(root["digest"])
    assert reader.hashed_bytes == sum(len(text) for text in store.values())


def test_random_values_round_trip_exactly():
    rng = random.Random(5)

    def value(depth=0):
        roll = rng.random()
        if depth > 3 or roll < 0.3:
            return rng.choice([0, -3, 1.25, "é" * rng.randint(0, 300), None, True, "a" * 900])
        if roll < 0.65:
            return [value(depth + 1) for _ in range(rng.randint(0, 6))]
        return {rng.choice(["a", "b", "zz", "é", "$ref", "mj"]): value(depth + 1) for _ in range(rng.randint(0, 5))}

    for _ in range(300):
        original = value()
        store = {}
        root, _ = mj.encode(original, store, threshold=256)
        assert mj.canonical(mj.decode_root(root, mj.Reader(store))) == mj.canonical(original)


def test_values_that_look_like_nodes_or_references_are_just_values():
    tricky = {"mj": 1, "r": [[["v"], "a" * 64]], "v": {"v": None}, "pad": "p" * 3000}
    store = {}
    root, _ = mj.encode(tricky, store, threshold=1024)
    assert mj.decode_root(root, mj.Reader(store)) == tricky


def tampered_store(change):
    store = {}
    root, _ = mj.encode(history(6), store, threshold=1024)
    change(store, root)
    return store, root


def rewrite_node(store, digest, mutate):
    node = json.loads(store[digest])
    mutate(node)
    store[digest] = mj.canonical(node)


def leaf_digest(store, root):
    node = json.loads(store[root["digest"]])
    return node["r"][0][1]


@pytest.mark.parametrize("change", [
    lambda store, root: store.__setitem__(root["digest"], store[root["digest"]].replace('"run"', '"rux"')),
    lambda store, root: store.pop(leaf_digest(store, root)),
    lambda store, root: store.__setitem__(root["digest"], store[root["digest"]].replace(",", ", ", 1)),
    lambda store, root: rewrite_node(store, root["digest"], lambda n: n["v"].__setitem__("content", {"x": 1})),
])
def test_changed_missing_or_noncanonical_nodes_fail_closed(change):
    store, root = tampered_store(change)
    with pytest.raises(mj.MerkleError):
        mj.Reader(store).verify(root["digest"])
    with pytest.raises(mj.MerkleError):
        mj.decode_root(root, mj.Reader(store))


def forged(node):
    text = mj.canonical(node)
    return hashlib.sha256(text.encode()).hexdigest(), text


@pytest.mark.parametrize("node", [
    {"mj": 1, "r": [[["a"], "b" * 64]], "v": {"a": 5}},            # not a null placeholder
    {"mj": 1, "r": [[["a"], "b" * 64], [["a"], "c" * 64]], "v": {"a": None}},  # duplicate path
    {"mj": 1, "r": [[[0], "b" * 64]], "v": "scalar"},               # refs need a container
    {"mj": 2, "r": [], "v": {}},                                     # unknown format
    {"mj": 1, "r": [], "v": {}, "extra": 1},                         # unknown member
])
def test_self_consistent_but_malformed_nodes_are_rejected(node):
    digest, text = forged(node)
    with pytest.raises(mj.MerkleError):
        mj.Reader({digest: text}).node(digest)


def test_a_reference_cycle_is_rejected():
    # A real hash cycle is infeasible; the reader still refuses one structurally.
    store = {}
    reader = mj.Reader(store)
    reader.verified["a" * 64] = {"mj": 1, "r": [[["x"], "a" * 64]], "v": {"x": None}}
    with pytest.raises(mj.MerkleError, match="cycle"):
        reader.decode("a" * 64)

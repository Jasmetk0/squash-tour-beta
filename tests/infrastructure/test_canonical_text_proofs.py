"""The canonical-text verifier must decide EXACTLY canonical_json(loads(t)) == t.

Reference reuse may only skip byte-identical segments of texts it proved
itself; it must never turn a non-canonical, foreign or changed text into a pass.
"""

import json
import random

import pytest

from beta_engine.domain.run_revisions import canonical_json
from beta_engine.infrastructure.db import canonical_text
from beta_engine.infrastructure.db.canonical_text import (
    CanonicalTextProofs,
    Layout,
    ProvenCanonicalText,
    span,
    verify_canonical_text,
)

pytestmark = pytest.mark.pr_critical


def full(text):
    try:
        return canonical_json(json.loads(text)) == text
    except (ValueError, RecursionError):
        return False


def random_value(rng, depth=0):
    roll = rng.random()
    if depth > 4 or roll < 0.35:
        return rng.choice([
            0, 1, -7, 12, 10 ** 20, 1.5, -0.25, 1e-7, 3.0, True, False, None,
            "", "a", "é", "日本", "\u0000x", "line\nnext", 'q"uote', "back\\slash",
            "\ud800", float("nan"), float("inf"),
        ])
    if roll < 0.65:
        return [random_value(rng, depth + 1) for _ in range(rng.randint(0, 5))]
    keys = ["a", "b", "aa", "B", "é", "k1", "k10", "k2", "", "payload", "x" * 30]
    return {rng.choice(keys): random_value(rng, depth + 1) for _ in range(rng.randint(0, 6))}


NONCANONICAL_EDITS = [
    lambda t: t.replace(",", ", ", 1),
    lambda t: t.replace(":", ": ", 1),
    lambda t: " " + t,
    lambda t: t + " ",
    lambda t: t + "\n",
    lambda t: t.replace("3.0", "3", 1),
    lambda t: t.replace("1.5", "1.50", 1),
    lambda t: t.replace("1e-07", "1E-07", 1),
    lambda t: t.replace("12", "012", 1),
    lambda t: t.replace("\\u00e9", "é", 1),
    lambda t: t.replace("\\u00e9", "\\u00E9", 1),
    lambda t: t.replace('"a"', '"\\u0061"', 1),
    lambda t: t.replace("\\n", "\\u000a", 1),
    lambda t: t.replace("true", "True", 1),
    lambda t: t[:-1],
    lambda t: t + "}",
]


def test_random_values_and_edits_match_the_full_re_encoding_verdict():
    rng = random.Random(20261115)
    for _ in range(3000):
        value = random_value(rng)
        text = canonical_json(value)
        assert (verify_canonical_text(text) is not None) is full(text)
        for edit in NONCANONICAL_EDITS:
            changed = edit(text)
            assert (verify_canonical_text(changed) is not None) is full(changed), changed


def big_doc(events, *, note="n"):
    return {
        "branch": {"branch_id": "b", "display_name": "x"},
        "content": {
            "calendar_player_sporting_checkpoint": {
                "fingerprint": "f" * 64,
                "state": {"events": [{"week": i, "body": "r" * 20000, "n": [i, i * 1.5]}
                                     for i in range(events)], "schema_version": "v"},
            },
            "small": {"note": note},
        },
        "run": {"run_id": "run"},
    }


def test_reference_reuse_gives_the_same_verdict_for_every_tampered_child():
    parent = canonical_json(big_doc(5))
    parent_proof = verify_canonical_text(parent)
    assert parent_proof is not None and parent_proof.layout.keys is not None
    child = canonical_json(big_doc(6, note="changed"))
    proof = verify_canonical_text(child, parent_proof)
    assert proof is not None
    assert span(proof, ("content", "calendar_player_sporting_checkpoint", "state")) == canonical_json(
        big_doc(6, note="changed")["content"]["calendar_player_sporting_checkpoint"]["state"])
    tampered = [
        child.replace('"week":3}', '"week": 3}'),               # inside a reused prefix
        child.replace('"week":5}', '"week":05}'),                # inside the novel suffix
        child.replace('"n":[2,3.0]', '"n":[2,3.00]'),             # number spelling
        child.replace('"n":[2,3.0]', '"n":[2,3e0]'),
        child.replace('"schema_version":"v"', '"schema_version":"v","schema_version":"v"'),
        child.replace('"branch_id":"b","display_name"', '"display_name":"x","branch_id":"b","display_name"'),
        child.replace('"body":"rrrr', '"body":"\\u0072rrr', 1),
        child.replace(']', '] ', 1),
        child + " ",
        child.replace('{"body":', '{"body":"","body":', 1),
    ]
    for text in tampered:
        assert text != child
        assert full(text) is False
        assert verify_canonical_text(text, parent_proof) is None, text
        assert verify_canonical_text(text) is None, text


def test_number_prefix_of_a_reference_is_not_mistaken_for_the_value():
    parent = canonical_json({"a": [1, "x" * 20000], "b": 1})
    child = canonical_json({"a": [12, "x" * 20000], "b": 12})
    parent_proof = verify_canonical_text(parent)
    assert verify_canonical_text(child, parent_proof) is not None
    # "12.0" is the canonical spelling of a DIFFERENT value: still canonical.
    assert verify_canonical_text(child.replace("12", "12.0"), parent_proof) is not None
    assert verify_canonical_text(child.replace("12", "12.00"), parent_proof) is None
    assert verify_canonical_text(child.replace("12", "1"), parent_proof) is not None


def test_forged_references_and_spans_are_refused():
    child = canonical_json(big_doc(3)).replace(",", ", ", 1)
    with pytest.raises(TypeError):
        verify_canonical_text(child, (child, Layout(0, len(child))))
    with pytest.raises(TypeError):
        ProvenCanonicalText(object(), child, Layout(0, len(child)))
    with pytest.raises(TypeError):
        span((child, Layout(0, len(child))), ())
    assert verify_canonical_text(child) is None


def test_proof_cache_matches_whole_strings_and_never_a_changed_text():
    proofs = CanonicalTextProofs()
    texts = [canonical_json(big_doc(n)) for n in range(1, 6)]
    for text in texts:
        assert proofs.prove(text, scope="run") is not None
    changed = texts[-1].replace('"week":2}', '"week": 2}')
    assert changed != texts[-1]
    assert proofs.prove(changed, scope="run") is None
    # same length, different characters: never a cache hit
    flipped = texts[-1].replace('"note":"n"', '"note":"m"')
    assert len(flipped) == len(texts[-1])
    proof = proofs.prove(flipped, scope="run")
    assert proof is not None and proof.text == flipped
    other_scope = canonical_json(big_doc(6)).replace(":", ": ", 1)
    assert proofs.prove(other_scope, scope="other") is None


def test_memory_bound_keeps_at_most_the_configured_references(monkeypatch):
    monkeypatch.setattr(canonical_text, "MAX_REFERENCES", 2)
    proofs = CanonicalTextProofs()
    for n in range(1, 6):
        proofs.prove(canonical_json(big_doc(n)), scope="run")
    assert len(proofs._entries) == 2


def _mutate(rng, value, depth=0):
    """A structurally similar child: append, replace, drop or keep sub-values."""
    if isinstance(value, list):
        out = [(_mutate(rng, v, depth + 1) if rng.random() < 0.3 else v) for v in value]
        if rng.random() < 0.5:
            out.append(random_value(rng, depth + 1))
        if out and rng.random() < 0.1:
            out.pop(rng.randrange(len(out)))
        return out
    if isinstance(value, dict):
        out = {k: (_mutate(rng, v, depth + 1) if rng.random() < 0.3 else v) for k, v in value.items()}
        if rng.random() < 0.3:
            out[rng.choice(["a", "zz", "é", "k3"])] = random_value(rng, depth + 1)
        return out
    return random_value(rng, depth + 1) if rng.random() < 0.3 else value


def test_reference_descent_equals_full_verdict_on_random_children(monkeypatch):
    monkeypatch.setattr(canonical_text, "LAYOUT_THRESHOLD", 8)
    rng = random.Random(7)
    checked = 0
    for _ in range(1500):
        parent = {"x": random_value(rng), "y": [random_value(rng) for _ in range(4)]}
        parent_text = canonical_json(parent)
        parent_proof = verify_canonical_text(parent_text)
        assert (parent_proof is not None) is full(parent_text)
        if parent_proof is None:
            continue
        child_text = canonical_json(_mutate(rng, parent))
        candidates = [child_text] + [edit(child_text) for edit in NONCANONICAL_EDITS]
        for text in candidates:
            verdict = verify_canonical_text(text, parent_proof)
            assert (verdict is not None) is full(text), text
            if verdict is not None:
                assert verdict.text is text
            checked += 1
    assert checked > 10000


def _original_dependency_branches(row):
    from beta_engine.infrastructure.db.native_fork_runtime_state import _dependency_content

    content = _dependency_content(row[9])
    baseline = content.get("native_fork_baseline", {}).get("state")
    branches = {baseline.get("selected_source_branch_id")} if isinstance(baseline, dict) else set()
    if "calendar_tour_authority" in content:
        branches.add(row[2])
    return branches


@pytest.mark.parametrize("baseline", [
    "absent", {"state": {"selected_source_branch_id": "src"}}, {"state": {"selected_source_branch_id": None}},
    {"state": {}}, {"other": 1}, {"state": {"selected_source_branch_id": 7}}, {"state": [1]}, [1, 2], "text",
])
@pytest.mark.parametrize("tour", [True, False])
@pytest.mark.parametrize("canonical", [True, False])
def test_proven_dependency_branches_equal_the_original_parser(monkeypatch, baseline, tour, canonical):
    from beta_engine.infrastructure.db import native_fork_runtime_state

    monkeypatch.setattr(canonical_text, "PROOFS", CanonicalTextProofs())
    content = {"filler": "z" * 70000}
    if baseline != "absent":
        content["native_fork_baseline"] = baseline
    if tour:
        content["calendar_tour_authority"] = {"state": {"x": 1}}
    text = canonical_json({"content": content, "run": {"run_id": "run"}})
    if not canonical:
        text = text.replace(",", ", ", 1)
    row = [None] * 12
    row[0], row[1], row[2], row[9] = "rev", "run", "branch", text
    proven = native_fork_runtime_state._proven_dependency_branches(row)
    try:
        original = _original_dependency_branches(row)
    except (TypeError, ValueError, AttributeError):
        original = "error"
    if proven is not None:
        # Otherwise (None) the caller runs exactly the original parser below.
        assert canonical and proven == original
    references = native_fork_runtime_state._dependency_references
    try:
        result = set(references(None, row, "digest"))
    except ValueError:
        result = "error"
    assert result == original

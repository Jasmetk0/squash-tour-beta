"""Prove that exact stored JSON text IS its own canonical encoding.

Saved Revision content hashes are defined over ``canonical_json(value)`` of the
DECODED value (``sort_keys``, ``separators=(",", ":")``, ASCII escapes). Writers
store exactly that encoding, so re-encoding every decoded revision only to
rebuild the same bytes dominates cold validation of long histories.

``verify_canonical_text`` decides the pure property

    canonical_json(json.loads(text)) == text

for one exact string, returning a layout of its large containers, or ``None``
when the property does not hold or is not established. It never trusts a
declared hash, an identifier or a row: only the exact characters of ``text``.

A segment of ``text`` is accepted only if it is either

* byte-for-byte equal to a segment of a REFERENCE text that was itself proven
  canonical by this function (the reference is held as the actual string, not a
  digest), or
* decoded with the standard library parser and re-encoded with the canonical
  encoder to exactly the same characters.

Container syntax between segments is checked strictly: no whitespace, the
canonical key encoding, keys strictly ascending (which also rejects duplicate
keys) and the exact ``,``/``:`` separators. Hence the verdict is the same as the
full re-encoding comparison, while unchanged history is compared, not re-encoded.
Canonical form is a pure function of the characters; it grants no ownership,
lineage, source or sporting authority. Every caller keeps those gates.
"""

from __future__ import annotations

import hashlib
import json
from json.decoder import scanstring
from json.encoder import encode_basestring_ascii
from threading import Lock

# Only containers at least this long get a recorded layout (and are descended
# into when they differ from the reference); smaller values are re-encoded.
LAYOUT_THRESHOLD = 16 * 1024
MAX_DEPTH = 8
# Bounded process memory for reference texts kept alive between validations.
MAX_REFERENCE_CHARACTERS = 96 * 1024 * 1024
MAX_REFERENCES = 4

_decoder = json.JSONDecoder()


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class Layout:
    """Spans of one proven-canonical text; children only for large containers."""

    __slots__ = ("start", "end", "keys", "items")

    def __init__(self, start, end, keys=None, items=None):
        self.start = start
        self.end = end
        self.keys = keys    # dict: key -> Layout (objects)
        self.items = items  # list[Layout] (arrays)


class _NotCanonical(Exception):
    pass


def _leaf(text, pos):
    """Decode one value and require its canonical re-encoding at ``pos``."""
    try:
        value, end = _decoder.raw_decode(text, pos)
    except (ValueError, RecursionError) as exc:
        raise _NotCanonical from exc
    try:
        encoded = _canonical(value)
    except (TypeError, ValueError, RecursionError) as exc:
        raise _NotCanonical from exc
    if end - pos != len(encoded) or not text.startswith(encoded, pos):
        raise _NotCanonical
    return end


def _same(text, pos, ref_text, ref):
    """Byte-equal to a proven-canonical reference value at ``pos``."""
    length = ref.end - ref.start
    end = pos + length
    if length <= 0 or end > len(text):
        return False
    # Numbers are not self-delimiting ("1" is a prefix of "12"): the value at
    # ``pos`` is exactly the reference segment only if a delimiter follows.
    if end < len(text) and text[end] not in ",]}":
        return False
    if length <= 64:
        return text[pos:end] == ref_text[ref.start:ref.end]
    return text.startswith(ref_text[ref.start:ref.end], pos)


def _value(text, pos, ref_text, ref, depth):
    """Verify the value starting at ``pos``; return (end, Layout or None)."""
    if ref is not None and _same(text, pos, ref_text, ref):
        end = pos + (ref.end - ref.start)
        # A reference value is a complete JSON value; the container grammar of
        # the caller checks the delimiter that must follow it.
        return end, _relocated(ref, pos - ref.start)
    if pos >= len(text):
        raise _NotCanonical
    opener = text[pos]
    if depth < MAX_DEPTH and opener == "{" and ref is not None and ref.keys is not None:
        return _object(text, pos, ref_text, ref, depth)
    if depth < MAX_DEPTH and opener == "[" and ref is not None and ref.items is not None:
        return _array(text, pos, ref_text, ref, depth)
    if depth < MAX_DEPTH and opener in "{[":
        # No usable reference: still record a layout for large containers so
        # that LATER texts can reuse this one. Small ones are re-encoded whole.
        end = _leaf(text, pos)
        if end - pos >= LAYOUT_THRESHOLD:
            return _container_layout(text, pos, end, depth)
        return end, None
    return _leaf(text, pos), None


def _relocated(ref, shift):
    if shift == 0:
        return ref
    keys = None if ref.keys is None else {k: _relocated(v, shift) for k, v in ref.keys.items()}
    items = None if ref.items is None else [_relocated(v, shift) for v in ref.items]
    return Layout(ref.start + shift, ref.end + shift, keys, items)


def _container_layout(text, start, end, depth):
    """Layout of an ALREADY re-encode-verified large container (spans only)."""
    if text[start] == "{":
        layout, stop = _object(text, start, None, Layout(0, 0, keys={}), depth, _verified=True)
    else:
        layout, stop = _array(text, start, None, Layout(0, 0, items=[]), depth, _verified=True)
    if stop != end:
        raise _NotCanonical
    return end, layout


def _object(text, pos, ref_text, ref, depth, _verified=False):
    start = pos
    pos += 1
    keys = {}
    previous = None
    ref_keys = ref.keys or {}
    if text.startswith("}", pos):
        end = pos + 1
        return ((Layout(start, end, keys={}), end) if _verified else (end, Layout(start, end, keys={})))
    while True:
        if not text.startswith('"', pos):
            raise _NotCanonical
        try:
            key, after_key = scanstring(text, pos + 1, True)
        except ValueError as exc:
            raise _NotCanonical from exc
        if encode_basestring_ascii(key) != text[pos:after_key]:
            raise _NotCanonical
        if previous is not None and not previous < key:
            raise _NotCanonical  # unsorted or duplicate key
        previous = key
        if not text.startswith(":", after_key):
            raise _NotCanonical
        value_start = after_key + 1
        if _verified:
            value_end = _skip(text, value_start)
            child = None
            if value_end - value_start >= LAYOUT_THRESHOLD and depth + 1 < MAX_DEPTH and text[value_start] in "{[":
                child = _container_layout(text, value_start, value_end, depth + 1)[1]
        else:
            value_end, child = _value(text, value_start, ref_text, ref_keys.get(key), depth + 1)
        keys[key] = child if child is not None else Layout(value_start, value_end)
        if text.startswith(",", value_end):
            pos = value_end + 1
            continue
        if text.startswith("}", value_end):
            end = value_end + 1
            layout = Layout(start, end, keys=keys)
            return (layout, end) if _verified else (end, layout)
        raise _NotCanonical


def _array(text, pos, ref_text, ref, depth, _verified=False):
    start = pos
    pos += 1
    items = []
    ref_items = ref.items or []
    if text.startswith("]", pos):
        end = pos + 1
        return ((Layout(start, end, items=[]), end) if _verified else (end, Layout(start, end, items=[])))
    index = 0
    while True:
        if _verified:
            value_end = _skip(text, pos)
            child = None
            if value_end - pos >= LAYOUT_THRESHOLD and depth + 1 < MAX_DEPTH and text[pos] in "{[":
                child = _container_layout(text, pos, value_end, depth + 1)[1]
        else:
            value_end, child = _value(
                text, pos, ref_text, ref_items[index] if index < len(ref_items) else None, depth + 1)
        items.append(child if child is not None else Layout(pos, value_end))
        index += 1
        if text.startswith(",", value_end):
            pos = value_end + 1
            continue
        if text.startswith("]", value_end):
            end = value_end + 1
            layout = Layout(start, end, items=items)
            return (layout, end) if _verified else (end, layout)
        raise _NotCanonical


def _skip(text, pos):
    """End of the value at ``pos`` inside text already proven canonical."""
    try:
        return _decoder.raw_decode(text, pos)[1]
    except (ValueError, RecursionError) as exc:
        raise _NotCanonical from exc


_TOKEN = object()


class ProvenCanonicalText:
    """An exact string together with the layout THIS module proved for it.

    Only this module constructs it, so a caller cannot pass a fabricated layout
    or a foreign string as a reference.
    """

    __slots__ = ("text", "layout")

    def __init__(self, token, text, layout):
        if token is not _TOKEN:
            raise TypeError("ProvenCanonicalText is created only by verify_canonical_text")
        self.text = text
        self.layout = layout


def verify_canonical_text(text, reference=None):
    """Proof if ``canonical_json(json.loads(text)) == text``, else ``None``.

    ``reference`` may only be a ``ProvenCanonicalText`` returned earlier by this
    function; byte-identical segments of it are compared instead of re-encoded.
    """
    if not isinstance(text, str):
        return None
    if reference is not None and type(reference) is not ProvenCanonicalText:
        raise TypeError("reference must be a ProvenCanonicalText")
    ref_text, ref = (reference.text, reference.layout) if reference is not None else (None, None)
    try:
        end, layout = _value(text, 0, ref_text, ref, 0)
    except _NotCanonical:
        return None
    if end != len(text):
        return None
    return ProvenCanonicalText(_TOKEN, text, layout if layout is not None else Layout(0, end))


class CanonicalTextProofs:
    """Process cache of texts PROVEN canonical, held as the actual strings.

    A hit requires the complete candidate string to equal a stored proven
    string. A new text is verified with the most recent proof of the same scope
    as its reference, which only lets byte-identical segments skip re-encoding.
    """

    def __init__(self):
        self._lock = Lock()
        self._entries = []  # [(scope, ProvenCanonicalText)], most recent last

    def prove(self, text, *, scope):
        if not isinstance(text, str):
            return None
        with self._lock:
            entries = list(self._entries)
        for _, proof in reversed(entries):
            if proof.text is text or (len(proof.text) == len(text) and proof.text == text):
                return proof
        reference = next((proof for s, proof in reversed(entries) if s == scope), None)
        proof = verify_canonical_text(text, reference)
        if proof is None:
            return None
        with self._lock:
            self._entries = [e for e in self._entries if e[1].text is not text]
            self._entries.append((scope, proof))
            while len(self._entries) > MAX_REFERENCES or (
                len(self._entries) > 1
                and sum(len(e[1].text) for e in self._entries) > MAX_REFERENCE_CHARACTERS
            ):
                self._entries.pop(0)
        return proof


PROOFS = CanonicalTextProofs()


def span(proof, path):
    """Exact text of the value at ``path`` inside a proven-canonical text.

    The returned characters are themselves the canonical encoding of that
    sub-value (a canonical encoding is composed of canonical encodings).
    """
    if type(proof) is not ProvenCanonicalText:
        raise TypeError("span requires a ProvenCanonicalText")
    node = proof.layout
    for key in path:
        if node is None:
            return None
        if isinstance(key, int):
            node = node.items[key] if node.items is not None and 0 <= key < len(node.items) else None
        else:
            node = node.keys.get(key) if node.keys is not None else None
    if node is None:
        return None
    return proof.text[node.start:node.end]


def _non_ascii_free(text):
    # Without any \u escape the ASCII canonical encoding equals the
    # ensure_ascii=False encoding used by canonical_hash, character for
    # character (no non-ASCII character and no \u-escaped control character).
    return "\\u" not in text


def span_canonical_hash(proof, path):
    """``canonical_hash(value_at(path))`` from the proven exact span, or None."""
    text = span(proof, path)
    if text is None or not _non_ascii_free(text):
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def composite_canonical_hash(members):
    """``canonical_hash(dict)`` for ``{key: value}`` given each member's encoding.

    ``members`` maps each key to the exact canonical (ensure_ascii=False) text of
    its value. Returns None unless every text is free of \\u escapes.
    """
    parts = []
    for key in sorted(members):
        text = members[key]
        if not isinstance(key, str) or text is None or not _non_ascii_free(text) or not _non_ascii_free(key):
            return None
        parts.append(json.dumps(key, ensure_ascii=False) + ":" + text)
    return hashlib.sha256(("{" + ",".join(parts) + "}").encode("utf-8")).hexdigest()

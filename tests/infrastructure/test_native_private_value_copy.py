"""Full isolation, alias and immutable sporting-record gates for fast cache copies."""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import Field, PrivateAttr

from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.sporting import PlayerSportingRecord
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.native_fork_source_projection import _copy_decoded_value
from beta_engine.infrastructure.db.native_private_value_copy import private_copy

pytestmark = pytest.mark.pr_critical


class Child(FrozenInput):
    name: str
    nested: dict[str, list[int]]


class Parent(FrozenInput):
    children: tuple[Child, ...]
    annotations: list[dict[str, list[int]]]


class PrivateValue(FrozenInput):
    text: str
    _hidden: dict = PrivateAttr(default_factory=dict)


class CustomDeepcopy(FrozenInput):
    x: int

    def __deepcopy__(self, memo=None):
        copied = super().__deepcopy__(memo)
        object.__setattr__(copied, "x", copied.x + 1)
        return copied


def test_frozen_models_still_copied_privately_including_nested_mutable_fields():
    source = Parent(
        children=(Child(name="a", nested={"scores": [1, 2]}),),
        annotations=[{"codes": [5]}],
    )
    original_hash = canonical_hash(source.model_dump(mode="json"))
    result, _ = _copy_decoded_value(source)
    standard = deepcopy(source)
    assert result.model_dump(mode="json") == standard.model_dump(mode="json")
    assert result is not source
    assert result.__dict__ is not source.__dict__
    assert result.children is not source.children
    assert result.children[0] is not source.children[0]
    assert result.children[0].nested is not source.children[0].nested
    assert result.annotations[0] is not source.annotations[0]
    result.children[0].nested["scores"].append(999)
    result.annotations[0]["codes"].append(888)
    assert source.children[0].nested == {"scores": [1, 2]}
    assert source.annotations == [{"codes": [5]}]
    assert canonical_hash(source.model_dump(mode="json")) == original_hash
    reread, _ = _copy_decoded_value(source)
    assert reread == standard


def test_reused_mutable_aliases_remain_aliased_only_inside_new_private_copy():
    source_list = [1]
    source = {"first": source_list, "second": source_list}
    cloned = private_copy(source, {})
    assert cloned["first"] is cloned["second"]
    assert cloned["first"] is not source_list
    cloned["first"].append(2)
    assert cloned["second"] == [1, 2]
    assert source_list == [1]


def test_tuple_cycle_falls_back_to_standard_deepcopy_without_recursing_forever():
    inner = []
    source = (inner,)
    inner.append(source)
    result = private_copy(source, {})
    assert result is not source
    assert result[0] is not inner
    assert result[0][0] is result
    result[0].append("private")
    assert len(inner) == 1


def test_custom_pydantic_deepcopy_and_private_attrs_are_not_bypassed():
    original = CustomDeepcopy(x=5)
    result, _ = _copy_decoded_value(original)
    assert result.x == 6
    assert original.x == 5
    with_private = PrivateValue(text="hello")
    with_private._hidden["mutable"] = [1]
    clone, _ = _copy_decoded_value(with_private)
    assert clone is not with_private
    assert clone._hidden is not with_private._hidden
    clone._hidden["mutable"].append(2)
    assert with_private._hidden["mutable"] == [1]


def test_unknown_types_and_noncanonical_dict_keys_use_original_deepcopy():
    value = SimpleNamespace(payload={"x": [1]})
    result, _ = _copy_decoded_value(value)
    assert result is not value
    result.payload["x"].append(2)
    assert value.payload["x"] == [1]
    source = {(1, 2): ["data"]}
    clone, _ = _copy_decoded_value(source)
    assert clone == source and clone is not source
    clone[(1, 2)].clear()
    assert source[(1, 2)] == ["data"]


def test_player_sporting_record_custom_immutable_attributes_optimization_remains():
    record = PlayerSportingRecord(
        player_id="player-1",
        attributes=tuple((name, 120) for name in CANONICAL_PLAYER_ATTRIBUTES),
        potential_ovr=180,
        potential_identity="born-a",
        potential_provenance="test",
        development_timing="Standard",
        current_form=100,
        long_term_form_norm=100,
        match_sharpness=75,
        long_term_fatigue=0,
    )
    before = canonical_hash(record.model_dump(mode="json"))
    one, hints = _copy_decoded_value((record, record))
    assert one[0] is one[1]
    assert one[0] is not record
    assert one[0].attributes is record.attributes  # Proven immutable scalar tuple
    assert one[0].__dict__ is not record.__dict__
    object.__setattr__(one[0], "current_form", 55)
    assert record.current_form == 100
    assert canonical_hash(record.model_dump(mode="json")) == before
    assert hints
    second, _ = _copy_decoded_value((record,), hints)
    assert second[0].current_form == 100


def test_non_scalar_tuple_with_mixed_nested_copies_isolated():
    original = ({"player": ["real"]}, "checksum", 6)
    private, _ = _copy_decoded_value(original)
    assert private == original and private is not original
    private[0]["player"].append("forged")
    assert original[0]["player"] == ["real"]
    exact_scalar_tuple = ("immutable", 1, True, None, 3.5)
    copied, _ = _copy_decoded_value(exact_scalar_tuple)
    assert copied is exact_scalar_tuple

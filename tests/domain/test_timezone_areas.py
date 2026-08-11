import pytest
from beta_engine.domain.timezone_areas import RingDirection, TimezoneArea, circular_displacement, validate_timezone_areas

def areas(count: int):
    return [TimezoneArea(code=f"A{i}", name=f"Area {i}", position=i) for i in range(count)]

@pytest.mark.parametrize("count", [1, 3, 4, 7])
def test_arbitrary_counts_have_deterministic_position_order(count):
    expected=areas(count)
    assert validate_timezone_areas(list(reversed(expected))) == expected

def test_first_and_last_are_adjacent_in_both_directions():
    ring=areas(5)
    assert circular_displacement(ring,"A0","A4").model_dump()=={"transitions":1,"direction":RingDirection.BACKWARD}
    assert circular_displacement(ring,"A4","A0").model_dump()=={"transitions":1,"direction":RingDirection.FORWARD}

def test_shortest_direction_and_even_ring_tie_are_structural():
    ring=areas(6)
    assert circular_displacement(ring,"A0","A2").direction == RingDirection.FORWARD
    assert circular_displacement(ring,"A0","A4").direction == RingDirection.BACKWARD
    assert circular_displacement(ring,"A0","A3").model_dump()=={"transitions":3,"direction":RingDirection.TIE}

@pytest.mark.parametrize("bad", [
    [TimezoneArea(code="A",name="A",position=0),TimezoneArea(code="A",name="B",position=1)],
    [TimezoneArea(code="A",name="A",position=1)],
])
def test_malformed_registry_rejected(bad):
    with pytest.raises(ValueError): validate_timezone_areas(bad)


def test_zero_displacement_is_nondirectional():
    assert circular_displacement(areas(4), "A2", "A2").model_dump() == {"transitions": 0, "direction": RingDirection.NONE}

@pytest.mark.parametrize(("source", "destination", "message"), [("MISSING", "A0", "unknown source"), ("A0", "MISSING", "unknown destination")])
def test_unknown_endpoints_fail(source, destination, message):
    with pytest.raises(ValueError, match=message):
        circular_displacement(areas(4), source, destination)


def test_empty_authored_registry_is_rejected():
    with pytest.raises(ValueError, match="at least one area"):
        validate_timezone_areas([])

import pytest

from beta_engine.domain.calendar.season_labels import (
    long_season_label_from_start_year,
    normalize_season_label,
    season_label_from_start_year,
    season_start_year_from_label,
    to_compact_season_label,
    to_long_season_label,
)


def test_normalize_compact_label() -> None:
    assert normalize_season_label("2000/01") == "2000/01"


def test_normalize_long_label() -> None:
    assert normalize_season_label("2000/2001") == "2000/01"


def test_start_year_from_compact_label() -> None:
    assert season_start_year_from_label("2000/01") == 2000


def test_start_year_from_long_label() -> None:
    assert season_start_year_from_label("2000/2001") == 2000


def test_long_label_from_start_year() -> None:
    assert long_season_label_from_start_year(2000) == "2000/2001"


def test_compact_label_from_start_year() -> None:
    assert season_label_from_start_year(2049) == "2049/50"


def test_roundtrip_helpers() -> None:
    assert to_compact_season_label("1999/2000") == "1999/00"
    assert to_long_season_label("1999/00") == "1999/2000"


@pytest.mark.parametrize("label", ["2000", "2000/3", "2000/03", "2000/2003", "2000-2001", "abcd/ef"])
def test_malformed_labels_raise(label: str) -> None:
    with pytest.raises(ValueError):
        normalize_season_label(label)

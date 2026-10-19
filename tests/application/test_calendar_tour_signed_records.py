"""Fast, strict Saved Tour career records and tied-holder chronology."""
import pytest

from beta_engine.application.calendar_tour_signed_records import (
    signed_tour_records,
)
from tests.application.test_calendar_tour_season_summary import fixture

pytestmark = pytest.mark.pr_critical


def record(result, scope, metric):
    return next(
        r for r in result["records"]
        if (r["scope"], r["metric"]) == (scope, metric)
    )


def test_two_closed_seasons_preserve_tied_titles_and_true_awards():
    state, world = fixture(closing=2)
    result = signed_tour_records(state, world)
    assert result["schema_version"] == "native_tour_signed_records.v1"
    assert result["completed_seasons"] == [0, 1]
    assert result["completed_edition_count"] == 2
    titles = record(result, "player", "titles")
    assert titles["value"] == 1
    assert [row["entity_id"] for row in titles["holders"]] == [
        "player-a", "player-b",
    ]
    assert [(row["season_index"], row["change"], row["holder_ids"])
            for row in titles["holder_history"]] == [
        (0, "established", ["player-a"]),
        (1, "tied", ["player-a", "player-b"]),
    ]
    assert [row["rank"] for row in titles["leaderboard"]] == [1, 1]
    points = record(result, "player", "awarded_points")
    assert points["value"] == 180
    assert points["holders"][0]["entity_id"] == "player-b"
    assert points["leaderboard"][0]["awarded_points"] == 180
    assert points["holder_history"][-1]["change"] == "improved"
    national = record(result, "country", "titles")
    assert {p["entity_id"] for p in national["holders"]} == {"CZE", "USA"}
    assert record(result, "country", "awarded_points")["value"] == 240


def test_historical_as_of_does_not_leak_next_season_results():
    state, world = fixture(closing=2)
    early = signed_tour_records(state, world, as_of_season_index=0)
    assert early["source_seasons"][0]["boundary_command_id"] == "close-0"
    assert early["completed_seasons"] == [0]
    assert record(early, "player", "titles")["holders"][0]["entity_id"] == "player-a"
    assert record(early, "player", "awarded_points")["value"] == 100
    assert len(record(early, "player", "titles")["holder_history"]) == 1
    with pytest.raises(ValueError, match="not Signed and completed"):
        signed_tour_records(state, world, as_of_season_index=2)


def test_fixed_period_and_country_filter_recompute_holders_from_start():
    state, world = fixture(closing=2)
    recent = signed_tour_records(
        state, world, as_of_season_index=1,
        from_season_index=1, country_code="CZE",
    )
    assert recent["completed_seasons"] == [1]
    assert recent["country_code"] == "CZE"
    titles = record(recent, "player", "titles")
    assert titles["value"] == 0 and titles["holders"] == []
    assert titles["leaderboard"] == [] and titles["holder_history"] == []
    assert record(recent, "player", "finals")["holders"][0]["entity_id"] == "player-a"
    assert record(recent, "player", "awarded_points")["value"] == 65
    assert [v["entity_id"] for v in record(recent, "country", "awarded_points")["holders"]] == ["CZE"]
    assert recent["source_seasons"][0]["season_index"] == 1


def test_all_tied_holders_visible_even_when_leaderboard_is_limited():
    state, world = fixture(closing=2)
    result = signed_tour_records(state, world, leaderboard_limit=1)
    assert len(record(result, "player", "titles")["holders"]) == 2
    assert len(record(result, "player", "titles")["leaderboard"]) == 1
    assert record(result, "player", "titles")["leaderboard_total"] == 2


def test_no_completed_edition_does_not_create_zero_point_fake_records():
    state, world = fixture()
    state.editions = ()
    state.receipts = ()
    result = signed_tour_records(state, world)
    assert result["completed_edition_count"] == 0
    assert all(
        entry["value"] == 0 and not entry["holders"]
        and not entry["holder_history"] and not entry["leaderboard"]
        for entry in result["records"]
    )


@pytest.mark.parametrize("params", [
    {"as_of_season_index": -1},
    {"as_of_season_index": True},
    {"as_of_season_index": 2},
    {"from_season_index": -1},
    {"from_season_index": 1, "as_of_season_index": 0},
    {"from_season_index": True},
    {"country_code": "cze"},
    {"country_code": "CZE-1"},
    {"leaderboard_limit": 0},
    {"leaderboard_limit": 101},
    {"leaderboard_limit": True},
])
def test_invalid_or_unsigned_cutoff_and_filter_rejected(params):
    state, world = fixture()
    with pytest.raises(ValueError):
        signed_tour_records(state, world, **params)


@pytest.mark.parametrize("tamper", ["winner", "field", "scope"])
def test_no_unauthenticated_champion_field_or_foreign_identity(tamper):
    state, world = fixture(tamper=tamper)
    with pytest.raises(ValueError):
        signed_tour_records(state, world)


def test_no_foreign_world_and_no_unsigned_year():
    state, world = fixture()
    world.branch_id = "foreign"
    with pytest.raises(ValueError, match="same Saved Run/Branch"):
        signed_tour_records(state, world)
    state, world = fixture(closing=0)
    with pytest.raises(ValueError, match="at least one"):
        signed_tour_records(state, world)

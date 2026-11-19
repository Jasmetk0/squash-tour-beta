"""Fast real-domain plan checks; the long HTTP load is explicitly opt-in."""
import pytest

from beta_engine.domain.tournaments.calendar_tour import required_stages
from scripts.giant_native_five_season_load import (
    EDITION_COUNT_PER_SEASON,
    MAIN_WEEKS,
    EXTRA_WEEKS,
    cohort_weeks,
    make_schedule,
    unsupported_execution_capabilities,
)

pytestmark = pytest.mark.pr_critical


def test_requested_profile_is_300_different_real_season_week_events():
    schedule = make_schedule()
    assert EDITION_COUNT_PER_SEASON == 60
    assert len(MAIN_WEEKS) == 47 and len(EXTRA_WEEKS) == 12
    assert len(schedule) == 300
    assert len({e.edition_id for e in schedule}) == 300
    assert {e.season for e in schedule} == set(range(5))
    assert all(sum(e.season == year for e in schedule) == 60 for year in range(5))
    assert {e.size for e in schedule} == {16, 32, 64, 128}
    assert all(4 <= e.week <= 51 and e.week - 2 >= 2 for e in schedule)
    assert all(sum(e.is_world_championship for e in schedule if e.season == year) == 1
               for year in range(5))
    worlds = [e for e in schedule if e.is_world_championship]
    assert len(worlds) == 5
    assert all((e.week, e.size, e.points, e.qualification_size, e.qualifier_spots)
               == (51, 128, 3000, 32, 4) for e in worlds)
    # Multiple independent Editions really share a week in the scenario.
    assert max(sum(e.season == 0 and e.week == week for e in schedule)
               for week in MAIN_WEEKS) >= 3


def test_requested_qualifying_profile_and_strict_engine_limit_detection():
    scenario = make_schedule()
    qualifying = [e for e in scenario if e.qualification_size]
    assert len(qualifying) > 50
    assert all(e.qualifier_spots == 4 and e.qualification_size in (16, 32)
               for e in qualifying)
    assert all(tuple(e.qualifying_point_table) == (
        ("qualification_winner", "qualification_final", "qualification_semifinal")
        if e.qualification_size == 16
        else ("qualification_winner", "qualification_final",
              "qualification_semifinal", "qualification_round"))
        for e in qualifying)
    assert all(not e.qualifying_point_table for e in scenario if not e.qualification_size)
    assert all(e.expected_played_matches ==
               e.size - 1 + max(0, e.qualification_size - e.qualifier_spots)
               for e in scenario)
    codes = {problem["code"] for problem in unsupported_execution_capabilities(scenario)}
    assert codes == {
        "configured_native_v2_main_not_16_to_128",
        "native_v2_qualification_not_supported",
    }


def test_every_ranked_edition_has_full_exact_stage_table_with_distinct_points():
    schedule = make_schedule()
    assert len({e.points for e in schedule}) >= 6
    for e in schedule:
        assert tuple(e.point_table) == required_stages(e.size)
        assert e.point_table["champion"] == e.points
        values = list(e.point_table.values())
        assert len(values) == e.size.bit_length()
        assert all(x > y >= 0 for x, y in zip(values, values[1:]))


def test_four_birth_waves_per_season_and_80_each_are_explicit():
    assert cohort_weeks(0) == (3, 15, 28, 41)
    assert cohort_weeks(1) == (2, 14, 27, 40)
    assert cohort_weeks(4) == (2, 14, 27, 40)
    assert len({(season, wave, athlete)
                for season in range(5)
                for wave in cohort_weeks(season)
                for athlete in range(20)}) == 400


def test_separate_compatible_profile_has_no_fake_large_draw_or_qualification():
    compatible = make_schedule(profile="compatible")
    assert len(compatible) == 300
    assert {e.size for e in compatible} == {4, 8}
    assert all(e.qualification_size == e.qualifier_spots == 0 for e in compatible)
    assert all(e.is_world_championship and e.size == 8 for e in compatible
               if e.week == 51)
    assert unsupported_execution_capabilities(compatible) == []
    assert all(not e.qualifying_point_table for e in compatible)
    assert len({e.edition_id for e in compatible}) == 300
    for e in compatible:
        assert tuple(e.point_table) == required_stages(e.size)


def test_short_schedules_remain_deterministic_without_world_claim():
    left = make_schedule(seasons=2, editions_per_season=3)
    right = make_schedule(seasons=2, editions_per_season=3)
    assert left == right
    assert len(left) == 6
    assert [e.week for e in left] == [4, 5, 6, 4, 5, 6]
    assert not any(e.is_world_championship for e in left)
    for kwargs in ({"seasons": 0}, {"seasons": 6},
                   {"editions_per_season": 0}, {"editions_per_season": 61},
                   {"profile": "unsupported"}):
        with pytest.raises(ValueError):
            make_schedule(**kwargs)

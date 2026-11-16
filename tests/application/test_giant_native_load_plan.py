"""Fast planning contracts only; never execute the five-season benchmark in pytest."""
import pytest

from beta_engine.domain.tournaments.calendar_tour import required_stages
from scripts.giant_native_five_season_load import (
    EVENT_WEEKS,
    TIERS,
    make_schedule,
)

pytestmark = pytest.mark.pr_critical


def test_default_plan_is_five_actual_seasons_120_diverse_editions():
    schedule = make_schedule()
    assert len(schedule) == 120
    assert len({row.edition_id for row in schedule}) == 120
    assert {row.season for row in schedule} == set(range(5))
    assert {row.week for row in schedule} == set(EVENT_WEEKS)
    assert all(sum(row.season == year for row in schedule) == 24 for year in range(5))
    assert {row.tier for row in schedule} == {tier for tier, _, _ in TIERS}
    assert {row.size for row in schedule} == {4, 8, 16, 32}
    assert all(row.week - 2 >= 2 and row.week <= 50 for row in schedule)


def test_every_ranked_edition_has_exact_engine_stage_table():
    for row in make_schedule():
        assert tuple(row.point_table) == required_stages(row.size)
        assert row.point_table["champion"] == row.points
        values = list(row.point_table.values())
        assert len(values) == row.size.bit_length() + 1
        assert all(x > y >= 0 for x, y in zip(values, values[1:]))


def test_partial_plans_cannot_exceed_horizon_or_repeat_ids():
    schedule = make_schedule(seasons=2, editions_per_season=3)
    assert len(schedule) == 6
    assert [row.week for row in schedule] == [4, 6, 8, 4, 6, 8]
    assert len({row.edition_id for row in schedule}) == len(schedule)
    for kwargs in (
        {"seasons": 0}, {"seasons": 6},
        {"editions_per_season": 0}, {"editions_per_season": 25}
    ):
        with pytest.raises(ValueError):
            make_schedule(**kwargs)

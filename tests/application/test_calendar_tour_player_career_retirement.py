"""Retirement summary of the native player career (pure projection, minimal state).

Component test over a hand-built Saved-Tour-shaped state: the HTTP/SQLite acceptance
fixtures cannot reach the automatic retirement age. Covers the Master v87 never-pro
exception, the historical-rule wording and the as-of boundary.
"""

from types import SimpleNamespace

import pytest

from beta_engine.application.calendar_tour_player_career import native_player_career
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition

pytestmark = pytest.mark.pr_critical

CLOCK = RunCalendar(10, 1, 2030, 2)
F = "f" * 64


def wk(n):
    return RunWeekPosition(calendar=CLOCK, season_index=0, week=n)


def build(*, v87, retire_at=6):
    ranking = lambda n, rank: SimpleNamespace(  # noqa: E731
        run_calendar=CLOCK.to_metadata(), week=SimpleNamespace(season_index=0, week=n),
        rows=[SimpleNamespace(player_id="P", rank=rank, points=0)], fingerprint=str(n) * 64,
    )
    retire = SimpleNamespace(
        retired_player_ids=("P",), target_week=wk(retire_at),
        sporting_advance_fingerprint="a" * 64, command_id="retire-week", turn_pro_decisions=(),
    )
    state = SimpleNamespace(
        run_id="r", branch_id="b", week=wk(8), fingerprint=F, schema_version="calendar_tour_authority.v1",
        rankings=[ranking(2, 40), ranking(3, 12)], transitions=[retire], editions=[], receipts=[],
        pre_tour_turn_pro=None,
    )
    world = SimpleNamespace(
        run_id="r", branch_id="b", fingerprint=F,
        players=[SimpleNamespace(player_id="P", name="Pat", country_code="CZE")],
        initial_turn_pro=SimpleNamespace(professional_player_ids=()) if v87 else None,
    )
    return state, world


def test_never_pro_retirement_summary_states_the_v87_exception_without_a_cause():
    state, world = build(v87=True)
    career = native_player_career(state, world, "P")
    summary = career["retirement_summary"]
    # P is in the ranking, but no Turn Pro decision/opening evidence exists: the exception.
    assert summary["without_turn_pro"] is True and summary["without_tour_entry"] is None
    assert summary["retired_week"]["week"] == 6 and summary["career_high_rank"] == 12
    assert summary["source"]["command_id"] == "retire-week"
    assert "no cause of retirement is implied" in summary["note"]
    retirement = next(m for m in career["milestones"] if m["kind"] == "retirement")
    assert retirement["detail"] == {"without_turn_pro": True}
    assert career["overview"]["status"] == "retired"


def test_historical_rule_says_no_tour_entry_not_turn_pro():
    state, world = build(v87=False)
    summary = native_player_career(state, world, "P")["retirement_summary"]
    assert summary["turn_pro_rule"] is False
    assert summary["without_turn_pro"] is None and summary["without_tour_entry"] is True
    retirement = next(m for m in native_player_career(state, world, "P")["milestones"] if m["kind"] == "retirement")
    assert retirement["detail"] == {"without_tour_entry": True}


def test_before_retirement_there_is_no_summary_and_no_future_fact():
    state, world = build(v87=True)
    earlier = native_player_career(state, world, "P", as_of_ordinal=4)  # before week 6 (ordinal 5)
    assert earlier["retirement_summary"] is None
    assert not [m for m in earlier["milestones"] if m["kind"] == "retirement"]
    assert earlier["overview"]["status"] != "retired"
    with pytest.raises(ValueError, match="cannot be later"):
        native_player_career(state, world, "P", as_of_ordinal=99)
    with pytest.raises(KeyError):
        native_player_career(state, world, "nobody")

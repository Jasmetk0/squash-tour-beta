"""Master v87: the native Tour ranking roster comes from Turn Pro, not applications."""

from types import SimpleNamespace

import pytest

from beta_engine.domain.players.calendar_lifecycle import advance_calendar_lifecycle
from beta_engine.domain.players.turn_pro import turn_pro_tie_break_token
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.tournaments.calendar_tour import (
    calculate_tour_ranking,
    professional_ranking_players,
    ranking_week,
)
from tests.domain.test_turn_pro_lifecycle import (
    application, bootstrap, decision, week,
)

pytestmark = pytest.mark.pr_critical


def v87_lifecycle_at_week3():
    start = bootstrap("turn_pro.v87")
    w2 = advance_calendar_lifecycle(start, week(2), (), (decision("a", 2),))
    return advance_calendar_lifecycle(w2, week(3), (), (decision("a", 2), decision("b", 3)))


def test_pro_without_any_application_is_in_the_roster_from_the_next_snapshot():
    lifecycle = v87_lifecycle_at_week3()
    roster = professional_ranking_players(lifecycle, before=week(3), retired=())
    assert [(p.player_id, p.tour_entry_week) for p in roster] == [("a", ranking_week(week(2)))]
    assert roster[0].tie_break_token == turn_pro_tie_break_token(
        run_id="r", branch_id="b", player_id="a"
    )
    # "b" turned pro in the week being published: not inserted into that snapshot.
    later = professional_ranking_players(lifecycle, before=week(4), retired=("b",))
    assert [(p.player_id, p.retired) for p in later] == [("a", False), ("b", True)]
    # A season-closing roster (no boundary) contains every recorded professional.
    assert [p.player_id for p in professional_ranking_players(lifecycle)] == ["a", "b"]


def test_professional_roster_refuses_the_historical_policy():
    legacy = advance_calendar_lifecycle(bootstrap(), week(2), (application("a", 1),))
    with pytest.raises(ValueError, match="requires the v87 lifecycle policy"):
        professional_ranking_players(legacy)


def _state(submissions=()):
    edition = SimpleNamespace(
        result_confirmed=False, submissions=submissions,
        edition=SimpleNamespace(week=week(1), edition_id="e"),
    )
    return SimpleNamespace(
        run_id="r", branch_id="b", editions=(edition,), rankings=(None,),
        policies=(SimpleNamespace(effective_week=week(1),
                                  ranking=OfficialRankingPolicy(policy_id="rank")),),
    )


def test_tour_ranking_switches_roster_source_only_for_v87():
    checkpoint = SimpleNamespace(tournaments=())
    target = week(3)
    lifecycle = v87_lifecycle_at_week3()
    # Even a stray application row cannot add "b" to the v87 roster.
    v87 = calculate_tour_ranking(
        _state((application("b", 1),)), checkpoint, target=target, lifecycle=lifecycle,
    )
    legacy_life = advance_calendar_lifecycle(bootstrap(), week(2), (application("b", 1),))
    legacy = calculate_tour_ranking(
        _state((application("b", 1),)), checkpoint, target=target, lifecycle=legacy_life,
    )
    without = calculate_tour_ranking(
        _state((application("b", 1),)), checkpoint, target=target,
    )
    assert {r.player_id for r in v87.rows} == {"a"}
    assert {r.player_id for r in legacy.rows} == {"b"}
    assert legacy == without

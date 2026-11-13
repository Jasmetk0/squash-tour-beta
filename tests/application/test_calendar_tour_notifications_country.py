"""Country follows: domestic leaders alert, other representatives and other countries do not.

Pure component test over a hand-built Saved-Tour-shaped state (the real HTTP fixture has
too few players to separate a domestic leader from an ordinary representative). It also
pins the dedup of a fact that matches both a player and a country follow, the grouping
window, and that muting a follow removes only the derived card.
"""

from types import SimpleNamespace

import pytest

from beta_engine.application.calendar_tour_notifications import (
    DOMESTIC_LEADERS,
    derive_notifications,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition

pytestmark = pytest.mark.pr_critical

CLOCK = RunCalendar(10, 1, 2030, 2)
F = "f" * 64
CZ = ["A", "B", "C", "D", "E"]  # ranked 1..5 in the first snapshot
OTHER = "X"  # another country, ranked 6th


def wk(n):
    return RunWeekPosition(calendar=CLOCK, season_index=0, week=n)


def ranking_week(n):
    """Behaves like the real pydantic ranking week (model_dump) for the projection."""
    return SimpleNamespace(
        season_index=0, week=n, model_dump=lambda mode=None: {"season_index": 0, "week": n}
    )


def snapshot(n, order):
    return SimpleNamespace(
        run_calendar=CLOCK.to_metadata(), week=ranking_week(n),
        rows=[SimpleNamespace(player_id=p, rank=i + 1, points=100 - i) for i, p in enumerate(order)],
        fingerprint=str(n) * 64,
    )


def build():
    players = [SimpleNamespace(player_id=p, name=f"Player {p}", country_code="CZE") for p in CZ]
    players.append(SimpleNamespace(player_id=OTHER, name="Other", country_code="AUT"))
    state = SimpleNamespace(
        run_id="r", branch_id="b", week=wk(6), fingerprint=F, schema_version="calendar_tour_authority.v1",
        rankings=[snapshot(2, [*CZ, OTHER]), snapshot(3, [*CZ, OTHER])],
        transitions=[], editions=[], receipts=[], pre_tour_turn_pro=None,
    )
    world = SimpleNamespace(run_id="r", branch_id="b", fingerprint=F, players=players,
                            initial_turn_pro=SimpleNamespace(professional_player_ids=()))
    return state, world


def cards(follows, as_of=None):
    state, world = build()
    return derive_notifications(state, world, follows, "b", as_of)["cards"]


def test_country_follow_alerts_only_for_domestic_leaders():
    assert DOMESTIC_LEADERS == 3
    got = cards([("country", "CZE", True)])
    assert {c["player_id"] for c in got} == {"A", "B", "C"}  # best three of the country
    for card in got:
        assert card["reasons"] == ["country:CZE:domestic_leader"]
        # Ranking facts of one week form ONE card per player, each item with its own source.
        kinds = [i["kind"] for i in card["items"]]
        assert sorted(kinds) == ["career_high_ranking", "first_top_rank"]
        assert len({i["source"]["fingerprint"] for i in card["items"]}) == 1  # same snapshot
    # D and E (ordinary representatives) and the other country's player produce no alert.
    assert not {c["player_id"] for c in got} & {"D", "E", OTHER}


def test_player_follow_alerts_regardless_of_domestic_rank_and_dedups_with_country():
    both = cards([("country", "CZE", True), ("player", "A", True), ("player", "E", True)])
    by_player = {c["player_id"]: c for c in both}
    assert set(by_player) == {"A", "B", "C", "E"}
    # A matches the player AND the country follow: one card, both reasons, no duplicate items.
    assert by_player["A"]["reasons"] == ["country:CZE:domestic_leader", "player:A"]
    assert len(by_player["A"]["items"]) == 2
    # E is followed on its own although it is not a domestic leader.
    assert by_player["E"]["reasons"] == ["player:E"]


def test_muted_follow_creates_no_card_but_never_touches_facts():
    assert cards([("country", "CZE", False), ("player", "A", False)]) == []
    state, world = build()
    from beta_engine.application.calendar_tour_player_career import native_player_career

    assert native_player_career(state, world, "D")["milestones"]  # history exists for everyone


def test_card_keys_are_stable_and_historical_views_show_no_later_fact():
    first = cards([("player", "A", True)])
    assert cards([("player", "A", True)]) == first  # derived, so an exact retry is identical
    assert len({c["notification_key"] for c in first}) == len(first)
    assert cards([("player", "A", True)], as_of=0) == []  # before the first ranking (ordinal 1)
    with pytest.raises(ValueError, match="later than the Saved Tour"):
        cards([("player", "A", True)], as_of=999)
    # Another Branch id gives other keys: the same fact never aliases across Branches.
    state, world = build()
    other = derive_notifications(state, world, [("player", "A", True)], "sibling")["cards"]
    assert {c["notification_key"] for c in other}.isdisjoint({c["notification_key"] for c in first})


def test_country_success_keeps_the_leaders_at_the_facts_week():
    state, world = build()
    # C was a domestic leader at week 2, then falls outside the current top three.
    state.rankings.append(snapshot(6, ["E", "D", "A", "B", "C", OTHER]))
    result = derive_notifications(state, world, [("country", "CZE", True)], "b")
    assert any(
        item["player_id"] == "C" and item["kind"] == "first_top_rank"
        and item["effective_week"]["week"] == 2
        for card in result["cards"] for item in card["items"]
    ), "A later ranking must not erase the country's recorded domestic-leader success"


def test_a_new_career_high_keeps_older_alert_facts_and_card_identity():
    state, world = build()
    state.rankings = [snapshot(2, ["B", "C", "D", "A", "E", OTHER])]
    before = derive_notifications(state, world, [("player", "A", True)], "b")["cards"]
    state.rankings.append(snapshot(3, ["A", "B", "C", "D", "E", OTHER]))
    after = derive_notifications(state, world, [("player", "A", True)], "b")["cards"]
    def signatures(cards):
        return {(i["kind"], i["source"]["fingerprint"]) for c in cards for i in c["items"]}
    assert signatures(before) <= signatures(after), "A career-high improvement must append, not replace history"
    assert before[0]["notification_key"] == after[0]["notification_key"]
    assert after[0]["item_count"] == before[0]["item_count"] + 1

"""Master v87 home opportunity: a public, upcoming Edition in the player's country."""

import json
from types import SimpleNamespace

import pytest

from beta_engine.application import calendar_tour_service as service
from beta_engine.domain.players.calendar_lifecycle import calendar_lifecycle_history
from beta_engine.domain.players.turn_pro_model import (
    build_turn_pro_candidates,
    decide_turn_pro,
    default_turn_pro_model_policy,
)
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarTourEdition,
    turn_pro_home_opportunities,
)
from tests.domain.test_turn_pro_lifecycle import bootstrap, week

pytestmark = pytest.mark.pr_critical


def edition(announce=2, play=5, host="CZE", edition_id="home"):
    return CalendarTourEdition(
        edition_id=edition_id, name="Small home event", week=week(play),
        announcement_week=week(announce), start_slot=1, main_entrant_count=13,
        ranked=False, point_table={}, validity_weeks=52,
        **({} if host is None else {"host_country_code": host}),
    )


def state(*editions):
    return SimpleNamespace(
        editions=tuple(SimpleNamespace(edition=e, submissions=()) for e in editions),
        transitions=(),
    )


def test_host_country_is_optional_and_keeps_historical_bytes():
    plain = edition(host=None)
    assert "host_country_code" not in json.loads(plain.model_dump_json())
    hosted = edition()
    assert CalendarTourEdition.model_validate_json(hosted.model_dump_json()) == hosted
    assert hosted.model_dump()["host_country_code"] == "CZE"
    with pytest.raises(ValueError):
        edition(host="cz")


@pytest.mark.parametrize("announce,play,host,target,expected", [
    (2, 5, "CZE", 3, True),    # announced in the completed week, played later
    (2, 5, "CZE", 5, True),    # played in the target week itself
    (3, 5, "CZE", 3, False),   # becomes public only at this transition
    (2, 4, "CZE", 5, False),   # already played
    (2, 5, "GER", 3, False),   # another country
    (2, 5, None, 3, False),    # no host country recorded
])
def test_only_public_upcoming_home_editions_count(announce, play, host, target, expected):
    home = turn_pro_home_opportunities(
        state(edition(announce, play, host)), week(target), {"a": "CZE", "b": "SVK"}
    )
    assert home == ({"a": True} if expected else {})
    assert turn_pro_home_opportunities(None, week(3), {"a": "CZE"}) == {}


def test_service_week_feeds_home_opportunity_into_the_model(monkeypatch):
    target = week(3)
    history = calendar_lifecycle_history(bootstrap("turn_pro.v87"), target, ())
    monkeypatch.setattr(service, "_lifecycle_history", lambda world, week, s: history)
    world = SimpleNamespace(players=(
        SimpleNamespace(player_id="a", country_code="CZE"),
        SimpleNamespace(player_id="b", country_code="SVK"),
    ))
    checkpoint = SimpleNamespace(players=(
        SimpleNamespace(player_id="a", ovr=50), SimpleNamespace(player_id="b", ovr=50),
    ))
    tour = state(edition())
    seen = []
    real = service.build_turn_pro_candidates

    def spy(*args, **kwargs):
        made = real(*args, **kwargs)
        seen.append(made)
        return made

    monkeypatch.setattr(service, "build_turn_pro_candidates", spy)
    _, decisions, model = service._turn_pro_week(world, tour, target, checkpoint, 9)
    assert [(c.player_id, c.home_opportunity) for c in seen[0]] == [
        ("a", True), ("b", False),
    ]
    expected = decide_turn_pro(
        predecessor=history[-2], target=target, policy=default_turn_pro_model_policy(),
        seed=9,
        candidates=build_turn_pro_candidates(
            history[-2], history[-1], {"a": 50, "b": 50},
            home_opportunity_by_player={"a": True},
        ),
    )
    assert decisions == expected and model == default_turn_pro_model_policy()

"""Master v87 Turn Pro: pure lifecycle contract, gating and historical byte safety."""

import json

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_lifecycle import (
    CalendarPlayerLifecycleIdentity,
    CalendarPlayerLifecycleState,
    advance_calendar_lifecycle,
    calendar_lifecycle_history,
)
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from beta_engine.domain.players.turn_pro import (
    PlayerTurnProDecision,
    require_professional_for_entry,
    turn_pro_tie_break_token,
)
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
)

pytestmark = pytest.mark.pr_critical

CLOCK = RunCalendar(52, 35, 2030, 3)


def week(n: int) -> RunWeekPosition:
    return RunWeekPosition(calendar=CLOCK, season_index=0, week=n)


def policy(rule=None) -> PlayerLifecyclePolicy:
    extra = {} if rule is None else {"tour_entry_rule": rule}
    return PlayerLifecyclePolicy(
        policy_id="stored", automatic_retirement_age=46,
        provenance="Stored initial world policy", **extra,
    )


def bootstrap(rule=None, *, retiring_player=False) -> CalendarPlayerLifecycleState:
    opening = week(1)
    birthday = week(3).calendar_position
    players = [
        CalendarPlayerLifecycleIdentity(
            player_id=pid, birth_year=2014, birth_year_week=10, age=16,
            source_generation_fingerprint=pid[0] * 64,
        )
        for pid in ("a", "b")
    ]
    if retiring_player:
        players.append(CalendarPlayerLifecycleIdentity(
            player_id="c", birth_year=birthday.calendar_year - 46,
            birth_year_week=birthday.year_week, age=45,
            source_generation_fingerprint="c" * 64,
        ))
    return CalendarPlayerLifecycleState(
        run_id="r", branch_id="b", week=opening, players=tuple(players),
        source_initial_world_fingerprint="f" * 64, policy=policy(rule),
    )


def decision(pid: str, n: int, **update) -> PlayerTurnProDecision:
    return PlayerTurnProDecision(
        run_id="r", branch_id="b", player_id=pid, effective_week=week(n),
        decision_source="player_ai", source_state_fingerprint="d" * 64,
        provenance="Reviewed player AI decision fixture",
    ).model_copy(update=update)


def application(pid: str, n: int) -> TournamentApplicationSubmissionAuthority:
    return TournamentApplicationSubmissionAuthority(
        schema_version="tournament_application_submission_authority.v2",
        application_id=f"e{n}:{pid}", run_id="r", branch_id="b", event_id=f"e{n}",
        player_id=pid, entry_window="main", submission_week=week(n),
        decision_slot_ordinal=1, nr_tie_break_token="application-token",
        validation_authority_id="review", validation_authority_fingerprint="c" * 64,
        provenance="Reviewed",
    )


def entries(state):
    return {p.player_id: p.tour_entry_week for p in state.players}


def test_historical_policy_keeps_its_exact_bytes_and_fingerprint():
    legacy = policy()
    assert json.loads(legacy.model_dump_json()) == {
        "policy_id": "stored", "automatic_retirement_age": 46,
        "provenance": "Stored initial world policy",
    }
    state = bootstrap()
    reloaded = CalendarPlayerLifecycleState.model_validate_json(state.model_dump_json())
    assert reloaded == state and reloaded.fingerprint == state.fingerprint
    assert "tour_entry_rule" not in state.model_dump_json()
    assert not legacy.requires_turn_pro

    v87 = bootstrap("turn_pro.v87")
    assert json.loads(v87.model_dump_json())["policy"]["tour_entry_rule"] == "turn_pro.v87"
    assert v87.fingerprint != state.fingerprint
    assert CalendarPlayerLifecycleState.model_validate_json(v87.model_dump_json()) == v87


def test_historical_policy_still_enters_through_its_first_application():
    advanced = advance_calendar_lifecycle(bootstrap(), week(2), (application("a", 1),))
    assert entries(advanced) == {"a": week(1), "b": None}
    with pytest.raises(ValueError, match="require the v87 lifecycle policy"):
        advance_calendar_lifecycle(bootstrap(), week(2), (), (decision("a", 2),))


def test_turn_pro_grants_entry_from_its_week_and_applications_follow_it():
    start = bootstrap("turn_pro.v87")
    w2 = advance_calendar_lifecycle(start, week(2), (), (decision("a", 2),))
    player = {p.player_id: p for p in w2.players}["a"]
    assert player.tour_entry_week == week(2)
    assert player.tie_break_token == turn_pro_tie_break_token(
        run_id="r", branch_id="b", player_id="a"
    )
    assert entries(w2)["b"] is None

    # Same-week application by the new pro is valid and changes nothing.
    w3 = advance_calendar_lifecycle(w2, week(3), (application("a", 2),), (decision("a", 2),))
    assert entries(w3) == {"a": week(2), "b": None}
    assert {p.player_id: p for p in w3.players}["a"].tie_break_token == player.tie_break_token


def test_an_application_never_creates_entry_under_v87():
    start = bootstrap("turn_pro.v87")
    with pytest.raises(ValueError, match="predates the player's Turn Pro week"):
        advance_calendar_lifecycle(start, week(2), (application("b", 1),))
    # Turning pro later cannot legitimise an earlier application.
    w2 = advance_calendar_lifecycle(start, week(2), (), (decision("b", 2),))
    with pytest.raises(ValueError, match="predates the player's Turn Pro week"):
        advance_calendar_lifecycle(w2, week(3), (application("b", 1),), (decision("b", 2),))


def test_entry_gate_is_a_no_op_for_history_and_strict_for_v87():
    legacy = bootstrap()
    require_professional_for_entry(legacy, "a", week(1))

    w2 = advance_calendar_lifecycle(bootstrap("turn_pro.v87"), week(2), (), (decision("a", 2),))
    require_professional_for_entry(w2, "a", week(2))
    with pytest.raises(ValueError, match="has not turned pro"):
        require_professional_for_entry(w2, "a", week(1))
    with pytest.raises(ValueError, match="has not turned pro"):
        require_professional_for_entry(w2, "b", week(2))
    with pytest.raises(ValueError, match="has not turned pro"):
        require_professional_for_entry(w2, "unknown", week(2))


@pytest.mark.parametrize("bad,message", [
    ([decision("a", 2), decision("a", 3)], "only once"),
    ([decision("a", 2, run_id="other")], "Foreign Turn Pro decision"),
    ([decision("zz", 2)], "absent from lifecycle"),
    ([decision("a", 1)], "not applied at its own week"),
])
def test_invalid_turn_pro_history_fails_closed(bad, message):
    with pytest.raises(ValueError, match=message):
        advance_calendar_lifecycle(bootstrap("turn_pro.v87"), week(2), (), tuple(bad))


def test_recorded_entry_cannot_be_rewritten_by_a_different_decision():
    w2 = advance_calendar_lifecycle(bootstrap("turn_pro.v87"), week(2), (), (decision("a", 2),))
    with pytest.raises(ValueError, match="conflicts with recorded Tour entry"):
        advance_calendar_lifecycle(w2, week(3), (), (decision("a", 3),))


def test_a_retired_player_cannot_turn_pro():
    start = bootstrap("turn_pro.v87", retiring_player=True)
    w2 = advance_calendar_lifecycle(start, week(2), ())
    with pytest.raises(ValueError, match="retired player cannot turn pro"):
        advance_calendar_lifecycle(w2, week(3), (), (decision("c", 3),))


def test_history_is_independent_of_decision_order_and_ignores_future_decisions():
    start = bootstrap("turn_pro.v87")
    forward = (decision("a", 2), decision("b", 3))
    one = calendar_lifecycle_history(start, week(3), turn_pro=forward)
    two = calendar_lifecycle_history(start, week(3), turn_pro=tuple(reversed(forward)))
    assert [s.fingerprint for s in one] == [s.fingerprint for s in two]
    assert entries(one[1]) == {"a": week(2), "b": None}
    assert entries(one[2]) == {"a": week(2), "b": week(3)}

    # A decision for a later week is invisible to an earlier snapshot.
    early = calendar_lifecycle_history(start, week(2), turn_pro=forward)
    assert entries(early[-1]) == {"a": week(2), "b": None}


def test_legacy_lifecycle_refuses_the_v87_rule_instead_of_ignoring_it():
    from beta_engine.domain.players.lifecycle import PlayerLifecycleWeekState
    from beta_engine.domain.rankings.official import RankingWeek

    with pytest.raises(ValueError, match="does not support the v87 Turn Pro rule"):
        PlayerLifecycleWeekState(
            run_id="r", branch_id="b", week=RankingWeek(season_index=0, week=1),
            players=(), source_initial_world_fingerprint="f",
            policy=policy("turn_pro.v87"),
        )

"""Official Ranking scaling seams keep the exact validation and values.

Pure domain tests. The previous-ranking owner check is compared with the
original per-row linear search kept verbatim below; the results memo is active
only inside a private replay scope and never remembers a failure.
"""

from types import SimpleNamespace

import pytest

from beta_engine.domain import replay_scope
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.calendar_native_ranking_bridge import (
    validate_previous_ranking_owner,
)
from beta_engine.domain.tournaments import calendar_tour

pytestmark = pytest.mark.pr_critical


def _original_owner_check(previous, previous_life, replay):
    """The pre-index implementation, verbatim (except the extracted inputs)."""
    from beta_engine.domain.tournaments.calendar_tour import ranking_week

    if previous is None or (
        (previous.run_id, previous.branch_id) != (replay.run_id, replay.branch_id)
        or previous.week != ranking_week(previous_life.week)
        or previous.run_calendar != previous_life.week.calendar.to_metadata()
    ):
        raise ValueError("Native Ranking bridge requires the exact previous Saved ranking")
    if any(
        row.player_id not in {person.player_id for person in previous_life.players}
        for row in previous.rows
    ):
        raise ValueError("Previous ranking contains an athlete not born at its publication")
    for row in previous.rows:
        prior = next(p for p in previous_life.players if p.player_id == row.player_id)
        if (
            prior.tour_entry_week is None
            or prior.tour_entry_week.ordinal >= previous_life.week.ordinal
            or prior.status == "retired"
        ):
            raise ValueError("Previous ranking contains an athlete without prior Tour Entry")


def _outcome(check, *args):
    try:
        check(*args)
    except ValueError as error:
        return str(error)
    return "ok"


def _case(rows, people, *, scope=("r", "b")):
    from beta_engine.domain.calendar.run_week_position import RunWeekPosition
    from beta_engine.domain.tournaments.calendar_tour import ranking_week

    clock = RunCalendar(8, 1, 2030, 3)
    week = RunWeekPosition(calendar=clock, season_index=0, week=5)
    life = SimpleNamespace(week=week, players=tuple(
        SimpleNamespace(
            player_id=pid,
            tour_entry_week=None if entry is None else SimpleNamespace(ordinal=entry),
            status=status,
        )
        for pid, entry, status in people
    ))
    previous = SimpleNamespace(
        run_id=scope[0], branch_id=scope[1], week=ranking_week(week),
        run_calendar=clock.to_metadata(),
        rows=tuple(SimpleNamespace(player_id=pid) for pid in rows),
    )
    return previous, life, SimpleNamespace(run_id="r", branch_id="b")


OK = ("a", 1, "active")
LATE = ("late", 4, "active")      # entered in the publication week itself
NEVER = ("never", None, "active")
GONE = ("gone", 2, "retired")


@pytest.mark.parametrize("rows,people,scope", [
    ((), (OK,), ("r", "b")),
    (("a",), (OK, LATE), ("r", "b")),
    (("a", "late"), (OK, LATE), ("r", "b")),
    (("never",), (OK, NEVER), ("r", "b")),
    (("gone",), (OK, GONE), ("r", "b")),
    (("unknown",), (OK,), ("r", "b")),
    # Message priority: an unborn row anywhere wins over an earlier bad Entry.
    (("never", "unknown"), (OK, NEVER), ("r", "b")),
    (("unknown", "never"), (OK, NEVER), ("r", "b")),
    # The FIRST occurrence of a duplicated identity is the one consulted.
    (("a",), (("a", None, "active"), OK), ("r", "b")),
    (("a",), (OK, ("a", None, "active")), ("r", "b")),
    (("a",), (OK,), ("foreign", "b")),
])
def test_indexed_previous_owner_check_matches_the_original_linear_search(rows, people, scope):
    args = _case(rows, people, scope=scope)
    assert _outcome(validate_previous_ranking_owner, *args) == _outcome(_original_owner_check, *args)


def test_missing_previous_ranking_still_blocks():
    _, life, replay = _case((), (OK,))
    for check in (validate_previous_ranking_owner, _original_owner_check):
        with pytest.raises(ValueError, match="exact previous Saved ranking"):
            check(None, life, replay)


def test_identity_values_binds_every_object_and_key_and_only_inside_a_scope():
    a, b = object(), object()
    calls = []

    def compute(value):
        return lambda: calls.append(value) or value

    assert replay_scope.identity_values("n", (a, b), compute(1)) == 1
    assert replay_scope.identity_values("n", (a, b), compute(2)) == 2  # no scope
    with replay_scope.replay_value_scope():
        assert replay_scope.identity_values("n", (a, b), compute(3), key=(1,)) == 3
        assert replay_scope.identity_values("n", (a, b), compute(4), key=(1,)) == 3
        assert replay_scope.identity_values("n", (b, a), compute(5), key=(1,)) == 5
        assert replay_scope.identity_values("n", (a, b), compute(6), key=(2,)) == 6
        assert replay_scope.identity_values("m", (a, b), compute(7), key=(1,)) == 7
        assert replay_scope.identity_values("n", (a,), compute(8), key=(1,)) == 8
    with replay_scope.replay_value_scope():  # a new scope remembers nothing
        assert replay_scope.identity_values("n", (a, b), compute(9), key=(1,)) == 9
    assert calls == [1, 2, 3, 5, 6, 7, 8, 9]


def test_published_results_memo_never_remembers_failure_or_crosses_a_clock(monkeypatch):
    authority, event = object(), object()
    first = RunCalendar(8, 1, 2030, 3)
    extended = RunCalendar(8, 1, 2030, 4)
    calls = []
    outcomes = iter([ValueError("detached"), ("r1",), ("r2",), ("r3",), ("r4",)])

    def rebuilt(a, e):
        calls.append((a, e))
        value = next(outcomes)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(calendar_tour, "edition_results", rebuilt)
    with replay_scope.replay_value_scope():
        with pytest.raises(ValueError, match="detached"):
            calendar_tour.published_edition_results(authority, event, first)
        assert calendar_tour.published_edition_results(authority, event, first) == ("r1",)
        assert calendar_tour.published_edition_results(authority, event, first) == ("r1",)
        # An equal-valued but distinct played event is rebuilt and re-checked.
        assert calendar_tour.published_edition_results(authority, object(), first) == ("r2",)
        assert calendar_tour.published_edition_results(authority, event, extended) == ("r3",)
    assert calendar_tour.published_edition_results(authority, event, first) == ("r4",)
    assert len(calls) == 5


def test_verified_results_cache_is_bounded_and_never_keeps_a_failure(monkeypatch):
    from beta_engine.domain.tournaments import calendar_native_tour_week as week

    monkeypatch.setattr(week, "_VERIFIED_RESULTS", type(week._VERIFIED_RESULTS)())
    monkeypatch.setattr(week, "_MAX_VERIFIED_RESULT_ENTRIES", 2)
    monkeypatch.setattr(week, "_MAX_VERIFIED_RESULTS", 3)
    calls = []
    outcomes = {"bad": ValueError("unverified"), "a": ("a1",), "b": ("b1", "b2"),
                "c": ("c1",), "big": ("x", "y", "z", "w")}

    def full(state, checkpoint, target, clock):
        calls.append(state)
        value = outcomes[state]
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(week, "_native_confirmed_results", full)

    def get(name):
        return week.native_confirmed_results(name, None, None, None, key=("k", name))

    for _ in range(2):
        with pytest.raises(ValueError, match="unverified"):
            get("bad")
    assert get("a") == ("a1",) and get("a") == ("a1",)
    assert get("b") == ("b1", "b2")          # 3 results in 2 entries: both kept
    assert week.native_results_cache_stats() == {"entries": 2, "results": 3}
    assert get("c") == ("c1",)               # evicts the least recently used "a"
    assert get("big") == ("x", "y", "z", "w")  # above the bound: never retained
    assert get("big") == ("x", "y", "z", "w")
    assert get("a") == ("a1",)
    assert calls == ["bad", "bad", "a", "b", "c", "big", "big", "a"]
    # No key (no private scope / unverified input): always the full path.
    assert week.native_confirmed_results("a", None, None, None, key=None) == ("a1",)
    assert calls[-1] == "a" and len(calls) == 9

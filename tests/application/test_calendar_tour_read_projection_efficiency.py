"""Pure equivalence checks for the authenticated Tour inspection read hot path.

No simulation, Saved write, database migration or large workload is performed.
"""
from types import SimpleNamespace as NS

import pytest

from beta_engine.application.calendar_tour_service import CalendarTourService


pytestmark = pytest.mark.pr_critical


def _owner(*, week, years, final_week, pending, nonneutral_health):
    clock = NS(weeks_per_year=final_week, season_count=years)
    position = NS(week=week, season_index=years - 1 if week == 0 else 0,
                  ordinal=week)
    cp = NS(week=position, fingerprint="same-checkpoint")
    edition = NS(edition=NS(week=NS(ordinal=week - 1), edition_id="event"),
                 result_confirmed=not pending)
    health = NS(players=(
        NS(records=(NS(lifecycle="Injured"),), permanent_consequences=())
        if nonneutral_health else
        NS(records=(NS(lifecycle="Recovered"),), permanent_consequences=()),
    ))
    ctx = (clock, None, None, health, cp, None, None)
    state = NS(checkpoint_fingerprint="same-checkpoint", editions=(edition,))
    return ctx, state


@pytest.mark.parametrize(
    "week,years,final_week,pending,health_issue",
    [
        (1, 2, 52, False, False),
        (9, 2, 52, True, False),
        (9, 2, 52, True, True),
        (52, 2, 52, False, False),
        (52, 2, 52, True, True),
        (52, 1, 52, False, False),
        (52, 1, 52, True, True),
    ],
)
def test_season_readiness_derived_from_single_week_check(
    week, years, final_week, pending, health_issue
):
    ctx, state = _owner(
        week=week, years=years, final_week=final_week,
        pending=pending, nonneutral_health=health_issue,
    )
    original_week = CalendarTourService._transition_blockers(
        state, ctx, season=False,
    )
    original_season = CalendarTourService._transition_blockers(
        state, ctx, season=True,
    )
    derived = CalendarTourService._season_blockers_from_week(
        original_week, ctx,
    )
    assert derived == original_season
    assert original_week == CalendarTourService._transition_blockers(
        state, ctx, season=False,
    )


def test_slot_index_keeps_first_accepted_slot_and_skips_non_slot_events():
    # The previous per-match scan selected the first matching slot, even when
    # an identical ID occurred again. Preserve that exact behavior.
    slots = (
        NS(number=1, accepted=(NS(match_id="a"), NS(match_id="b"))),
        NS(number=2, accepted=(NS(match_id="a"), NS(match_id="c"))),
        NS(number=3, other="event without accepted"),
    )
    checkpoint = NS(history_global_slots=slots)
    index = CalendarTourService._global_match_slot_index(checkpoint)
    assert index == {"a": 1, "b": 1, "c": 2}
    for match_id in ("a", "b", "c", "missing"):
        old = next(
            (
                slot.number
                for slot in checkpoint.history_global_slots
                if hasattr(slot, "accepted")
                and any(item.match_id == match_id for item in slot.accepted)
            ),
            None,
        )
        assert index.get(match_id) == old


def test_slot_index_legacy_events_fallback():
    checkpoint = NS(events=(
        NS(number=4, accepted=(NS(match_id="legacy"),)),
        NS(number=5, accepted=()),
    ))
    assert CalendarTourService._global_match_slot_index(checkpoint) == {"legacy": 4}


@pytest.mark.parametrize("reuse", [False, True])
def test_readiness_reuses_authenticated_lifecycle_within_same_snapshot(monkeypatch, reuse):
    """Only the expensive lifecycle DB decode is skipped; birth replay still runs."""
    from beta_engine.application import calendar_tour_service as module
    from beta_engine.domain.players import calendar_prospect_birth
    from beta_engine.infrastructure.db import run_prospect_source_state

    position = NS(week=9, season_index=0, ordinal=9)
    clock = NS(weeks_per_year=52, season_count=2,
               position_at_ordinal=lambda ordinal: NS(season_index=0, season_week=ordinal+1))
    checkpoint = NS(week=position, fingerprint="same-checkpoint")
    state = NS(run_id="run", branch_id="branch", editions=(),
               checkpoint_fingerprint="same-checkpoint")
    payload = {"run": "run"}
    owner = NS(saved_revision=NS(payload=payload))
    world = NS(world_package_id="world")
    ctx = (clock, owner, world, None, checkpoint, None, None)
    already_read = object()
    calls = {"load": 0, "birth": 0}

    class Session:
        def __init__(self):
            self.queries = 0

        def scalar(self, statement):
            self.queries += 1
            # Current Run has native prospects; no staged ranking corrections.
            return "a-prospect" if self.queries == 1 else None

    def load_lifecycle(*, session, run_id, branch_id, week):
        assert (run_id, branch_id, week) == ("run", "branch", position)
        calls["load"] += 1
        return already_read

    def birth_event(*, predecessor, target, source, world_package_id):
        assert predecessor is already_read
        assert target.ordinal == 10
        assert world_package_id == "world"
        calls["birth"] += 1

    monkeypatch.setattr(module, "get_lifecycle", load_lifecycle)
    monkeypatch.setattr(module, "RunWeekPosition", lambda **kw: NS(ordinal=kw["week"]))
    monkeypatch.setattr(
        run_prospect_source_state, "validate_live_run_prospect_source_against_saved",
        lambda session, payload, *, run_id: NS(for_week=lambda week: ("births", week)),
    )
    monkeypatch.setattr(calendar_prospect_birth, "build_calendar_prospect_birth_event",
                        birth_event)

    blockers = CalendarTourService._transition_blockers(
        state, ctx, Session(),
        **({"_verified_lifecycle": already_read} if reuse else {}),
    )
    assert blockers == ["saved_health_baseline_missing"]
    assert calls == {"load": 0 if reuse else 1, "birth": 1}

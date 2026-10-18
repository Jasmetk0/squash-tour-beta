"""Native lifecycle progression uses existing policy and actual first Entry."""

import json
from types import SimpleNamespace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_lifecycle import (
    CalendarPlayerLifecycleIdentity,
    CalendarPlayerLifecycleState,
    CalendarTourLifecycleState,
    advance_calendar_lifecycle,
)
from beta_engine.domain.players.calendar_sporting_week import (
    CalendarAnnualDevelopmentPolicy,
    develop_and_recover,
)
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
)
from tests.domain.test_calendar_sporting_week import population

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("width,offset", [(52, 35), (61, 37), (80, 80)])
def test_actual_birthday_retirement_entry_and_frozen_bootstrap(width, offset):
    clock = RunCalendar(width, offset, 2030, 3)
    opening = RunWeekPosition(calendar=clock, season_index=0, week=1)
    target = RunWeekPosition(calendar=clock, season_index=0, week=2)
    birthday = target.calendar_position
    baseline = CalendarPlayerLifecycleState(
        run_id="r",
        branch_id="b",
        week=opening,
        players=(
            CalendarPlayerLifecycleIdentity(
                player_id="p",
                birth_year=birthday.calendar_year - 46,
                birth_year_week=birthday.year_week,
                age=45,
                source_generation_fingerprint="a" * 64,
            ),
        ),
        source_initial_world_fingerprint="b" * 64,
        policy=PlayerLifecyclePolicy(
            policy_id="stored",
            automatic_retirement_age=46,
            provenance="Stored initial world policy",
        ),
    )
    original = baseline.model_dump_json()
    fp = baseline.fingerprint
    application = TournamentApplicationSubmissionAuthority(
        schema_version="tournament_application_submission_authority.v2",
        application_id="e:p",
        run_id="r",
        branch_id="b",
        event_id="e",
        player_id="p",
        entry_window="main",
        submission_week=opening,
        decision_slot_ordinal=1,
        nr_tie_break_token="stable",
        validation_authority_id="review",
        validation_authority_fingerprint="c" * 64,
        provenance="Reviewed",
    )
    future = application.model_copy(
        update={
            "submission_week": RunWeekPosition(calendar=clock, season_index=0, week=3)
        }
    )
    assert (
        advance_calendar_lifecycle(baseline, target, (future,))
        .players[0]
        .tour_entry_week
        is None
    )
    current = advance_calendar_lifecycle(baseline, target, (application,))
    p = current.players[0]
    assert (
        p.age,
        p.status,
        p.retirement_effective_week,
        p.tour_entry_week,
        p.tie_break_token,
    ) == (46, "retired", target, opening, "stable")
    assert current.predecessor_fingerprint == fp
    assert (
        CalendarTourLifecycleState.model_validate_json(current.model_dump_json())
        == current
    )
    assert baseline.model_dump_json() == original and baseline.fingerprint == fp
    with pytest.raises(ValueError, match="Foreign"):
        advance_calendar_lifecycle(
            baseline, target, (application.model_copy(update={"branch_id": "foreign"}),)
        )
    raw = json.loads(current.model_dump_json())
    raw["players"][0]["age"] = 45
    with pytest.raises(ValueError):
        CalendarTourLifecycleState.model_validate_json(json.dumps(raw))


def test_official_development_stops_for_already_retired_players_without_changing_historical_kernel():
    cp, world = population()
    world.lifecycle_policy = SimpleNamespace(automatic_retirement_age=19)
    policy = CalendarAnnualDevelopmentPolicy()
    args = {
        "completed_week": cp.week,
        "seed": 3,
        "policy": policy,
        "counts": tuple((p.player_id, 0) for p in cp.players),
    }
    assert develop_and_recover(cp, world, official=True, **args) == (
        cp.players,
        cp.players,
    )
    assert develop_and_recover(cp, world, **args)[1] != cp.players

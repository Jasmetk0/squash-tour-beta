"""Pure current-fact projection contracts; these are not fork integration tests."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.native_fork_baseline import (
    NativeForkBaseline,
    project_native_fork_baseline,
)
from beta_engine.domain.native_fork_source import (
    NativeForkComponentSource,
    NativeForkSavedSource,
    NativeForkSourceBinding,
)
from beta_engine.domain.players.calendar_health import (
    CalendarHealthProfile,
    CalendarHealthRecord,
)
from tests.domain.test_calendar_prospect_admission_bundle import checkpoint_for
from tests.domain.test_calendar_prospect_birth_event import lifecycle, week

pytestmark = pytest.mark.pr_critical


def inputs(width=52, offset=1):
    clock = RunCalendar(width, offset, 2030, 3)
    current = week(clock, 0, 3)
    life = lifecycle(clock, current)
    checkpoint = checkpoint_for(life)
    checkpoint.source_initial_world_fingerprint = life.source_initial_world_fingerprint
    profile = CalendarHealthProfile(
        player_id="existing",
        records=(
            CalendarHealthRecord(
                record_id="actual-injury",
                kind="Injury",
                condition_key="stored-input",
                lifecycle="Active",
                severity=21,
                affected_domains=("movement",),
                onset_week=week(clock, 0, 2),
                provenance="Explicit original Health fact",
            ),
        ),
    )
    health = SimpleNamespace(
        run_id="r",
        branch_id="b",
        week=current,
        players=(profile,),
        source_initial_world_fingerprint=life.source_initial_world_fingerprint,
        fingerprint="d" * 64,
    )
    tour = SimpleNamespace(
        run_id="r",
        branch_id="b",
        week=current,
        checkpoint_fingerprint=checkpoint.fingerprint,
        lifecycle_fingerprint=life.fingerprint,
        fingerprint="f" * 64,
        rankings=(SimpleNamespace(fingerprint="9" * 64),),
        slot_cursor=5,
    )
    binding = NativeForkSourceBinding(
        run_id="r",
        source=NativeForkSavedSource(
            revision_id="saved", branch_id="b", content_hash="a" * 64
        ),
        components=(
            NativeForkComponentSource(key="initial_world", content_hash="b" * 64),
        ),
        historical_sources=(
            NativeForkSavedSource(
                revision_id="pre-play", branch_id="b", content_hash="c" * 64
            ),
        ),
    )
    return {
        "binding": binding,
        "selected_source_branch_id": "b",
        "target_branch_id": "target",
        "week": current,
        "world_fingerprint": life.source_initial_world_fingerprint,
        "lifecycle": life,
        "health": health,
        "checkpoint": checkpoint,
        "tour": tour,
    }


@pytest.mark.parametrize("width,offset", [(7, 1), (52, 35), (61, 37), (80, 80)])
def test_baseline_copies_every_current_fact_without_healing_growth_or_historical_rebinding(
    width, offset
):
    values = inputs(width, offset)
    life = values["lifecycle"].model_dump_json()
    health = values["health"].players[0].model_dump_json()
    sport = values["checkpoint"].players[0].model_dump_json()
    baseline = project_native_fork_baseline(**values)
    assert (
        baseline.branch_id == "target"
        and baseline.source_binding.source.branch_id == "b"
    )
    assert baseline.lifecycle_players == values["lifecycle"].players
    assert baseline.health_players == values["health"].players
    assert baseline.sporting_players == values["checkpoint"].players
    assert baseline.slot_cursor == 5
    assert baseline.health_players[0].records[0].severity == 21
    assert baseline.health_players[0].records[0].lifecycle == "Active"
    assert baseline.sporting_players[0].current_form == 112
    assert baseline.sporting_players[0].long_term_fatigue == 4
    assert baseline.source_ranking_fingerprint == "9" * 64
    assert baseline.source_lifecycle_fingerprint == values["lifecycle"].fingerprint
    restored = NativeForkBaseline.model_validate_json(baseline.model_dump_json())
    assert restored == baseline and restored.fingerprint == baseline.fingerprint
    assert values["lifecycle"].model_dump_json() == life
    assert values["health"].players[0].model_dump_json() == health
    assert values["checkpoint"].players[0].model_dump_json() == sport
    another = project_native_fork_baseline(**(values | {"target_branch_id": "sibling"}))
    assert another.fingerprint != baseline.fingerprint
    assert another.sporting_players == baseline.sporting_players
    with pytest.raises(ValidationError):
        restored.health_players[0].records[0].severity = 0


@pytest.mark.parametrize(
    "mutation",
    [
        "same_owner",
        "foreign_source",
        "wrong_week",
        "different_checkpoint",
        "missing_health_player",
        "future_health",
        "health_date_after_original_source",
        "wrong_age",
    ],
)
def test_baseline_rejects_incoherent_current_authority(mutation):
    values = inputs()
    if mutation == "same_owner":
        values["target_branch_id"] = "b"
    elif mutation == "foreign_source":
        values["health"].branch_id = "foreign"
    elif mutation == "wrong_week":
        values["checkpoint"].week = week(values["week"].calendar, 0, 4)
    elif mutation == "different_checkpoint":
        values["tour"].checkpoint_fingerprint = "0" * 64
    elif mutation == "missing_health_player":
        values["health"].players = ()
    elif mutation == "health_date_after_original_source":
        values["health"].week = week(values["week"].calendar, 0, 1)
    elif mutation == "future_health":
        old = values["health"].players[0]
        values["health"].players = (
            old.model_copy(
                update={
                    "records": (
                        old.records[0].model_copy(
                            update={"onset_week": week(values["week"].calendar, 0, 4)}
                        ),
                    )
                }
            ),
        )
    else:
        life = values["lifecycle"]
        values["lifecycle"] = life.model_copy(
            update={"players": (life.players[0].model_copy(update={"age": 99}),)}
        )
        values["tour"].lifecycle_fingerprint = values["lifecycle"].fingerprint
    with pytest.raises(ValueError):
        project_native_fork_baseline(**values)


def test_compatible_horizon_extension_keeps_original_dated_facts():
    values = inputs()
    old_date = values["health"].players[0].records[0].onset_week
    values["week"] = week(RunCalendar(52, 1, 2030, 5), 0, 3)
    baseline = project_native_fork_baseline(**values)
    assert baseline.week.calendar.season_count == 5
    assert baseline.health_players[0].records[0].onset_week == old_date
    assert baseline.health_players[0].records[0].onset_week.calendar.season_count == 3


def test_older_saved_health_facts_remain_dated_and_do_not_invent_a_weekly_transition():
    values = inputs()
    original = values["health"].players[0].model_dump_json()
    values["health"].week = week(values["week"].calendar, 0, 2)
    baseline = project_native_fork_baseline(**values)
    assert baseline.week.week == 3 and baseline.source_health_week.week == 2
    assert baseline.health_players[0].model_dump_json() == original

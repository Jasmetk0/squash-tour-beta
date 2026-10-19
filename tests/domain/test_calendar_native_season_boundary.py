"""The new season event is explicit; historical sporting week hashes stay unchanged."""
import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_sporting_week import CalendarSportingWeekAdvance
from beta_engine.domain.run_packages import canonical_hash

pytestmark = pytest.mark.pr_critical


def boundary(clock, version="calendar_sporting_week_advance.v3", *, start=None, target=None):
    completed = start or RunWeekPosition(calendar=clock, season_index=0, week=clock.weeks_per_year)
    succeeding = target or RunWeekPosition(calendar=clock, season_index=1, week=1)
    command = {
        "command_id": "season-one",
        "expected_saved_head": "saved-one",
        "expected_checkpoint_fingerprint": "a" * 64,
        "seed": 2026,
        "operator_label": "Admin",
        "audit_reason": "Reviewed end-of-season boundary",
    }
    return CalendarSportingWeekAdvance(
        schema_version=version,
        scope=("configured_tour_season_transition" if version.endswith(".v3")
               else "configured_tour_week_transition"),
        run_id="run", branch_id="branch",
        command_id=command["command_id"],
        source_saved_head=command["expected_saved_head"],
        source_checkpoint_fingerprint=command["expected_checkpoint_fingerprint"],
        completed_week=completed, target_week=succeeding,
        seed=command["seed"], operator_label=command["operator_label"],
        audit_reason=command["audit_reason"],
        request_fingerprint=canonical_hash({
            "run_id": "run", "branch_id": "branch", "command": command,
        }),
        played_counts=(("player-a", 1), ("player-b", 0)),
        developed_players_fingerprint="b" * 64,
        recovered_players_fingerprint="c" * 64,
    )


@pytest.mark.parametrize("width,offset", [(52, 1), (61, 37), (80, 1)])
def test_exact_run_calendar_season_crossing_v3(width, offset):
    clock = RunCalendar(width, offset, 2030, 3)
    event = boundary(clock)
    parsed = CalendarSportingWeekAdvance.model_validate_json(event.model_dump_json())
    assert parsed == event
    assert event.target_week.ordinal == event.completed_week.ordinal + 1
    assert event.target_week.calendar_position.season_index == 1
    assert event.scope == "configured_tour_season_transition"
    with pytest.raises(ValueError):
        boundary(clock, version="calendar_sporting_week_advance.v2")


@pytest.mark.parametrize("width", [52, 61, 80])
def test_wrong_week_or_calendar_is_never_promoted_to_season(width):
    clock = RunCalendar(width, 1, 2030, 3)
    with pytest.raises(ValueError, match="requires exactly W"):
        boundary(clock, start=RunWeekPosition(calendar=clock, season_index=0, week=width-1),
                 target=RunWeekPosition(calendar=clock, season_index=0, week=width))
    with pytest.raises(ValueError):
        boundary(clock, target=RunWeekPosition(calendar=clock, season_index=2, week=1))
    with pytest.raises(ValueError):
        boundary(clock, target=RunWeekPosition(calendar=clock, season_index=1, week=2))


def test_terminal_season_does_not_wrap_or_extend_automatically():
    clock = RunCalendar(52, 1, 2030, 1)
    with pytest.raises(ValueError):
        RunWeekPosition(calendar=clock, season_index=1, week=1)
    with pytest.raises(ValueError):
        clock.position_at_ordinal(52)

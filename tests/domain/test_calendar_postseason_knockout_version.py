"""Fast contract gate: a post-season real Tour match must not downgrade v10.

The full HTTP/SQLite test validates actual player/rally effects and independent
signed replay; this small test isolates the event reducer's *version choice*
to keep CI useful instead of waiting through the long tournament twice.
"""
import json
from types import SimpleNamespace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players import calendar_followup_knockout as followup
from beta_engine.domain.players import calendar_sporting_checkpoint as sporting

pytestmark=pytest.mark.pr_critical


@pytest.mark.parametrize(
    "checkpoint_version,event_version,expected",
    [
        ("calendar_sporting_checkpoint.v10","calendar_followup_knockout.v5","calendar_sporting_checkpoint.v10"),
        ("calendar_sporting_checkpoint.v9","calendar_followup_knockout.v5","calendar_sporting_checkpoint.v9"),
        ("calendar_sporting_checkpoint.v8","calendar_followup_knockout.v4","calendar_sporting_checkpoint.v8"),
    ],
)
def test_after_season_knockout_retains_exact_original_checkpoint_version(
    monkeypatch,checkpoint_version,event_version,expected
):
    clock=RunCalendar(4,2,2030,3)
    week=RunWeekPosition(calendar=clock,season_index=1,week=1)
    previous=SimpleNamespace(
        schema_version=checkpoint_version,run_id="r",branch_id="b",
        fingerprint="a"*64,week=week,
        week_events=("season-event",), weekly_advances=(),played_continuations=(),
        tournaments=(),closures=(),players=(SimpleNamespace(player_id="p"),),
    )
    previous.model_copy=lambda *,update: SimpleNamespace(
        model_dump_json=lambda:json.dumps(update)
    )
    event=SimpleNamespace(
        schema_version=event_version,run_id="r",branch_id="b",
        command_id="tour-match",tournament_id="s2-cup",
        source_checkpoint_fingerprint="a"*64,week=week,
        entrant_ids=("p",),matches=(),
    )
    monkeypatch.setattr(followup,"append_continuation",lambda prior,*a,**kw:prior)
    monkeypatch.setattr(
        sporting.CalendarSportingCheckpoint,"model_validate_json",
        classmethod(lambda cls,body:json.loads(body))
    )
    result=followup.append_followup_knockout(previous,object(),event)
    assert result["schema_version"]==expected
    assert result["week_events"][-1] is not None


def test_season_reducer_rejects_foreign_sources_before_replay(monkeypatch):
    clock=RunCalendar(4,2,2030,3)
    week=RunWeekPosition(calendar=clock,season_index=1,week=1)
    state=SimpleNamespace(
        schema_version="calendar_sporting_checkpoint.v10",
        run_id="r",branch_id="b",week=week,fingerprint="a"*64,
        week_events=(object(),),weekly_advances=(),played_continuations=(),
        tournaments=(),closures=(),players=(SimpleNamespace(player_id="p"),),
    )
    foreign=SimpleNamespace(
        run_id="r",branch_id="foreign",source_checkpoint_fingerprint="a"*64,
        week=week,command_id="c",tournament_id="t",entrant_ids=("p",),matches=(),
    )
    monkeypatch.setattr(
        followup,"append_continuation",
        lambda *_args,**_kw: (_ for _ in ()).throw(AssertionError("unexpected replay"))
    )
    with pytest.raises(ValueError,match="source/roster or identity"):
        followup.append_followup_knockout(state,object(),foreign)

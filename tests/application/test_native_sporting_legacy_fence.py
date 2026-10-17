"""Isolated legacy ownership fence; Saved-calendar resolver/SQL boundary mocked.

This does not create a native InitialWorld on the reserved legacy reference clock.
"""
import pytest
from beta_engine.application import run_calendar_read_authority as authority
from beta_engine.domain.calendar.run_calendar import RunCalendar

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize('native_owner', [False, True])
def test_reference_calendar_equality_cannot_grant_legacy_ownership(monkeypatch, native_owner):
    clock = RunCalendar.fax_default()
    calls = []
    def resolve(session, *, run_id, branch_id):
        assert (run_id, branch_id) == ('run', 'branch')
        return clock
    monkeypatch.setattr(authority, 'resolve_saved_run_calendar', resolve)
    class Session:
        def scalar(self, query):
            calls.append(str(query))
            return 'run' if native_owner else None
    if native_owner:
        with pytest.raises(ValueError, match='native population sporting checkpoint'):
            authority.require_supported_legacy_sporting_calendar(Session(), run_id='run', branch_id='branch', operation='Legacy writer')
    else:
        assert authority.require_supported_legacy_sporting_calendar(Session(), run_id='run', branch_id='branch', operation='Legacy writer') == clock
    assert len(calls) == 1 and 'calendar_player_sporting_checkpoints' in calls[0]

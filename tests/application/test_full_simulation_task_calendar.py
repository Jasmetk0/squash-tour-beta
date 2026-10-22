"""Clock/read-contract tests, not W52/W80 Full Simulation execution evidence.

Saved calendars are produced by normal Run creation, fork and horizon Save.
Only progress arithmetic uses a minimal command/parent stand-in: no fabricated
sporting results are submitted to the production task worker.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from beta_engine.application.full_simulation_tasks import _progress_evidence
from beta_engine.application.run_branch_creation_service import RunBranchCreationService
from beta_engine.application.run_calendar_extension_commit import (
    review_run_calendar_extension, save_run_calendar_extension,
)
from beta_engine.application.run_calendar_read_authority import (
    require_supported_full_simulation_calendar, resolve_revision_run_calendar,
    resolve_saved_run_calendar,
)
from beta_engine.application.run_container_creation_service import RunContainerCreationService
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db import (
    DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel

pytestmark = pytest.mark.pr_critical


def setup_calendar(tmp_path, calendar):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'task-clock.sqlite'}"))
    factory = create_session_factory(engine)
    repo = SimulationPersistenceRepository(engine=engine, session_factory=factory)
    repo.bootstrap_schema()
    ids = iter(('run', 'branch', 'saved', 'draft'))
    RunContainerCreationService(repo, lambda _: next(ids)).create_empty_run(
        display_name='Task clock', calendar=calendar,
    )
    return engine, factory, repo


def week(index, number):
    value = {'season_index': index, 'week': number}
    return SimpleNamespace(**value, model_dump=lambda **_: value)


@pytest.mark.parametrize('calendar', [
    RunCalendar(52, 1, 2030, 3), RunCalendar(52, 52, 1955, 64),
    RunCalendar(61, 37, 2000, 50), RunCalendar(80, 80, 2026, 64),
    RunCalendar(1, 1, 0, 2),
])
def test_saved_clock_drives_progress_across_season_boundary_without_writes(tmp_path, calendar):
    engine, factory, repo = setup_calendar(tmp_path, calendar)
    try:
        original = repo.get_branch_saved_revision(revision_id='saved')
        with factory() as session:
            clock = resolve_revision_run_calendar(session, run_id='run', revision_id='saved')
            command = SimpleNamespace(expected_start_week=week(0, calendar.weeks_per_year))
            row = SimpleNamespace(run_id='run', branch_id='branch')
            measured = _progress_evidence(session, row, SimpleNamespace(status='pending'), {}, command,
                                          calendar.weeks_per_year, clock)
        assert measured == {
            'schema_version': 'full_simulation_task_progress_evidence.v2',
            'kind': 'live_branch', 'week': {'season_index': 1, 'week': 1},
            'weeks_advanced_since_start': 1,
            'completed_slot_receipts_this_week': 0, 'committed_group_receipts_this_week': 0,
            'receipt_scope': 'branch_current_week',
        }
        assert repo.get_branch_saved_revision(revision_id='saved') == original
        assert repo.verify_branch_saved_revision_hash(revision_id='saved')
    finally:
        engine.dispose()


@pytest.mark.parametrize('bad', [-1, 52 * 3, True, 1.5])
def test_progress_rejects_out_of_range_or_noninteger_ordinals(tmp_path, bad):
    clock = RunCalendar(52, 1, 2030, 3)
    engine, factory, _ = setup_calendar(tmp_path, clock)
    try:
        with factory() as session, pytest.raises(ValueError, match='Task Position'):
            _progress_evidence(session, SimpleNamespace(run_id='run', branch_id='branch'),
                               SimpleNamespace(status='pending'), {},
                               SimpleNamespace(expected_start_week=week(0, 1)), bad, clock)
    finally:
        engine.dispose()


def test_completed_progress_uses_original_final_week_and_ignores_live_branch(tmp_path):
    clock = RunCalendar(80, 37, 2030, 64)
    engine, factory, _ = setup_calendar(tmp_path, clock)
    try:
        start = week(62, 80)
        result = {'schema_version': 'authoritative_full_simulation_result.v1',
                  'run_id': 'run', 'branch_id': 'branch', 'start_week': start.model_dump(),
                  'final_week': {'season_index': 63, 'week': 80}}
        with factory() as session:
            evidence = _progress_evidence(session, SimpleNamespace(run_id='run', branch_id='branch'),
                SimpleNamespace(status='complete'), result, SimpleNamespace(expected_start_week=start),
                9999999, clock)
            assert evidence['week'] == {'season_index': 63, 'week': 80}
            assert evidence['weeks_advanced_since_start'] == 80
            assert evidence['kind'] == 'terminal_frozen'
            assert evidence['receipt_scope'] is None
            assert evidence['completed_slot_receipts_this_week'] is None
            with pytest.raises(ValueError, match='terminal position'):
                _progress_evidence(session, SimpleNamespace(run_id='run', branch_id='branch'),
                    SimpleNamespace(status='complete'), {**result, 'final_week': {'season_index':49,'week':61}},
                    SimpleNamespace(expected_start_week=start), None, clock)
    finally:
        engine.dispose()


def test_original_shared_saved_clock_survives_real_fork_extension_and_sqlite_reopen(tmp_path):
    clock = RunCalendar(80, 37, 2030, 3)
    engine, factory, repo = setup_calendar(tmp_path, clock)
    try:
        original = repo.get_branch_saved_revision(revision_id='saved')
        RunBranchCreationService(repo, lambda kind: {'branch':'fork','working-draft':'fork-draft'}[kind]).create_from_saved_revision(
            run_id='run', source_branch_id='branch', source_saved_revision_id='saved', display_name='Alternative')
        with factory() as session:
            assert resolve_saved_run_calendar(session, run_id='run', branch_id='fork') == clock
            review = review_run_calendar_extension(session, repo, run_id='run', new_season_count=64)
        assert review['can_save'], review['blockers']
        save_run_calendar_extension(repo, run_id='run', command_id='extend', new_season_count=64,
                                    review_fingerprint=review['review_fingerprint'], explicit_confirmation=True)
        assert repo.get_branch_saved_revision(revision_id='saved') == original
        engine.dispose()
        with factory() as session:
            assert resolve_saved_run_calendar(session, run_id='run', branch_id='fork') == clock.extend_to(64)
            assert resolve_revision_run_calendar(session, run_id='run', revision_id='saved') == clock
    finally:
        engine.dispose()


def test_task_clock_rejects_wrong_run_missing_or_corrupted_saved_revision(tmp_path):
    engine, factory, _ = setup_calendar(tmp_path, RunCalendar.earth_default())
    try:
        with factory() as session:
            for run, revision in [('wrong-run','saved'), ('run','missing')]:
                with pytest.raises(ValueError, match='missing or outside'):
                    resolve_revision_run_calendar(session, run_id=run, revision_id=revision)
        with factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, 'saved')
            payload = json.loads(row.payload_json)
            payload['run']['run_calendar']['weeks_per_year'] = 80
            row.payload_json = json.dumps(payload)
        with factory() as session, pytest.raises(ValueError, match='content-hash'):
            resolve_revision_run_calendar(session, run_id='run', revision_id='saved')
    finally:
        engine.dispose()


@pytest.mark.parametrize('clock', [RunCalendar.earth_default(), RunCalendar(80, 37, 2030, 64)])
def test_read_contract_does_not_enable_unsupported_legacy_execution(clock):
    with pytest.raises(ValueError, match='cannot execute this Run calendar'):
        require_supported_full_simulation_calendar(clock)

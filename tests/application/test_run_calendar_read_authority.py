"""Real SQLite Run calendar authority, plus bounded Full Simulation preview integration.

The preview-position stub tests only the calendar boundary; no sport is mocked
into being a successful simulation. Persistence and Saved Revision are real.
"""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeFullSimulationPreviewRequest,
    AuthoritativeRunSimulationDriver,
)
from beta_engine.application.run_calendar_read_authority import (
    require_supported_full_simulation_calendar, resolve_saved_run_calendar,
)
from beta_engine.application.run_container_creation_service import RunContainerCreationService
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.run_revisions import saved_revision_content_hash
from beta_engine.infrastructure.db import (
    DatabaseSettings, SimulationPersistenceRepository,
    create_session_factory, create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel, RunContainerModel,
)


def _setup(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'calendar-authority.db'}"))
    factory = create_session_factory(engine)
    repo = SimulationPersistenceRepository(engine=engine, session_factory=factory)
    repo.bootstrap_schema()
    ids = iter(("run-1", "branch-1", "revision-1", "draft-1"))
    RunContainerCreationService(
        repository=repo, id_factory=lambda _: next(ids)
    ).create_empty_run(display_name="Clock authority")
    return engine, factory, repo


def _signed_test_calendar(factory, calendar: RunCalendar | None) -> None:
    """Disposable test-only legacy/W52 fixture; production never rewrites history."""
    with factory.begin() as session:
        run = session.get(RunContainerModel, "run-1")
        rev = session.get(BranchSavedRevisionModel, "revision-1")
        payload = json.loads(rev.payload_json)
        metadata = json.loads(run.metadata_json)
        if calendar is None:
            metadata.pop("run_calendar", None)
            payload["run"].pop("run_calendar", None)
        else:
            metadata["run_calendar"] = calendar.to_metadata()
            payload["run"]["run_calendar"] = calendar.to_metadata()
            run.timeline_start_season = calendar.start_year
            run.timeline_end_season = calendar.start_year + calendar.season_count - 1
            payload["run"]["timeline_start_season"] = run.timeline_start_season
            payload["run"]["timeline_end_season"] = run.timeline_end_season
        run.metadata_json = json.dumps(metadata)
        rev.payload_json = json.dumps(payload)
        changes = json.loads(rev.change_summary_json)
        rev.content_hash = saved_revision_content_hash(
            revision_id=rev.revision_id, run_id=rev.run_id, branch_id=rev.branch_id,
            sequence=rev.sequence, parent_revision_id=rev.parent_revision_id,
            kind=rev.kind, payload_schema_version=rev.payload_schema_version,
            payload=payload, change_summary=changes,
        )


@pytest.mark.pr_critical
@pytest.mark.parametrize('change', ['whitespace', 'payload', 'change-summary', 'declared-hash', 'rehash-clock', 'rehash-identity'])
def test_verified_calendar_projection_still_binds_all_actual_saved_bytes(tmp_path, monkeypatch, change):
    from beta_engine.application import run_calendar_read_authority as authority

    engine, factory, repo = _setup(tmp_path)
    try:
        repo.get_branch_revision_state(branch_id='branch-1')
        with factory() as session:
            expected = resolve_saved_run_calendar(session, run_id='run-1', branch_id='branch-1')
        original_hash = authority.saved_revision_content_hash
        calls = []

        def counted(**fields):
            calls.append(fields)
            return original_hash(**fields)

        monkeypatch.setattr(authority, 'saved_revision_content_hash', counted)
        with factory() as session:
            assert resolve_saved_run_calendar(session, run_id='run-1', branch_id='branch-1', _repository=repo) == expected
            assert calls == []
        with factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, 'revision-1')
            if change == 'whitespace':
                row.payload_json += ' '
            elif change == 'declared-hash':
                row.content_hash = '0' * 64
            elif change == 'change-summary':
                row.change_summary_json = json.dumps({'changed': True})
            else:
                payload = json.loads(row.payload_json)
                if change == 'payload':
                    payload['content']['unexpected'] = {'actual': 1}
                elif change == 'rehash-clock':
                    payload['run']['run_calendar']['season_count'] += 1
                else:
                    payload['run']['run_id'] = 'foreign'
                row.payload_json = json.dumps(payload)
                if change.startswith('rehash-'):
                    row.content_hash = original_hash(**{
                        name: getattr(row, name) for name in ('revision_id', 'run_id', 'branch_id', 'sequence',
                            'parent_revision_id', 'kind', 'payload_schema_version')
                    }, payload=payload, change_summary=json.loads(row.change_summary_json))
        with factory() as session:
            if change == 'whitespace':
                assert resolve_saved_run_calendar(session, run_id='run-1', branch_id='branch-1', _repository=repo) == expected
            else:
                with pytest.raises(ValueError):
                    resolve_saved_run_calendar(session, run_id='run-1', branch_id='branch-1', _repository=repo)
        assert len(calls) == 1, 'Changed actual bytes must take the original full content-hash gate'
    finally:
        engine.dispose()


@pytest.mark.pr_critical
def test_saved_run_calendar_is_read_with_verified_hash_and_no_writes(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        original = repo.get_branch_revision_state(branch_id="branch-1").saved_revision
        with factory() as session:
            clock = resolve_saved_run_calendar(session, run_id="run-1", branch_id="branch-1")
            assert clock == RunCalendar.fax_default()
            require_supported_full_simulation_calendar(clock)
            assert clock.season_to_calendar(0, 26).year_week == 1
            assert clock.season_to_calendar(49, 61).calendar_year == 2050
        assert repo.get_branch_revision_state(branch_id="branch-1").saved_revision == original
        assert repo.verify_branch_saved_revision_hash(revision_id="revision-1")
        # Even a valid calendar on the Run row is insufficient without a
        # matching immutable Saved head (no fallback to current defaults).
        with factory.begin() as session:
            run = session.get(RunContainerModel, "run-1")
            run.metadata_json = json.dumps({"run_calendar": RunCalendar.earth_default().to_metadata()})
        with factory() as session, pytest.raises(ValueError, match="differs"):
            resolve_saved_run_calendar(session, run_id="run-1", branch_id="branch-1")
    finally:
        engine.dispose()


@pytest.mark.pr_critical
def test_history_absence_and_broken_explicit_metadata_are_distinct(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, None)
        initial = repo.get_branch_revision_state(branch_id="branch-1").saved_revision
        with factory() as session:
            legacy = resolve_saved_run_calendar(session, run_id="run-1", branch_id="branch-1")
            assert legacy == RunCalendar.legacy_fax()
        assert repo.get_branch_revision_state(branch_id="branch-1").saved_revision == initial
        for raw in (
            '{"run_calendar":null}',
            '{"run_calendar":{}}',
            '{"run_calendar":{"schema_version":"unknown"}}',
            'invalid JSON',
        ):
            with factory.begin() as session:
                session.get(RunContainerModel, "run-1").metadata_json = raw
            with factory() as session, pytest.raises(ValueError):
                resolve_saved_run_calendar(session, run_id="run-1", branch_id="branch-1")
        with factory.begin() as session:
            session.get(RunContainerModel, "run-1").metadata_json = "{}"
            rev = session.get(BranchSavedRevisionModel, "revision-1")
            rev.content_hash = "f" * 64
        with factory() as session, pytest.raises(ValueError, match="hash"):
            resolve_saved_run_calendar(session, run_id="run-1", branch_id="branch-1")
    finally:
        engine.dispose()


@pytest.mark.pr_critical
def test_full_simulation_preview_uses_saved_clock_and_blocks_unsupported_w52_before_sport(
    tmp_path, monkeypatch,
):
    engine, factory, repo = _setup(tmp_path)
    driver = AuthoritativeRunSimulationDriver(
        factory=factory, match_service=None, awards_service=None,
    )
    request = AuthoritativeFullSimulationPreviewRequest(
        run_id="run-1", branch_id="branch-1", command_id="review",
        operator_label="Admin", audit_reason="Explicit reviewed clock",
    )
    calls = []
    def position(*args, **kwargs):
        calls.append("position")
        return SimpleNamespace(
            current_week=RankingWeek(season_index=0, week=1),
            position_fingerprint="a" * 64,
            transition_blockers=(),
        )
    monkeypatch.setattr(AuthoritativeRunSimulationDriver, "_position", position)
    monkeypatch.setattr(AuthoritativeRunSimulationDriver, "_branch_final_closure_evidence", lambda *args, **kwargs: None)
    try:
        # The legacy-supporting preview remains byte-compatible FAX shape.
        preview = driver.preview_full_simulation(request)
        assert calls == ["position"]
        assert preview["final_week"] == {"season_index": 49, "week": 61}
        assert preview["remaining_weeks_including_current"] == 50 * 61
        with factory() as session:
            assert resolve_saved_run_calendar(session, run_id="run-1", branch_id="branch-1") == RunCalendar.fax_default()

        # A fully consistent, rehashed W52 test fixture is still NOT
        # authorized to execute while sporting/RankingWeek uses FAX ordinals.
        _signed_test_calendar(factory, RunCalendar.earth_default())
        with factory() as session:
            assert resolve_saved_run_calendar(session, run_id="run-1", branch_id="branch-1").weeks_per_year == 52
        with pytest.raises(ValueError, match="cannot execute this Run calendar"):
            driver.preview_full_simulation(request)
        assert calls == ["position"]  # rejected before even reading sporting position
        assert repo.verify_branch_saved_revision_hash(revision_id="revision-1")
    finally:
        engine.dispose()

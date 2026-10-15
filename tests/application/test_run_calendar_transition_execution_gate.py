"""V82 fail-closed transition gate against REAL SQLite Saved Run authority.

These tests deliberately do not simulate a fake sporting result. A valid but
unsupported W52/O1 Saved Run must be rejected before any ledger/Save mutation;
historical default FAX and absent-v0 records remain recognized.
"""

from __future__ import annotations

import json

import pytest

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
    AuthoritativeWeekPreviewRequest, AuthoritativeWeekCommand,
    AuthoritativeSeasonPreviewRequest, AuthoritativeSeasonCommand,
)
from beta_engine.application.run_calendar_read_authority import (
    require_supported_legacy_sporting_calendar,
)
from beta_engine.application.season_transition_configuration import (
    resolve_season_transition_configuration,
)
from beta_engine.application.authoritative_week_transition import (
    AuthoritativeWeekTransitionCommand,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.command_audit import RankingCommandAudit
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.authoritative_week_transition import (
    AuthoritativeWeekTransitionRunner,
    transition_in_transaction,
    week_transition_readiness_blockers,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWeekTransitionReceiptModel,
    AuthoritativeWorldEventModel,
    PublishedOfficialRankingModel,
    RunContainerModel,
)
from tests.application.test_run_calendar_read_authority import (
    _setup, _signed_test_calendar,
)

pytestmark = pytest.mark.pr_critical


def _scoped_request(kind):
    return kind(
        command_id="next",
        run_id="run-1",
        branch_id="branch-1",
        operator_label="Operator",
        audit_reason="Reviewed calendar protection",
    )


def _week_command():
    return AuthoritativeWeekTransitionCommand(
        command_id="transition-1",
        run_id="run-1",
        branch_id="branch-1",
        base_revision_id="revision-1",
        completed_week=RankingWeek(season_index=0, week=1),
        target_week=RankingWeek(season_index=0, week=2),
        authority_fingerprint="a" * 64,
        audit=RankingCommandAudit(actor_label="Operator", reason="Protect Run clock"),
    )


def _week_parent():
    return AuthoritativeWeekCommand(
        **_scoped_request(AuthoritativeWeekPreviewRequest).model_dump(),
        expected_week=RankingWeek(season_index=0, week=1),
        expected_position_fingerprint="a" * 64,
        expected_revision_id="revision-1",
        expected_preview_fingerprint="b" * 64,
    )


def _season_parent():
    return AuthoritativeSeasonCommand(
        **_scoped_request(AuthoritativeSeasonPreviewRequest).model_dump(),
        expected_start_week=RankingWeek(season_index=0, week=1),
        expected_position_fingerprint="a" * 64,
        expected_revision_id="revision-1",
        expected_preview_fingerprint="b" * 64,
    )


def test_actual_w52_saved_run_blocks_every_new_transition_entry_and_writer(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    driver = AuthoritativeRunSimulationDriver(
        factory=factory, match_service=None, awards_service=None,
    )
    _signed_test_calendar(factory, RunCalendar.earth_default())
    before = repo.get_branch_revision_state(branch_id="branch-1")
    run_before = repo.get_run_container(run_id="run-1")
    try:
        with factory() as session:
            assert week_transition_readiness_blockers(
                session, run_id="run-1", branch_id="branch-1",
                completed_week=RankingWeek(season_index=0, week=1),
            ) == ("run_calendar_execution_unsupported",)
            with pytest.raises(ValueError, match="Season Transition cannot execute"):
                resolve_season_transition_configuration(
                    session, run_id="run-1", branch_id="branch-1",
                )
            with pytest.raises(ValueError, match="Week Transition cannot execute"):
                transition_in_transaction(session, None, _week_command())

        for preview, pattern in (
            (lambda: driver.preview_next_week(_scoped_request(AuthoritativeWeekPreviewRequest)), "Next Week cannot execute"),
            (lambda: driver.preview_next_season(_scoped_request(AuthoritativeSeasonPreviewRequest)), "Next Season cannot execute"),
            (lambda: driver.season_transition_preflight(run_id="run-1", branch_id="branch-1"), "Season Transition cannot execute"),
            (lambda: driver.simulate_next_week(_week_parent()), "Next Week cannot execute"),
            (lambda: driver.simulate_next_season(_season_parent()), "Next Season cannot execute"),
            (lambda: AuthoritativeWeekTransitionRunner(factory).preview(_week_command()), "Week Transition cannot execute"),
            (lambda: AuthoritativeWeekTransitionRunner(factory).execute(_week_command()), "Week Transition cannot execute"),
        ):
            with pytest.raises(ValueError, match=pattern):
                preview()

        assert repo.get_run_container(run_id="run-1") == run_before
        assert repo.get_branch_revision_state(branch_id="branch-1") == before
        assert repo.verify_branch_saved_revision_hash(revision_id="revision-1")
        with factory() as session:
            assert session.query(AuthoritativeWeekTransitionReceiptModel).count() == 0
            assert session.query(AuthoritativeWorldEventModel).count() == 0
            assert session.query(PublishedOfficialRankingModel).count() == 0
    finally:
        engine.dispose()


@pytest.mark.parametrize("clock", [
    RunCalendar(61, 35, 2000, 50),
    RunCalendar.fax_default(start_year=2024),
    RunCalendar.fax_default(season_count=51),
    RunCalendar(52, 1, 2000, 50),
])
def test_other_calendar_scopes_also_reject_legacy_writers(tmp_path, clock):
    engine, factory, repo = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, clock)
        with factory() as session:
            with pytest.raises(ValueError, match="cannot execute this Run calendar"):
                require_supported_legacy_sporting_calendar(
                    session, run_id="run-1", branch_id="branch-1",
                    operation="Week Transition",
                )
        assert repo.verify_branch_saved_revision_hash(revision_id="revision-1")
    finally:
        engine.dispose()


def test_w61_saved_and_absent_historical_fax_remain_eligible_for_existing_writers(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        with factory() as session:
            clock = require_supported_legacy_sporting_calendar(
                session, run_id="run-1", branch_id="branch-1",
                operation="Week Transition",
            )
            assert clock == RunCalendar.fax_default()
        _signed_test_calendar(factory, None)
        revision = repo.get_branch_revision_state(branch_id="branch-1").saved_revision
        with factory() as session:
            legacy = require_supported_legacy_sporting_calendar(
                session, run_id="run-1", branch_id="branch-1",
                operation="Season Transition",
            )
            assert legacy == RunCalendar.legacy_fax()
        assert repo.get_branch_revision_state(branch_id="branch-1").saved_revision == revision
        assert repo.verify_branch_saved_revision_hash(revision_id="revision-1")
    finally:
        engine.dispose()


def test_tampered_run_calendar_fails_before_sport_and_does_not_repair_metadata(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        with factory.begin() as session:
            run = session.get(RunContainerModel, "run-1")
            original = json.loads(run.metadata_json)
            original["run_calendar"]["weeks_per_year"] = 52
            run.metadata_json = json.dumps(original)
        before = repo.get_run_container(run_id="run-1")
        with factory() as session:
            with pytest.raises(ValueError, match="differs"):
                require_supported_legacy_sporting_calendar(
                    session, run_id="run-1", branch_id="branch-1",
                    operation="Week Transition",
                )
        assert repo.get_run_container(run_id="run-1") == before
        assert repo.verify_branch_saved_revision_hash(revision_id="revision-1")
    finally:
        engine.dispose()

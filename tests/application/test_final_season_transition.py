import json
import threading
from collections.abc import Iterator

import pytest
from sqlalchemy import select

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeFullSimulationCommand,
    AuthoritativeFullSimulationPreviewRequest,
    AuthoritativeFullSimulationAbandonCommand,
    AuthoritativeRunSimulationDriver,
    AuthoritativeSimulationPosition,
)
from beta_engine.application.run_branch_creation_service import RunBranchCreationService
import beta_engine.application.final_season_transition as final_transition
from beta_engine.application.final_season_transition import (
    FINAL_WEEK,
    FinalSeasonTransitionCommand,
    commit_final_season_transition,
)
from beta_engine.domain.players.lifecycle import PlayerLifecycleWeekState
from beta_engine.domain.rankings.official import (
    OfficialRankingPolicy,
    calculate_official_ranking,
)
from beta_engine.domain.run_containers import (
    ARCHIVED_RUN_STATUS,
    COMPLETED_RUN_STATUS,
    WORKING_RUN_STATUS,
)
from beta_engine.domain.run_revisions import (
    CLEAN_WORKING_DRAFT_STATUS,
    CONTENT_HASH_ALGORITHM,
    INITIAL_SAVED_REVISION_KIND,
    RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
    RUN_WORKING_DRAFT_SCHEMA_VERSION,
    initial_saved_revision_payload,
    saved_revision_content_hash,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    AuthoritativeSimulationCommandModel,
    Base,
    BranchRevisionAuditEventModel,
    BranchSavedRevisionModel,
    BranchWorkingDraftModel,
    OfficialRankingCandidateModel,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    SeasonClosingRankingModel,
)
from beta_engine.infrastructure.db.player_lifecycle_state import put_lifecycle
from beta_engine.infrastructure.db.saved_revision_season_closure import (
    load_saved_revision_season_closure,
)
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'final-transition.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    yield factory
    engine.dispose()


def _install_final_boundary(session):
    run = RunContainerModel(
        run_id="run",
        display_name="Run",
        storage_kind="custom_local",
        read_only=0,
        timeline_start_season=2000,
        timeline_end_season=2049,
        official_branch_id="branch",
        status=WORKING_RUN_STATUS,
    )
    branch = RunBranchModel(
        run_id="run",
        branch_id="branch",
        display_name="Timeline 1",
        status="active",
        read_only=0,
        saved_head_revision_id="revision-before-final",
    )
    session.add_all([run, branch])

    base_payload = initial_saved_revision_payload(
        run_id="run",
        display_name="Run",
        run_status=WORKING_RUN_STATUS,
        timeline_start_season=2000,
        timeline_end_season=2049,
        branch_id="branch",
        branch_display_name="Timeline 1",
        branch_status="active",
    )
    base_summary = {
        "kind": INITIAL_SAVED_REVISION_KIND,
        "summary": "Test final-boundary base",
    }
    base_hash = saved_revision_content_hash(
        revision_id="revision-before-final",
        run_id="run",
        branch_id="branch",
        sequence=1,
        parent_revision_id=None,
        kind=INITIAL_SAVED_REVISION_KIND,
        payload_schema_version=RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
        payload=base_payload,
        change_summary=base_summary,
    )
    session.add(
        BranchSavedRevisionModel(
            revision_id="revision-before-final",
            run_id="run",
            branch_id="branch",
            sequence=1,
            parent_revision_id=None,
            kind=INITIAL_SAVED_REVISION_KIND,
            payload_schema_version=RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
            content_hash_algorithm=CONTENT_HASH_ALGORITHM,
            content_hash=base_hash,
            payload_json=json.dumps(base_payload, sort_keys=True, separators=(",", ":")),
            change_summary_json=json.dumps(
                base_summary, sort_keys=True, separators=(",", ":")
            ),
        )
    )
    session.add(
        BranchWorkingDraftModel(
            draft_id="draft",
            run_id="run",
            branch_id="branch",
            base_revision_id="revision-before-final",
            status=CLEAN_WORKING_DRAFT_STATUS,
            change_count=0,
            draft_version=7,
            draft_schema_version=RUN_WORKING_DRAFT_SCHEMA_VERSION,
            changes_json="[]",
        )
    )
    session.flush()

    policy = OfficialRankingPolicy(policy_id="final-policy", best_n=15)
    official = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=FINAL_WEEK,
        policy=policy,
        players=(),
        results=(),
    )
    session.add(
        OfficialRankingCandidateModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=FINAL_WEEK.ordinal,
            fingerprint=official.fingerprint,
            payload_json=official.model_dump_json(),
        )
    )
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=FINAL_WEEK.ordinal,
            snapshot_fingerprint=official.fingerprint,
            payload_json=official.model_dump_json(),
        )
    )
    session.add(
        AuthoritativeWorldStateModel(
            run_id="run",
            branch_id="branch",
            current_ordinal=FINAL_WEEK.ordinal,
            ranking_fingerprint=official.fingerprint,
        )
    )
    put_lifecycle(
        session,
        PlayerLifecycleWeekState(
            run_id="run",
            branch_id="branch",
            week=FINAL_WEEK,
            players=(),
            source_initial_world_fingerprint="empty-final-world",
        ),
    )
    session.flush()


def _patch_saved_revision_captures(monkeypatch):
    calls = []

    def fake_capture(name):
        def capture(session, payload, *, run_id, branch_id):
            calls.append((name, run_id, branch_id))
        return capture

    for name in (
        "capture_saved_ranking_component",
        "capture_saved_initial_world",
        "capture_saved_lifecycle",
        "capture_saved_sporting",
        "capture_saved_simulation_slots",
    ):
        monkeypatch.setattr(final_transition, name, fake_capture(name))
    return calls


def _command(preflight_fingerprint: str = "a" * 64):
    return FinalSeasonTransitionCommand(
        command_id="close-final-season",
        run_id="run",
        branch_id="branch",
        expected_preflight_fingerprint=preflight_fingerprint,
        expected_saved_revision_id="revision-before-final",
        expected_draft_version=7,
        final_saved_revision_id="revision-final",
        audit_event_id="audit-final",
    )


@pytest.mark.pr_critical
def test_atomic_final_season_writer_commits_one_complete_final_state(database, monkeypatch):
    capture_calls = _patch_saved_revision_captures(monkeypatch)
    with database.begin() as session:
        _install_final_boundary(session)

    position = AuthoritativeSimulationPosition(
        run_id="run",
        branch_id="branch",
        current_week=FINAL_WEEK,
        current_slot_id=None,
        slot_ordinal=None,
        unresolved_group_ids=(),
        eligible_match_ids=(),
        blocked_match_ids=(),
        current_slot_complete=True,
        supported_tournament_complete=True,
        week_ready_for_transition=True,
        transition_blockers=("season_transition_required",),
        terminal_sporting_fingerprint="d" * 64,
        position_fingerprint="e" * 64,
    )
    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_position",
        lambda self, session, run_id, branch_id: position,
    )
    driver = AuthoritativeRunSimulationDriver(database, None, None)
    preflight = driver.season_transition_preflight(run_id="run", branch_id="branch")
    assert preflight.final_season is True
    assert preflight.target_week is None
    assert preflight.state_blockers == ()
    assert preflight.implementation_gaps == ()
    assert preflight.ready_for_execution is True
    assert preflight.saved_revision_id == "revision-before-final"
    assert preflight.draft_version == 7

    command = _command(preflight.preflight_fingerprint)
    result = driver.finalize_final_season(command)
    assert result.run_status == COMPLETED_RUN_STATUS
    assert result.completed_week == FINAL_WEEK
    assert result.saved_revision_id == "revision-final"
    assert result.draft_version == 8
    assert [name for name, _, _ in capture_calls] == [
        "capture_saved_ranking_component",
        "capture_saved_initial_world",
        "capture_saved_lifecycle",
        "capture_saved_sporting",
        "capture_saved_simulation_slots",
    ]
    assert all((run_id, branch_id) == ("run", "branch") for _, run_id, branch_id in capture_calls)

    with database() as session:
        run = session.get(RunContainerModel, "run")
        branch = session.get(RunBranchModel, "branch")
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == "branch"
            )
        )
        revision = session.get(BranchSavedRevisionModel, "revision-final")
        assert run.status == COMPLETED_RUN_STATUS
        assert branch.saved_head_revision_id == "revision-final"
        assert draft.base_revision_id == "revision-final"
        assert draft.draft_version == 8
        assert draft.status == CLEAN_WORKING_DRAFT_STATUS
        assert revision.parent_revision_id == "revision-before-final"
        assert revision.sequence == 2

        payload = json.loads(revision.payload_json)
        assert payload["run"]["status"] == COMPLETED_RUN_STATUS
        closure = load_saved_revision_season_closure(
            payload,
            run_id="run",
            branch_id="branch",
            revision_id="revision-final",
        )
        assert closure is not None
        assert closure.parsed_marker.completed_week == FINAL_WEEK
        assert closure.parsed_marker.final_saved_revision_id == "revision-final"

        closing = session.scalars(select(SeasonClosingRankingModel)).all()
        assert len(closing) == 1
        publications = session.scalars(select(PublishedOfficialRankingModel)).all()
        assert [row.week_ordinal for row in publications] == [FINAL_WEEK.ordinal]
        audits = session.scalars(select(BranchRevisionAuditEventModel)).all()
        assert len(audits) == 1

    with database.begin() as session:
        retry = commit_final_season_transition(session, command)
        assert retry.saved_revision_id == "revision-final"
        assert retry.run_status == COMPLETED_RUN_STATUS

    with database() as session:
        assert len(session.scalars(select(BranchSavedRevisionModel)).all()) == 2
        assert len(session.scalars(select(SeasonClosingRankingModel)).all()) == 1
        assert len(session.scalars(select(BranchRevisionAuditEventModel)).all()) == 1


@pytest.mark.pr_critical
def test_full_simulation_observes_reviewed_final_run_closure(database, monkeypatch):
    _patch_saved_revision_captures(monkeypatch)
    with database.begin() as session:
        _install_final_boundary(session)

    position = AuthoritativeSimulationPosition(
        run_id="run",
        branch_id="branch",
        current_week=FINAL_WEEK,
        current_slot_id=None,
        slot_ordinal=None,
        unresolved_group_ids=(),
        eligible_match_ids=(),
        blocked_match_ids=(),
        current_slot_complete=True,
        supported_tournament_complete=True,
        week_ready_for_transition=True,
        transition_blockers=("season_transition_required",),
        terminal_sporting_fingerprint="d" * 64,
        position_fingerprint="e" * 64,
    )

    def frozen_final_position(
        self,
        session,
        run_id,
        branch_id,
        allow_missing_schedule=False,
    ):
        assert (run_id, branch_id) == ("run", "branch")
        return position

    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_position",
        frozen_final_position,
    )
    driver = AuthoritativeRunSimulationDriver(database, None, None)

    preview_request = AuthoritativeFullSimulationPreviewRequest(
        command_id="full-simulation-final-edge",
        run_id="run",
        branch_id="branch",
        operator_label="Final acceptance admin",
        audit_reason="Review the final canonical Run closure boundary",
    )
    preview = driver.preview_full_simulation(preview_request)
    assert preview["start_week"] == FINAL_WEEK.model_dump(mode="json")
    assert preview["final_week"] == FINAL_WEEK.model_dump(mode="json")
    assert preview["remaining_weeks_including_current"] == 1
    assert preview["remaining_seasons_including_current"] == 1
    assert preview["initial_action"] == "final_season_range"

    command = AuthoritativeFullSimulationCommand(
        **preview_request.model_dump(mode="json"),
        expected_start_week=FINAL_WEEK,
        expected_position_fingerprint=preview["expected_position_fingerprint"],
        expected_revision_id=preview["expected_revision_id"],
        expected_preview_fingerprint=preview["preview_fingerprint"],
    )
    progress = driver.simulate_full_simulation(command)
    assert progress["schema_version"] == "authoritative_full_simulation_progress.v1"
    assert progress["status"] == "blocked"
    assert progress["checkpoint"] == "final_run_closure_review_required"
    assert progress["completed_season_count"] == 0
    assert progress["final_completed_week_count"] == 1
    preflight = progress["season_transition_preflight"]
    assert preflight["final_season"] is True
    assert preflight["ready_for_execution"] is True
    assert preflight["saved_revision_id"] == "revision-before-final"

    pending = driver.inspect_pending_full_simulations(
        run_id="run",
        branch_id="branch",
    )
    assert pending["schema_version"] == (
        "authoritative_full_simulation_pending_collection.v1"
    )
    assert pending["legacy_pending_count"] == 0
    assert len(pending["operations"]) == 1
    resumed = pending["operations"][0]
    assert resumed["command"] == command.model_dump(mode="json")
    assert resumed["review"] == preview
    assert resumed["completed_season_count"] == 0
    assert resumed["final_completed_week_count"] == 1

    competing_request = AuthoritativeFullSimulationPreviewRequest(
        command_id="full-simulation-competing-parent",
        run_id="run",
        branch_id="branch",
        operator_label="Second admin",
        audit_reason="Attempt a competing complete Run parent",
    )
    with pytest.raises(ValueError, match="already has a pending parent"):
        driver.preview_full_simulation(competing_request)

    competing_command = AuthoritativeFullSimulationCommand(
        **competing_request.model_dump(mode="json"),
        expected_start_week=FINAL_WEEK,
        expected_position_fingerprint=preview["expected_position_fingerprint"],
        expected_revision_id=preview["expected_revision_id"],
        expected_preview_fingerprint=preview["preview_fingerprint"],
    )
    with pytest.raises(ValueError, match="already has a pending parent"):
        driver.simulate_full_simulation(competing_command)

    final_command = _command(preflight["preflight_fingerprint"])
    final_result = driver.finalize_final_season(final_command)
    assert final_result.run_status == COMPLETED_RUN_STATUS
    assert final_result.saved_revision_id == "revision-final"

    result = driver.simulate_full_simulation(command)
    assert result["schema_version"] == "authoritative_full_simulation_result.v1"
    assert result["status"] == "complete"
    assert result["run_status"] == COMPLETED_RUN_STATUS
    assert result["final_week"] == FINAL_WEEK.model_dump(mode="json")
    assert result["completed_seasons"] == [49]
    assert result["completed_season_count"] == 1
    assert result["final_saved_revision_id"] == "revision-final"
    assert len(result["closure_marker_fingerprint"]) == 64
    assert len(result["season_summary_fingerprint"]) == 64

    history = driver.inspect_full_simulation_history(
        run_id="run",
        branch_id="branch",
    )
    assert history["schema_version"] == "authoritative_full_simulation_history.v1"
    assert history["item_count"] == 1
    completed_item = history["items"][0]
    assert completed_item["command_id"] == command.command_id
    assert completed_item["status"] == "complete"
    assert completed_item["operator_label"] == "Final acceptance admin"
    assert completed_item["audit_reason"] == (
        "Review the final canonical Run closure boundary"
    )
    assert completed_item["completed_season_count"] == 1

    detail = driver.inspect_full_simulation_parent(
        run_id="run",
        branch_id="branch",
        command_id=command.command_id,
    )
    assert detail["schema_version"] == (
        "authoritative_full_simulation_parent_detail.v1"
    )
    assert detail["status"] == "complete"
    assert detail["operator_label"] == "Final acceptance admin"
    assert detail["final_boundary_saved_revision_id"] == "revision-final"
    assert len(detail["receipt_request_fingerprint"]) == 64

    assert driver.simulate_full_simulation(command) == result


@pytest.mark.pr_critical
def test_full_simulation_abandon_releases_parent_without_rolling_back_child_work(
    database, monkeypatch
):
    _patch_saved_revision_captures(monkeypatch)
    with database.begin() as session:
        _install_final_boundary(session)

    position = AuthoritativeSimulationPosition(
        run_id="run",
        branch_id="branch",
        current_week=FINAL_WEEK,
        current_slot_id=None,
        slot_ordinal=None,
        unresolved_group_ids=(),
        eligible_match_ids=(),
        blocked_match_ids=(),
        current_slot_complete=True,
        supported_tournament_complete=True,
        week_ready_for_transition=True,
        transition_blockers=("season_transition_required",),
        terminal_sporting_fingerprint="d" * 64,
        position_fingerprint="e" * 64,
    )

    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_position",
        lambda self, session, run_id, branch_id, allow_missing_schedule=False: position,
    )
    driver = AuthoritativeRunSimulationDriver(database, None, None)
    preview_request = AuthoritativeFullSimulationPreviewRequest(
        command_id="full-simulation-abandon",
        run_id="run",
        branch_id="branch",
        operator_label="Original admin",
        audit_reason="Start reviewed final-range parent",
    )
    preview = driver.preview_full_simulation(preview_request)
    command = AuthoritativeFullSimulationCommand(
        **preview_request.model_dump(mode="json"),
        expected_start_week=FINAL_WEEK,
        expected_position_fingerprint=preview["expected_position_fingerprint"],
        expected_revision_id=preview["expected_revision_id"],
        expected_preview_fingerprint=preview["preview_fingerprint"],
    )
    progress = driver.simulate_full_simulation(command)
    assert progress["checkpoint"] == "final_run_closure_review_required"
    assert progress["final_completed_week_count"] == 1

    abandoned = driver.abandon_full_simulation(
        AuthoritativeFullSimulationAbandonCommand(
            target_command_id=command.command_id,
            run_id="run",
            branch_id="branch",
            operator_label="Override admin",
            audit_reason="Stop parent while retaining committed canonical work",
            confirm_committed_child_work_persists=True,
        )
    )
    assert abandoned["status"] == "abandoned"
    assert abandoned["committed_child_work_persists"] is True
    assert abandoned["final_completed_week_count"] == 1
    pending = driver.inspect_pending_full_simulations(
        run_id="run",
        branch_id="branch",
    )
    assert pending["operations"] == []
    assert pending["legacy_pending_count"] == 0

    history = driver.inspect_full_simulation_history(
        run_id="run",
        branch_id="branch",
    )
    assert history["item_count"] == 1
    abandoned_item = history["items"][0]
    assert abandoned_item["command_id"] == command.command_id
    assert abandoned_item["status"] == "abandoned"
    assert abandoned_item["operator_label"] == "Original admin"
    assert abandoned_item["abandonment"]["operator_label"] == "Override admin"
    assert abandoned_item["abandonment"]["committed_child_work_persists"] is True
    assert abandoned_item["final_completed_week_count"] == 1

    abandoned_detail = driver.inspect_full_simulation_parent(
        run_id="run",
        branch_id="branch",
        command_id=command.command_id,
    )
    assert abandoned_detail["status"] == "abandoned"
    assert abandoned_detail["operator_label"] == "Original admin"
    assert abandoned_detail["abandonment"]["operator_label"] == "Override admin"
    assert abandoned_detail["final_completed_weeks"] == [
        FINAL_WEEK.model_dump(mode="json")
    ]

    with database() as session:
        receipt = session.get(
            AuthoritativeSimulationCommandModel,
            ("run", "branch", command.command_id),
        )
        assert receipt is not None
        assert receipt.status == "abandoned"
        stored = json.loads(receipt.result_json)
        assert stored["final_completed_weeks"] == [
            FINAL_WEEK.model_dump(mode="json")
        ]
        assert stored["abandonment"]["committed_child_work_persists"] is True
        assert stored["abandonment"]["audit_reason"] == (
            "Stop parent while retaining committed canonical work"
        )

    database_url = str(database.kw["bind"].url)
    database.kw["bind"].dispose()
    reopened_engine = create_sqlite_engine(DatabaseSettings(url=database_url))
    reopened_database = create_session_factory(reopened_engine)
    reopened_driver = AuthoritativeRunSimulationDriver(reopened_database, None, None)

    reopened_pending = reopened_driver.inspect_pending_full_simulations(
        run_id="run", branch_id="branch"
    )
    assert reopened_pending["operations"] == []
    assert reopened_driver.inspect_full_simulation_history(
        run_id="run", branch_id="branch"
    )["items"][0] == abandoned_item
    assert reopened_driver.inspect_full_simulation_parent(
        run_id="run", branch_id="branch", command_id=command.command_id
    ) == abandoned_detail

    replacement = AuthoritativeFullSimulationPreviewRequest(
        command_id="full-simulation-replacement",
        run_id="run",
        branch_id="branch",
        operator_label="Replacement admin",
        audit_reason="Review from the canonical state left by abandoned parent",
    )
    replacement_preview = reopened_driver.preview_full_simulation(replacement)
    assert replacement_preview["start_week"] == FINAL_WEEK.model_dump(mode="json")

    with pytest.raises(ValueError, match="invalid status"):
        reopened_driver.simulate_full_simulation(command)
    reopened_engine.dispose()


@pytest.mark.pr_critical
def test_active_full_simulation_abandon_fences_the_next_writer_transaction(
    database, monkeypatch
):
    """Abandon wins before the next child/progress writer and becomes durable."""

    _patch_saved_revision_captures(monkeypatch)
    with database.begin() as session:
        _install_final_boundary(session)
    position = AuthoritativeSimulationPosition(
        run_id="run",
        branch_id="branch",
        current_week=FINAL_WEEK,
        current_slot_id=None,
        slot_ordinal=None,
        unresolved_group_ids=(),
        eligible_match_ids=(),
        blocked_match_ids=(),
        current_slot_complete=True,
        supported_tournament_complete=True,
        week_ready_for_transition=True,
        transition_blockers=("season_transition_required",),
        terminal_sporting_fingerprint="d" * 64,
        position_fingerprint="e" * 64,
    )
    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_position",
        lambda self, session, run_id, branch_id, allow_missing_schedule=False: position,
    )

    review_driver = AuthoritativeRunSimulationDriver(database, None, None)
    request = AuthoritativeFullSimulationPreviewRequest(
        command_id="actively-abandoned-parent",
        run_id="run",
        branch_id="branch",
        operator_label="Worker",
        audit_reason="Prove the active execution fence",
    )
    preview = review_driver.preview_full_simulation(request)
    command = AuthoritativeFullSimulationCommand(
        **request.model_dump(mode="json"),
        expected_start_week=FINAL_WEEK,
        expected_position_fingerprint=preview["expected_position_fingerprint"],
        expected_revision_id=preview["expected_revision_id"],
        expected_preview_fingerprint=preview["preview_fingerprint"],
    )

    parent_created = threading.Event()
    release_worker = threading.Event()
    checks = 0

    def pause_after_parent_creation():
        nonlocal checks
        checks += 1
        if checks == 2:
            parent_created.set()
            assert release_worker.wait(timeout=10)

    worker_driver = AuthoritativeRunSimulationDriver(
        database,
        None,
        None,
        full_simulation_before_transaction_check=pause_after_parent_creation,
    )
    failures: list[BaseException] = []

    def run_worker():
        try:
            worker_driver.simulate_full_simulation(command)
        except BaseException as exc:  # captured for deterministic thread assertion
            failures.append(exc)

    thread = threading.Thread(target=run_worker)
    thread.start()
    assert parent_created.wait(timeout=10)
    abandoned = review_driver.abandon_full_simulation(
        AuthoritativeFullSimulationAbandonCommand(
            target_command_id=command.command_id,
            run_id="run",
            branch_id="branch",
            operator_label="Canceller",
            audit_reason="Cancel while the original invocation is active",
            confirm_committed_child_work_persists=True,
        )
    )
    release_worker.set()
    thread.join(timeout=10)

    assert not thread.is_alive()
    assert abandoned["status"] == "abandoned"
    assert len(failures) == 1
    assert "execution is fenced" in str(failures[0])
    with database() as session:
        receipt = session.get(
            AuthoritativeSimulationCommandModel,
            ("run", "branch", command.command_id),
        )
        assert receipt is not None
        assert receipt.status == "abandoned"
        stored = json.loads(receipt.result_json)
        assert stored["completed_seasons"] == []
        assert stored["final_completed_weeks"] == []
        assert stored["season_children"] == {}
        assert stored["final_week_children"] == {}


@pytest.mark.pr_critical
def test_completed_run_allows_unfinished_branch_full_simulation_preview(
    database, monkeypatch
):
    """Global lifecycle completion is not sporting finality for this Branch."""

    _patch_saved_revision_captures(monkeypatch)
    with database.begin() as session:
        _install_final_boundary(session)
        session.get(RunContainerModel, "run").status = COMPLETED_RUN_STATUS
    position = AuthoritativeSimulationPosition(
        run_id="run",
        branch_id="branch",
        current_week=FINAL_WEEK,
        current_slot_id=None,
        slot_ordinal=None,
        unresolved_group_ids=(),
        eligible_match_ids=(),
        blocked_match_ids=(),
        current_slot_complete=True,
        supported_tournament_complete=True,
        week_ready_for_transition=True,
        transition_blockers=("season_transition_required",),
        terminal_sporting_fingerprint="d" * 64,
        position_fingerprint="e" * 64,
    )
    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_position",
        lambda self, session, run_id, branch_id, allow_missing_schedule=False: position,
    )
    preview = AuthoritativeRunSimulationDriver(
        database, None, None
    ).preview_full_simulation(
        AuthoritativeFullSimulationPreviewRequest(
            command_id="completed-run-unfinished-branch",
            run_id="run",
            branch_id="branch",
            operator_label="Alternative timeline admin",
            audit_reason="Continue this unfinished alternative Branch",
        )
    )
    assert preview["start_week"] == FINAL_WEEK.model_dump(mode="json")
    assert preview["initial_action"] == "final_season_range"


@pytest.mark.pr_critical
def test_pending_branch_parent_ignores_other_branch_run_completion(
    database, monkeypatch
):
    _patch_saved_revision_captures(monkeypatch)
    with database.begin() as session:
        _install_final_boundary(session)
    position = AuthoritativeSimulationPosition(
        run_id="run",
        branch_id="branch",
        current_week=FINAL_WEEK,
        current_slot_id=None,
        slot_ordinal=None,
        unresolved_group_ids=(),
        eligible_match_ids=(),
        blocked_match_ids=(),
        current_slot_complete=True,
        supported_tournament_complete=True,
        week_ready_for_transition=True,
        transition_blockers=("season_transition_required",),
        terminal_sporting_fingerprint="d" * 64,
        position_fingerprint="e" * 64,
    )
    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_position",
        lambda self, session, run_id, branch_id, allow_missing_schedule=False: position,
    )
    driver = AuthoritativeRunSimulationDriver(database, None, None)
    request = AuthoritativeFullSimulationPreviewRequest(
        command_id="pending-branch-b",
        run_id="run",
        branch_id="branch",
        operator_label="Branch B admin",
        audit_reason="Keep B pending while another Branch completes",
    )
    preview = driver.preview_full_simulation(request)
    command = AuthoritativeFullSimulationCommand(
        **request.model_dump(mode="json"),
        expected_start_week=FINAL_WEEK,
        expected_position_fingerprint=preview["expected_position_fingerprint"],
        expected_revision_id=preview["expected_revision_id"],
        expected_preview_fingerprint=preview["preview_fingerprint"],
    )
    first = driver.simulate_full_simulation(command)
    assert first["checkpoint"] == "final_run_closure_review_required"

    with database.begin() as session:
        session.get(RunContainerModel, "run").status = COMPLETED_RUN_STATUS
        session.add(
            RunBranchModel(
                run_id="run",
                branch_id="other-final-branch",
                display_name="Timeline 2",
                status="active",
                read_only=0,
                saved_head_revision_id=None,
            )
        )

    retry = driver.simulate_full_simulation(command)
    assert retry["schema_version"] == "authoritative_full_simulation_progress.v1"
    assert retry["checkpoint"] == "final_run_closure_review_required"
    with database() as session:
        parent = session.get(
            AuthoritativeSimulationCommandModel,
            ("run", "branch", command.command_id),
        )
        assert parent.status == "pending"


@pytest.mark.pr_critical
@pytest.mark.parametrize(
    ("run_status", "run_read_only", "branch_read_only", "branch_status"),
    (
        (ARCHIVED_RUN_STATUS, 0, 0, "active"),
        (COMPLETED_RUN_STATUS, 1, 0, "active"),
        (COMPLETED_RUN_STATUS, 0, 1, "active"),
        (COMPLETED_RUN_STATUS, 0, 0, "archived"),
        ("corrupt-unknown-status", 0, 0, "active"),
    ),
)
def test_full_simulation_preview_blocks_archived_or_read_only_scope(
    database,
    monkeypatch,
    run_status,
    run_read_only,
    branch_read_only,
    branch_status,
):
    _patch_saved_revision_captures(monkeypatch)
    with database.begin() as session:
        _install_final_boundary(session)
        run = session.get(RunContainerModel, "run")
        branch = session.get(RunBranchModel, "branch")
        run.status = run_status
        run.read_only = run_read_only
        branch.read_only = branch_read_only
        branch.status = branch_status
    position = AuthoritativeSimulationPosition(
        run_id="run",
        branch_id="branch",
        current_week=FINAL_WEEK,
        current_slot_id=None,
        slot_ordinal=None,
        unresolved_group_ids=(),
        eligible_match_ids=(),
        blocked_match_ids=(),
        current_slot_complete=True,
        supported_tournament_complete=True,
        week_ready_for_transition=True,
        transition_blockers=(),
        terminal_sporting_fingerprint="d" * 64,
        position_fingerprint="e" * 64,
    )
    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_position",
        lambda self, session, run_id, branch_id, allow_missing_schedule=False: position,
    )
    driver = AuthoritativeRunSimulationDriver(database, None, None)
    with pytest.raises(ValueError, match="writable active Branch"):
        driver.preview_full_simulation(
            AuthoritativeFullSimulationPreviewRequest(
                command_id="blocked-scope",
                run_id="run",
                branch_id="branch",
                operator_label="Scope admin",
                audit_reason="Archived/read-only scope must fail closed",
            )
        )


@pytest.mark.pr_critical
def test_second_branch_final_closure_is_idempotent_in_completed_run(
    database, monkeypatch
):
    """A Branch may install its own closure without cycling global lifecycle."""

    _patch_saved_revision_captures(monkeypatch)
    command = _command()
    with database.begin() as session:
        _install_final_boundary(session)
        session.get(RunContainerModel, "run").status = COMPLETED_RUN_STATUS

    with database.begin() as session:
        result = commit_final_season_transition(session, command)
        assert result.saved_revision_id == "revision-final"
        assert result.run_status == COMPLETED_RUN_STATUS
    with database.begin() as session:
        retry = commit_final_season_transition(session, command)
        assert retry == result
    with database() as session:
        assert session.get(RunContainerModel, "run").status == COMPLETED_RUN_STATUS
        assert len(session.scalars(select(SeasonClosingRankingModel)).all()) == 1
        assert len(session.scalars(select(BranchRevisionAuditEventModel)).all()) == 1


@pytest.mark.pr_critical
def test_archived_run_preserves_valid_branch_final_closure_evidence(
    database, monkeypatch
):
    _patch_saved_revision_captures(monkeypatch)
    with database.begin() as session:
        _install_final_boundary(session)
        commit_final_season_transition(session, _command())
        session.get(RunContainerModel, "run").status = ARCHIVED_RUN_STATUS

    with database() as session:
        evidence = AuthoritativeRunSimulationDriver._branch_final_closure_evidence(
            session, run_id="run", branch_id="branch"
        )
    assert evidence["final_saved_revision_id"] == "revision-final"
    with database.begin() as session:
        session.get(RunContainerModel, "run").status = "corrupt-unknown-status"
    with database() as session, pytest.raises(ValueError, match="unknown Run lifecycle"):
        AuthoritativeRunSimulationDriver._branch_final_closure_evidence(
            session, run_id="run", branch_id="branch"
        )


@pytest.mark.pr_critical
def test_canonical_completed_run_forks_its_historical_revision_without_viewer_switch(
    database, monkeypatch
):
    _patch_saved_revision_captures(monkeypatch)
    with database.begin() as session:
        _install_final_boundary(session)
        commit_final_season_transition(session, _command())

    identities: Iterator[str] = iter(("branch-b", "draft-b"))
    repository = SimulationPersistenceRepository(
        engine=database.kw["bind"], session_factory=database
    )
    created = RunBranchCreationService(
        repository=repository,
        id_factory=lambda _kind: next(identities),
    ).create_from_saved_revision(
        run_id="run",
        source_branch_id="branch",
        source_saved_revision_id="revision-before-final",
    )

    assert created.branch_id == "branch-b"
    assert created.status == "active"
    assert created.read_only is False
    assert created.saved_head_revision_id == "revision-before-final"
    with database() as session:
        run = session.get(RunContainerModel, "run")
        source = session.get(RunBranchModel, "branch")
        target = session.get(RunBranchModel, "branch-b")
        target_draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == "branch-b"
            )
        )
        assert run.status == COMPLETED_RUN_STATUS
        assert run.official_branch_id == "branch"
        assert source.saved_head_revision_id == "revision-final"
        assert target.saved_head_revision_id == "revision-before-final"
        assert target_draft.status == CLEAN_WORKING_DRAFT_STATUS
        assert target_draft.base_revision_id == "revision-before-final"


@pytest.mark.pr_critical
def test_atomic_final_season_writer_rolls_back_everything_after_partial_failure(database, monkeypatch):
    _patch_saved_revision_captures(monkeypatch)
    command = _command()
    with database.begin() as session:
        _install_final_boundary(session)

    with pytest.raises(RuntimeError, match="fault after final closure revision"):
        with database.begin() as session:
            commit_final_season_transition(
                session,
                command,
                fault_at="after_revision",
            )

    with database() as session:
        run = session.get(RunContainerModel, "run")
        branch = session.get(RunBranchModel, "branch")
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == "branch"
            )
        )
        assert run.status == WORKING_RUN_STATUS
        assert branch.saved_head_revision_id == "revision-before-final"
        assert draft.base_revision_id == "revision-before-final"
        assert draft.draft_version == 7
        assert session.get(BranchSavedRevisionModel, "revision-final") is None
        assert session.get(BranchRevisionAuditEventModel, "audit-final") is None
        assert session.scalars(select(SeasonClosingRankingModel)).all() == []

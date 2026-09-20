import hashlib
import json

import pytest
from sqlalchemy import select

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
    AuthoritativeSimulationPosition,
)
from beta_engine.application.final_season_transition import (
    FINAL_WEEK,
    FinalSeasonTransitionCommand,
    commit_final_season_transition,
)
from beta_engine.domain.players.lifecycle import PlayerLifecycleWeekState
from beta_engine.domain.rankings.input_manifest import RankingInputManifest
from beta_engine.domain.rankings.official import (
    OfficialRankingPolicy,
    calculate_official_ranking,
)
from beta_engine.domain.run_containers import COMPLETED_RUN_STATUS, WORKING_RUN_STATUS
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
    Base,
    BranchRevisionAuditEventModel,
    BranchSavedRevisionModel,
    BranchWorkingDraftModel,
    OfficialRankingCommandModel,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    SeasonClosingRankingModel,
)
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.player_lifecycle_state import put_lifecycle
from beta_engine.infrastructure.db.saved_revision_season_closure import (
    load_saved_revision_season_closure,
)


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
    OfficialRankingCandidateStore(session).append(official, bootstrap=True)
    request_json = json.dumps(
        {
            "command_id": "final-ranking-evidence",
            "context": {
                "run_id": "run",
                "branch_id": "branch",
                "target_week": FINAL_WEEK.model_dump(mode="json"),
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    request_fingerprint = hashlib.sha256(request_json.encode()).hexdigest()
    manifest = RankingInputManifest(
        command_request_fingerprint=request_fingerprint,
        players=(),
        results=(),
    )
    manifest.verify(official, None)
    session.add(
        OfficialRankingCommandModel(
            run_id="run",
            branch_id="branch",
            command_id="final-ranking-evidence",
            request_fingerprint=request_fingerprint,
            request_payload_json=request_json,
            target_ordinal=FINAL_WEEK.ordinal,
            snapshot_fingerprint=official.fingerprint,
            input_manifest_version=1,
            input_manifest_json=manifest.model_dump_json(),
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
def test_atomic_final_season_writer_rolls_back_everything_after_partial_failure(database):
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

import json

import pytest
from sqlalchemy import select, text

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
    AuthoritativeSimulationPosition,
)
from beta_engine.application.ordinary_season_transition import (
    OrdinarySeasonTransitionCommand,
    commit_ordinary_season_transition,
)
from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.application.season_transition_configuration import (
    resolve_season_transition_configuration,
)
from beta_engine.domain.players.lifecycle import PlayerLifecycleWeekState
from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    PlayerDevelopmentPolicy,
    PlayerSportingWeekState,
)
from beta_engine.domain.rankings.input_manifest import RankingInputManifest
from beta_engine.domain.rankings.official import (
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.run_containers import WORKING_RUN_STATUS
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
    AuthoritativeWorldEventModel,
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
from beta_engine.infrastructure.db.player_lifecycle_state import (
    get_lifecycle,
    put_lifecycle,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    get_sporting,
    put_completed_context,
    put_sporting,
)
from beta_engine.infrastructure.db.saved_revision_season_closure import (
    load_saved_revision_season_closure,
)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'ordinary-season-transition.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    yield factory
    engine.dispose()


def _install_boundary(session):
    completed = RankingWeek(season_index=0, week=61)
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
        saved_head_revision_id="revision-before-season",
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
        "summary": "Test ordinary-season boundary base",
    }
    base_hash = saved_revision_content_hash(
        revision_id="revision-before-season",
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
            revision_id="revision-before-season",
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
            base_revision_id="revision-before-season",
            status=CLEAN_WORKING_DRAFT_STATUS,
            change_count=0,
            draft_version=7,
            draft_schema_version=RUN_WORKING_DRAFT_SCHEMA_VERSION,
            changes_json="[]",
        )
    )
    session.flush()

    lifecycle = put_lifecycle(
        session,
        PlayerLifecycleWeekState(
            run_id="run",
            branch_id="branch",
            week=completed,
            players=(),
            source_initial_world_fingerprint="world",
        ),
    )
    policy = OfficialRankingPolicy(policy_id="season-0-policy", best_n=15)
    candidates = OfficialRankingCandidateStore(session)
    previous = None
    for week_number in range(1, 62):
        ranking_week = RankingWeek(season_index=0, week=week_number)
        if previous is None:
            receipt_command = RankingBootstrapCommand(
                command_id="ranking-week-1",
                run_id="run",
                branch_id="branch",
                target_week=ranking_week,
                policy=policy,
                players=(),
                discipline="stored_zeros",
            )
        else:
            receipt_command = RankingWeekCommand(
                command_id=f"ranking-week-{week_number}",
                context=RankingTransitionContext(
                    run_id="run",
                    branch_id="branch",
                    completed_week=previous.week,
                    target_week=ranking_week,
                    policy=policy,
                    players=(),
                    discipline="stored_zeros",
                ),
                tournaments=(),
            )
        snapshot = calculate_official_ranking(
            run_id="run",
            branch_id="branch",
            week=ranking_week,
            policy=policy,
            players=(),
            results=(),
            previous=previous,
        )
        candidates.append(snapshot, bootstrap=previous is None)
        manifest = RankingInputManifest(
            command_request_fingerprint=receipt_command.fingerprint,
            zeros_from_history=True,
            players=(),
            results=(),
        )
        session.add(
            OfficialRankingCommandModel(
                run_id="run",
                branch_id="branch",
                command_id=receipt_command.command_id,
                request_fingerprint=receipt_command.fingerprint,
                request_payload_json=receipt_command.canonical_request_json,
                target_ordinal=ranking_week.ordinal,
                snapshot_fingerprint=snapshot.fingerprint,
                input_manifest_version=1,
                input_manifest_json=manifest.model_dump_json(),
            )
        )
        previous = snapshot

    official = previous
    assert official is not None and official.week == completed
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=completed.ordinal,
            snapshot_fingerprint=official.fingerprint,
            payload_json=official.model_dump_json(),
        )
    )
    session.add(
        AuthoritativeWorldStateModel(
            run_id="run",
            branch_id="branch",
            current_ordinal=completed.ordinal,
            ranking_fingerprint=official.fingerprint,
        )
    )

    completed_context = CompletedWeekSportingContext(
        run_id="run",
        branch_id="branch",
        completed_week=completed,
        competitive_match_counts=(),
        source_fingerprints=(),
        provenance="explicit empty ordinary-season transition test context",
    )
    put_completed_context(session, completed_context)
    put_sporting(
        session,
        PlayerSportingWeekState(
            run_id="run",
            branch_id="branch",
            week=completed,
            players=(),
            effective_development_policy=PlayerDevelopmentPolicy(
                policy_id="season-0-development"
            ),
            completed_context_fingerprint=completed_context.fingerprint,
            source_initial_world_fingerprint="world",
            stage_provenance="test",
        ),
    )
    return completed


def _position(completed):
    return AuthoritativeSimulationPosition(
        run_id="run",
        branch_id="branch",
        current_week=completed,
        current_slot_id=None,
        slot_ordinal=None,
        unresolved_group_ids=(),
        eligible_match_ids=(),
        blocked_match_ids=(),
        current_slot_complete=True,
        supported_tournament_complete=True,
        week_ready_for_transition=True,
        transition_blockers=("season_transition_required",),
        terminal_sporting_fingerprint="a" * 64,
        position_fingerprint="b" * 64,
    )


def _command(configuration, preflight_fingerprint):
    return OrdinarySeasonTransitionCommand(
        command_id="advance-season-1",
        run_id="run",
        branch_id="branch",
        configuration=configuration,
        expected_preflight_fingerprint=preflight_fingerprint,
        expected_saved_revision_id="revision-before-season",
        expected_draft_version=7,
        next_saved_revision_id="revision-season-1",
        audit_event_id="audit-season-1",
    )


@pytest.mark.pr_critical
def test_driver_commits_complete_ordinary_season_transition_and_retry(database, monkeypatch):
    with database.begin() as session:
        completed = _install_boundary(session)

    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_position",
        lambda self, session, run_id, branch_id: _position(completed),
    )
    driver = AuthoritativeRunSimulationDriver(database, None, None)
    preflight = driver.season_transition_preflight(run_id="run", branch_id="branch")
    assert preflight.ready_for_execution is True
    assert preflight.implementation_gaps == ()
    assert preflight.default_closing_ranking_fingerprint is not None
    assert preflight.default_sporting_fingerprint is not None
    assert preflight.default_lifecycle_fingerprint is not None
    assert preflight.default_ranking_fingerprint is not None

    with database() as session:
        configuration = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
        )
    command = _command(configuration, preflight.preflight_fingerprint)

    result = driver.advance_ordinary_season(command)
    assert result.target_week == RankingWeek(season_index=1, week=1)
    assert result.draft_version == 8

    with database() as session:
        world = session.get(AuthoritativeWorldStateModel, ("run", "branch"))
        assert world.current_ordinal == result.target_week.ordinal
        assert world.ranking_fingerprint == result.official_ranking_fingerprint

        publication = session.get(
            PublishedOfficialRankingModel,
            ("run", "branch", result.target_week.ordinal),
        )
        assert publication.snapshot_fingerprint == result.official_ranking_fingerprint

        lifecycle = get_lifecycle(
            session,
            run_id="run",
            branch_id="branch",
            week=result.target_week,
        )
        sporting = get_sporting(
            session,
            run_id="run",
            branch_id="branch",
            week=result.target_week,
        )
        assert lifecycle.fingerprint == result.player_lifecycle_fingerprint
        assert sporting.fingerprint == result.player_sporting_fingerprint

        revision = session.get(BranchSavedRevisionModel, "revision-season-1")
        branch = session.get(RunBranchModel, "branch")
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == "branch"
            )
        )
        assert revision.parent_revision_id == "revision-before-season"
        assert branch.saved_head_revision_id == "revision-season-1"
        assert draft.base_revision_id == "revision-season-1"
        assert draft.draft_version == 8

        revision_payload = json.loads(revision.payload_json)
        assert (
            revision_payload["content"]["ranking_preparation"]["state"]["schema_version"]
            == "ranking_revision_state.v7"
        )
        assert [
            row["event_kind"]
            for row in revision_payload["content"]["ranking_preparation"]["state"][
                "authoritative_transition_state"
            ]["events"]
        ] == ["season_transition_completed"]

        closure = load_saved_revision_season_closure(
            revision_payload,
            run_id="run",
            branch_id="branch",
            revision_id="revision-season-1",
        )
        assert closure is not None
        assert closure.parsed_summary.fingerprint == result.season_summary_fingerprint
        assert closure.parsed_marker.fingerprint == result.closure_marker_fingerprint

        event = session.get(
            AuthoritativeWorldEventModel,
            ("run", "branch", "advance-season-1"),
        )
        assert event.event_kind == "season_transition_completed"
        assert event.week_ordinal == result.target_week.ordinal
        audit = session.get(BranchRevisionAuditEventModel, "audit-season-1")
        assert audit.saved_revision_id == "revision-season-1"

    assert driver.advance_ordinary_season(command) == result


@pytest.mark.pr_critical
def test_atomic_writer_rolls_back_every_stage_after_public_state_fault(database):
    with database.begin() as session:
        completed = _install_boundary(session)

    with database() as session:
        configuration = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
        )
    command = _command(configuration, "c" * 64)

    with pytest.raises(RuntimeError, match="public state"):
        with database.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            commit_ordinary_season_transition(
                session,
                command,
                fault_at="after_public_state",
            )

    target = RankingWeek(season_index=1, week=1)
    with database() as session:
        world = session.get(AuthoritativeWorldStateModel, ("run", "branch"))
        assert world.current_ordinal == completed.ordinal
        assert (
            session.get(PublishedOfficialRankingModel, ("run", "branch", target.ordinal))
            is None
        )
        assert get_lifecycle(
            session,
            run_id="run",
            branch_id="branch",
            week=target,
        ) is None
        assert get_sporting(
            session,
            run_id="run",
            branch_id="branch",
            week=target,
        ) is None
        assert session.scalars(select(SeasonClosingRankingModel)).all() == []
        assert session.get(BranchSavedRevisionModel, "revision-season-1") is None
        assert (
            session.get(
                AuthoritativeWorldEventModel,
                ("run", "branch", "advance-season-1"),
            )
            is None
        )

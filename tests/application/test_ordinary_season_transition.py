import json

import pytest
from sqlalchemy import select

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
    AuthoritativeSimulationPosition,
)
import beta_engine.application.ordinary_season_transition as ordinary_transition
from beta_engine.application.ordinary_season_transition import (
    OrdinarySeasonTransitionCommand,
    commit_ordinary_season_transition,
)
from beta_engine.application.season_transition_configuration import (
    resolve_season_transition_configuration,
)
from beta_engine.domain.players.lifecycle import PlayerLifecycleWeekState
from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    PlayerDevelopmentPolicy,
    PlayerSportingWeekState,
)
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
    SEASON_TRANSITION_AUDIT_EVENT_KIND,
    SEASON_TRANSITION_SAVED_REVISION_KIND,
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
    OfficialRankingCandidateModel,
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


COMPLETED_WEEK = RankingWeek(season_index=0, week=61)
TARGET_WEEK = RankingWeek(season_index=1, week=1)


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
        "summary": "Test ordinary season-boundary base",
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
            week=COMPLETED_WEEK,
            players=(),
            source_initial_world_fingerprint="empty-world",
        ),
    )
    ranking_policy = OfficialRankingPolicy(policy_id="season-0-policy", best_n=15)
    official = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=COMPLETED_WEEK,
        policy=ranking_policy,
        players=lifecycle.ranking_roster(),
        results=(),
    )
    OfficialRankingCandidateStore(session).append(official, bootstrap=True)
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=COMPLETED_WEEK.ordinal,
            snapshot_fingerprint=official.fingerprint,
            payload_json=official.model_dump_json(),
        )
    )
    session.add(
        AuthoritativeWorldStateModel(
            run_id="run",
            branch_id="branch",
            current_ordinal=COMPLETED_WEEK.ordinal,
            ranking_fingerprint=official.fingerprint,
        )
    )

    development_policy = PlayerDevelopmentPolicy(policy_id="season-0-development")
    sporting = PlayerSportingWeekState(
        run_id="run",
        branch_id="branch",
        week=COMPLETED_WEEK,
        players=(),
        effective_development_policy=development_policy,
        completed_context_fingerprint="week61-context",
        source_initial_world_fingerprint="empty-world",
        stage_provenance="test",
    )
    put_sporting(session, sporting)
    put_completed_context(
        session,
        CompletedWeekSportingContext(
            run_id="run",
            branch_id="branch",
            completed_week=COMPLETED_WEEK,
            competitive_match_counts=(),
            source_fingerprints=(),
            provenance="explicit empty Week 61 test context",
        ),
    )
    session.flush()
    return official


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
        monkeypatch.setattr(ordinary_transition, name, fake_capture(name))
    return calls


def _command(configuration, preflight_fingerprint="a" * 64):
    return OrdinarySeasonTransitionCommand(
        command_id="advance-season-0",
        run_id="run",
        branch_id="branch",
        expected_preflight_fingerprint=preflight_fingerprint,
        expected_saved_revision_id="revision-before-season",
        expected_draft_version=7,
        configuration=configuration,
        season_saved_revision_id="revision-season-1",
        audit_event_id="audit-season-1",
    )


@pytest.mark.pr_critical
def test_atomic_ordinary_season_writer_commits_complete_week1_state(database, monkeypatch):
    capture_calls = _patch_saved_revision_captures(monkeypatch)
    with database.begin() as session:
        predecessor = _install_boundary(session)
        configuration = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
        )

    position = AuthoritativeSimulationPosition(
        run_id="run",
        branch_id="branch",
        current_week=COMPLETED_WEEK,
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
    assert preflight.final_season is False
    assert preflight.target_week == TARGET_WEEK
    assert preflight.default_closing_ranking_fingerprint is not None
    assert preflight.default_configuration_fingerprint == configuration.fingerprint
    assert preflight.default_sporting_fingerprint is not None
    assert preflight.default_lifecycle_fingerprint is not None
    assert preflight.default_ranking_fingerprint is not None
    assert preflight.state_blockers == ()
    assert preflight.implementation_gaps == (
        "season_prospect_creation_bridge_not_implemented",
    )
    assert preflight.ready_for_execution is False

    result = driver.advance_season(
        _command(configuration, preflight.preflight_fingerprint)
    )
    assert result.completed_week == COMPLETED_WEEK
    assert result.target_week == TARGET_WEEK
    assert result.saved_revision_id == "revision-season-1"
    assert result.draft_version == 8
    assert [name for name, _, _ in capture_calls] == [
        "capture_saved_ranking_component",
        "capture_saved_initial_world",
        "capture_saved_lifecycle",
        "capture_saved_sporting",
        "capture_saved_simulation_slots",
    ]

    with database() as session:
        branch = session.get(RunBranchModel, "branch")
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == "branch"
            )
        )
        revision = session.get(BranchSavedRevisionModel, "revision-season-1")
        world = session.get(AuthoritativeWorldStateModel, ("run", "branch"))
        publication = session.get(
            PublishedOfficialRankingModel,
            ("run", "branch", TARGET_WEEK.ordinal),
        )
        event = session.get(
            AuthoritativeWorldEventModel,
            ("run", "branch", "advance-season-0"),
        )
        lifecycle = get_lifecycle(
            session, run_id="run", branch_id="branch", week=TARGET_WEEK
        )
        sporting = get_sporting(
            session, run_id="run", branch_id="branch", week=TARGET_WEEK
        )

        assert branch.saved_head_revision_id == "revision-season-1"
        assert draft.base_revision_id == "revision-season-1"
        assert draft.draft_version == 8
        assert revision.kind == SEASON_TRANSITION_SAVED_REVISION_KIND
        assert revision.parent_revision_id == "revision-before-season"
        assert revision.sequence == 2
        assert world.current_ordinal == TARGET_WEEK.ordinal
        assert publication.snapshot_fingerprint == result.official_ranking_fingerprint
        assert world.ranking_fingerprint == publication.snapshot_fingerprint
        assert lifecycle.fingerprint == result.player_lifecycle_fingerprint
        assert sporting.fingerprint == result.player_sporting_fingerprint
        assert event.event_kind == "season_transition_completed"
        assert event.week_ordinal == TARGET_WEEK.ordinal
        assert predecessor.fingerprint != publication.snapshot_fingerprint

        payload = json.loads(revision.payload_json)
        closure = load_saved_revision_season_closure(
            payload,
            run_id="run",
            branch_id="branch",
            revision_id="revision-season-1",
        )
        assert closure is not None
        assert closure.parsed_marker.completed_week == COMPLETED_WEEK
        assert closure.parsed_marker.final_saved_revision_id == "revision-season-1"
        assert (
            closure.parsed_marker.closing_ranking_fingerprint
            == result.closing_ranking_fingerprint
        )

        closing = session.scalars(select(SeasonClosingRankingModel)).all()
        assert len(closing) == 1
        assert closing[0].fingerprint == result.closing_ranking_fingerprint
        audit = session.get(BranchRevisionAuditEventModel, "audit-season-1")
        assert audit.event_kind == SEASON_TRANSITION_AUDIT_EVENT_KIND

    with database.begin() as session:
        retry = commit_ordinary_season_transition(
            session,
            _command(configuration, preflight.preflight_fingerprint),
        )
        assert retry == result

    with database() as session:
        assert len(session.scalars(select(BranchSavedRevisionModel)).all()) == 2
        assert len(session.scalars(select(SeasonClosingRankingModel)).all()) == 1
        assert len(session.scalars(select(BranchRevisionAuditEventModel)).all()) == 1
        assert len(session.scalars(select(AuthoritativeWorldEventModel)).all()) == 1


@pytest.mark.pr_critical
def test_atomic_ordinary_season_writer_rolls_back_after_publication_failure(
    database, monkeypatch
):
    _patch_saved_revision_captures(monkeypatch)
    with database.begin() as session:
        predecessor = _install_boundary(session)
        configuration = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
        )
    command = _command(configuration)

    with pytest.raises(RuntimeError, match="fault after ordinary Season Transition publication"):
        with database.begin() as session:
            commit_ordinary_season_transition(
                session,
                command,
                fault_at="after_publication",
            )

    with database() as session:
        branch = session.get(RunBranchModel, "branch")
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == "branch"
            )
        )
        world = session.get(AuthoritativeWorldStateModel, ("run", "branch"))
        assert branch.saved_head_revision_id == "revision-before-season"
        assert draft.base_revision_id == "revision-before-season"
        assert draft.draft_version == 7
        assert world.current_ordinal == COMPLETED_WEEK.ordinal
        assert world.ranking_fingerprint == predecessor.fingerprint
        assert (
            session.get(
                PublishedOfficialRankingModel,
                ("run", "branch", TARGET_WEEK.ordinal),
            )
            is None
        )
        assert get_lifecycle(
            session, run_id="run", branch_id="branch", week=TARGET_WEEK
        ) is None
        assert get_sporting(
            session, run_id="run", branch_id="branch", week=TARGET_WEEK
        ) is None
        assert session.get(BranchSavedRevisionModel, "revision-season-1") is None
        assert session.get(BranchRevisionAuditEventModel, "audit-season-1") is None
        assert session.get(
            AuthoritativeWorldEventModel,
            ("run", "branch", "advance-season-0"),
        ) is None
        assert session.scalars(select(SeasonClosingRankingModel)).all() == []
        candidates = session.scalars(
            select(OfficialRankingCandidateModel).order_by(
                OfficialRankingCandidateModel.week_ordinal
            )
        ).all()
        assert [row.week_ordinal for row in candidates] == [COMPLETED_WEEK.ordinal]

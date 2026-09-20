import pytest
from sqlalchemy import select

from beta_engine.application.season_transition_configuration import (
    resolve_season_transition_configuration,
    validate_season_transition_configuration,
)
from beta_engine.domain.players.sporting import (
    PlayerDevelopmentPolicy,
    PlayerSportingWeekState,
)
from beta_engine.domain.rankings.official import (
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    Base,
    BranchWorkingDraftModel,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.player_sporting_state import put_sporting


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'season-config.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    yield factory
    engine.dispose()


def _install_boundary(session, *, season_index=0):
    week = RankingWeek(season_index=season_index, week=61)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Run",
            storage_kind="custom_local",
            read_only=0,
            timeline_start_season=2000,
            timeline_end_season=2049,
            official_branch_id="branch",
            status="working",
        )
    )
    session.add(
        RunBranchModel(
            run_id="run",
            branch_id="branch",
            display_name="Timeline 1",
            status="active",
            read_only=0,
            saved_head_revision_id="revision-1",
        )
    )
    session.add(
        BranchWorkingDraftModel(
            draft_id="draft",
            run_id="run",
            branch_id="branch",
            base_revision_id="revision-1",
            status="clean",
            change_count=0,
            draft_version=3,
            draft_schema_version="run_working_draft_v1",
            changes_json="[]",
        )
    )
    session.flush()

    ranking_policy = OfficialRankingPolicy(
        policy_id="season-outgoing-ranking",
        best_n=15,
    )
    official = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=week,
        policy=ranking_policy,
        players=(),
        results=(),
    )
    OfficialRankingCandidateStore(session).append(official, bootstrap=True)
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=week.ordinal,
            snapshot_fingerprint=official.fingerprint,
            payload_json=official.model_dump_json(),
        )
    )
    session.add(
        AuthoritativeWorldStateModel(
            run_id="run",
            branch_id="branch",
            current_ordinal=week.ordinal,
            ranking_fingerprint=official.fingerprint,
        )
    )
    development_policy = PlayerDevelopmentPolicy(policy_id="development-outgoing")
    sporting = PlayerSportingWeekState(
        run_id="run",
        branch_id="branch",
        week=week,
        players=(),
        effective_development_policy=development_policy,
        completed_context_fingerprint="completed-week-61",
        source_initial_world_fingerprint="world",
        stage_provenance="test",
    )
    put_sporting(session, sporting)
    return week, official, sporting


@pytest.mark.pr_critical
def test_default_configuration_inherits_supported_outgoing_policies(database):
    with database.begin() as session:
        completed, official, sporting = _install_boundary(session)
        config = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
        )

        assert config.completed_week == completed
        assert config.target_week == RankingWeek(season_index=1, week=1)
        assert config.base_revision_id == "revision-1"
        assert config.predecessor_official_fingerprint == official.fingerprint
        assert config.predecessor_sporting_fingerprint == sporting.fingerprint
        assert config.target_ranking_policy == official.policy
        assert (
            config.target_development_policy
            == sporting.effective_development_policy
        )
        assert config.ranking_policy_inherited is True
        assert config.development_policy_inherited is True
        assert config.reset_catalog.component_ids == ()
        assert len(config.reset_catalog.fingerprint) == 64
        assert len(config.fingerprint) == 64


@pytest.mark.pr_critical
def test_explicit_target_policy_overrides_are_bound_without_rewriting_outgoing_truth(
    database,
):
    with database.begin() as session:
        _, official, sporting = _install_boundary(session)
        target_ranking = OfficialRankingPolicy(
            policy_id="season-incoming-ranking",
            best_n=12,
        )
        target_development = PlayerDevelopmentPolicy(
            policy_id="development-incoming"
        )
        config = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
            target_ranking_policy=target_ranking,
            target_development_policy=target_development,
        )

        assert config.target_ranking_policy == target_ranking
        assert config.target_development_policy == target_development
        assert config.ranking_policy_inherited is False
        assert config.development_policy_inherited is False
        assert config.predecessor_official_fingerprint == official.fingerprint
        assert config.predecessor_sporting_fingerprint == sporting.fingerprint


@pytest.mark.pr_critical
def test_configuration_fails_closed_after_saved_head_changes(database):
    with database.begin() as session:
        _install_boundary(session)
        config = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
        )
        branch = session.get(RunBranchModel, "branch")
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == "branch"
            )
        )
        branch.saved_head_revision_id = "revision-2"
        draft.base_revision_id = "revision-2"
        session.flush()

        with pytest.raises(ValueError, match="configuration is stale"):
            validate_season_transition_configuration(session, config)


def test_final_season_has_no_incoming_configuration(database):
    with database.begin() as session:
        _install_boundary(session, season_index=49)
        with pytest.raises(ValueError, match="Final season"):
            resolve_season_transition_configuration(
                session,
                run_id="run",
                branch_id="branch",
            )

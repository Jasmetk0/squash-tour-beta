import pytest
from sqlalchemy import select

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
    AuthoritativeSimulationPosition,
)
from beta_engine.application.canonical_tournament_points import (
    build_tournament_point_award_authority,
)
from beta_engine.application.ranking_tournament_ingestion import TournamentRankingBinding
from beta_engine.application.season_transition_configuration import (
    resolve_season_transition_configuration,
    validate_season_transition_configuration,
)
from beta_engine.application.season_transition_lifecycle import (
    resolve_season_transition_lifecycle,
    stage_season_transition_lifecycle,
)
from beta_engine.application.season_transition_ranking import (
    resolve_season_transition_ranking,
    stage_season_transition_ranking,
)
from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
)
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
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.tournaments.result_authority import (
    TournamentPlayerResultAuthority,
    TournamentResultAuthority,
)
from beta_engine.application.season_point_awards_service import FrozenPointAwardAuthority
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
    RunProspectModel,
)
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.player_lifecycle_state import (
    get_lifecycle,
    put_lifecycle,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    put_completed_context,
    put_sporting,
)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'season-config.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    yield factory
    engine.dispose()


def _install_boundary(session, *, season_index=0, with_players=False):
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

    lifecycle_players = ()
    if with_players:
        position = season_week_to_calendar_position(2000 + season_index, 61)
        lifecycle_players = tuple(
            PlayerLifecycleIdentity(
                player_id=player_id,
                birth_year=1980,
                birth_year_week=1,
                tie_break_token=f"token-{player_id}",
                tie_break_provenance=f"test:{player_id}",
                tour_entry_week=RankingWeek(season_index=season_index, week=1),
                age=age_at_calendar_position(
                    birth_year=1980,
                    birth_year_week=1,
                    calendar_year=position.calendar_year,
                    year_week=position.year_week,
                ),
                status="active",
                origin="test",
            )
            for player_id in ("A", "B")
        )
    lifecycle = put_lifecycle(
        session,
        PlayerLifecycleWeekState(
            run_id="run",
            branch_id="branch",
            week=week,
            players=lifecycle_players,
            source_initial_world_fingerprint="world",
        ),
    )

    ranking_policy = OfficialRankingPolicy(
        policy_id="season-outgoing-ranking",
        best_n=15,
    )
    official = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=week,
        policy=ranking_policy,
        players=lifecycle.ranking_roster(),
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
    put_completed_context(
        session,
        CompletedWeekSportingContext(
            run_id="run",
            branch_id="branch",
            completed_week=week,
            competitive_match_counts=(),
            source_fingerprints=(),
            provenance="explicit empty W61 test context",
        ),
    )
    return week, official, sporting


def _install_owned_week61_source(session):
    completed = RankingWeek(season_index=0, week=61)
    result = TournamentResultAuthority(
        run_id="run",
        branch_id="branch",
        event_id="week61-event",
        completed_week=completed,
        draw_authority_fingerprint="a" * 64,
        match_package_fingerprint="b" * 64,
        champion_player_id="B",
        finalist_player_id="A",
        players=(
            TournamentPlayerResultAuthority(
                player_id="A",
                draw_type="main",
                reached_stage="finalist",
            ),
            TournamentPlayerResultAuthority(
                player_id="B",
                draw_type="main",
                reached_stage="champion",
            ),
        ),
        matches=(),
    )
    awards = build_tournament_point_award_authority(
        result=result,
        point_authority=FrozenPointAwardAuthority(
            ranking_status="ranked",
            point_distribution={"champion": 200, "finalist": 100},
            point_distribution_source="calendar_event.ranking_points_table",
        ),
        seed=77,
    )
    binding = TournamentRankingBinding(
        run_id="run",
        branch_id="branch",
        edition_id="week61-event",
        event_id="week61-event",
        completed_week=completed,
        first_publication_week=RankingWeek(season_index=1, week=1),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result.fingerprint,
        expected_award_fingerprint=awards.fingerprint,
    )
    return OwnedTournamentRankingSourceStore(session).append(
        OwnedTournamentRankingSource(
            schema_version="owned_tournament_ranking_source.v4",
            binding=binding,
            canonical_result=result,
            canonical_awards=awards,
            adopted_by_command_id="close-week61",
            provenance_kind="canonical_run_owned_tournament_authorities",
        )
    )


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


@pytest.mark.pr_critical
def test_cross_season_lifecycle_candidate_stages_without_advancing_public_world(database):
    with database.begin() as session:
        completed, _, _ = _install_boundary(session)
        config = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
        )
        resolved = resolve_season_transition_lifecycle(session, config)

        assert resolved.target_state.week == RankingWeek(season_index=1, week=1)
        assert (
            resolved.target_state.predecessor_fingerprint
            == resolved.predecessor_lifecycle_fingerprint
        )

        staged = stage_season_transition_lifecycle(session, config)
        installed = get_lifecycle(
            session,
            run_id="run",
            branch_id="branch",
            week=config.target_week,
        )
        assert installed is not None
        assert installed.fingerprint == staged.target_state.fingerprint

        world = session.get(AuthoritativeWorldStateModel, ("run", "branch"))
        assert world.current_ordinal == completed.ordinal


@pytest.mark.pr_critical
def test_cross_season_lifecycle_activates_target_week_prospect_as_pre_tour_draft(database):
    with database.begin() as session:
        _install_boundary(session)
        config = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
        )
        position = season_week_to_calendar_position(2001, 1)
        session.add(
            RunProspectModel(
                prospect_id="prospect-s1-w1",
                run_id="run",
                world_id="fax_official",
                season_start_year=2001,
                season_label="2001/02",
                season_week=1,
                calendar_year=position.calendar_year,
                year_week=position.year_week,
                birth_year=1986,
                birth_year_week=position.year_week,
                age=15,
                country_code="EGY",
                cohort_policy_version="test.v1",
                profile_version="test.v1",
                display_name="Prospect",
                identity_seed="identity",
                profile_seed="profile",
                development_seed="development",
                potential_seed="potential",
                trait_seed="trait",
            )
        )
        session.flush()

        resolved = resolve_season_transition_lifecycle(session, config)
        prospect = next(
            player
            for player in resolved.target_state.players
            if player.player_id == "prospect-s1-w1"
        )
        assert prospect.age == 15
        assert prospect.tour_entry_week is None
        assert prospect.status == "active"
        assert prospect.origin == "run_prospect:weekly_15yo_cohort:test.v1"
        assert len(prospect.tie_break_token) == 64
        assert "prospect-s1-w1" not in {
            player.player_id for player in resolved.target_state.ranking_roster()
        }


@pytest.mark.pr_critical
def test_week1_ranking_resolves_and_stages_without_publication_or_clock_advance(database):
    with database.begin() as session:
        completed, predecessor, _ = _install_boundary(session)
        incoming_policy = OfficialRankingPolicy(
            policy_id="season-incoming-ranking",
            best_n=12,
        )
        config = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
            target_ranking_policy=incoming_policy,
        )
        resolved = resolve_season_transition_ranking(session, config)

        assert resolved.target_snapshot.week == RankingWeek(season_index=1, week=1)
        assert resolved.target_snapshot.policy == incoming_policy
        assert resolved.target_snapshot.previous_fingerprint == predecessor.fingerprint
        assert resolved.predecessor_official_fingerprint == predecessor.fingerprint
        assert len(resolved.ranking_command_fingerprint) == 64

        staged = stage_season_transition_ranking(session, config)
        assert staged.target_snapshot.fingerprint == resolved.target_snapshot.fingerprint
        history = OfficialRankingCandidateStore(session).history(
            run_id="run",
            branch_id="branch",
        )
        assert history[-1].fingerprint == resolved.target_snapshot.fingerprint
        assert (
            session.get(
                PublishedOfficialRankingModel,
                ("run", "branch", config.target_week.ordinal),
            )
            is None
        )
        world = session.get(AuthoritativeWorldStateModel, ("run", "branch"))
        assert world.current_ordinal == completed.ordinal
        assert world.ranking_fingerprint == predecessor.fingerprint


@pytest.mark.pr_critical
def test_week1_ranking_consumes_owned_week61_tournament_source(database):
    with database.begin() as session:
        _install_boundary(session, with_players=True)
        _install_owned_week61_source(session)
        config = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
        )

        resolved = resolve_season_transition_ranking(session, config)
        assert [(row.player_id, row.points) for row in resolved.target_snapshot.rows] == [
            ("B", 200),
            ("A", 100),
        ]

        staged = stage_season_transition_ranking(session, config)
        assert staged.target_snapshot.fingerprint == resolved.target_snapshot.fingerprint
        assert (
            session.get(
                PublishedOfficialRankingModel,
                ("run", "branch", config.target_week.ordinal),
            )
            is None
        )


@pytest.mark.pr_critical
def test_ordinary_preflight_fingerprints_default_configuration(database, monkeypatch):
    with database.begin() as session:
        completed, _, _ = _install_boundary(session)
        expected = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
        )

    position = AuthoritativeSimulationPosition(
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
    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_position",
        lambda self, session, run_id, branch_id: position,
    )
    driver = AuthoritativeRunSimulationDriver(database, None, None)
    preflight = driver.season_transition_preflight(
        run_id="run",
        branch_id="branch",
    )

    assert preflight.final_season is False
    assert preflight.target_week == RankingWeek(season_index=1, week=1)
    assert preflight.default_configuration_fingerprint == expected.fingerprint
    assert preflight.default_closing_ranking_fingerprint is not None
    assert len(preflight.default_closing_ranking_fingerprint) == 64
    assert preflight.default_sporting_fingerprint is not None
    assert len(preflight.default_sporting_fingerprint) == 64
    assert preflight.default_lifecycle_fingerprint is not None
    assert len(preflight.default_lifecycle_fingerprint) == 64
    assert preflight.default_ranking_fingerprint is not None
    assert len(preflight.default_ranking_fingerprint) == 64
    assert "new_season_policy_activation_not_implemented" not in preflight.implementation_gaps
    assert "season_scoped_reset_catalog_not_implemented" not in preflight.implementation_gaps
    assert preflight.implementation_gaps == ()
    assert preflight.state_blockers == ()
    assert preflight.ready_for_execution is True

@pytest.mark.pr_critical
def test_ordinary_preflight_accepts_target_week_pre_tour_draft_prospect(
    database,
    monkeypatch,
):
    with database.begin() as session:
        completed, _, _ = _install_boundary(session)
        target_position = season_week_to_calendar_position(2001, 1)
        session.add(
            RunProspectModel(
                prospect_id="prospect-s1-w1",
                run_id="run",
                world_id="fax_official",
                season_start_year=2001,
                season_label="2001/02",
                season_week=1,
                calendar_year=target_position.calendar_year,
                year_week=target_position.year_week,
                birth_year=1986,
                birth_year_week=target_position.year_week,
                age=15,
                country_code="EGY",
                cohort_policy_version="test.v1",
                profile_version="test.v1",
                display_name="Prospect",
                identity_seed="identity",
                profile_seed="profile",
                development_seed="development",
                potential_seed="potential",
                trait_seed="trait",
            )
        )

    position = AuthoritativeSimulationPosition(
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
        position_fingerprint="c" * 64,
    )
    monkeypatch.setattr(
        AuthoritativeRunSimulationDriver,
        "_position",
        lambda self, session, run_id, branch_id: position,
    )
    preflight = AuthoritativeRunSimulationDriver(
        database, None, None
    ).season_transition_preflight(run_id="run", branch_id="branch")

    assert preflight.default_closing_ranking_fingerprint is not None
    assert preflight.default_sporting_fingerprint is not None
    assert preflight.default_lifecycle_fingerprint is not None
    assert preflight.default_ranking_fingerprint is not None
    assert preflight.implementation_gaps == ()
    assert preflight.state_blockers == ()
    assert preflight.ready_for_execution is True


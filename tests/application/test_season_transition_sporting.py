import pytest

from beta_engine.application.season_transition_configuration import (
    resolve_season_transition_configuration,
)
from beta_engine.application.season_transition_sporting import (
    resolve_season_transition_sporting,
    stage_season_transition_sporting,
)
from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.prospect_sporting_profile import (
    materialize_prospect_sporting_profile,
)
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
)
from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    CompetitiveMatchCount,
    PlayerDevelopmentPolicy,
    PlayerSportingRecord,
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
    RunProspectModel,
)
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.player_lifecycle_state import (
    get_lifecycle,
    put_lifecycle,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    capture_saved_sporting,
    get_sporting,
    load_saved_sporting,
    put_completed_context,
    put_sporting,
    stage_sporting_transition,
)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'season-sporting.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    yield factory
    engine.dispose()


def _install_empty_w61_boundary(session):
    completed = RankingWeek(season_index=0, week=61)
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
        policy_id="ranking-season-0",
        best_n=15,
    )
    official = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=completed,
        policy=ranking_policy,
        players=(),
        results=(),
    )
    OfficialRankingCandidateStore(session).append(official, bootstrap=True)
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
    lifecycle = PlayerLifecycleWeekState(
        run_id="run",
        branch_id="branch",
        week=completed,
        players=(),
        source_initial_world_fingerprint="world",
    )
    put_lifecycle(session, lifecycle)
    outgoing_development = PlayerDevelopmentPolicy(
        policy_id="development-season-0",
        weekly_change_basis_points=10000,
        form_regression_divisor=2,
        fatigue_recovery=7,
    )
    sporting = PlayerSportingWeekState(
        run_id="run",
        branch_id="branch",
        week=completed,
        players=(),
        effective_development_policy=outgoing_development,
        completed_context_fingerprint="week-60-context",
        source_initial_world_fingerprint="world",
        stage_provenance="test",
    )
    put_sporting(session, sporting)
    context = CompletedWeekSportingContext(
        run_id="run",
        branch_id="branch",
        completed_week=completed,
        competitive_match_counts=(),
        source_fingerprints=(),
        provenance="explicit empty W61 test context",
    )
    put_completed_context(session, context)
    return completed, official, sporting, context


def _install_week1_prospect(
    session,
    *,
    canonical_profile: bool = True,
):
    target = RankingWeek(season_index=1, week=1)
    position = season_week_to_calendar_position(2001, 1)
    profile_seed = "season-profile-seed"
    development_seed = "season-development-seed"
    potential_seed = "season-potential-seed"

    if canonical_profile:
        canonical = materialize_prospect_sporting_profile(
            player_id="prospect-s1-w1",
            profile_seed=profile_seed,
            development_seed=development_seed,
            potential_seed=potential_seed,
        )
        fingerprint = canonical.fingerprint
        profile_json = {
            "schema_version": "prospect_profile_v1",
            "canonical_sporting_profile": canonical.model_dump(mode="json"),
            "canonical_sporting_profile_fingerprint": fingerprint,
            "materialization_policy": {
                "sporting_profile_policy_id": canonical.profile_policy_id,
                "sporting_profile_policy_fingerprint": canonical.profile_policy_fingerprint,
            },
        }
        development_json = {
            "schema_version": "prospect_profile_v1",
            "development_timing": canonical.development_timing,
            "source_development_seed_digest": canonical.source_development_seed_digest,
            "sporting_profile_fingerprint": fingerprint,
        }
        potential_json = {
            "schema_version": "prospect_profile_v1",
            "potential_ovr": canonical.potential_ovr,
            "potential_identity": canonical.potential_identity,
            "potential_provenance": canonical.potential_provenance,
            "source_potential_seed_digest": canonical.source_potential_seed_digest,
            "sporting_profile_fingerprint": fingerprint,
        }
    else:
        canonical = None
        profile_json = {"reserved_for_future_attributes": True}
        development_json = {"reserved_for_future_development": True}
        potential_json = {"reserved_for_future_potential": True}

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
            birth_year=position.calendar_year - 15,
            birth_year_week=position.year_week,
            age=15,
            country_code="EGY",
            country_name="Egypt",
            status="prospect",
            source_type="weekly_15yo_cohort",
            cohort_policy_version="weekly_15yo_cohort_v1",
            profile_version="prospect_profile_v1",
            display_name="EGY Prospect 0001",
            identity_seed="season-identity-seed",
            profile_seed=profile_seed,
            development_seed=development_seed,
            potential_seed=potential_seed,
            trait_seed="season-trait-seed",
            profile_json=json.dumps(profile_json),
            development_json=json.dumps(development_json),
            potential_json=json.dumps(potential_json),
            trait_json=json.dumps({"reserved_for_future_traits": True}),
        )
    )
    session.flush()
    return canonical


@pytest.mark.pr_critical
def test_cross_season_sporting_uses_outgoing_policy_then_installs_incoming(database):
    with database.begin() as session:
        completed, _, predecessor, context = _install_empty_w61_boundary(session)
        incoming = PlayerDevelopmentPolicy(
            policy_id="development-season-1",
            weekly_change_basis_points=0,
            form_regression_divisor=9,
            fatigue_recovery=1,
        )
        configuration = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
            target_development_policy=incoming,
        )
        staged = resolve_season_transition_sporting(session, configuration)

        assert staged.target_state.week == RankingWeek(season_index=1, week=1)
        assert staged.target_state.predecessor_fingerprint == predecessor.fingerprint
        assert staged.target_state.completed_context_fingerprint == context.fingerprint
        assert (
            staged.target_state.applied_development_policy_id
            == predecessor.effective_development_policy.policy_id
        )
        assert staged.target_state.effective_development_policy == incoming
        assert (
            staged.applied_outgoing_development_policy_fingerprint
            == configuration.outgoing_development_policy_fingerprint
        )
        assert (
            staged.effective_target_development_policy_fingerprint
            != configuration.outgoing_development_policy_fingerprint
        )

        persisted = stage_season_transition_sporting(session, configuration)
        assert persisted.target_state.fingerprint == staged.target_state.fingerprint
        assert (
            get_sporting(
                session,
                run_id="run",
                branch_id="branch",
                week=configuration.target_week,
            ).fingerprint
            == staged.target_state.fingerprint
        )
        # This kernel stages only sporting/context state. Lifecycle and public world
        # advancement remain later Season Transition steps.
        assert (
            get_lifecycle(
                session,
                run_id="run",
                branch_id="branch",
                week=configuration.target_week,
            )
            is None
        )
        world = session.get(AuthoritativeWorldStateModel, ("run", "branch"))
        assert world.current_ordinal == completed.ordinal


@pytest.mark.pr_critical
def test_cross_season_sporting_adopts_week1_prospect_after_w61_development(database):
    with database.begin() as session:
        _, _, predecessor, context = _install_empty_w61_boundary(session)
        canonical = _install_week1_prospect(session, canonical_profile=True)
        incoming = PlayerDevelopmentPolicy(
            policy_id="development-season-1",
            weekly_change_basis_points=0,
            form_regression_divisor=9,
            fatigue_recovery=1,
        )
        configuration = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
            target_development_policy=incoming,
        )
        staged = resolve_season_transition_sporting(session, configuration)

        assert staged.target_state.predecessor_fingerprint == predecessor.fingerprint
        assert staged.target_state.completed_context_fingerprint == context.fingerprint
        assert [player.player_id for player in staged.target_state.players] == [
            "prospect-s1-w1"
        ]
        prospect = staged.target_state.players[0]
        assert canonical is not None
        assert prospect.attributes == canonical.attributes
        assert prospect.potential_ovr == canonical.potential_ovr
        assert prospect.development_timing == canonical.development_timing
        defaults = incoming.bootstrap_policy
        assert prospect.current_form == defaults.default_form
        assert prospect.long_term_form_norm == defaults.default_form_norm
        assert prospect.match_sharpness == defaults.default_match_sharpness
        assert prospect.long_term_fatigue == defaults.default_fatigue
        assert "birth_week_prospect_sporting_adoption.v1" in staged.target_state.stage_provenance


@pytest.mark.pr_critical
def test_cross_season_sporting_blocks_week1_placeholder_profile(database):
    with database.begin() as session:
        _install_empty_w61_boundary(session)
        _install_week1_prospect(session, canonical_profile=False)
        configuration = resolve_season_transition_configuration(
            session,
            run_id="run",
            branch_id="branch",
        )

        with pytest.raises(
            ValueError,
            match="Canonical prospect sporting profile evidence is missing",
        ):
            resolve_season_transition_sporting(session, configuration)


def _one_player_boundary():
    completed = RankingWeek(season_index=0, week=1)
    target = RankingWeek(season_index=0, week=2)
    position = season_week_to_calendar_position(2000, 1)
    age = age_at_calendar_position(
        birth_year=1980,
        birth_year_week=1,
        calendar_year=position.calendar_year,
        year_week=position.year_week,
    )
    lifecycle = PlayerLifecycleWeekState(
        run_id="run",
        branch_id="branch",
        week=completed,
        players=(
            PlayerLifecycleIdentity(
                player_id="p",
                birth_year=1980,
                birth_year_week=1,
                tie_break_token="token",
                tie_break_provenance="test",
                tour_entry_week=completed,
                age=age,
                status="active",
                origin="test",
            ),
        ),
        source_initial_world_fingerprint="world",
    )
    player = PlayerSportingRecord(
        player_id="p",
        attributes=tuple((name, 100) for name in CANONICAL_PLAYER_ATTRIBUTES),
        potential_ovr=150,
        potential_identity="potential",
        potential_provenance="test",
        development_timing="Standard",
        current_form=110,
        long_term_form_norm=100,
        match_sharpness=80,
        long_term_fatigue=30,
    )
    predecessor = PlayerSportingWeekState(
        run_id="run",
        branch_id="branch",
        week=completed,
        players=(player,),
        effective_development_policy=PlayerDevelopmentPolicy(
            policy_id="outgoing",
            weekly_change_basis_points=0,
        ),
        completed_context_fingerprint="bootstrap:not-a-completed-week",
        source_initial_world_fingerprint="world",
        stage_provenance="test",
    )
    terminal_player = player.model_copy(
        update={
            "current_form": 120,
            "match_sharpness": 90,
            "long_term_fatigue": 40,
        }
    )
    context = CompletedWeekSportingContext(
        schema_version="completed_week_sporting_context.v2",
        run_id="run",
        branch_id="branch",
        completed_week=completed,
        competitive_match_counts=(CompetitiveMatchCount(player_id="p", count=1),),
        source_fingerprints=("result",),
        terminal_sporting_fingerprint="terminal",
        match_effect_fingerprints=("effect",),
        provenance="test terminal match state",
    )
    return completed, target, lifecycle, predecessor, terminal_player, context


@pytest.mark.pr_critical
def test_pre_tour_draft_can_remain_outside_sporting_roster_across_next_week():
    completed, target, lifecycle, predecessor, _, context = _one_player_boundary()
    position = season_week_to_calendar_position(2000, completed.week)
    prospect = PlayerLifecycleIdentity(
        player_id="prospect",
        birth_year=1984,
        birth_year_week=50,
        tie_break_token="prospect-token",
        tie_break_provenance="birth-week draft",
        tour_entry_week=None,
        age=age_at_calendar_position(
            birth_year=1984,
            birth_year_week=50,
            calendar_year=position.calendar_year,
            year_week=position.year_week,
        ),
        status="active",
        origin="run_prospect:weekly_15yo_cohort:prospect_profile_v1",
    )
    lifecycle_with_draft = lifecycle.model_copy(
        update={
            "players": tuple(
                sorted((*lifecycle.players, prospect), key=lambda player: player.player_id)
            )
        }
    )

    successor = stage_sporting_transition(
        predecessor=predecessor,
        context=context,
        lifecycle=lifecycle_with_draft,
        target=target,
    )

    assert tuple(player.player_id for player in lifecycle_with_draft.players) == (
        "p",
        "prospect",
    )
    assert tuple(player.player_id for player in successor.players) == ("p",)
    assert successor.predecessor_fingerprint == predecessor.fingerprint


@pytest.mark.pr_critical
def test_terminal_match_state_preserves_saved_weekly_predecessor_lineage(database):
    completed, target, lifecycle, predecessor, terminal_player, context = (
        _one_player_boundary()
    )
    successor = stage_sporting_transition(
        predecessor=predecessor,
        context=context,
        lifecycle=lifecycle,
        target=target,
        terminal_players=(terminal_player,),
    )
    assert successor.predecessor_fingerprint == predecessor.fingerprint
    assert successor.predecessor_fingerprint != predecessor.model_copy(
        update={"players": (terminal_player,)}
    ).fingerprint
    assert successor.players[0].current_form > predecessor.players[0].current_form

    with database.begin() as session:
        put_sporting(session, predecessor)
        put_completed_context(session, context)
        put_sporting(session, successor)
        payload = {"content": {}}
        capture_saved_sporting(
            session,
            payload,
            run_id="run",
            branch_id="branch",
        )
        restored = load_saved_sporting(
            payload,
            run_id="run",
            branch_id="branch",
        )
        assert tuple(state.fingerprint for state in restored) == (
            predecessor.fingerprint,
            successor.fingerprint,
        )

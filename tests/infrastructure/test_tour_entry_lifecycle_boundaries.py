import pytest

from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
)
from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.domain.rankings.command_audit import RankingCommandAudit
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
    Base,
    BranchWorkingDraftModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.player_lifecycle_state import (
    advance_lifecycle_with_completed_tour_entries,
    put_lifecycle,
)
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PlayerTourEntryTriggerStore,
)
from beta_engine.infrastructure.db.ranking_transition_authority import (
    derive_ranking_transition_authority,
)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'tour-entry-boundary.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    yield factory
    engine.dispose()


def _install_scope(session):
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
            draft_version=1,
            draft_schema_version="run_working_draft_v1",
            changes_json="[]",
        )
    )
    session.flush()


def _player(week):
    position = season_week_to_calendar_position(2000 + week.season_index, week.week)
    return PlayerLifecycleIdentity(
        player_id="prospect",
        birth_year=1985,
        birth_year_week=10,
        tie_break_token="prospect-token",
        tie_break_provenance="test",
        tour_entry_week=None,
        age=age_at_calendar_position(
            birth_year=1985,
            birth_year_week=10,
            calendar_year=position.calendar_year,
            year_week=position.year_week,
        ),
        status="active",
        origin="test-prospect",
    )


def _lifecycle(week):
    return PlayerLifecycleWeekState(
        run_id="run",
        branch_id="branch",
        week=week,
        players=(_player(week),),
        source_initial_world_fingerprint="world",
    )


def _trigger(week):
    return PlayerTourEntryTrigger(
        run_id="run",
        branch_id="branch",
        player_id="prospect",
        event_id="event",
        trigger_kind="valid_tournament_application",
        trigger_week=week,
        decision_slot_ordinal=3,
        source_evidence_id=f"application-{week.ordinal}",
        source_evidence_fingerprint="a" * 64,
        provenance="test",
    )


@pytest.mark.pr_critical
def test_completed_week_tour_entry_is_sealed_into_next_opening_snapshot(database):
    completed = RankingWeek(season_index=0, week=20)
    target = RankingWeek(season_index=0, week=21)
    with database.begin() as session:
        _install_scope(session)
        predecessor = put_lifecycle(session, _lifecycle(completed))
        PlayerTourEntryTriggerStore(session).append(_trigger(completed))

        advanced = advance_lifecycle_with_completed_tour_entries(
            session,
            predecessor=predecessor,
            target=target,
        )

        assert predecessor.players[0].tour_entry_week is None
        assert advanced.players[0].tour_entry_week == completed
        assert advanced.predecessor_fingerprint == predecessor.fingerprint
        assert tuple(player.player_id for player in advanced.ranking_roster()) == (
            "prospect",
        )


@pytest.mark.pr_critical
def test_target_week_trigger_is_not_backdated_into_opening_snapshot(database):
    completed = RankingWeek(season_index=0, week=20)
    target = RankingWeek(season_index=0, week=21)
    with database.begin() as session:
        _install_scope(session)
        predecessor = put_lifecycle(session, _lifecycle(completed))
        PlayerTourEntryTriggerStore(session).append(_trigger(target))

        advanced = advance_lifecycle_with_completed_tour_entries(
            session,
            predecessor=predecessor,
            target=target,
        )

        assert advanced.players[0].tour_entry_week is None
        assert advanced.ranking_roster() == ()


@pytest.mark.pr_critical
def test_ranking_authority_includes_completed_week_new_tour_player(database):
    completed = RankingWeek(season_index=0, week=20)
    with database.begin() as session:
        _install_scope(session)
        lifecycle = put_lifecycle(session, _lifecycle(completed))
        policy = OfficialRankingPolicy(policy_id="ranking-policy", best_n=15)
        predecessor = calculate_official_ranking(
            run_id="run",
            branch_id="branch",
            week=completed,
            policy=policy,
            players=lifecycle.ranking_roster(),
            results=(),
        )
        OfficialRankingCandidateStore(session).append(predecessor, bootstrap=True)
        PlayerTourEntryTriggerStore(session).append(_trigger(completed))

        authority = derive_ranking_transition_authority(
            session,
            run_id="run",
            branch_id="branch",
            command_id="authority-1",
            audit=RankingCommandAudit(actor_label="test", reason="tour entry boundary"),
        )

        assert tuple(player.player_id for player in authority.players) == ("prospect",)
        assert authority.players[0].tour_entry_week == completed
        assert authority.target_week == RankingWeek(season_index=0, week=21)

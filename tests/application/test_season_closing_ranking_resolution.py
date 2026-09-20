"""Canonical Week-61 source resolution for archived Season Closing Ranking."""

import pytest
from sqlalchemy import select

from beta_engine.application.canonical_tournament_points import (
    build_tournament_point_award_authority,
)
from beta_engine.application.ranking_tournament_ingestion import TournamentRankingBinding
from beta_engine.application.season_closing_ranking_resolution import (
    resolve_canonical_season_closing_ranking,
    stage_canonical_season_closing_ranking,
)
from beta_engine.application.season_point_awards_service import FrozenPointAwardAuthority
from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
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
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    Base,
    OfficialRankingResultVersionModel,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    SeasonClosingRankingModel,
)
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.player_lifecycle_state import put_lifecycle


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'season-closing-resolver.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        session.add(
            RunContainerModel(
                run_id="run",
                timeline_start_season=2000,
                timeline_end_season=2049,
            )
        )
        session.add(
            RunBranchModel(
                run_id="run",
                branch_id="branch",
                display_name="Timeline 1",
            )
        )
    yield factory
    engine.dispose()


def _lifecycle_player(player_id: str, token: str) -> PlayerLifecycleIdentity:
    position = season_week_to_calendar_position(2000, 61)
    birth_year = 1975
    birth_year_week = 1
    return PlayerLifecycleIdentity(
        player_id=player_id,
        birth_year=birth_year,
        birth_year_week=birth_year_week,
        tie_break_token=token,
        tie_break_provenance=f"test:{player_id}",
        tour_entry_week=RankingWeek(season_index=0, week=1),
        age=age_at_calendar_position(
            birth_year=birth_year,
            birth_year_week=birth_year_week,
            calendar_year=position.calendar_year,
            year_week=position.year_week,
        ),
        status="active",
        origin="test",
    )


def _install_week61_authority(session):
    completed = RankingWeek(season_index=0, week=61)
    lifecycle = put_lifecycle(
        session,
        PlayerLifecycleWeekState(
            run_id="run",
            branch_id="branch",
            week=completed,
            players=(
                _lifecycle_player("A", "token-A"),
                _lifecycle_player("B", "token-B"),
            ),
            source_initial_world_fingerprint="initial-world-test",
        ),
    )
    predecessor = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=completed,
        policy=OfficialRankingPolicy(policy_id="season-2000-policy", best_n=15),
        players=lifecycle.ranking_roster(),
        results=(),
    )
    OfficialRankingCandidateStore(session).append(predecessor, bootstrap=True)
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=completed.ordinal,
            snapshot_fingerprint=predecessor.fingerprint,
            payload_json=predecessor.model_dump_json(),
        )
    )
    session.add(
        AuthoritativeWorldStateModel(
            run_id="run",
            branch_id="branch",
            current_ordinal=completed.ordinal,
            ranking_fingerprint=predecessor.fingerprint,
        )
    )
    return completed, predecessor


def _owned_week61_source():
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
    frozen_points = FrozenPointAwardAuthority(
        ranking_status="ranked",
        point_distribution={
            "champion": 200,
            "finalist": 100,
        },
        point_distribution_source="calendar_event.ranking_points_table",
    )
    awards = build_tournament_point_award_authority(
        result=result,
        point_authority=frozen_points,
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
    return OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v4",
        binding=binding,
        canonical_result=result,
        canonical_awards=awards,
        adopted_by_command_id="close-week61",
        provenance_kind="canonical_run_owned_tournament_authorities",
    )


@pytest.mark.pr_critical
def test_resolver_consumes_frozen_week61_source_without_week1_publication(database):
    with database.begin() as session:
        completed, predecessor = _install_week61_authority(session)
        OwnedTournamentRankingSourceStore(session).append(_owned_week61_source())

        preview = resolve_canonical_season_closing_ranking(
            session,
            run_id="run",
            branch_id="branch",
            completed_week=completed,
        )
        assert preview.predecessor_official_fingerprint == predecessor.fingerprint
        assert [(row.player_id, row.points) for row in preview.rows] == [
            ("B", 200),
            ("A", 100),
        ]

        staged = stage_canonical_season_closing_ranking(
            session,
            run_id="run",
            branch_id="branch",
            completed_week=completed,
        )
        assert staged == preview
        assert stage_canonical_season_closing_ranking(
            session,
            run_id="run",
            branch_id="branch",
            completed_week=completed,
        ) == preview

        # Week-61 owned tournament evidence is consumed in-memory. The resolver
        # does not pretend that ordinary Week Transition already ingested it.
        assert session.scalars(select(OfficialRankingResultVersionModel)).all() == []

    with database() as session:
        closing = session.scalars(select(SeasonClosingRankingModel)).all()
        assert len(closing) == 1
        publications = session.scalars(
            select(PublishedOfficialRankingModel).order_by(
                PublishedOfficialRankingModel.week_ordinal
            )
        ).all()
        assert len(publications) == 1
        assert publications[0].week_ordinal == RankingWeek(
            season_index=0, week=61
        ).ordinal
        world = session.get(AuthoritativeWorldStateModel, ("run", "branch"))
        assert world.current_ordinal == RankingWeek(season_index=0, week=61).ordinal


def test_resolver_requires_published_world_head(database):
    with database.begin() as session:
        completed, _ = _install_week61_authority(session)
        OwnedTournamentRankingSourceStore(session).append(_owned_week61_source())
        session.delete(session.get(AuthoritativeWorldStateModel, ("run", "branch")))
        with pytest.raises(ValueError, match="published authoritative Week 61 head"):
            resolve_canonical_season_closing_ranking(
                session,
                run_id="run",
                branch_id="branch",
                completed_week=completed,
            )


def test_final_season_remains_fail_closed_for_dedicated_adapter(database):
    with database.begin() as session:
        with pytest.raises(ValueError, match="final-season source adapter"):
            resolve_canonical_season_closing_ranking(
                session,
                run_id="run",
                branch_id="branch",
                completed_week=RankingWeek(season_index=49, week=61),
            )

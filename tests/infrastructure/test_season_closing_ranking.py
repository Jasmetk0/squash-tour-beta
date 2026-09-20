"""Season Closing Ranking is archived evidence, never Official publication."""

import pytest
from sqlalchemy import select

from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.season_closing import (
    calculate_season_closing_ranking,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    Base,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    SeasonClosingRankingModel,
)
from beta_engine.infrastructure.db.official_rankings import (
    OfficialRankingCandidateStore,
)
from beta_engine.infrastructure.db.season_closing_rankings import (
    SeasonClosingRankingConflict,
    SeasonClosingRankingStore,
)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'season-closing.db'}")
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


def _players():
    return (
        OfficialRankingPlayer(
            player_id="p1",
            tie_break_token="token-1",
            tour_entry_week=RankingWeek(season_index=0, week=1),
        ),
        OfficialRankingPlayer(
            player_id="p2",
            tie_break_token="token-2",
            tour_entry_week=RankingWeek(season_index=0, week=1),
        ),
    )


def _old_results():
    return (
        OfficialRankingResult(
            edition_id="old-p1",
            player_id="p1",
            source_fingerprint="old-p1-source",
            completed_week=RankingWeek(season_index=0, week=1),
            first_publication_week=RankingWeek(season_index=0, week=2),
            main_points=100,
        ),
        OfficialRankingResult(
            edition_id="old-p2",
            player_id="p2",
            source_fingerprint="old-p2-source",
            completed_week=RankingWeek(season_index=0, week=1),
            first_publication_week=RankingWeek(season_index=0, week=2),
            main_points=50,
        ),
    )


def _week61_result(points=200):
    return OfficialRankingResult(
        edition_id="week61-p2",
        player_id="p2",
        source_fingerprint=f"week61-p2-{points}",
        completed_week=RankingWeek(season_index=0, week=61),
        first_publication_week=RankingWeek(season_index=1, week=1),
        main_points=points,
    )


def _predecessor():
    policy = OfficialRankingPolicy(policy_id="season-2000-policy", best_n=15)
    return calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=61),
        policy=policy,
        players=_players(),
        results=_old_results(),
    )


def _closing(points=200):
    predecessor = _predecessor()
    return calculate_season_closing_ranking(
        run_id="run",
        branch_id="branch",
        completed_week=RankingWeek(season_index=0, week=61),
        policy=predecessor.policy,
        players=_players(),
        results=_old_results() + (_week61_result(points),),
        predecessor=predecessor,
    )


@pytest.mark.pr_critical
def test_week61_result_changes_archived_closing_order_without_official_publication(
    database,
):
    predecessor = _predecessor()
    assert [row.player_id for row in predecessor.rows] == ["p1", "p2"]

    closing = _closing()
    assert [row.player_id for row in closing.rows] == ["p2", "p1"]
    assert closing.rows[0].points == 250
    assert closing.rows[0].counted_results[0].edition_id == "week61-p2"
    assert closing.policy == predecessor.policy
    assert closing.predecessor_official_fingerprint == predecessor.fingerprint

    with database.begin() as session:
        OfficialRankingCandidateStore(session).append(predecessor, bootstrap=True)
        store = SeasonClosingRankingStore(session)
        assert store.append(closing) == closing
        assert store.append(closing) == closing

    with database() as session:
        stored = SeasonClosingRankingStore(session).get(
            run_id="run", branch_id="branch", season_index=0
        )
        assert stored == closing
        assert len(session.scalars(select(SeasonClosingRankingModel)).all()) == 1
        assert session.scalars(select(PublishedOfficialRankingModel)).all() == []
        assert session.scalars(select(AuthoritativeWorldStateModel)).all() == []


def test_closing_ranking_requires_week61_and_outgoing_policy():
    predecessor = _predecessor()
    with pytest.raises(ValueError, match="Week 61"):
        calculate_season_closing_ranking(
            run_id="run",
            branch_id="branch",
            completed_week=RankingWeek(season_index=0, week=60),
            policy=predecessor.policy,
            players=_players(),
            results=_old_results(),
            predecessor=predecessor,
        )
    with pytest.raises(ValueError, match="outgoing"):
        calculate_season_closing_ranking(
            run_id="run",
            branch_id="branch",
            completed_week=RankingWeek(season_index=0, week=61),
            policy=OfficialRankingPolicy(policy_id="wrong-policy"),
            players=_players(),
            results=_old_results(),
            predecessor=predecessor,
        )


def test_store_rejects_conflict_and_non_head_predecessor(database):
    predecessor = _predecessor()
    closing = _closing()
    with database.begin() as session:
        OfficialRankingCandidateStore(session).append(predecessor, bootstrap=True)
        store = SeasonClosingRankingStore(session)
        store.append(closing)
        with pytest.raises(SeasonClosingRankingConflict):
            store.append(_closing(points=201))

    with database.begin() as session:
        row = session.get(
            SeasonClosingRankingModel,
            ("run", "branch", 0),
        )
        session.delete(row)

    altered_predecessor = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=61),
        policy=OfficialRankingPolicy(policy_id="other-policy"),
        players=_players(),
        results=_old_results(),
    )
    bad = calculate_season_closing_ranking(
        run_id="run",
        branch_id="branch",
        completed_week=RankingWeek(season_index=0, week=61),
        policy=altered_predecessor.policy,
        players=_players(),
        results=_old_results() + (_week61_result(),),
        predecessor=altered_predecessor,
    )
    with database.begin() as session:
        with pytest.raises(ValueError, match="current Official Ranking Week 61"):
            SeasonClosingRankingStore(session).append(bad)

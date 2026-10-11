import pytest

from beta_engine.application.season_closure_resolution import (
    bind_canonical_season_closure_marker,
    resolve_canonical_season_closure_package,
)
from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.season_closing import calculate_season_closing_ranking
from beta_engine.domain.run_revisions import CONTENT_HASH_ALGORITHM
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    Base,
    BranchSavedRevisionModel,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.season_closing_rankings import (
    SeasonClosingRankingStore,
)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'season-closure.db'}")
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


def _install_closing(session):
    week = RankingWeek(season_index=0, week=61)
    players = (
        OfficialRankingPlayer(
            player_id="A",
            tie_break_token="token-A",
            tour_entry_week=RankingWeek(season_index=0, week=1),
        ),
    )
    policy = OfficialRankingPolicy(policy_id="season-2000-policy", best_n=15)
    predecessor = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=week,
        policy=policy,
        players=players,
        results=(),
    )
    OfficialRankingCandidateStore(session).append(predecessor, bootstrap=True)
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=week.ordinal,
            snapshot_fingerprint=predecessor.fingerprint,
            payload_json=predecessor.model_dump_json(),
        )
    )
    session.add(
        AuthoritativeWorldStateModel(
            run_id="run",
            branch_id="branch",
            current_ordinal=week.ordinal,
            ranking_fingerprint=predecessor.fingerprint,
        )
    )
    closing = calculate_season_closing_ranking(
        run_id="run",
        branch_id="branch",
        completed_week=week,
        policy=policy,
        players=players,
        results=(),
        predecessor=predecessor,
    )
    SeasonClosingRankingStore(session).append(closing)
    return week, closing


@pytest.mark.pr_critical
def test_canonical_closure_package_requires_closing_and_binds_future_revision(database):
    with database.begin() as session:
        week, closing = _install_closing(session)

        package = resolve_canonical_season_closure_package(
            session,
            run_id="run",
            branch_id="branch",
            completed_week=week,
        )
        assert package.summary.closing_ranking_fingerprint == closing.fingerprint
        assert package.summary.season_scoped_statistics == ()
        assert package.marker.season_summary_fingerprint == package.summary.fingerprint
        assert package.marker.closing_ranking_fingerprint == closing.fingerprint

        with pytest.raises(ValueError, match="staged Saved Revision"):
            bind_canonical_season_closure_marker(
                session,
                package,
                final_saved_revision_id="missing-revision",
            )

        session.add(
            BranchSavedRevisionModel(
                revision_id="season-transition-revision",
                run_id="run",
                branch_id="branch",
                sequence=1,
                parent_revision_id=None,
                kind="season_transition",
                payload_schema_version="branch_saved_revision.v1",
                content_hash_algorithm=CONTENT_HASH_ALGORITHM,
                content_hash="a" * 64,
                payload_json='{"content":{}}',
                change_summary_json='{}',
            )
        )
        session.flush()

        marker = bind_canonical_season_closure_marker(
            session,
            package,
            final_saved_revision_id="season-transition-revision",
        )
        assert marker.final_saved_revision_id == "season-transition-revision"
        assert marker.completed_week == week
        assert marker.season_summary_fingerprint == package.summary.fingerprint


def test_canonical_closure_package_requires_current_week61_world_head(database):
    with database.begin() as session:
        week, _ = _install_closing(session)
        world = session.get(AuthoritativeWorldStateModel, ("run", "branch"))
        world.current_ordinal = RankingWeek(season_index=0, week=60).ordinal
        with pytest.raises(ValueError, match="authoritative Week 61 world head"):
            resolve_canonical_season_closure_package(
                session,
                run_id="run",
                branch_id="branch",
                completed_week=week,
            )

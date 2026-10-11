"""File-backed SQLite integration of historical sources and ranking staging."""

import pytest

from beta_engine.application.official_ranking_transition import (
    RankingTransitionContext,
    stage_official_ranking_from_history,
)
from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.result_history import RankingResultVersion
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    Base,
    OfficialRankingResultVersionModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.official_rankings import (
    OfficialRankingCandidateStore,
)
from beta_engine.infrastructure.db.ranking_result_history import (
    OfficialRankingResultStore,
)


def week(n):
    return RankingWeek(season_index=(n - 1) // 61, week=(n - 1) % 61 + 1)


def source(*, previous=None, effective=62, points=100, **changes):
    result = OfficialRankingResult(
        edition_id="edition",
        player_id="p",
        source_fingerprint=f"award-{points}",
        completed_week=week(61),
        first_publication_week=week(62),
        main_points=points,
    )
    values = {
        "run_id": "run",
        "branch_id": "branch",
        "effective_week": week(effective),
        "result": result,
        "previous_fingerprint": previous.fingerprint if previous else None,
    }
    values.update(changes)
    return RankingResultVersion(**values)


def context(n):
    return RankingTransitionContext(
        run_id="run",
        branch_id="branch",
        completed_week=week(n - 1),
        target_week=week(n),
        policy=OfficialRankingPolicy(policy_id="policy"),
        discipline="none",
        players=(
            OfficialRankingPlayer(
                player_id="p", tie_break_token="stored-token", tour_entry_week=week(1)
            ),
        ),
    )


def bootstrap(session):
    c = context(62)
    return OfficialRankingCandidateStore(session).append(
        calculate_official_ranking(
            run_id=c.run_id,
            branch_id=c.branch_id,
            week=c.completed_week,
            policy=c.policy,
            players=c.players,
            results=(),
        ),
        bootstrap=True,
    )


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'sources.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        session.add(
            RunContainerModel(
                run_id="run", timeline_start_season=2000, timeline_end_season=2049
            )
        )
        session.add(
            RunContainerModel(
                run_id="other-run", timeline_start_season=2000, timeline_end_season=2049
            )
        )
        session.add(
            RunBranchModel(run_id="run", branch_id="branch", display_name="Timeline 1")
        )
        session.add(
            RunBranchModel(run_id="run", branch_id="other", display_name="Timeline 2")
        )
    yield factory
    engine.dispose()


def test_persisted_sources_correction_historical_retry_and_expiry(database):
    first = source()
    correction = source(previous=first, effective=63, points=150)
    with database.begin() as session:
        bootstrap(session)
        sources = OfficialRankingResultStore(session)
        sources.append(first)
        sources.append(correction)
    with database.begin() as session:
        sources = OfficialRankingResultStore(session)
        candidates = OfficialRankingCandidateStore(session)
        assert sources.resolve(run_id="run", branch_id="branch", week=week(61)) == ()
        original = stage_official_ranking_from_history(candidates, sources, context(62))
        corrected = stage_official_ranking_from_history(
            candidates, sources, context(63)
        )
        assert original.rows[0].points == 100
        assert corrected.rows[0].points == 150
        assert corrected.rows[0].counted_results[0].first_publication_week == week(62)
        assert (
            stage_official_ranking_from_history(candidates, sources, context(62))
            == original
        )
        assert sources.append(first) == first
        for n in range(64, 124):
            latest = stage_official_ranking_from_history(
                candidates, sources, context(n)
            )
        assert latest.rows[0].points == 0  # original week 62 + 61, not correction + 61
    with database() as session:
        history = OfficialRankingCandidateStore(session).history(
            run_id="run", branch_id="branch"
        )
        assert history[1] == original
        assert history[2] == corrected
        assert history[-1] == latest


def test_result_and_candidate_share_rollback(database):
    with database.begin() as session:
        initial = bootstrap(session)
    with pytest.raises(RuntimeError), database.begin() as session:
        sources = OfficialRankingResultStore(session)
        sources.append(source())
        stage_official_ranking_from_history(
            OfficialRankingCandidateStore(session), sources, context(62)
        )
        session.get(RunBranchModel, "branch").metadata_json = '{"advance":true}'
        raise RuntimeError("later component failed")
    with database() as session:
        assert (
            OfficialRankingResultStore(session).history(
                run_id="run", branch_id="branch"
            )
            == ()
        )
        assert OfficialRankingCandidateStore(session).history(
            run_id="run", branch_id="branch"
        ) == (initial,)
        assert session.get(RunBranchModel, "branch").metadata_json == "{}"


@pytest.mark.parametrize("damage", ["payload", "hash", "identity", "missing_initial"])
def test_source_corruption_fails_closed(database, damage):
    first = source()
    with database.begin() as session:
        store = OfficialRankingResultStore(session)
        store.append(first)
        store.append(source(previous=first, effective=63))
    with database.begin() as session:
        record = session.get(
            OfficialRankingResultVersionModel, ("run", "branch", "edition", "p", 61)
        )
        if damage == "payload":
            record.payload_json = "{}"
        elif damage == "hash":
            record.fingerprint = "0" * 64
        elif damage == "identity":
            record.player_id = "other-player"
        else:
            session.delete(record)
    with database() as session, pytest.raises(ValueError):
        OfficialRankingResultStore(session).resolve(
            run_id="run", branch_id="branch", week=week(63)
        )


def test_conflicts_backdating_and_missing_predecessor(database):
    first = source()
    with database.begin() as session:
        bootstrap(session)
        store = OfficialRankingResultStore(session)
        store.append(first)
        with pytest.raises(ValueError, match="Conflicting"):
            store.append(source(points=200))
        with pytest.raises(ValueError, match="missing predecessor"):
            store.append(
                source(
                    previous=first,
                    effective=63,
                    result=first.result.model_copy(update={"edition_id": "missing"}),
                )
            )
        stage_official_ranking_from_history(
            OfficialRankingCandidateStore(session), store, context(62)
        )
        with pytest.raises(ValueError, match="backdate"):
            store.append(
                source(result=first.result.model_copy(update={"edition_id": "late"}))
            )
        assert store.history(run_id="run", branch_id="branch") == (first,)


@pytest.mark.parametrize(
    "field,value",
    [
        ("first_publication_week", week(63)),
        ("completed_week", week(60)),
        ("validity_weeks", 100),
    ],
)
def test_correction_cannot_restart_or_change_lifetime(database, field, value):
    first = source()
    with database.begin() as session:
        store = OfficialRankingResultStore(session)
        store.append(first)
        with pytest.raises(ValueError, match="original timing"):
            store.append(
                source(
                    previous=first,
                    effective=64,
                    result=first.result.model_copy(update={field: value}),
                )
            )


def test_source_scope_readonly_and_fork_guards(database):
    with database.begin() as session:
        store = OfficialRankingResultStore(session)
        store.append(source())
        assert store.resolve(run_id="run", branch_id="other", week=week(62)) == ()
        with pytest.raises(ValueError, match="scope"):
            store.resolve(run_id="other-run", branch_id="branch", week=week(62))
        session.get(RunBranchModel, "other").read_only = 1
        with pytest.raises(ValueError, match="read-only"):
            store.append(source(branch_id="other"))
        session.get(RunBranchModel, "other").read_only = 0
        session.get(RunBranchModel, "other").forked_from_branch_id = "branch"
        with pytest.raises(ValueError, match="ancestry"):
            store.resolve(run_id="run", branch_id="other", week=week(62))
        session.get(RunContainerModel, "run").read_only = 1
        with pytest.raises(ValueError, match="read-only"):
            store.append(source())

"""Real extraction/award/SQLite components over a synthetic completed bracket."""

import pytest
from test_season_point_awards_service import make_points_service

from beta_engine.application.official_ranking_transition import (
    RankingTransitionContext,
    stage_official_ranking_from_history,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    ingest_tournament_ranking_sources,
    prepare_tournament_ranking_sources,
)
from beta_engine.application.season_event_results_service import (
    EventResultExtractRequest,
)
from beta_engine.application.season_point_awards_service import (
    PointAwardGenerateRequest,
)
from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import Base, RunBranchModel, RunContainerModel
from beta_engine.infrastructure.db.official_rankings import (
    OfficialRankingCandidateStore,
)
from beta_engine.infrastructure.db.ranking_result_history import (
    OfficialRankingResultStore,
)


@pytest.fixture
def packages(tmp_path):
    service, event_id = make_points_service(tmp_path)
    matches = service.result_service.match_service._load_registry()
    matches.matches_by_event_id[event_id].qualification_matches = []
    service.result_service.match_service._save_registry(matches)
    result = service.result_service.extract_event_result(
        event_id=event_id,
        request=EventResultExtractRequest(
            seed=10,
            dry_run=False,
            overwrite_existing=True,
        ),
    ).result_package
    awards = service.generate_event_point_awards(
        event_id=event_id, request=PointAwardGenerateRequest(seed=77, dry_run=False)
    ).award_package
    binding = TournamentRankingBinding(
        run_id="run",
        branch_id="branch",
        edition_id="edition",
        event_id=event_id,
        completed_week=RankingWeek(season_index=0, week=result.season_week),
        first_publication_week=RankingWeek(season_index=0, week=result.season_week + 1),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result.metadata.build_fingerprint,
        expected_award_fingerprint=awards.metadata.build_fingerprint,
    )
    return service, binding, result, awards


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'ranking.db'}")
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
            RunBranchModel(run_id="run", branch_id="branch", display_name="Timeline 1")
        )
    yield factory
    engine.dispose()


def test_persisted_tournament_to_ranking_and_retry_without_mutating_files(
    packages, database
):
    service, binding, result, awards = packages
    paths = [
        service.awards_path,
        service.result_service.results_path,
        service.active_players_service.active_players_path,
    ]
    before = [p.read_bytes() for p in paths]
    players = tuple(
        OfficialRankingPlayer(
            player_id=p.player_id,
            tie_break_token=p.player_id,
            tour_entry_week=RankingWeek(season_index=0, week=1),
        )
        for p in result.player_results
    )
    policy = OfficialRankingPolicy(policy_id="policy")
    with database.begin() as session:
        candidates = OfficialRankingCandidateStore(session)
        candidates.append(
            calculate_official_ranking(
                run_id="run",
                branch_id="branch",
                week=binding.completed_week,
                policy=policy,
                players=players,
                results=(),
            ),
            bootstrap=True,
        )
        sources = OfficialRankingResultStore(session)
        versions = ingest_tournament_ranking_sources(service, sources, binding)
        snapshot = stage_official_ranking_from_history(
            candidates,
            sources,
            RankingTransitionContext(
                run_id="run",
                branch_id="branch",
                completed_week=binding.completed_week,
                target_week=binding.first_publication_week,
                policy=policy,
                players=players,
                discipline="none",
            ),
        )
        assert {r.player_id: r.points for r in snapshot.rows} == {
            a.player_id: a.ranking_points_awarded for a in awards.awards
        }
        assert ingest_tournament_ranking_sources(service, sources, binding) == versions
    with database() as session:
        assert len(
            OfficialRankingResultStore(session).history(
                run_id="run", branch_id="branch"
            )
        ) == len(awards.awards)
        assert (
            OfficialRankingCandidateStore(session).history(
                run_id="run", branch_id="branch"
            )[-1]
            == snapshot
        )
    assert [p.read_bytes() for p in paths] == before


@pytest.mark.parametrize(
    "damage",
    [
        "incomplete",
        "preview",
        "duplicate",
        "missing_award",
        "points",
        "future_week",
        "qualification",
        "fallback",
        "provenance",
    ],
)
def test_bad_packages_are_rejected(packages, damage):
    _, binding, result, awards = packages
    if damage == "incomplete":
        result.completion_status = "partial"
    elif damage == "preview":
        awards.dry_run = True
    elif damage == "duplicate":
        result.player_results.append(result.player_results[0])
    elif damage == "missing_award":
        awards.awards.pop()
    elif damage == "points":
        awards.awards[0].ranking_points_awarded += 1
    elif damage == "future_week":
        binding = binding.model_copy(
            update={"completed_week": RankingWeek(season_index=0, week=61)}
        )
    elif damage == "qualification":
        result.player_results[0].qualifier = True
    elif damage == "fallback":
        awards.metadata.point_distribution_source = "fallback.stage_points"
    else:
        binding = binding.model_copy(update={"expected_result_fingerprint": "0" * 64})
    with pytest.raises(ValueError):
        prepare_tournament_ranking_sources(binding, result, awards)


def test_late_batch_failure_rolls_back_earlier_player_writes(packages, database):
    service, binding, result, awards = packages
    expected = prepare_tournament_ranking_sources(binding, result, awards)
    conflict = expected[-1].model_copy(
        update={"result": expected[-1].result.model_copy(update={"main_points": 9999})}
    )
    with database.begin() as session:
        OfficialRankingResultStore(session).append(conflict)
    with pytest.raises(ValueError, match="Conflicting"), database.begin() as session:
        ingest_tournament_ranking_sources(
            service, OfficialRankingResultStore(session), binding
        )
    with database() as session:
        assert OfficialRankingResultStore(session).history(
            run_id="run", branch_id="branch"
        ) == (conflict,)

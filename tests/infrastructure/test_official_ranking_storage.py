"""Real SQLite transaction tests; no production publication is implied."""

import pytest
from sqlalchemy import select

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
    OfficialRankingCandidateModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.official_rankings import (
    OfficialRankingCandidateStore,
    RankingCandidateConflict,
)


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
        session.add(
            RunBranchModel(run_id="run", branch_id="other", display_name="Timeline 2")
        )
    yield factory
    engine.dispose()


def candidate(n=61, *, previous=None, branch="branch", policy="policy"):
    return calculate_official_ranking(
        run_id="run",
        branch_id=branch,
        week=RankingWeek(season_index=(n - 1) // 61, week=(n - 1) % 61 + 1),
        policy=OfficialRankingPolicy(policy_id=policy),
        players=(),
        results=(),
        previous=previous,
    )


def test_commit_reload_rollover_and_exact_retry(database):
    first = candidate()
    second = candidate(62, previous=first)
    with database.begin() as session:
        store = OfficialRankingCandidateStore(session)
        store.append(first, bootstrap=True)
        store.append(second)
        assert store.append(first) == first
    with database() as session:
        assert OfficialRankingCandidateStore(session).history(
            run_id="run", branch_id="branch"
        ) == (first, second)
        assert len(session.scalars(select(OfficialRankingCandidateModel)).all()) == 2


def test_caller_rollback_removes_candidate_and_other_transition_write(database):
    with pytest.raises(RuntimeError), database.begin() as session:
        OfficialRankingCandidateStore(session).append(candidate(), bootstrap=True)
        session.get(RunBranchModel, "branch").metadata_json = '{"transition":"pending"}'
        raise RuntimeError("later transition step failed")
    with database() as session:
        assert (
            OfficialRankingCandidateStore(session).history(
                run_id="run", branch_id="branch"
            )
            == ()
        )
        assert session.get(RunBranchModel, "branch").metadata_json == "{}"


def test_bootstrap_conflict_and_gap_do_not_replace_history(database):
    first = candidate()
    with database.begin() as session:
        store = OfficialRankingCandidateStore(session)
        with pytest.raises(RankingCandidateConflict):
            store.append(first)
        store.append(first, bootstrap=True)
        with pytest.raises(RankingCandidateConflict):
            store.append(candidate(policy="changed"))
        with pytest.raises(RankingCandidateConflict):
            store.append(candidate(63))
        with pytest.raises(RankingCandidateConflict):
            store.append(candidate(62, previous=first), bootstrap=True)
        assert store.history(run_id="run", branch_id="branch") == (first,)


def test_fork_cannot_silently_bootstrap_without_ancestry(database):
    with database.begin() as session:
        session.get(RunBranchModel, "other").forked_from_branch_id = "branch"
        with pytest.raises(RankingCandidateConflict, match="ancestry"):
            OfficialRankingCandidateStore(session).append(
                candidate(branch="other"), bootstrap=True
            )


def test_scope_isolation_and_read_only_guards(database):
    with database.begin() as session:
        store = OfficialRankingCandidateStore(session)
        store.append(candidate(), bootstrap=True)
        assert store.history(run_id="run", branch_id="other") == ()
        with pytest.raises(ValueError):
            store.history(run_id="unknown", branch_id="branch")
        session.get(RunBranchModel, "other").read_only = 1
        with pytest.raises(ValueError):
            store.append(candidate(branch="other"), bootstrap=True)
        session.get(RunContainerModel, "run").read_only = 1
        with pytest.raises(ValueError):
            store.append(candidate(), bootstrap=True)


@pytest.mark.parametrize("damage", ["payload", "fingerprint", "missing_parent"])
def test_corrupt_history_fails_closed(database, damage):
    first = candidate()
    second = candidate(62, previous=first)
    with database.begin() as session:
        store = OfficialRankingCandidateStore(session)
        store.append(first, bootstrap=True)
        store.append(second)
    with database.begin() as session:
        record = session.get(OfficialRankingCandidateModel, ("run", "branch", 60))
        if damage == "payload":
            record.payload_json = "{}"
        elif damage == "fingerprint":
            record.fingerprint = "0" * 64
        else:
            session.delete(record)
    with database() as session, pytest.raises(ValueError):
        OfficialRankingCandidateStore(session).history(run_id="run", branch_id="branch")


def transition_request(**changes):
    from beta_engine.application.official_ranking_transition import (
        ResolvedRankingTransition,
    )
    from beta_engine.domain.rankings.official import (
        OfficialRankingPlayer,
        OfficialRankingResult,
    )

    values = {
        "run_id": "run",
        "branch_id": "branch",
        "completed_week": RankingWeek(season_index=0, week=61),
        "target_week": RankingWeek(season_index=1, week=1),
        "policy": OfficialRankingPolicy(policy_id="next-season", best_n=1),
        "players": (
            OfficialRankingPlayer(
                player_id="p",
                tie_break_token="persisted-token",
                tour_entry_week=RankingWeek(season_index=0, week=1),
            ),
        ),
        "results": (
            OfficialRankingResult(
                player_id="p",
                edition_id="edition",
                source_fingerprint="resolved-award",
                completed_week=RankingWeek(season_index=0, week=61),
                first_publication_week=RankingWeek(season_index=1, week=1),
                qualification_points=10,
                main_points=100,
            ),
        ),
        "discipline": "none",
    }
    values.update(changes)
    return ResolvedRankingTransition(**values)


def test_transition_calculation_commit_reload_and_historical_retry(database):
    from beta_engine.application.official_ranking_transition import (
        stage_official_ranking_transition,
    )

    request = transition_request()
    first = candidate()
    with database.begin() as session:
        store = OfficialRankingCandidateStore(session)
        store.append(first, bootstrap=True)
        second = stage_official_ranking_transition(store, request)
        assert second.rows[0].points == 110
        assert second.policy.best_n == 1
        assert second.previous_fingerprint == first.fingerprint
        third = stage_official_ranking_transition(
            store,
            transition_request(
                completed_week=request.target_week,
                target_week=RankingWeek(season_index=1, week=2),
            ),
        )
        assert stage_official_ranking_transition(store, request) == second
        with pytest.raises(RankingCandidateConflict):
            stage_official_ranking_transition(
                store,
                transition_request(
                    policy=OfficialRankingPolicy(policy_id="different"),
                ),
            )
    with database() as session:
        assert OfficialRankingCandidateStore(session).history(
            run_id="run", branch_id="branch"
        ) == (first, second, third)


@pytest.mark.parametrize(
    "failure", ["missing_previous", "gap", "future_completion", "future_publication"]
)
def test_transition_invalid_boundaries_do_not_stage(database, failure):
    from beta_engine.application.official_ranking_transition import (
        stage_official_ranking_transition,
    )

    request = transition_request()
    if failure == "gap":
        request = transition_request(target_week=RankingWeek(season_index=1, week=2))
    elif failure in {"future_completion", "future_publication"}:
        result = request.results[0].model_copy(
            update={
                "first_publication_week": RankingWeek(season_index=1, week=3),
                **(
                    {"completed_week": RankingWeek(season_index=1, week=2)}
                    if failure == "future_completion"
                    else {}
                ),
            }
        )
        request = transition_request(results=(result,))
    with database.begin() as session:
        store = OfficialRankingCandidateStore(session)
        if failure != "missing_previous":
            store.append(candidate(), bootstrap=True)
        before = store.history(run_id="run", branch_id="branch")
        with pytest.raises(ValueError):
            stage_official_ranking_transition(store, request)
        assert store.history(run_id="run", branch_id="branch") == before


def test_transition_later_failure_rolls_back_computed_ranking(database):
    from beta_engine.application.official_ranking_transition import (
        stage_official_ranking_transition,
    )

    with database.begin() as session:
        OfficialRankingCandidateStore(session).append(candidate(), bootstrap=True)
    with pytest.raises(RuntimeError), database.begin() as session:
        stage_official_ranking_transition(
            OfficialRankingCandidateStore(session), transition_request()
        )
        session.get(RunBranchModel, "branch").metadata_json = '{"next_week":62}'
        raise RuntimeError("another transition component failed")
    with database() as session:
        assert OfficialRankingCandidateStore(session).history(
            run_id="run", branch_id="branch"
        ) == (candidate(),)
        assert session.get(RunBranchModel, "branch").metadata_json == "{}"


def test_transition_requires_explicit_supported_discipline_scope():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        transition_request(discipline="active_sanctions")


def test_transition_reconsiders_previously_uncounted_results_after_expiry(database):
    from beta_engine.application.official_ranking_transition import (
        stage_official_ranking_transition,
    )

    request = transition_request()
    expiring = request.results[0].model_copy(update={"validity_weeks": 1})
    reserve = expiring.model_copy(
        update={
            "edition_id": "reserve",
            "main_points": 40,
            "validity_weeks": 61,
        }
    )
    request = transition_request(results=(expiring, reserve))
    with database.begin() as session:
        store = OfficialRankingCandidateStore(session)
        store.append(candidate(), bootstrap=True)
        first = stage_official_ranking_transition(store, request)
        assert first.rows[0].points == 110
        second = stage_official_ranking_transition(
            store,
            transition_request(
                completed_week=request.target_week,
                target_week=RankingWeek(season_index=1, week=2),
                results=(reserve, expiring),
            ),
        )
        assert second.rows[0].points == 50
        assert second.rows[0].counted_results == (reserve,)
        assert first.rows[0].counted_results == (expiring,)

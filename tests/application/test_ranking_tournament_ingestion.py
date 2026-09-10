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


def ranking_command(packages, database, *, command_id="prepare-week"):
    from beta_engine.application.ranking_week_command import RankingWeekCommand

    _, binding, result, _ = packages
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
        OfficialRankingCandidateStore(session).append(
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
    return RankingWeekCommand(
        command_id=command_id,
        tournaments=(binding,),
        context=RankingTransitionContext(
            run_id="run",
            branch_id="branch",
            completed_week=binding.completed_week,
            target_week=binding.first_publication_week,
            policy=policy,
            players=players,
            discipline="none",
        ),
    )


def test_owned_command_commits_and_replays_without_rereading_legacy_files(
    packages, database
):
    from beta_engine.infrastructure.db.ranking_week_command import (
        RankingWeekCommandRunner,
    )

    command = ranking_command(packages, database)
    service = packages[0]
    runner = RankingWeekCommandRunner(database, service)
    first = runner.execute(command)
    assert {r.player_id: r.points for r in first.rows} == {
        a.player_id: a.ranking_points_awarded for a in packages[3].awards
    }
    service.awards_path.write_text("invalid current JSON")
    reordered = command.model_copy(
        update={
            "context": command.context.model_copy(
                update={"players": tuple(reversed(command.context.players))}
            )
        }
    )
    assert runner.execute(reordered) == first
    with pytest.raises(ValueError, match="already staged"):
        runner.execute(command.model_copy(update={"command_id": "different-id"}))
    with pytest.raises(ValueError, match="different request"):
        runner.execute(command.model_copy(update={"tournaments": ()}))


def test_owned_command_rolls_back_sources_when_ranking_fails(packages, database):
    from sqlalchemy import select

    from beta_engine.infrastructure.db.models import OfficialRankingCommandModel
    from beta_engine.infrastructure.db.ranking_week_command import (
        RankingWeekCommandRunner,
    )

    command = ranking_command(packages, database)
    # Ingestion succeeds for all players, but calculation rejects the missing roster member.
    command = command.model_copy(
        update={
            "context": command.context.model_copy(
                update={"players": command.context.players[:-1]}
            )
        }
    )
    with pytest.raises(ValueError, match="unknown player"):
        RankingWeekCommandRunner(database, packages[0]).execute(command)
    with database() as session:
        assert (
            OfficialRankingResultStore(session).history(
                run_id="run", branch_id="branch"
            )
            == ()
        )
        assert (
            len(
                OfficialRankingCandidateStore(session).history(
                    run_id="run", branch_id="branch"
                )
            )
            == 1
        )
        assert session.scalars(select(OfficialRankingCommandModel)).all() == []


def test_receipt_detects_deleted_candidate_tail(packages, database):
    from beta_engine.infrastructure.db.models import OfficialRankingCandidateModel
    from beta_engine.infrastructure.db.ranking_week_command import (
        RankingWeekCommandRunner,
    )

    command = ranking_command(packages, database)
    runner = RankingWeekCommandRunner(database, packages[0])
    runner.execute(command)
    with database.begin() as session:
        record = session.get(
            OfficialRankingCandidateModel,
            ("run", "branch", command.context.target_week.ordinal),
        )
        session.delete(record)
    with pytest.raises(ValueError, match="missing or corrupt snapshot"):
        runner.execute(command)


@pytest.mark.parametrize("damage", ["scope", "duplicate", "boundary"])
def test_command_validates_batch_before_writing(packages, database, damage):
    from beta_engine.infrastructure.db.ranking_week_command import (
        RankingWeekCommandRunner,
    )

    command = ranking_command(packages, database)
    binding = command.tournaments[0]
    if damage == "scope":
        bindings = (binding.model_copy(update={"branch_id": "other"}),)
    elif damage == "duplicate":
        bindings = (binding, binding)
    else:
        bindings = (
            binding.model_copy(
                update={"first_publication_week": RankingWeek(season_index=0, week=61)}
            ),
        )
    with pytest.raises(ValueError):
        RankingWeekCommandRunner(database, packages[0]).execute(
            command.model_copy(update={"tournaments": bindings})
        )
    with database() as session:
        assert (
            OfficialRankingResultStore(session).history(
                run_id="run", branch_id="branch"
            )
            == ()
        )


def test_second_tournament_failure_rolls_back_first_tournament(packages, database):
    from beta_engine.infrastructure.db.ranking_week_command import (
        RankingWeekCommandRunner,
    )

    command = ranking_command(packages, database)
    missing = command.tournaments[0].model_copy(
        update={"edition_id": "zz-missing", "event_id": "missing-event"}
    )
    command = command.model_copy(
        update={"tournaments": (*command.tournaments, missing)}
    )
    with pytest.raises(ValueError, match="Persisted tournament"):
        RankingWeekCommandRunner(database, packages[0]).execute(command)
    with database() as session:
        assert (
            OfficialRankingResultStore(session).history(
                run_id="run", branch_id="branch"
            )
            == ()
        )


def test_receipt_write_failure_rolls_back_candidate_and_sources(packages, database):
    from sqlalchemy import event

    from beta_engine.infrastructure.db.models import OfficialRankingCommandModel
    from beta_engine.infrastructure.db.ranking_week_command import (
        RankingWeekCommandRunner,
    )

    command = ranking_command(packages, database)

    def fail_receipt(*args):
        raise RuntimeError("receipt write failed")

    event.listen(OfficialRankingCommandModel, "before_insert", fail_receipt)
    try:
        with pytest.raises(RuntimeError, match="receipt write failed"):
            RankingWeekCommandRunner(database, packages[0]).execute(command)
    finally:
        event.remove(OfficialRankingCommandModel, "before_insert", fail_receipt)
    with database() as session:
        assert (
            OfficialRankingResultStore(session).history(
                run_id="run", branch_id="branch"
            )
            == ()
        )
        assert (
            len(
                OfficialRankingCandidateStore(session).history(
                    run_id="run", branch_id="branch"
                )
            )
            == 1
        )


def assert_only_bootstrap(session):
    from sqlalchemy import select
    from beta_engine.infrastructure.db.models import OfficialRankingCommandModel

    assert OfficialRankingResultStore(session).history(run_id="run", branch_id="branch") == ()
    assert len(OfficialRankingCandidateStore(session).history(run_id="run", branch_id="branch")) == 1
    assert session.scalars(select(OfficialRankingCommandModel)).all() == []


@pytest.mark.smoke
def test_composed_command_waits_for_outer_commit_and_replays(packages, database):
    from sqlalchemy import text
    from beta_engine.infrastructure.db.ranking_week_command import stage_ranking_week_command

    command = ranking_command(packages, database)
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        first = stage_ranking_week_command(session, packages[0], command)
        assert stage_ranking_week_command(session, packages[0], command) == first
        with database() as reader:
            assert_only_bootstrap(reader)
    with database() as reader:
        assert OfficialRankingCandidateStore(reader).history(run_id="run", branch_id="branch")[-1] == first


@pytest.mark.smoke
def test_later_transition_failure_rolls_back_successful_ranking(packages, database):
    from sqlalchemy import text
    from beta_engine.infrastructure.db.ranking_week_command import stage_ranking_week_command

    command = ranking_command(packages, database)
    with pytest.raises(RuntimeError, match="later transition failed"):
        with database.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            stage_ranking_week_command(session, packages[0], command)
            raise RuntimeError("later transition failed")
    with database() as reader:
        assert_only_bootstrap(reader)


@pytest.mark.smoke
def test_caught_component_failure_preserves_outer_work_without_partial_ranking(packages, database):
    from sqlalchemy import text
    from beta_engine.infrastructure.db.ranking_week_command import stage_ranking_week_command

    command = ranking_command(packages, database)
    invalid = command.model_copy(update={"context": command.context.model_copy(
        update={"players": command.context.players[:-1]}
    )})
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        session.get(RunBranchModel, "branch").display_name = "Renamed timeline"
        with pytest.raises(ValueError, match="unknown player"):
            stage_ranking_week_command(session, packages[0], invalid)
        assert_only_bootstrap(session)
    with database() as reader:
        assert_only_bootstrap(reader)
        assert reader.get(RunBranchModel, "branch").display_name == "Renamed timeline"


@pytest.mark.smoke
@pytest.mark.parametrize("autobegin", [False, True])
def test_composed_command_rejects_missing_physical_transaction(packages, database, autobegin):
    from sqlalchemy import text
    from beta_engine.infrastructure.db.ranking_week_command import stage_ranking_week_command

    command = ranking_command(packages, database)
    with database() as session:
        if autobegin:
            session.execute(text("SELECT 1"))
        with pytest.raises(ValueError, match="transaction"):
            stage_ranking_week_command(session, packages[0], command)
    with database() as reader:
        assert_only_bootstrap(reader)


def correction_command(packages, database):
    from beta_engine.domain.rankings.result_history import RankingResultVersion
    from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner

    original = ranking_command(packages, database)
    runner = RankingWeekCommandRunner(database, packages[0])
    before = runner.execute(original)
    target = RankingWeek(season_index=0, week=before.week.week + 1)
    with database() as session:
        versions = OfficialRankingResultStore(session).history(run_id="run", branch_id="branch")
    corrections = tuple(
        RankingResultVersion(
            run_id="run", branch_id="branch", effective_week=target,
            previous_fingerprint=v.fingerprint,
            result=v.result.model_copy(update={"main_points": v.result.main_points + 100,
                                              "source_fingerprint": "corrected-" + v.result.player_id}),
        ) for v in versions
    )
    command = original.model_copy(update={
        "command_id": "correct-next-week", "tournaments": (), "corrections": corrections,
        "context": original.context.model_copy(update={"completed_week": before.week, "target_week": target}),
    })
    return runner, command, before, versions


@pytest.mark.smoke
def test_week_corrections_preserve_history_timing_and_canonical_replay(packages, database):
    runner, command, before, versions = correction_command(packages, database)
    after = runner.execute(command)
    old_points = {r.player_id: r.points for r in before.rows}
    assert {r.player_id: r.points for r in after.rows} == {p: n + 100 for p, n in old_points.items()}
    old_results = {v.result.player_id: v.result for v in versions}
    for row in after.rows:
        result = row.counted_results[0]
        original = old_results[row.player_id]
        assert result.first_publication_week == original.first_publication_week
        assert result.validity_weeks == original.validity_weeks
    reordered = command.model_copy(update={"corrections": tuple(reversed(command.corrections))})
    assert reordered.fingerprint == command.fingerprint
    packages[0].awards_path.write_text("invalid current JSON")
    assert runner.execute(reordered) == after
    with database() as session:
        history = OfficialRankingCandidateStore(session).history(run_id="run", branch_id="branch")
        assert history[-2] == before
        assert len(OfficialRankingResultStore(session).history(run_id="run", branch_id="branch")) == 2 * len(versions)
    with pytest.raises(ValueError, match="different request"):
        runner.execute(command.model_copy(update={"corrections": ()}))


@pytest.mark.smoke
def test_second_correction_failure_rolls_back_first_and_receipt(packages, database):
    from sqlalchemy import select
    from beta_engine.infrastructure.db.models import OfficialRankingCommandModel

    runner, command, before, versions = correction_command(packages, database)
    assert len(command.corrections) > 1
    damaged = (*command.corrections[:-1], command.corrections[-1].model_copy(
        update={"previous_fingerprint": "0" * 64}
    ))
    with pytest.raises(ValueError, match="extend its source lineage"):
        runner.execute(command.model_copy(update={"corrections": damaged}))
    with database() as session:
        assert OfficialRankingResultStore(session).history(run_id="run", branch_id="branch") == versions
        assert OfficialRankingCandidateStore(session).history(run_id="run", branch_id="branch")[-1] == before
        assert len(session.scalars(select(OfficialRankingCommandModel)).all()) == 1
    assert runner.execute(command).week == command.context.target_week


@pytest.mark.parametrize("damage", ["scope", "boundary", "duplicate", "initial", "lifetime"])
def test_invalid_week_corrections_are_rejected_without_writes(packages, database, damage):
    runner, command, before, versions = correction_command(packages, database)
    correction = command.corrections[0]
    if damage == "scope":
        correction = correction.model_copy(update={"branch_id": "other"})
    elif damage == "boundary":
        correction = correction.model_copy(update={"effective_week": before.week})
    elif damage == "initial":
        correction = correction.model_copy(update={"previous_fingerprint": None})
    elif damage == "lifetime":
        correction = correction.model_copy(update={"result": correction.result.model_copy(update={"validity_weeks": 62})})
    corrections = (correction, correction) if damage == "duplicate" else (correction,)
    with pytest.raises(ValueError):
        runner.execute(command.model_copy(update={"corrections": corrections}))
    with database() as session:
        assert OfficialRankingResultStore(session).history(run_id="run", branch_id="branch") == versions
        assert OfficialRankingCandidateStore(session).history(run_id="run", branch_id="branch")[-1] == before


@pytest.mark.smoke
def test_empty_corrections_keep_legacy_command_fingerprint(packages, database):
    import hashlib
    import json

    command = ranking_command(packages, database)
    legacy = command.model_dump(mode="json", exclude={"corrections"})
    legacy["context"]["players"].sort(key=lambda p: p["player_id"])
    legacy["tournaments"].sort(key=lambda t: t["edition_id"])
    expected = hashlib.sha256(json.dumps(legacy, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert command.fingerprint == expected


def test_tournament_command_requires_award_service_before_writing(packages, database):
    from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner

    request = ranking_command(packages, database)
    with pytest.raises(ValueError, match="requires an award service"):
        RankingWeekCommandRunner(database).execute(request)
    with database() as session:
        assert_only_bootstrap(session)

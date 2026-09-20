import pytest

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
    TournamentApplicationSubmissionBatchAuthority,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    Base,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PlayerTourEntryTriggerStore,
)
from beta_engine.infrastructure.db.tournament_application_submissions import (
    TOURNAMENT_APPLICATION_SUBMISSION_COMPONENT_KEY,
    TournamentApplicationSubmissionConflict,
    TournamentApplicationSubmissionStore,
    capture_saved_application_submissions,
    load_saved_application_submissions,
    record_valid_application_submission,
    record_valid_application_submission_batch,
    restore_saved_application_submissions,
)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'application-submissions.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
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
            )
        )
    yield factory
    engine.dispose()


def _submission(**overrides):
    payload = {
        "application_id": "application-1",
        "run_id": "run",
        "branch_id": "branch",
        "event_id": "event-1",
        "player_id": "prospect-1",
        "entry_window": "main",
        "submission_week": RankingWeek(season_index=0, week=9),
        "decision_slot_ordinal": 3,
        "nr_tie_break_token": "nr-token-1",
        "validation_authority_id": "validation-1",
        "validation_authority_fingerprint": "a" * 64,
        "provenance": "canonical valid tournament application",
    }
    payload.update(overrides)
    return TournamentApplicationSubmissionAuthority(**payload)


@pytest.mark.pr_critical
def test_valid_submission_persists_with_first_tour_entry_atomically(database):
    submission = _submission()
    with database.begin() as session:
        result = record_valid_application_submission(session, submission)
        assert result.submission == submission
        assert result.first_tour_entry_trigger == submission.to_tour_entry_trigger()
        assert TournamentApplicationSubmissionStore(session).get(
            run_id="run",
            branch_id="branch",
            application_id="application-1",
        ) == submission
        assert PlayerTourEntryTriggerStore(session).get(
            run_id="run",
            branch_id="branch",
            player_id="prospect-1",
        ) == submission.to_tour_entry_trigger()


@pytest.mark.pr_critical
def test_exact_retry_is_idempotent_and_later_application_keeps_first_trigger(database):
    first = _submission()
    later = _submission(
        application_id="application-2",
        event_id="event-2",
        submission_week=RankingWeek(season_index=0, week=12),
        decision_slot_ordinal=4,
        nr_tie_break_token="nr-token-2",
    )
    with database.begin() as session:
        first_result = record_valid_application_submission(session, first)
        retry_result = record_valid_application_submission(session, first)
        later_result = record_valid_application_submission(session, later)

        assert retry_result == first_result
        assert later_result.first_tour_entry_trigger == first_result.first_tour_entry_trigger
        assert TournamentApplicationSubmissionStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == (first, later)


@pytest.mark.pr_critical
def test_earlier_or_simultaneous_distinct_submission_cannot_rewrite_first_entry(database):
    first = _submission(
        application_id="application-later",
        submission_week=RankingWeek(season_index=0, week=10),
        decision_slot_ordinal=5,
    )
    earlier = _submission(
        application_id="application-earlier",
        submission_week=RankingWeek(season_index=0, week=9),
        decision_slot_ordinal=1,
    )
    simultaneous = _submission(
        application_id="application-same-slot",
        submission_week=RankingWeek(season_index=0, week=10),
        decision_slot_ordinal=5,
    )
    with database.begin() as session:
        record_valid_application_submission(session, first)
        with pytest.raises(
            TournamentApplicationSubmissionConflict,
            match="predates persisted first Tour-entry trigger",
        ):
            record_valid_application_submission(session, earlier)
        with pytest.raises(
            TournamentApplicationSubmissionConflict,
            match="simultaneous first-entry authority",
        ):
            record_valid_application_submission(session, simultaneous)

        assert TournamentApplicationSubmissionStore(session).get(
            run_id="run",
            branch_id="branch",
            application_id="application-earlier",
        ) is None
        assert TournamentApplicationSubmissionStore(session).get(
            run_id="run",
            branch_id="branch",
            application_id="application-same-slot",
        ) is None


@pytest.mark.pr_critical
def test_same_slot_multi_application_batch_is_order_independent(database):
    app_a = _submission(
        application_id="application-a",
        event_id="event-a",
        nr_tie_break_token="nr-a",
    )
    app_b = _submission(
        application_id="application-b",
        event_id="event-b",
        nr_tie_break_token="nr-b",
    )
    batch = TournamentApplicationSubmissionBatchAuthority.from_submissions(
        (app_b, app_a)
    )

    with database.begin() as session:
        result = record_valid_application_submission_batch(session, batch)

        assert result.batch.submissions == (app_a, app_b)
        assert result.first_tour_entry_triggers == (app_a.to_tour_entry_trigger(),)
        assert TournamentApplicationSubmissionStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == (app_a, app_b)
        assert PlayerTourEntryTriggerStore(session).get(
            run_id="run",
            branch_id="branch",
            player_id="prospect-1",
        ) == app_a.to_tour_entry_trigger()


@pytest.mark.pr_critical
def test_same_slot_batch_creates_one_first_trigger_per_player(database):
    first = _submission(
        application_id="application-a",
        player_id="prospect-1",
        event_id="event-a",
    )
    second = _submission(
        application_id="application-b",
        player_id="prospect-2",
        event_id="event-b",
        nr_tie_break_token="nr-token-2",
    )
    batch = TournamentApplicationSubmissionBatchAuthority.from_submissions(
        (second, first)
    )

    with database.begin() as session:
        result = record_valid_application_submission_batch(session, batch)

        assert tuple(
            trigger.player_id for trigger in result.first_tour_entry_triggers
        ) == ("prospect-1", "prospect-2")
        assert PlayerTourEntryTriggerStore(session).get(
            run_id="run",
            branch_id="branch",
            player_id="prospect-1",
        ) == first.to_tour_entry_trigger()
        assert PlayerTourEntryTriggerStore(session).get(
            run_id="run",
            branch_id="branch",
            player_id="prospect-2",
        ) == second.to_tour_entry_trigger()


@pytest.mark.pr_critical
def test_individual_same_slot_calls_fail_closed_instead_of_using_call_order(database):
    app_b = _submission(
        application_id="application-b",
        event_id="event-b",
    )
    app_a = _submission(
        application_id="application-a",
        event_id="event-a",
    )

    with database.begin() as session:
        record_valid_application_submission(session, app_b)
        with pytest.raises(
            TournamentApplicationSubmissionConflict,
            match="simultaneous first-entry authority",
        ):
            record_valid_application_submission(session, app_a)


@pytest.mark.pr_critical
def test_application_id_conflict_does_not_change_first_trigger(database):
    first = _submission()
    conflicting = _submission(event_id="different-event")
    with database.begin() as session:
        record_valid_application_submission(session, first)
        with pytest.raises(
            TournamentApplicationSubmissionConflict,
            match="Application ID already has different",
        ):
            record_valid_application_submission(session, conflicting)

        assert PlayerTourEntryTriggerStore(session).get(
            run_id="run",
            branch_id="branch",
            player_id="prospect-1",
        ) == first.to_tour_entry_trigger()


@pytest.mark.pr_critical
def test_saved_component_round_trip_restores_submission_history(database):
    empty_payload = {"content": {}}
    with database.begin() as session:
        capture_saved_application_submissions(
            session,
            empty_payload,
            run_id="run",
            branch_id="branch",
        )
    assert empty_payload["content"][TOURNAMENT_APPLICATION_SUBMISSION_COMPONENT_KEY][
        "submissions"
    ] == []

    submission = _submission()
    current_payload = {"content": {}}
    with database.begin() as session:
        TournamentApplicationSubmissionStore(session).append(submission)
        capture_saved_application_submissions(
            session,
            current_payload,
            run_id="run",
            branch_id="branch",
        )

    assert load_saved_application_submissions(
        current_payload,
        run_id="run",
        branch_id="branch",
    ) == (submission,)

    with database.begin() as session:
        restore_saved_application_submissions(
            session,
            current_payload=current_payload,
            target_payload=empty_payload,
            run_id="run",
            branch_id="branch",
        )
        assert TournamentApplicationSubmissionStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == ()

    with database.begin() as session:
        restore_saved_application_submissions(
            session,
            current_payload=empty_payload,
            target_payload=current_payload,
            run_id="run",
            branch_id="branch",
        )
        assert TournamentApplicationSubmissionStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == (submission,)

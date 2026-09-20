import pytest

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
)
from beta_engine.domain.tournaments.definitive_wild_card_assignment import (
    DefinitiveWildCardAssignmentAuthority,
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
    record_valid_application_submission,
)
from beta_engine.infrastructure.db.definitive_wild_card_assignments import (
    DEFINITIVE_WILD_CARD_ASSIGNMENT_COMPONENT_KEY,
    DefinitiveWildCardAssignmentConflict,
    DefinitiveWildCardAssignmentStore,
    capture_saved_definitive_wild_card_assignments,
    load_saved_definitive_wild_card_assignments,
    record_definitive_wild_card_assignment,
    restore_saved_definitive_wild_card_assignments,
)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'definitive-wc.db'}")
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


def _assignment(**overrides):
    payload = {
        "run_id": "run",
        "branch_id": "branch",
        "event_id": "event-wc",
        "player_id": "prospect-1",
        "wildcard_index": 1,
        "assignment_source": "original_wc",
        "assignment_week": RankingWeek(season_index=0, week=9),
        "decision_slot_ordinal": 3,
        "source_wild_card_command_id": "wc-command-1",
        "source_wild_card_authority_fingerprint": "a" * 64,
        "source_entry_field_fingerprint": "b" * 64,
        "source_field_sequence": 2,
        "provenance": "canonical definitive WC field assignment",
    }
    payload.update(overrides)
    return DefinitiveWildCardAssignmentAuthority(**payload)


def _submission(**overrides):
    payload = {
        "application_id": "application-1",
        "run_id": "run",
        "branch_id": "branch",
        "event_id": "event-app",
        "player_id": "prospect-1",
        "entry_window": "main",
        "submission_week": RankingWeek(season_index=0, week=8),
        "decision_slot_ordinal": 2,
        "nr_tie_break_token": "nr-token",
        "validation_authority_id": "validation-1",
        "validation_authority_fingerprint": "c" * 64,
        "provenance": "canonical valid tournament application",
    }
    payload.update(overrides)
    return TournamentApplicationSubmissionAuthority(**payload)


@pytest.mark.pr_critical
def test_definitive_wc_persists_with_first_tour_entry_atomically(database):
    assignment = _assignment()
    with database.begin() as session:
        result = record_definitive_wild_card_assignment(session, assignment)
        assert result.assignment == assignment
        assert result.first_tour_entry_trigger == assignment.to_tour_entry_trigger()
        assert DefinitiveWildCardAssignmentStore(session).get(
            run_id="run",
            branch_id="branch",
            assignment_id=assignment.source_evidence_id,
        ) == assignment
        assert PlayerTourEntryTriggerStore(session).get(
            run_id="run",
            branch_id="branch",
            player_id="prospect-1",
        ) == assignment.to_tour_entry_trigger()


@pytest.mark.pr_critical
def test_exact_retry_and_later_wc_keep_original_first_trigger(database):
    first = _assignment()
    later = _assignment(
        event_id="event-wc-2",
        assignment_week=RankingWeek(season_index=0, week=12),
        decision_slot_ordinal=4,
        source_wild_card_command_id="wc-command-2",
        source_wild_card_authority_fingerprint="d" * 64,
    )
    with database.begin() as session:
        first_result = record_definitive_wild_card_assignment(session, first)
        retry_result = record_definitive_wild_card_assignment(session, first)
        later_result = record_definitive_wild_card_assignment(session, later)

        assert retry_result == first_result
        assert later_result.first_tour_entry_trigger == first_result.first_tour_entry_trigger
        assert DefinitiveWildCardAssignmentStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == (first, later)


@pytest.mark.pr_critical
def test_later_wc_after_application_keeps_application_first_entry(database):
    submission = _submission()
    assignment = _assignment(
        assignment_week=RankingWeek(season_index=0, week=10),
        decision_slot_ordinal=5,
    )
    with database.begin() as session:
        application_result = record_valid_application_submission(session, submission)
        wc_result = record_definitive_wild_card_assignment(session, assignment)

        assert wc_result.first_tour_entry_trigger == (
            application_result.first_tour_entry_trigger
        )
        assert DefinitiveWildCardAssignmentStore(session).get(
            run_id="run",
            branch_id="branch",
            assignment_id=assignment.source_evidence_id,
        ) == assignment


@pytest.mark.pr_critical
def test_later_application_after_wc_keeps_wc_first_entry(database):
    assignment = _assignment(
        assignment_week=RankingWeek(season_index=0, week=8),
        decision_slot_ordinal=2,
    )
    submission = _submission(
        application_id="application-later",
        submission_week=RankingWeek(season_index=0, week=10),
        decision_slot_ordinal=5,
    )
    with database.begin() as session:
        wc_result = record_definitive_wild_card_assignment(session, assignment)
        application_result = record_valid_application_submission(session, submission)

        assert application_result.first_tour_entry_trigger == (
            wc_result.first_tour_entry_trigger
        )


@pytest.mark.pr_critical
def test_earlier_or_simultaneous_wc_cannot_rewrite_first_entry(database):
    first = _assignment(
        source_wild_card_command_id="wc-command-later",
        assignment_week=RankingWeek(season_index=0, week=10),
        decision_slot_ordinal=5,
    )
    earlier = _assignment(
        source_wild_card_command_id="wc-command-earlier",
        assignment_week=RankingWeek(season_index=0, week=9),
        decision_slot_ordinal=1,
    )
    simultaneous = _assignment(
        source_wild_card_command_id="wc-command-same-slot",
        assignment_week=RankingWeek(season_index=0, week=10),
        decision_slot_ordinal=5,
    )
    with database.begin() as session:
        record_definitive_wild_card_assignment(session, first)
        with pytest.raises(
            DefinitiveWildCardAssignmentConflict,
            match="predates persisted first Tour-entry trigger",
        ):
            record_definitive_wild_card_assignment(session, earlier)
        with pytest.raises(
            DefinitiveWildCardAssignmentConflict,
            match="simultaneous first-entry authorities",
        ):
            record_definitive_wild_card_assignment(session, simultaneous)

        assert DefinitiveWildCardAssignmentStore(session).get(
            run_id="run",
            branch_id="branch",
            assignment_id=earlier.source_evidence_id,
        ) is None
        assert DefinitiveWildCardAssignmentStore(session).get(
            run_id="run",
            branch_id="branch",
            assignment_id=simultaneous.source_evidence_id,
        ) is None


@pytest.mark.pr_critical
def test_wc_assignment_identity_conflict_does_not_change_first_trigger(database):
    first = _assignment()
    conflicting = _assignment(event_id="different-event")
    with database.begin() as session:
        record_definitive_wild_card_assignment(session, first)
        with pytest.raises(
            DefinitiveWildCardAssignmentConflict,
            match="WC assignment ID already has different",
        ):
            record_definitive_wild_card_assignment(session, conflicting)

        assert PlayerTourEntryTriggerStore(session).get(
            run_id="run",
            branch_id="branch",
            player_id="prospect-1",
        ) == first.to_tour_entry_trigger()


@pytest.mark.pr_critical
def test_saved_component_round_trip_restores_definitive_wc_history(database):
    empty_payload = {"content": {}}
    with database.begin() as session:
        capture_saved_definitive_wild_card_assignments(
            session,
            empty_payload,
            run_id="run",
            branch_id="branch",
        )
    assert empty_payload["content"][DEFINITIVE_WILD_CARD_ASSIGNMENT_COMPONENT_KEY][
        "assignments"
    ] == []

    assignment = _assignment()
    current_payload = {"content": {}}
    with database.begin() as session:
        DefinitiveWildCardAssignmentStore(session).append(assignment)
        capture_saved_definitive_wild_card_assignments(
            session,
            current_payload,
            run_id="run",
            branch_id="branch",
        )

    assert load_saved_definitive_wild_card_assignments(
        current_payload,
        run_id="run",
        branch_id="branch",
    ) == (assignment,)

    with database.begin() as session:
        restore_saved_definitive_wild_card_assignments(
            session,
            current_payload=current_payload,
            target_payload=empty_payload,
            run_id="run",
            branch_id="branch",
        )
        assert DefinitiveWildCardAssignmentStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == ()

    with database.begin() as session:
        restore_saved_definitive_wild_card_assignments(
            session,
            current_payload=empty_payload,
            target_payload=current_payload,
            run_id="run",
            branch_id="branch",
        )
        assert DefinitiveWildCardAssignmentStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == (assignment,)

import pytest

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.application_validation_authority import (
    ResolvedApplicationValidationSlot,
    TournamentApplicationValidationAuthority,
)
from beta_engine.domain.tournaments.run_entry_decision_slot import (
    EntryDecisionEvidence,
    RunEntryDecisionSlotAuthority,
)
from beta_engine.infrastructure.db.application_validation_slots import (
    APPLICATION_VALIDATION_SLOT_COMPONENT_KEY,
    ApplicationValidationSlotConflict,
    ApplicationValidationSlotStore,
    capture_saved_application_validation_slots,
    load_saved_application_validation_slots,
    remap_saved_application_validation_slots_component,
    record_resolved_application_validation_slot,
    restore_saved_application_validation_slots,
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
from beta_engine.infrastructure.db.run_entry_decision_slots import (
    RunEntryDecisionSlotStore,
)
from beta_engine.infrastructure.db.tournament_application_submissions import (
    TournamentApplicationSubmissionStore,
)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'application-validation.db'}")
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


def _slot():
    return RunEntryDecisionSlotAuthority(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=9),
        decision_slot_ordinal=1,
        source_entry_batch_fingerprint="a" * 64,
        source_application_decisions_fingerprint="b" * 64,
        source_active_players_fingerprint="c" * 64,
        decisions=(
            EntryDecisionEvidence(
                event_id="event-1",
                player_id="prospect-1",
                target="MAIN",
                source_decision_fingerprint="d" * 64,
            ),
            EntryDecisionEvidence(
                event_id="event-2",
                player_id="prospect-2",
                target="QUALIFICATION",
                source_decision_fingerprint="e" * 64,
            ),
        ),
    )


def _resolved(*, all_invalid=False, policy_fingerprint="f" * 64):
    slot = _slot()
    first = TournamentApplicationValidationAuthority(
        validation_id="validation-1",
        application_id="application-1",
        run_id=slot.run_id,
        branch_id=slot.branch_id,
        week=slot.week,
        decision_slot_ordinal=slot.decision_slot_ordinal,
        source_slot_fingerprint=slot.fingerprint,
        event_id="event-1",
        player_id="prospect-1",
        entry_window="main",
        source_decision_fingerprint="d" * 64,
        outcome="invalid" if all_invalid else "valid",
        nr_tie_break_token=None if all_invalid else "nr-token-1",
        validation_policy_id="policy-v1",
        validation_policy_fingerprint=policy_fingerprint,
        reasons=("ineligible_under_resolved_policy",) if all_invalid else (),
        provenance="resolved application validation",
    )
    second = TournamentApplicationValidationAuthority(
        validation_id="validation-2",
        application_id="application-2",
        run_id=slot.run_id,
        branch_id=slot.branch_id,
        week=slot.week,
        decision_slot_ordinal=slot.decision_slot_ordinal,
        source_slot_fingerprint=slot.fingerprint,
        event_id="event-2",
        player_id="prospect-2",
        entry_window="qualification",
        source_decision_fingerprint="e" * 64,
        outcome="invalid",
        nr_tie_break_token=None,
        validation_policy_id="policy-v1",
        validation_policy_fingerprint=policy_fingerprint,
        reasons=("ineligible_under_resolved_policy",),
        provenance="resolved application validation",
    )
    return ResolvedApplicationValidationSlot(
        slot=slot,
        validations=(first, second),
    )


@pytest.mark.pr_critical
def test_validation_commit_requires_exact_persisted_source_entry_slot(database):
    resolved = _resolved()
    with database.begin() as session:
        with pytest.raises(
            ApplicationValidationSlotConflict,
            match="requires a persisted Run entry-decision slot",
        ):
            record_resolved_application_validation_slot(session, resolved)

        assert ApplicationValidationSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == ()
        assert TournamentApplicationSubmissionStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == ()


@pytest.mark.pr_critical
def test_resolved_validation_persists_with_submission_and_first_tour_entry(database):
    resolved = _resolved()
    with database.begin() as session:
        RunEntryDecisionSlotStore(session).append(resolved.slot)
        result = record_resolved_application_validation_slot(session, resolved)

        assert result.validation_slot == resolved
        assert result.submission_commit is not None
        assert ApplicationValidationSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == (resolved,)
        submissions = TournamentApplicationSubmissionStore(session).list(
            run_id="run",
            branch_id="branch",
        )
        assert len(submissions) == 1
        assert submissions[0].application_id == "application-1"
        trigger = PlayerTourEntryTriggerStore(session).get(
            run_id="run",
            branch_id="branch",
            player_id="prospect-1",
        )
        assert trigger is not None
        assert trigger.trigger_week == RankingWeek(season_index=0, week=9)
        assert trigger.decision_slot_ordinal == 1
        assert PlayerTourEntryTriggerStore(session).get(
            run_id="run",
            branch_id="branch",
            player_id="prospect-2",
        ) is None


@pytest.mark.pr_critical
def test_exact_retry_is_idempotent(database):
    resolved = _resolved()
    with database.begin() as session:
        RunEntryDecisionSlotStore(session).append(resolved.slot)
        first = record_resolved_application_validation_slot(session, resolved)
        retry = record_resolved_application_validation_slot(session, resolved)

        assert retry == first
        assert ApplicationValidationSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == (resolved,)
        assert len(
            TournamentApplicationSubmissionStore(session).list(
                run_id="run",
                branch_id="branch",
            )
        ) == 1


@pytest.mark.pr_critical
def test_all_invalid_slot_persists_without_submission_or_tour_entry(database):
    resolved = _resolved(all_invalid=True)
    with database.begin() as session:
        RunEntryDecisionSlotStore(session).append(resolved.slot)
        result = record_resolved_application_validation_slot(session, resolved)

        assert result.submission_commit is None
        assert ApplicationValidationSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == (resolved,)
        assert TournamentApplicationSubmissionStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == ()
        assert PlayerTourEntryTriggerStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == ()


@pytest.mark.pr_critical
def test_conflicting_same_slot_fails_before_rewriting_downstream_history(database):
    first = _resolved()
    conflicting = _resolved(policy_fingerprint="0" * 64)
    with database.begin() as session:
        RunEntryDecisionSlotStore(session).append(first.slot)
        record_resolved_application_validation_slot(session, first)
        with pytest.raises(
            ApplicationValidationSlotConflict,
            match="already has different resolved authority",
        ):
            record_resolved_application_validation_slot(session, conflicting)

        assert ApplicationValidationSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == (first,)
        submissions = TournamentApplicationSubmissionStore(session).list(
            run_id="run",
            branch_id="branch",
        )
        assert len(submissions) == 1
        assert submissions[0].validation_authority_fingerprint == (
            first.validations[0].fingerprint
        )


@pytest.mark.pr_critical
def test_saved_validation_slots_remap_branch_and_source_slot_identity(database):
    resolved = _resolved()
    payload = {"content": {}}
    with database.begin() as session:
        ApplicationValidationSlotStore(session).append(resolved)
        capture_saved_application_validation_slots(
            session,
            payload,
            run_id="run",
            branch_id="branch",
        )

    target_slot = resolved.slot.model_copy(update={"branch_id": "target"})
    component, resolved_map, validation_map = (
        remap_saved_application_validation_slots_component(
            payload,
            run_id="run",
            source_branch_id="branch",
            target_branch_id="target",
            entry_slot_fingerprint_map={
                resolved.slot.fingerprint: target_slot.fingerprint
            },
        )
    )
    assert component is not None
    target_payload = {
        "content": {APPLICATION_VALIDATION_SLOT_COMPONENT_KEY: component}
    }
    target = load_saved_application_validation_slots(
        target_payload,
        run_id="run",
        branch_id="target",
    )
    assert target is not None
    assert len(target) == 1
    rebuilt = target[0]
    assert rebuilt.slot == target_slot
    assert all(item.branch_id == "target" for item in rebuilt.validations)
    assert all(
        item.source_slot_fingerprint == target_slot.fingerprint
        for item in rebuilt.validations
    )
    assert resolved_map == {resolved.fingerprint: rebuilt.fingerprint}
    assert validation_map == {
        source.fingerprint: target_validation.fingerprint
        for source, target_validation in zip(
            resolved.validations,
            rebuilt.validations,
            strict=True,
        )
    }


@pytest.mark.pr_critical
def test_saved_component_round_trip_restores_validation_slots(database):
    empty_payload = {"content": {}}
    with database.begin() as session:
        capture_saved_application_validation_slots(
            session,
            empty_payload,
            run_id="run",
            branch_id="branch",
        )
    assert empty_payload["content"][APPLICATION_VALIDATION_SLOT_COMPONENT_KEY][
        "slots"
    ] == []

    resolved = _resolved()
    current_payload = {"content": {}}
    with database.begin() as session:
        ApplicationValidationSlotStore(session).append(resolved)
        capture_saved_application_validation_slots(
            session,
            current_payload,
            run_id="run",
            branch_id="branch",
        )

    assert load_saved_application_validation_slots(
        current_payload,
        run_id="run",
        branch_id="branch",
    ) == (resolved,)

    with database.begin() as session:
        restore_saved_application_validation_slots(
            session,
            current_payload=current_payload,
            target_payload=empty_payload,
            run_id="run",
            branch_id="branch",
        )
        assert ApplicationValidationSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == ()

    with database.begin() as session:
        restore_saved_application_validation_slots(
            session,
            current_payload=empty_payload,
            target_payload=current_payload,
            run_id="run",
            branch_id="branch",
        )
        assert ApplicationValidationSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == (resolved,)

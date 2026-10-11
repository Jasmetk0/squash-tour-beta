import pytest

from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.domain.rankings.official import RankingWeek
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
    PLAYER_TOUR_ENTRY_COMPONENT_KEY,
    PlayerTourEntryTriggerConflict,
    PlayerTourEntryTriggerStore,
    capture_saved_tour_entry_triggers,
    load_saved_tour_entry_triggers,
    remap_saved_tour_entry_triggers_component,
    restore_saved_tour_entry_triggers,
)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'tour-entry-trigger.db'}")
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


def _trigger(**overrides):
    payload = {
        "run_id": "run",
        "branch_id": "branch",
        "player_id": "prospect-1",
        "event_id": "event-1",
        "trigger_kind": "valid_tournament_application",
        "trigger_week": RankingWeek(season_index=0, week=9),
        "decision_slot_ordinal": 3,
        "source_evidence_id": "application-1",
        "source_evidence_fingerprint": "a" * 64,
        "provenance": "canonical application submission",
    }
    payload.update(overrides)
    return PlayerTourEntryTrigger(**payload)


@pytest.mark.pr_critical
def test_tour_entry_store_is_one_time_and_exact_retry_is_idempotent(database):
    trigger = _trigger()
    with database.begin() as session:
        store = PlayerTourEntryTriggerStore(session)
        assert store.append(trigger) == trigger
        assert store.append(trigger) == trigger
        assert store.get(
            run_id="run",
            branch_id="branch",
            player_id="prospect-1",
        ) == trigger
        assert store.list(run_id="run", branch_id="branch") == (trigger,)

        with pytest.raises(
            PlayerTourEntryTriggerConflict,
            match="different first Tour-entry trigger",
        ):
            store.append(
                _trigger(
                    trigger_kind="definitive_wild_card_assignment",
                    source_evidence_id="wc-1",
                    source_evidence_fingerprint="b" * 64,
                )
            )


@pytest.mark.pr_critical
def test_saved_application_trigger_remaps_to_target_submission_evidence(database):
    trigger = _trigger()
    payload = {"content": {}}
    with database.begin() as session:
        PlayerTourEntryTriggerStore(session).append(trigger)
        capture_saved_tour_entry_triggers(
            session,
            payload,
            run_id="run",
            branch_id="branch",
        )

    target_submission_fingerprint = "b" * 64
    component, fingerprint_map = remap_saved_tour_entry_triggers_component(
        payload,
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        application_submission_identity_map={
            trigger.source_evidence_fingerprint: (
                trigger.source_evidence_id,
                target_submission_fingerprint,
            ),
        },
    )
    assert component is not None
    target_payload = {"content": {PLAYER_TOUR_ENTRY_COMPONENT_KEY: component}}
    target = load_saved_tour_entry_triggers(
        target_payload,
        run_id="run",
        branch_id="target",
    )
    assert target is not None and len(target) == 1
    mapped = target[0]
    assert mapped.branch_id == "target"
    assert mapped.player_id == trigger.player_id
    assert mapped.source_evidence_id == trigger.source_evidence_id
    assert mapped.source_evidence_fingerprint == target_submission_fingerprint
    assert fingerprint_map == {trigger.fingerprint: mapped.fingerprint}

    with pytest.raises(
        ValueError,
        match="application id differs from mapped submission",
    ):
        remap_saved_tour_entry_triggers_component(
            payload,
            run_id="run",
            source_branch_id="branch",
            target_branch_id="target",
            application_submission_identity_map={
                trigger.source_evidence_fingerprint: (
                    "different-application",
                    target_submission_fingerprint,
                ),
            },
        )


@pytest.mark.pr_critical
def test_saved_wild_card_trigger_remaps_to_target_assignment_evidence(database):
    trigger = _trigger(
        trigger_kind="definitive_wild_card_assignment",
        source_evidence_id="wc-assignment",
    )
    payload = {"content": {}}
    with database.begin() as session:
        PlayerTourEntryTriggerStore(session).append(trigger)
        capture_saved_tour_entry_triggers(
            session,
            payload,
            run_id="run",
            branch_id="branch",
        )

    target_assignment_fingerprint = "b" * 64
    component, fingerprint_map = remap_saved_tour_entry_triggers_component(
        payload,
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        application_submission_identity_map={},
        definitive_wild_card_assignment_identity_map={
            trigger.source_evidence_fingerprint: (
                trigger.source_evidence_id,
                target_assignment_fingerprint,
            )
        },
    )
    assert component is not None
    target_payload = {"content": {PLAYER_TOUR_ENTRY_COMPONENT_KEY: component}}
    target = load_saved_tour_entry_triggers(
        target_payload,
        run_id="run",
        branch_id="target",
    )
    assert target is not None and len(target) == 1
    mapped = target[0]
    assert mapped.branch_id == "target"
    assert mapped.source_evidence_id == trigger.source_evidence_id
    assert mapped.source_evidence_fingerprint == target_assignment_fingerprint
    assert fingerprint_map == {trigger.fingerprint: mapped.fingerprint}

    with pytest.raises(
        ValueError,
        match="definitive Wild Card assignment without a target mapping",
    ):
        remap_saved_tour_entry_triggers_component(
            payload,
            run_id="run",
            source_branch_id="branch",
            target_branch_id="target",
            application_submission_identity_map={},
            definitive_wild_card_assignment_identity_map={},
        )

    with pytest.raises(
        ValueError,
        match="evidence id differs from mapped definitive Wild Card assignment",
    ):
        remap_saved_tour_entry_triggers_component(
            payload,
            run_id="run",
            source_branch_id="branch",
            target_branch_id="target",
            application_submission_identity_map={},
            definitive_wild_card_assignment_identity_map={
                trigger.source_evidence_fingerprint: (
                    "different-wc-assignment",
                    target_assignment_fingerprint,
                )
            },
        )

@pytest.mark.pr_critical
def test_saved_component_round_trip_restores_exact_trigger_history(database):
    empty_payload = {"content": {}}
    with database.begin() as session:
        capture_saved_tour_entry_triggers(
            session,
            empty_payload,
            run_id="run",
            branch_id="branch",
        )

    assert empty_payload["content"][PLAYER_TOUR_ENTRY_COMPONENT_KEY]["triggers"] == []

    trigger = _trigger()
    current_payload = {"content": {}}
    with database.begin() as session:
        PlayerTourEntryTriggerStore(session).append(trigger)
        capture_saved_tour_entry_triggers(
            session,
            current_payload,
            run_id="run",
            branch_id="branch",
        )

    assert load_saved_tour_entry_triggers(
        current_payload,
        run_id="run",
        branch_id="branch",
    ) == (trigger,)

    with database.begin() as session:
        restore_saved_tour_entry_triggers(
            session,
            current_payload=current_payload,
            target_payload=empty_payload,
            run_id="run",
            branch_id="branch",
        )
        assert PlayerTourEntryTriggerStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == ()

    with database.begin() as session:
        restore_saved_tour_entry_triggers(
            session,
            current_payload=empty_payload,
            target_payload=current_payload,
            run_id="run",
            branch_id="branch",
        )
        assert PlayerTourEntryTriggerStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == (trigger,)


@pytest.mark.pr_critical
def test_saved_component_rejects_tampered_trigger_history(database):
    payload = {"content": {}}
    with database.begin() as session:
        PlayerTourEntryTriggerStore(session).append(_trigger())
        capture_saved_tour_entry_triggers(
            session,
            payload,
            run_id="run",
            branch_id="branch",
        )

    payload["content"][PLAYER_TOUR_ENTRY_COMPONENT_KEY]["triggers"][0][
        "decision_slot_ordinal"
    ] = 99

    with pytest.raises(ValueError, match="fingerprint mismatch"):
        load_saved_tour_entry_triggers(
            payload,
            run_id="run",
            branch_id="branch",
        )

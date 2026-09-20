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

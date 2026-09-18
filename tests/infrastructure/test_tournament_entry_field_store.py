"""Authoritative Tournament Entry Field persistence and Saved Revision recovery."""

from __future__ import annotations

import pytest

from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryApplication,
    TournamentEntryFieldCapacity,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    Base,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    TournamentEntryFieldVersionModel,
    WeekSimulationScheduleModel,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    capture_saved_simulation_slots,
    restore_saved_simulation_slots,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldConflict,
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)


pytestmark = pytest.mark.smoke


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'entry-field.db'}")
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


def ranking_snapshot():
    completed = RankingWeek(season_index=0, week=1)
    published = RankingWeek(season_index=0, week=2)
    target = RankingWeek(season_index=0, week=3)
    points = {
        "A": 100,
        "B": 90,
        "C": 80,
        "D": 70,
        "E": 60,
        "F": 50,
        "G": 40,
    }
    players = tuple(
        OfficialRankingPlayer(
            player_id=player_id,
            tie_break_token=f"rank-{player_id}",
            tour_entry_week=RankingWeek(season_index=0, week=1),
        )
        for player_id in sorted(points)
    )
    results = tuple(
        OfficialRankingResult(
            edition_id=f"prior-{player_id}",
            player_id=player_id,
            source_fingerprint=f"source-{player_id}",
            completed_week=completed,
            first_publication_week=published,
            main_points=value,
        )
        for player_id, value in sorted(points.items())
    )
    return calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=target,
        policy=OfficialRankingPolicy(policy_id="policy"),
        players=players,
        results=results,
    )


def install_ranking_authority(session):
    snapshot = ranking_snapshot()
    session.add(
        PublishedOfficialRankingModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=snapshot.week.ordinal,
            snapshot_fingerprint=snapshot.fingerprint,
            payload_json=snapshot.model_dump_json(),
        )
    )
    session.flush()
    return TournamentRankingSnapshotAuthorityStore(session).adopt(
        run_id="run",
        branch_id="branch",
        event_id="event",
        ranking_week=snapshot.week,
        command_id="adopt-ranking",
    )


def app(player_id: str, window: str):
    return TournamentEntryApplication(
        application_id=f"app-{player_id}",
        run_id="run",
        branch_id="branch",
        event_id="event",
        player_id=player_id,
        entry_window=window,
        decision_slot_ordinal=10,
        nr_tie_break_token=f"entry-{player_id}",
    )


def applications():
    return (
        app("A", "main"),
        app("C", "main"),
        app("D", "main"),
        app("B", "qualification"),
        app("E", "qualification"),
        app("F", "qualification"),
        app("G", "qualification"),
    )


def capacity():
    return TournamentEntryFieldCapacity(
        main_draw_size=4,
        qualification_draw_size=2,
        qualifier_spots=1,
    )


def capture(session):
    payload = {"content": {}}
    capture_saved_simulation_slots(
        session,
        payload,
        run_id="run",
        branch_id="branch",
    )
    return payload


def test_legacy_simulation_component_without_entry_fields_keeps_wire_identity(
    database,
):
    with database.begin() as session:
        session.add(
            WeekSimulationScheduleModel(
                run_id="run",
                branch_id="branch",
                week_ordinal=1,
                request_id="legacy-schedule",
                request_fingerprint="1" * 64,
                schedule_fingerprint="2" * 64,
                payload_json="{}",
            )
        )
        session.flush()
        saved = capture(session)
        component = saved["content"]["simulation_slot_match_state"]
        assert "entry_fields" not in component
        assert "draw_inputs" not in component
        assert "draw_authorities" not in component

        restore_saved_simulation_slots(
            session,
            current_payload=saved,
            target_payload=saved,
            run_id="run",
            branch_id="branch",
        )
        recaptured = capture(session)
        assert (
            recaptured["content"]["simulation_slot_match_state"]["fingerprint"]
            == component["fingerprint"]
        )
        assert "entry_fields" not in recaptured["content"]["simulation_slot_match_state"]
        assert "draw_inputs" not in recaptured["content"]["simulation_slot_match_state"]
        assert "draw_authorities" not in recaptured["content"]["simulation_slot_match_state"]


def test_store_replays_initial_repair_and_exact_retries(database):
    with database.begin() as session:
        install_ranking_authority(session)
        store = TournamentEntryFieldStore(session)
        initial = store.stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=list(reversed(applications())),
            capacity=capacity(),
            command_id="initial-field",
        )
        assert initial.direct_main_player_ids == ("A", "C", "D")
        assert initial.qualification_player_ids == ("B", "E")
        assert initial.below_qualification_cut_player_ids == ("F", "G")

        assert store.stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=applications(),
            capacity=capacity(),
            command_id="initial-field",
        ) == initial

        repaired = store.stage_pre_draw_repair(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=applications(),
            withdrawn_player_ids=("D",),
            command_id="withdraw-d",
        )
        assert repaired.direct_main_player_ids == ("A", "B", "C")
        assert repaired.qualification_player_ids == ("E", "F")
        assert repaired.below_qualification_cut_player_ids == ("G",)

        assert store.stage_pre_draw_repair(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=list(reversed(applications())),
            withdrawn_player_ids=("D",),
            command_id="withdraw-d",
        ) == repaired
        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (initial, repaired)


def test_followup_repair_canonicalizes_already_withdrawn_players(database):
    with database.begin() as session:
        install_ranking_authority(session)
        store = TournamentEntryFieldStore(session)
        initial = store.stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=applications(),
            capacity=capacity(),
            command_id="initial-field",
        )
        first = store.stage_pre_draw_repair(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=applications(),
            withdrawn_player_ids=("D",),
            command_id="withdraw-d",
        )
        second = store.stage_pre_draw_repair(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=applications(),
            withdrawn_player_ids=("D", "E"),
            command_id="withdraw-e",
        )
        assert second.withdrawn_player_ids == ("D", "E")
        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (initial, first, second)

        assert store.stage_pre_draw_repair(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=list(reversed(applications())),
            withdrawn_player_ids=("D", "E"),
            command_id="withdraw-e",
        ) == second


def test_command_reuse_and_corrupt_frozen_inputs_fail_closed(database):
    with database.begin() as session:
        install_ranking_authority(session)
        store = TournamentEntryFieldStore(session)
        store.stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=applications(),
            capacity=capacity(),
            command_id="initial-field",
        )
        with pytest.raises(TournamentEntryFieldConflict, match="different request"):
            store.stage_initial(
                run_id="run",
                branch_id="branch",
                event_id="event",
                applications=applications(),
                capacity=TournamentEntryFieldCapacity(
                    main_draw_size=8,
                    qualification_draw_size=2,
                    qualifier_spots=1,
                ),
                command_id="initial-field",
            )

    with database.begin() as session:
        row = session.get(
            TournamentEntryFieldVersionModel,
            ("run", "branch", "event", 1),
        )
        row.applications_json = row.applications_json.replace(
            '"player_id":"A"',
            '"player_id":"CORRUPT"',
            1,
        )

    with database() as session:
        with pytest.raises(ValueError):
            TournamentEntryFieldStore(session).history(
                run_id="run",
                branch_id="branch",
                event_id="event",
            )


def test_saved_simulation_component_restores_field_history_backward_and_forward(
    database,
):
    with database.begin() as session:
        install_ranking_authority(session)
        store = TournamentEntryFieldStore(session)
        initial = store.stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=applications(),
            capacity=capacity(),
            command_id="initial-field",
        )
        saved_initial = capture(session)

        repaired = store.stage_pre_draw_repair(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=applications(),
            withdrawn_player_ids=("D",),
            command_id="withdraw-d",
        )
        saved_repaired = capture(session)
        assert (
            saved_initial["content"]["simulation_slot_match_state"]["fingerprint"]
            != saved_repaired["content"]["simulation_slot_match_state"]["fingerprint"]
        )

        restore_saved_simulation_slots(
            session,
            current_payload=saved_repaired,
            target_payload=saved_initial,
            run_id="run",
            branch_id="branch",
        )
        store = TournamentEntryFieldStore(session)
        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (initial,)
        current_initial = capture(session)
        assert (
            current_initial["content"]["simulation_slot_match_state"]["fingerprint"]
            == saved_initial["content"]["simulation_slot_match_state"]["fingerprint"]
        )

        restore_saved_simulation_slots(
            session,
            current_payload=current_initial,
            target_payload=saved_repaired,
            run_id="run",
            branch_id="branch",
        )
        assert TournamentEntryFieldStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (initial, repaired)


def test_saved_component_corruption_is_rejected_before_live_mutation(database):
    with database.begin() as session:
        install_ranking_authority(session)
        TournamentEntryFieldStore(session).stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=applications(),
            capacity=capacity(),
            command_id="initial-field",
        )
        saved = capture(session)
        corrupt = {
            "content": {
                key: (
                    dict(value)
                    if isinstance(value, dict)
                    else value
                )
                for key, value in saved["content"].items()
            }
        }
        component = dict(corrupt["content"]["simulation_slot_match_state"])
        entry_fields = [dict(row) for row in component["entry_fields"]]
        entry_fields[0]["field_fingerprint"] = "0" * 64
        component["entry_fields"] = entry_fields
        corrupt["content"]["simulation_slot_match_state"] = component

        before = TournamentEntryFieldStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        )
        with pytest.raises(ValueError):
            restore_saved_simulation_slots(
                session,
                current_payload=saved,
                target_payload=corrupt,
                run_id="run",
                branch_id="branch",
            )
        assert TournamentEntryFieldStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == before

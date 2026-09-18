"""Canonical Run-owned Tournament Draw authority regression coverage."""

from __future__ import annotations

import pytest

from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawAuthorityBuilder,
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
    TournamentDrawAuthorityModel,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    capture_saved_simulation_slots,
    restore_saved_simulation_slots,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityConflict,
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import TournamentEntryFieldStore
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)


pytestmark = pytest.mark.smoke


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'draw-authority.db'}")
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


def ranking_snapshot(player_ids=("A", "B", "C", "D", "E", "F", "G")):
    completed = RankingWeek(season_index=0, week=1)
    published = RankingWeek(season_index=0, week=2)
    target = RankingWeek(season_index=0, week=3)
    points = {
        player_id: (len(player_ids) - index) * 10
        for index, player_id in enumerate(player_ids)
    }
    players = tuple(
        OfficialRankingPlayer(
            player_id=player_id,
            tie_break_token=f"rank-{player_id}",
            tour_entry_week=RankingWeek(season_index=0, week=1),
        )
        for player_id in player_ids
    )
    results = tuple(
        OfficialRankingResult(
            edition_id=f"prior-{player_id}",
            player_id=player_id,
            source_fingerprint=f"source-{player_id}",
            completed_week=completed,
            first_publication_week=published,
            main_points=points[player_id],
        )
        for player_id in player_ids
    )
    return calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=target,
        policy=OfficialRankingPolicy(policy_id="policy"),
        players=players,
        results=results,
    )


def install_ranking_authority(session, player_ids=("A", "B", "C", "D", "E", "F", "G")):
    snapshot = ranking_snapshot(player_ids)
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


def standard_applications():
    return (
        app("A", "main"),
        app("C", "main"),
        app("D", "main"),
        app("B", "qualification"),
        app("E", "qualification"),
        app("F", "qualification"),
        app("G", "qualification"),
    )


def install_draw_input(
    session,
    *,
    applications=None,
    capacity=None,
    draw_seed=123,
    main_seed_count=1,
    qualification_seed_count=1,
):
    install_ranking_authority(session)
    TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id="event",
        applications=applications or standard_applications(),
        capacity=capacity
        or TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=2,
            qualifier_spots=1,
        ),
        command_id="initial-field",
    )
    return TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="commit-draw-input",
        draw_seed=draw_seed,
        main_seed_count=main_seed_count,
        qualification_seed_count=qualification_seed_count,
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


def test_builder_generates_complete_main_and_qualification_brackets(database):
    with database.begin() as session:
        draw_input = install_draw_input(session)
        authority = TournamentDrawAuthorityBuilder.build(
            draw_input=draw_input,
            command_id="generate-draw",
        )

        assert authority.draw_input_fingerprint == draw_input.fingerprint
        assert authority.schema_version == "tournament_draw_authority.v1"
        assert "qualification_sections" not in authority.model_dump(mode="json")
        assert authority.qualification is not None
        assert authority.qualification.bracket_size == 2
        assert len(authority.qualification.nodes) == 1
        assert {slot.player_id for slot in authority.qualification.slots} == {"B", "E"}
        q_seed = next(
            slot for slot in authority.qualification.slots if slot.seed_number == 1
        )
        assert q_seed.player_id == "B"

        assert authority.main.bracket_size == 4
        assert len(authority.main.nodes) == 3
        assert authority.algorithm_version == "idealized_seed_tiers.v2"
        assert authority.main.seed_positions == ((1, 1),)
        assert authority.main.slots[0].player_id == "A"
        assert authority.main.slots[0].seed_number == 1
        assert tuple(
            slot.idealized_slot_number for slot in authority.main.slots
        ) == (1, 4, 3, 2)
        assert {
            slot.player_id
            for slot in authority.main.slots
            if slot.entrant_kind == "player"
        } == {"A", "C", "D"}
        assert len(authority.main.qualifier_placeholder_slots) == 1
        assert authority.main.qualifier_placeholder_slots[0][0] == "Q1"
        assert authority.main.bye_slot_indexes == ()


def test_master_idealized_slots_and_seed_tiers_for_eight_player_draw(database):
    with database.begin() as session:
        players = tuple(chr(ord("A") + index) for index in range(8))
        applications = tuple(app(player_id, "main") for player_id in players)
        install_ranking_authority(session, players)
        TournamentEntryFieldStore(session).stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=applications,
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=8,
                qualification_draw_size=0,
                qualifier_spots=0,
            ),
            command_id="initial-field",
        )
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="commit-draw-input",
            draw_seed=777,
            main_seed_count=1,
            qualification_seed_count=0,
        )
        authority = TournamentDrawAuthorityBuilder.build(
            draw_input=draw_input,
            command_id="generate-draw",
        )

        assert tuple(
            slot.idealized_slot_number for slot in authority.main.slots
        ) == (1, 8, 5, 4, 3, 6, 7, 2)
        seeded = {
            slot.seed_number: (slot.player_id, slot.idealized_slot_number)
            for slot in authority.main.slots
            if slot.seed_number is not None
        }
        assert seeded == {
            1: ("A", 1),
            2: ("B", 2),
        }


def test_master_seed_tier_three_four_is_replayable_but_not_fixed_to_player_order():
    draw_input = TournamentDrawInputAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event-tier",
        committed_by_command_id="input",
        draw_seed=2026,
        main_seed_count=4,
        qualification_seed_count=0,
        field_sequence=1,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=16,
            qualification_draw_size=0,
            qualifier_spots=0,
        ),
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=tuple(f"P{index:02d}" for index in range(1, 17)),
        qualification_player_ids=(),
        qualifier_placeholder_ids=(),
        withdrawn_player_ids=(),
        main_seed_player_ids=("P01", "P02", "P03", "P04"),
        qualification_seed_player_ids=(),
    )
    first = TournamentDrawAuthorityBuilder.build(
        draw_input=draw_input,
        command_id="draw",
    )
    second = TournamentDrawAuthorityBuilder.build(
        draw_input=draw_input,
        command_id="draw",
    )
    assert first == second

    seeded = {
        slot.seed_number: slot.idealized_slot_number
        for slot in first.main.slots
        if slot.seed_number is not None
    }
    assert seeded[1] == 1
    assert seeded[2] == 2
    assert {seeded[3], seeded[4]} == {3, 4}


def test_master_initial_byes_use_highest_idealized_slots():
    direct = tuple(f"P{index:02d}" for index in range(1, 29))
    draw_input = TournamentDrawInputAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event-byes",
        committed_by_command_id="input",
        draw_seed=3030,
        main_seed_count=8,
        qualification_seed_count=0,
        field_sequence=1,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=32,
            qualification_draw_size=0,
            qualifier_spots=0,
            bye_slots=4,
        ),
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=direct,
        qualification_player_ids=(),
        qualifier_placeholder_ids=(),
        withdrawn_player_ids=(),
        main_seed_player_ids=direct[:8],
        qualification_seed_player_ids=(),
    )
    authority = TournamentDrawAuthorityBuilder.build(
        draw_input=draw_input,
        command_id="draw",
    )

    bye_slots = [
        slot for slot in authority.main.slots if slot.entrant_kind == "bye"
    ]
    assert {
        slot.idealized_slot_number for slot in bye_slots
    } == {29, 30, 31, 32}
    for slot in bye_slots:
        opponent_index = slot.slot_index + 1 if slot.slot_index % 2 else slot.slot_index - 1
        opponent = authority.main.slots[opponent_index - 1]
        assert opponent.seed_number in {1, 2, 3, 4}


def test_historical_v1_algorithm_replays_without_idealized_slot_fields():
    draw_input = TournamentDrawInputAuthority(
        run_id="run",
        branch_id="branch",
        event_id="legacy",
        committed_by_command_id="legacy-input",
        draw_seed=9,
        main_seed_count=2,
        qualification_seed_count=0,
        field_sequence=1,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=0,
            qualifier_spots=0,
        ),
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=("A", "B", "C", "D"),
        qualification_player_ids=(),
        qualifier_placeholder_ids=(),
        withdrawn_player_ids=(),
        main_seed_player_ids=("A", "B"),
        qualification_seed_player_ids=(),
    )
    authority = TournamentDrawAuthorityBuilder.build(
        draw_input=draw_input,
        command_id="legacy-draw",
        algorithm_version="protected_seed_shuffle.v1",
    )
    assert authority.algorithm_version == "protected_seed_shuffle.v1"
    assert authority.main.seed_positions == ((1, 1), (2, 4))
    assert all(
        slot.idealized_slot_number is None for slot in authority.main.slots
    )
    assert "idealized_slot_number" not in authority.model_dump_json()


def test_same_frozen_input_replays_identical_bracket_and_store_retry(database):
    with database.begin() as session:
        draw_input = install_draw_input(session)
        first = TournamentDrawAuthorityBuilder.build(
            draw_input=draw_input,
            command_id="generate-draw",
        )
        second = TournamentDrawAuthorityBuilder.build(
            draw_input=draw_input,
            command_id="generate-draw",
        )
        assert second == first
        assert second.fingerprint == first.fingerprint

        store = TournamentDrawAuthorityStore(session)
        persisted = store.generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )
        assert persisted == first
        assert store.generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        ) == persisted

        with pytest.raises(
            TournamentDrawAuthorityConflict,
            match="already has canonical Draw authority",
        ):
            store.generate(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="another-command",
            )


def test_explicit_main_bye_is_placed_against_highest_seed(database):
    with database.begin() as session:
        applications = (
            app("A", "main"),
            app("B", "main"),
            app("C", "main"),
        )
        draw_input = install_draw_input(
            session,
            applications=applications,
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=4,
                qualification_draw_size=0,
                qualifier_spots=0,
                bye_slots=1,
            ),
            main_seed_count=1,
            qualification_seed_count=0,
        )
        authority = TournamentDrawAuthorityBuilder.build(
            draw_input=draw_input,
            command_id="generate-draw",
        )

        assert authority.qualification is None
        assert authority.main.bye_slot_indexes == (2,)
        assert authority.main.slots[0].player_id == "A"
        assert authority.main.slots[0].seed_number == 1
        assert authority.main.slots[1].entrant_kind == "bye"


def test_multi_qualifier_sections_persist_and_replay(database):
    with database.begin() as session:
        applications = (
            app("A", "main"),
            app("B", "main"),
            app("C", "qualification"),
            app("D", "qualification"),
            app("E", "qualification"),
            app("F", "qualification"),
        )
        draw_input = install_draw_input(
            session,
            applications=applications,
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=4,
                qualification_draw_size=4,
                qualifier_spots=2,
            ),
            main_seed_count=1,
            qualification_seed_count=2,
        )
        store = TournamentDrawAuthorityStore(session)
        authority = store.generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )

        assert authority.schema_version == "tournament_draw_authority.v2"
        assert authority.qualification is None
        assert tuple(
            section.section_id for section in authority.qualification_brackets
        ) == ("Q1", "Q2")
        assert all(
            section.bracket_size == 2 for section in authority.qualification_brackets
        )
        assert tuple(
            next(
                slot.player_id
                for slot in section.slots
                if slot.seed_number is not None
            )
            for section in authority.qualification_brackets
        ) == ("C", "D")
        assert store.get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == authority
        assert TournamentDrawAuthorityBuilder.build(
            draw_input=draw_input,
            command_id="generate-draw",
        ) == authority


def test_incomplete_qualification_fails_closed_without_persistence(database):
    with database.begin() as session:
        applications = (
            app("A", "main"),
            app("B", "main"),
            app("C", "main"),
            app("D", "qualification"),
        )
        install_draw_input(
            session,
            applications=applications,
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=4,
                qualification_draw_size=2,
                qualifier_spots=1,
            ),
            main_seed_count=2,
            qualification_seed_count=1,
        )
        with pytest.raises(ValueError, match="fully resolved field"):
            TournamentDrawAuthorityStore(session).generate(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="generate-draw",
            )
        assert session.get(
            TournamentDrawAuthorityModel,
            ("run", "branch", "event"),
        ) is None


def test_corrupt_persisted_draw_fails_closed(database):
    with database.begin() as session:
        install_draw_input(session)
        TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )

    with database.begin() as session:
        row = session.get(
            TournamentDrawAuthorityModel,
            ("run", "branch", "event"),
        )
        assert row is not None
        row.payload_json = row.payload_json.replace(
            '"bracket_size":4',
            '"bracket_size":8',
            1,
        )

    with database() as session:
        with pytest.raises(ValueError):
            TournamentDrawAuthorityStore(session).get(
                run_id="run",
                branch_id="branch",
                event_id="event",
            )


def test_saved_revision_restores_draw_authority_backward_and_forward(database):
    with database.begin() as session:
        install_draw_input(session)
        saved_before_draw = capture(session)
        before_component = saved_before_draw["content"]["simulation_slot_match_state"]
        assert "draw_authorities" not in before_component

        authority = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )
        saved_after_draw = capture(session)
        after_component = saved_after_draw["content"]["simulation_slot_match_state"]
        assert len(after_component["draw_authorities"]) == 1
        assert after_component["fingerprint"] != before_component["fingerprint"]

        restore_saved_simulation_slots(
            session,
            current_payload=saved_after_draw,
            target_payload=saved_before_draw,
            run_id="run",
            branch_id="branch",
        )
        assert TournamentDrawAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) is None
        recaptured_before = capture(session)
        assert (
            recaptured_before["content"]["simulation_slot_match_state"]["fingerprint"]
            == before_component["fingerprint"]
        )

        restore_saved_simulation_slots(
            session,
            current_payload=recaptured_before,
            target_payload=saved_after_draw,
            run_id="run",
            branch_id="branch",
        )
        assert TournamentDrawAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == authority
        recaptured_after = capture(session)
        assert (
            recaptured_after["content"]["simulation_slot_match_state"]["fingerprint"]
            == after_component["fingerprint"]
        )


def test_unsaved_draw_authority_blocks_saved_revision_restore(database):
    with database.begin() as session:
        install_draw_input(session)
        saved_before_draw = capture(session)
        authority = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )

        with pytest.raises(
            ValueError, match="Live simulation-slot state differs from saved head"
        ):
            restore_saved_simulation_slots(
                session,
                current_payload=saved_before_draw,
                target_payload=saved_before_draw,
                run_id="run",
                branch_id="branch",
            )
        assert TournamentDrawAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == authority


def test_corrupt_saved_draw_authority_rejected_before_live_mutation(database):
    with database.begin() as session:
        install_draw_input(session)
        authority = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )
        saved = capture(session)
        corrupt = {
            "content": {
                key: (dict(value) if isinstance(value, dict) else value)
                for key, value in saved["content"].items()
            }
        }
        component = dict(corrupt["content"]["simulation_slot_match_state"])
        rows = [dict(value) for value in component["draw_authorities"]]
        rows[0]["authority_fingerprint"] = "0" * 64
        component["draw_authorities"] = rows
        corrupt["content"]["simulation_slot_match_state"] = component

        with pytest.raises(ValueError):
            restore_saved_simulation_slots(
                session,
                current_payload=saved,
                target_payload=corrupt,
                run_id="run",
                branch_id="branch",
            )
        assert TournamentDrawAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == authority
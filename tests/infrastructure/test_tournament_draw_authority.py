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
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
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
    TournamentDrawProcessAuthorityModel,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    capture_saved_simulation_slots,
    restore_saved_simulation_slots,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityConflict,
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_process_authority import (
    TournamentDrawProcessAuthorityConflict,
    TournamentDrawProcessAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_revision import (
    TournamentDrawRevisionStore,
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
            main_seed_count=2,
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


def test_single_qualification_section_materializes_missing_player_as_master_bye(database):
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
            main_seed_count=1,
            qualification_seed_count=1,
        )
        authority = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )

        assert authority.qualification is not None
        assert len(authority.qualification.bye_slot_indexes) == 1
        bye = next(
            slot
            for slot in authority.qualification.slots
            if slot.entrant_kind == "bye"
        )
        assert bye.idealized_slot_number == 2
        player = next(
            slot
            for slot in authority.qualification.slots
            if slot.entrant_kind == "player"
        )
        assert player.player_id == "D"
        assert player.seed_number == 1


def test_multi_q_byes_fill_idealized_layers_across_sections_deterministically():
    direct = ("M01", "M02", "M03", "M04", "M05")
    qualification = tuple(f"QF{index:02d}" for index in range(1, 21))
    draw_input = TournamentDrawInputAuthority(
        schema_version="tournament_draw_input_authority.v2",
        run_id="run",
        branch_id="branch",
        event_id="event-q-byes",
        committed_by_command_id="input",
        draw_seed=6060,
        main_seed_count=2,
        qualification_seed_count=6,
        field_sequence=1,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=8,
            qualification_draw_size=24,
            qualifier_spots=3,
        ),
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=direct,
        qualification_player_ids=qualification,
        qualifier_placeholder_ids=("Q1", "Q2", "Q3"),
        withdrawn_player_ids=(),
        main_seed_player_ids=direct[:2],
        qualification_seed_player_ids=qualification[:6],
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

    sections = first.qualification_brackets
    assert tuple(section.section_id for section in sections) == ("Q1", "Q2", "Q3")
    assert [section.bracket_size for section in sections] == [8, 8, 8]

    bye_counts = [len(section.bye_slot_indexes) for section in sections]
    assert sorted(bye_counts) == [1, 1, 2]
    assert sum(bye_counts) == 4

    for section, bye_count in zip(sections, bye_counts, strict=True):
        bye_idealized = {
            slot.idealized_slot_number
            for slot in section.slots
            if slot.entrant_kind == "bye"
        }
        assert bye_idealized == set(range(9 - bye_count, 9))

    first_layer = []
    for section in sections:
        seeded = sorted(
            (
                slot.seed_number,
                slot.player_id,
            )
            for slot in section.slots
            if slot.seed_number is not None
        )
        first_layer.append(seeded[0])
    assert tuple(seed_number for seed_number, _ in first_layer) == (1, 2, 3)
    assert tuple(player_id for _, player_id in first_layer) == (
        "QF01",
        "QF02",
        "QF03",
    )

    q_players = {
        slot.player_id
        for section in sections
        for slot in section.slots
        if slot.player_id is not None
    }
    assert q_players == set(qualification)


def test_multi_q_bye_partial_layer_changes_with_draw_seed_but_stays_in_same_layer():
    def build(seed):
        direct = ("M01", "M02", "M03", "M04", "M05")
        qualification = tuple(f"QF{index:02d}" for index in range(1, 21))
        return TournamentDrawAuthorityBuilder.build(
            draw_input=TournamentDrawInputAuthority(
                schema_version="tournament_draw_input_authority.v2",
                run_id="run",
                branch_id="branch",
                event_id="event-q-byes-seed",
                committed_by_command_id="input",
                draw_seed=seed,
                main_seed_count=2,
                qualification_seed_count=6,
                field_sequence=1,
                capacity=TournamentEntryFieldCapacity(
                    main_draw_size=8,
                    qualification_draw_size=24,
                    qualifier_spots=3,
                ),
                tournament_ranking_authority_fingerprint="1" * 64,
                ranking_snapshot_fingerprint="2" * 64,
                entry_field_fingerprint="3" * 64,
                direct_main_player_ids=direct,
                qualification_player_ids=qualification,
                qualifier_placeholder_ids=("Q1", "Q2", "Q3"),
                withdrawn_player_ids=(),
                main_seed_player_ids=direct[:2],
                qualification_seed_player_ids=qualification[:6],
            ),
            command_id="draw",
        )

    variants = [build(seed) for seed in range(7000, 7012)]
    extra_bye_sections = {
        next(
            section.section_id
            for section in draw.qualification_brackets
            if len(section.bye_slot_indexes) == 2
        )
        for draw in variants
    }
    assert len(extra_bye_sections) > 1
    for draw in variants:
        assert sorted(
            len(section.bye_slot_indexes)
            for section in draw.qualification_brackets
        ) == [1, 1, 2]


def test_draw_process_authority_keeps_qualification_and_main_phases_independent(database):
    with database.begin() as session:
        install_draw_input(session)
        draw = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )
        process = TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="configure-draw-process",
            qualification_process_window_count=3,
            main_process_window_count=5,
        )

        assert process.draw_authority_fingerprint == draw.fingerprint
        assert process.qualification is not None
        assert process.qualification.redraw_cutoff_window_ordinal == 2
        assert process.qualification.draw_freeze_window_ordinal == 3
        assert process.main.redraw_cutoff_window_ordinal == 4
        assert process.main.draw_freeze_window_ordinal == 5

        assert process.phase_for(
            draw_type="qualification", process_window_ordinal=1
        ) == "full_redraw"
        assert process.phase_for(
            draw_type="qualification", process_window_ordinal=2
        ) == "seed_cascade"
        assert process.phase_for(
            draw_type="qualification", process_window_ordinal=3
        ) == "draw_frozen"

        assert process.phase_for(
            draw_type="main", process_window_ordinal=1
        ) == "full_redraw"
        assert process.phase_for(
            draw_type="main", process_window_ordinal=3
        ) == "full_redraw"
        assert process.phase_for(
            draw_type="main", process_window_ordinal=4
        ) == "seed_cascade"
        assert process.phase_for(
            draw_type="main", process_window_ordinal=5
        ) == "draw_frozen"

        assert (
            TournamentDrawProcessAuthorityStore(session).get(
                run_id="run",
                branch_id="branch",
                event_id="event",
            )
            == process
        )
        assert TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="configure-draw-process",
            qualification_process_window_count=3,
            main_process_window_count=5,
        ) == process

        with pytest.raises(
            TournamentDrawProcessAuthorityConflict,
            match="different request",
        ):
            TournamentDrawProcessAuthorityStore(session).configure(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="configure-draw-process",
                qualification_process_window_count=4,
                main_process_window_count=5,
            )


def test_draw_process_authority_requires_exact_draw_structure(database):
    with database.begin() as session:
        install_draw_input(session)
        TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )

        with pytest.raises(ValueError, match="Qualification Draw requires"):
            TournamentDrawProcessAuthorityStore(session).configure(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="missing-q-process",
                main_process_window_count=4,
            )

        with pytest.raises(ValueError, match="at least Redraw Cutoff"):
            TournamentDrawProcessAuthorityStore(session).configure(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="too-few-windows",
                qualification_process_window_count=1,
                main_process_window_count=4,
            )


def test_saved_revision_restores_draw_process_authority_backward_and_forward(database):
    with database.begin() as session:
        install_draw_input(session)
        TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )
        saved_before_process = capture(session)
        before_component = saved_before_process["content"]["simulation_slot_match_state"]
        assert "draw_process_authorities" not in before_component

        process = TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="configure-draw-process",
            qualification_process_window_count=3,
            main_process_window_count=5,
        )
        saved_after_process = capture(session)
        after_component = saved_after_process["content"]["simulation_slot_match_state"]
        assert len(after_component["draw_process_authorities"]) == 1
        assert after_component["fingerprint"] != before_component["fingerprint"]

        restore_saved_simulation_slots(
            session,
            current_payload=saved_after_process,
            target_payload=saved_before_process,
            run_id="run",
            branch_id="branch",
        )
        assert TournamentDrawProcessAuthorityStore(session).get(
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
            target_payload=saved_after_process,
            run_id="run",
            branch_id="branch",
        )
        assert TournamentDrawProcessAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == process


def test_corrupt_saved_draw_process_authority_is_rejected(database):
    with database.begin() as session:
        install_draw_input(session)
        TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )
        process = TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="configure-draw-process",
            qualification_process_window_count=3,
            main_process_window_count=5,
        )
        saved = capture(session)

        corrupt = {
            "content": {
                key: (dict(value) if isinstance(value, dict) else value)
                for key, value in saved["content"].items()
            }
        }
        component = dict(corrupt["content"]["simulation_slot_match_state"])
        rows = [dict(value) for value in component["draw_process_authorities"]]
        rows[0]["authority_fingerprint"] = "0" * 64
        component["draw_process_authorities"] = rows
        corrupt["content"]["simulation_slot_match_state"] = component

        with pytest.raises(ValueError):
            restore_saved_simulation_slots(
                session,
                current_payload=saved,
                target_payload=corrupt,
                run_id="run",
                branch_id="branch",
            )
        assert TournamentDrawProcessAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == process


def test_full_redraw_main_creates_append_only_active_revision(database):
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
        TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="commit-draw-input",
            draw_seed=123,
            main_seed_count=2,
            qualification_seed_count=0,
        )
        draw_store = TournamentDrawAuthorityStore(session)
        initial = draw_store.generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="configure-process",
            main_process_window_count=4,
        )

        revision = TournamentDrawRevisionStore(session).full_redraw(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="redraw-main-1",
            draw_type="main",
            process_window_ordinal=1,
            repair_draw_seed=987654,
        )

        assert revision.sequence == 1
        assert revision.predecessor_draw_fingerprint == initial.fingerprint
        assert revision.successor_draw.draw_input_fingerprint == initial.draw_input_fingerprint
        assert revision.successor_draw.main != initial.main
        assert draw_store.get_initial(
            run_id="run", branch_id="branch", event_id="event"
        ) == initial
        assert draw_store.get(
            run_id="run", branch_id="branch", event_id="event"
        ) == revision.successor_draw
        assert TournamentDrawRevisionStore(session).history(
            run_id="run", branch_id="branch", event_id="event"
        ) == (revision,)


def test_full_redraw_qualification_preserves_main_and_q_linkages(database):
    with database.begin() as session:
        applications = (
            app("A", "main"),
            app("B", "main"),
            app("C", "qualification"),
            app("D", "qualification"),
            app("E", "qualification"),
            app("F", "qualification"),
        )
        install_draw_input(
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
        draw_store = TournamentDrawAuthorityStore(session)
        initial = draw_store.generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="configure-process",
            main_process_window_count=5,
            qualification_process_window_count=3,
        )

        revision = TournamentDrawRevisionStore(session).full_redraw(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="redraw-q-1",
            draw_type="qualification",
            process_window_ordinal=1,
            repair_draw_seed=246810,
        )

        assert revision.successor_draw.main == initial.main
        assert tuple(
            section.section_id
            for section in revision.successor_draw.qualification_brackets
        ) == ("Q1", "Q2")
        assert revision.successor_draw.main.qualifier_placeholder_slots == (
            initial.main.qualifier_placeholder_slots
        )
        assert revision.successor_draw.qualification_brackets != initial.qualification_brackets


def test_full_redraw_is_rejected_at_or_after_redraw_cutoff(database):
    with database.begin() as session:
        install_draw_input(session)
        TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="configure-process",
            main_process_window_count=4,
            qualification_process_window_count=3,
        )

        with pytest.raises(ValueError, match="only legal before Redraw Cutoff"):
            TournamentDrawRevisionStore(session).full_redraw(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="too-late-redraw",
                draw_type="qualification",
                process_window_ordinal=2,
                repair_draw_seed=44,
            )


def test_saved_revision_restores_active_full_redraw(database):
    with database.begin() as session:
        install_draw_input(session)
        draw_store = TournamentDrawAuthorityStore(session)
        initial = draw_store.generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="configure-process",
            main_process_window_count=4,
            qualification_process_window_count=3,
        )
        saved_before = capture(session)

        revision = TournamentDrawRevisionStore(session).full_redraw(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="redraw-main",
            draw_type="main",
            process_window_ordinal=1,
            repair_draw_seed=9991,
        )
        saved_after = capture(session)
        assert len(
            saved_after["content"]["simulation_slot_match_state"]["draw_revisions"]
        ) == 1

        restore_saved_simulation_slots(
            session,
            current_payload=saved_after,
            target_payload=saved_before,
            run_id="run",
            branch_id="branch",
        )
        assert draw_store.get(
            run_id="run", branch_id="branch", event_id="event"
        ) == initial

        recaptured = capture(session)
        restore_saved_simulation_slots(
            session,
            current_payload=recaptured,
            target_payload=saved_after,
            run_id="run",
            branch_id="branch",
        )
        assert draw_store.get(
            run_id="run", branch_id="branch", event_id="event"
        ) == revision.successor_draw


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
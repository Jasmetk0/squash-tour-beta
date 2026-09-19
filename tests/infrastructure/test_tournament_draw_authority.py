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
from beta_engine.domain.tournaments.draw_revision_authority import (
    TournamentDrawRevisionBuilder,
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
    TournamentDrawRevisionConflict,
    TournamentDrawRevisionStore,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import TournamentEntryFieldStore
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_wild_card_authority import (
    TournamentWildCardAuthorityStore,
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


def test_main_withdrawal_full_redraw_atomically_repairs_main_and_qualification(database):
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
            main_process_window_count=5,
            qualification_process_window_count=3,
        )

        revision = TournamentDrawRevisionStore(session).full_redraw_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-c-redraw",
            withdrawn_player_ids=("C",),
            main_process_window_ordinal=1,
            qualification_process_window_ordinal=1,
            repair_draw_seed=987654,
        )

        assert revision.sequence == 1
        assert revision.predecessor_draw_fingerprint == initial.fingerprint
        assert revision.affected_draw_types == ("main", "qualification")
        assert revision.withdrawn_player_ids == ("C",)
        assert revision.successor_field.direct_main_player_ids == ("A", "B", "D")
        assert revision.successor_field.qualification_player_ids == ("E", "F")
        assert revision.successor_field.below_qualification_cut_player_ids == ("G",)
        assert revision.successor_draw_input.withdrawn_player_ids == ("C",)
        assert revision.successor_draw.draw_input_fingerprint == (
            revision.successor_draw_input.fingerprint
        )
        assert draw_store.get_initial(
            run_id="run", branch_id="branch", event_id="event"
        ) == initial
        assert draw_store.get(
            run_id="run", branch_id="branch", event_id="event"
        ) == revision.successor_draw
        assert len(revision.successor_draw.qualification_brackets) == 1
        assert revision.successor_draw.qualification_brackets[0].section_id is None
        assert {
            placeholder_id
            for placeholder_id, _ in revision.successor_draw.main.qualifier_placeholder_slots
        } == {"Q1"}


def test_qualification_only_withdrawal_redraw_preserves_main(database):
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
            main_process_window_count=5,
            qualification_process_window_count=3,
        )

        revision = TournamentDrawRevisionStore(session).full_redraw_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-b-redraw",
            withdrawn_player_ids=("B",),
            qualification_process_window_ordinal=1,
            repair_draw_seed=246810,
        )

        assert revision.affected_draw_types == ("qualification",)
        assert revision.successor_field.direct_main_player_ids == ("A", "C", "D")
        assert revision.successor_field.qualification_player_ids == ("E", "F")
        assert revision.successor_draw.main == initial.main
        assert revision.successor_draw.main.qualifier_placeholder_slots == (
            initial.main.qualifier_placeholder_slots
        )
        assert len(revision.successor_draw.qualification_brackets) == 1
        assert revision.successor_draw.qualification_brackets[0].section_id is None


def test_full_redraw_checks_each_affected_component_phase(database):
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
            main_process_window_count=5,
            qualification_process_window_count=3,
        )

        with pytest.raises(
            ValueError,
            match="Qualification full redraw is only legal before Redraw Cutoff",
        ):
            TournamentDrawRevisionStore(session).full_redraw_withdrawal(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="too-late-main-withdrawal",
                withdrawn_player_ids=("C",),
                main_process_window_ordinal=1,
                qualification_process_window_ordinal=2,
                repair_draw_seed=44,
            )


def test_multiple_full_redraw_withdrawals_chain_from_frozen_successor_field(database):
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
            main_process_window_count=5,
            qualification_process_window_count=3,
        )

        first = TournamentDrawRevisionStore(session).full_redraw_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-c",
            withdrawn_player_ids=("C",),
            main_process_window_ordinal=1,
            qualification_process_window_ordinal=1,
            repair_draw_seed=101,
        )
        second = TournamentDrawRevisionStore(session).full_redraw_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-e",
            withdrawn_player_ids=("E",),
            qualification_process_window_ordinal=1,
            repair_draw_seed=202,
        )

        assert first.successor_field.qualification_player_ids == ("E", "F")
        assert second.sequence == 2
        assert second.predecessor_draw_fingerprint == first.successor_draw.fingerprint
        assert second.successor_field.direct_main_player_ids == ("A", "B", "D")
        assert second.successor_field.qualification_player_ids == ("F", "G")
        assert second.successor_field.withdrawn_player_ids == ("C", "E")


def test_full_redraw_retry_returns_original_revision_after_later_revision(database):
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
            main_process_window_count=5,
            qualification_process_window_count=3,
        )

        store = TournamentDrawRevisionStore(session)
        first = store.full_redraw_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-c",
            withdrawn_player_ids=("C",),
            main_process_window_ordinal=1,
            qualification_process_window_ordinal=1,
            repair_draw_seed=101,
        )
        store.full_redraw_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-e",
            withdrawn_player_ids=("E",),
            qualification_process_window_ordinal=1,
            repair_draw_seed=202,
        )

        assert store.full_redraw_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-c",
            withdrawn_player_ids=("C",),
            main_process_window_ordinal=1,
            qualification_process_window_ordinal=1,
            repair_draw_seed=101,
        ) == first


def test_saved_revision_restores_active_full_redraw_withdrawal(database):
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
            main_process_window_count=5,
            qualification_process_window_count=3,
        )
        saved_before = capture(session)

        revision = TournamentDrawRevisionStore(session).full_redraw_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-c",
            withdrawn_player_ids=("C",),
            main_process_window_ordinal=1,
            qualification_process_window_ordinal=1,
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


def install_seed_cascade_main(session, *, player_count=34):
    player_ids = tuple(f"P{index:02d}" for index in range(1, player_count + 1))
    install_ranking_authority(session, player_ids)
    TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id="event",
        applications=tuple(app(player_id, "main") for player_id in player_ids),
        capacity=TournamentEntryFieldCapacity(main_draw_size=32),
        command_id="seed-cascade-field",
    )
    TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seed-cascade-input",
        draw_seed=12345,
        main_seed_count=8,
        qualification_seed_count=0,
    )
    initial = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seed-cascade-draw",
    )
    TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seed-cascade-process",
        main_process_window_count=3,
    )
    return initial


def install_seed_cascade_multi_q(session):
    main_ids = tuple(f"M{index:02d}" for index in range(1, 6))
    q_ids = tuple(f"Q{index:02d}" for index in range(1, 26))
    player_ids = (*main_ids, *q_ids)
    install_ranking_authority(session, player_ids)
    TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id="event",
        applications=(
            *tuple(app(player_id, "main") for player_id in main_ids),
            *tuple(app(player_id, "qualification") for player_id in q_ids),
        ),
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=8,
            qualification_draw_size=24,
            qualifier_spots=3,
        ),
        command_id="seed-cascade-q-field",
    )
    TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seed-cascade-q-input",
        draw_seed=24680,
        main_seed_count=2,
        qualification_seed_count=6,
    )
    initial = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seed-cascade-q-draw",
    )
    TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seed-cascade-q-process",
        main_process_window_count=3,
        qualification_process_window_count=3,
    )
    return initial




def install_frozen_external_rwc_main(session):
    player_ids = ("A", "C", "D", "E", "F", "G")
    install_ranking_authority(session, player_ids)
    TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id="event",
        applications=tuple(app(player_id, "main") for player_id in player_ids),
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            wild_card_slots=1,
        ),
        command_id="wc-field",
    )
    wc = TournamentWildCardAuthorityStore(session).resolve(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="wc-resolve",
        original_wild_card_player_ids=("A",),
        reserve_wild_card_player_ids=("E", "F", "G"),
    )
    assert wc.active_wild_card_player_ids == ("E",)
    draw_input = TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="wc-draw-input",
        draw_seed=445566,
    )
    initial = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="wc-draw",
    )
    TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="wc-process",
        main_process_window_count=3,
    )
    return initial, draw_input, wc




def install_frozen_seeded_wc_main(session):
    install_ranking_authority(session)
    TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id="event",
        applications=standard_applications(),
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=8,
            wild_card_slots=1,
            bye_slots=4,
        ),
        command_id="seeded-wc-field",
    )
    wc = TournamentWildCardAuthorityStore(session).resolve(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seeded-wc-resolve",
        original_wild_card_player_ids=("B",),
        reserve_wild_card_player_ids=("E", "F", "G"),
    )
    draw_input = TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seeded-wc-input",
        draw_seed=778899,
    )
    initial = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seeded-wc-draw",
    )
    TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seeded-wc-process",
        main_process_window_count=3,
    )
    return initial, draw_input, wc


def draw_player_slots(bracket):
    return {
        slot.player_id: slot
        for slot in bracket.slots
        if slot.player_id is not None
    }


def test_seed_cascade_main_preserves_seed_numbers_and_physical_history(database):
    with database.begin() as session:
        initial = install_seed_cascade_main(session)
        before = draw_player_slots(initial.main)

        revision = TournamentDrawRevisionStore(
            session
        ).seed_cascade_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-seed-one-cascade",
            withdrawn_player_ids=("P01",),
            main_process_window_ordinal=2,
        )

        after = draw_player_slots(revision.successor_draw.main)
        assert revision.schema_version == "tournament_draw_revision.v5"
        assert revision.repair_kind == "seed_cascade_phase"
        assert tuple(
            authority.status for authority in revision.replacement_cutoff_authorities
        ) == ("replacement_open",)
        assert revision.main_repair_action == "seed_cascade"
        assert revision.repair_draw_seed is None
        assert revision.successor_draw_input.draw_seed == 12345

        assert after["P03"].slot_index == before["P01"].slot_index
        assert after["P03"].seed_number == 3
        assert after["P05"].slot_index == before["P03"].slot_index
        assert after["P05"].seed_number == 5
        assert after["P09"].slot_index == before["P05"].slot_index
        assert after["P09"].seed_number is None
        assert after["P33"].slot_index == before["P09"].slot_index
        assert after["P33"].seed_number is None
        assert after["P02"] == before["P02"]

        assert TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


def test_seed_cascade_phase_directly_fills_unseeded_withdrawal(database):
    with database.begin() as session:
        initial = install_seed_cascade_main(session)
        before = draw_player_slots(initial.main)

        revision = TournamentDrawRevisionStore(
            session
        ).seed_cascade_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-unseeded-direct-fill",
            withdrawn_player_ids=("P20",),
            main_process_window_ordinal=2,
        )

        after = draw_player_slots(revision.successor_draw.main)
        assert revision.main_repair_action == "direct_slot_fill"
        assert after["P33"].slot_index == before["P20"].slot_index
        assert revision.successor_draw.main.seed_positions == initial.main.seed_positions
        for player_id, slot in before.items():
            if player_id != "P20":
                assert after[player_id] == slot


def test_seed_cascade_multiple_withdrawals_are_atomic_and_order_independent(database):
    with database.begin() as session:
        initial = install_seed_cascade_main(session)
        before = draw_player_slots(initial.main)
        store = TournamentDrawRevisionStore(session)

        revision = store.seed_cascade_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-two-seeds-cascade",
            withdrawn_player_ids=("P04", "P01"),
            main_process_window_ordinal=2,
        )
        retry = store.seed_cascade_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-two-seeds-cascade",
            withdrawn_player_ids=("P01", "P04"),
            main_process_window_ordinal=2,
        )
        assert retry == revision

        after = draw_player_slots(revision.successor_draw.main)
        assert after["P03"].slot_index == before["P01"].slot_index
        assert after["P03"].seed_number == 3
        assert after["P05"].slot_index == before["P03"].slot_index
        assert after["P05"].seed_number == 5
        assert after["P06"].slot_index == before["P04"].slot_index
        assert after["P06"].seed_number == 6
        assert after["P09"].slot_index == before["P05"].slot_index
        assert after["P10"].slot_index == before["P06"].slot_index
        assert {
            after["P33"].slot_index,
            after["P34"].slot_index,
        } == {
            before["P09"].slot_index,
            before["P10"].slot_index,
        }


def test_seed_cascade_rejects_frozen_phase(database):
    with database.begin() as session:
        install_seed_cascade_main(session)
        with pytest.raises(
            ValueError,
            match="not legal after Draw Freeze",
        ):
            TournamentDrawRevisionStore(
                session
            ).seed_cascade_phase_withdrawal(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="wrong-cascade-frozen-phase",
                withdrawn_player_ids=("P01",),
                main_process_window_ordinal=3,
            )


def test_seed_cascade_multi_q_preserves_q_identity_and_global_seed_numbers(database):
    with database.begin() as session:
        initial = install_seed_cascade_multi_q(session)
        assert tuple(
            section.section_id for section in initial.qualification_brackets
        ) == ("Q1", "Q2", "Q3")

        before = {
            slot.player_id: (section.section_id, slot)
            for section in initial.qualification_brackets
            for slot in section.slots
            if slot.player_id is not None
        }
        q1 = initial.qualification_brackets[0]
        q1_second_seed = next(
            slot
            for slot in q1.slots
            if slot.seed_number is not None and slot.seed_number != 1
        )
        assert q1_second_seed.player_id is not None

        revision = TournamentDrawRevisionStore(
            session
        ).seed_cascade_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-q1-global-seed",
            withdrawn_player_ids=("Q01",),
            qualification_process_window_ordinal=2,
        )

        assert revision.qualification_repair_action == "seed_cascade"
        assert tuple(
            section.section_id
            for section in revision.successor_draw.qualification_brackets
        ) == ("Q1", "Q2", "Q3")
        after = {
            slot.player_id: (section.section_id, slot)
            for section in revision.successor_draw.qualification_brackets
            for slot in section.slots
            if slot.player_id is not None
        }

        _, withdrawn_slot = before["Q01"]
        moved_section, moved_seed = after[q1_second_seed.player_id]
        assert moved_section == "Q1"
        assert moved_seed.slot_index == withdrawn_slot.slot_index
        assert moved_seed.seed_number == q1_second_seed.seed_number

        q07_before_section, q07_before = before["Q07"]
        q07_after_section, q07_after = after["Q07"]
        assert q07_after_section == "Q1"
        assert q07_after.slot_index == q1_second_seed.slot_index
        assert q07_after.seed_number is None

        q25_section, q25_after = after["Q25"]
        assert q25_section == q07_before_section
        assert q25_after.slot_index == q07_before.slot_index
        assert q25_after.seed_number is None
        assert revision.successor_draw.main == initial.main


def test_seed_cascade_supports_main_full_redraw_with_q_cascade(database):
    with database.begin() as session:
        initial = install_seed_cascade_multi_q(session)

        revision = TournamentDrawRevisionStore(
            session
        ).seed_cascade_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="mixed-main-redraw-q-cascade",
            withdrawn_player_ids=("M01",),
            main_process_window_ordinal=1,
            qualification_process_window_ordinal=2,
            repair_draw_seed=13579,
        )

        assert revision.main_repair_action == "full_redraw"
        assert revision.qualification_repair_action == "seed_cascade"
        assert revision.repair_draw_seed == 13579
        assert revision.successor_draw_input.draw_seed == 24680
        assert revision.successor_draw.main != initial.main
        assert tuple(
            section.section_id
            for section in revision.successor_draw.qualification_brackets
        ) == ("Q1", "Q2", "Q3")
        assert TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


def test_seed_cascade_supports_main_cascade_with_q_full_redraw(database):
    with database.begin() as session:
        initial = install_seed_cascade_multi_q(session)
        before_main = draw_player_slots(initial.main)

        revision = TournamentDrawRevisionStore(
            session
        ).seed_cascade_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="mixed-main-cascade-q-redraw",
            withdrawn_player_ids=("M01",),
            main_process_window_ordinal=2,
            qualification_process_window_ordinal=1,
            repair_draw_seed=97531,
        )

        assert revision.main_repair_action == "seed_cascade"
        assert revision.qualification_repair_action == "full_redraw"
        assert revision.repair_draw_seed == 97531
        assert revision.successor_draw_input.draw_seed == 24680

        after_main = draw_player_slots(revision.successor_draw.main)
        assert after_main["M02"] == before_main["M02"]
        assert after_main["M03"].slot_index == before_main["M01"].slot_index
        assert after_main["M03"].seed_number is None
        assert tuple(
            section.section_id
            for section in revision.successor_draw.qualification_brackets
        ) == ("Q1", "Q2", "Q3")
        assert TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


def test_seed_cascade_repairs_main_and_q_together_when_both_are_cascade(database):
    with database.begin() as session:
        initial = install_seed_cascade_multi_q(session)
        before_main = draw_player_slots(initial.main)
        before_q = {
            slot.player_id: (section.section_id, slot)
            for section in initial.qualification_brackets
            for slot in section.slots
            if slot.player_id is not None
        }
        q1 = initial.qualification_brackets[0]
        q1_second_seed = next(
            slot
            for slot in q1.slots
            if slot.seed_number is not None and slot.seed_number != 1
        )
        assert q1_second_seed.player_id is not None

        revision = TournamentDrawRevisionStore(
            session
        ).seed_cascade_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="main-and-q-both-cascade",
            withdrawn_player_ids=("M01",),
            main_process_window_ordinal=2,
            qualification_process_window_ordinal=2,
        )

        assert revision.main_repair_action == "seed_cascade"
        assert revision.qualification_repair_action == "seed_cascade"
        assert revision.repair_draw_seed is None

        after_main = draw_player_slots(revision.successor_draw.main)
        assert after_main["M02"] == before_main["M02"]
        assert after_main["M03"].slot_index == before_main["M01"].slot_index
        assert after_main["M03"].seed_number is None
        assert after_main["Q01"].slot_index == before_main["M03"].slot_index

        after_q = {
            slot.player_id: (section.section_id, slot)
            for section in revision.successor_draw.qualification_brackets
            for slot in section.slots
            if slot.player_id is not None
        }
        _, q01_before = before_q["Q01"]
        moved_section, moved_seed = after_q[q1_second_seed.player_id]
        assert moved_section == "Q1"
        assert moved_seed.slot_index == q01_before.slot_index
        assert moved_seed.seed_number == q1_second_seed.seed_number

        q07_before_section, q07_before = before_q["Q07"]
        q07_after_section, q07_after = after_q["Q07"]
        assert q07_after_section == "Q1"
        assert q07_after.slot_index == q1_second_seed.slot_index
        assert q07_after.seed_number is None
        q25_section, q25_after = after_q["Q25"]
        assert q25_section == q07_before_section
        assert q25_after.slot_index == q07_before.slot_index

        assert TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


def test_saved_revision_restores_active_seed_cascade(database):
    with database.begin() as session:
        initial = install_seed_cascade_main(session)
        draw_store = TournamentDrawAuthorityStore(session)
        saved_before = capture(session)

        revision = TournamentDrawRevisionStore(
            session
        ).seed_cascade_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="saved-seed-cascade",
            withdrawn_player_ids=("P01",),
            main_process_window_ordinal=2,
        )
        saved_after = capture(session)
        component_after = saved_after["content"]["simulation_slot_match_state"]
        assert len(component_after["draw_revisions"]) == 1
        assert component_after["draw_revisions"][0]["revision_fingerprint"] == (
            revision.fingerprint
        )

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

        recaptured_before = capture(session)
        restore_saved_simulation_slots(
            session,
            current_payload=recaptured_before,
            target_payload=saved_after,
            run_id="run",
            branch_id="branch",
        )
        assert draw_store.get(
            run_id="run", branch_id="branch", event_id="event"
        ) == revision.successor_draw
        recaptured_after = capture(session)
        assert (
            recaptured_after["content"]["simulation_slot_match_state"]["fingerprint"]
            == component_after["fingerprint"]
        )




def test_draw_freeze_seeded_withdrawal_fills_exact_slot_without_cascade(database):
    with database.begin() as session:
        initial = install_seed_cascade_main(session)
        before = draw_player_slots(initial.main)
        store = TournamentDrawRevisionStore(session)

        revision = store.draw_frozen_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-seed-one-frozen",
            withdrawn_player_ids=("P01",),
            main_process_window_ordinal=3,
        )
        retry = store.draw_frozen_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-seed-one-frozen",
            withdrawn_player_ids=("P01",),
            main_process_window_ordinal=3,
        )

        assert retry == revision
        assert revision.schema_version == "tournament_draw_revision.v5"
        assert revision.repair_kind == "draw_frozen_phase"
        assert tuple(
            authority.status for authority in revision.replacement_cutoff_authorities
        ) == ("replacement_open",)
        assert revision.main_repair_action == "frozen_slot_fill"
        assert revision.repair_draw_seed is None
        assert revision.successor_draw_input.draw_seed == 12345

        after = draw_player_slots(revision.successor_draw.main)
        assert after["P33"].slot_index == before["P01"].slot_index
        assert after["P33"].seed_number is None
        assert after["P33"].is_seed_protected is False
        for player_id, slot in before.items():
            if player_id != "P01":
                assert after[player_id] == slot

        with pytest.raises(TournamentDrawRevisionConflict):
            store.draw_frozen_phase_withdrawal(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="withdraw-seed-one-frozen",
                withdrawn_player_ids=("P02",),
                main_process_window_ordinal=3,
            )


def test_draw_freeze_unseeded_withdrawal_only_changes_exact_slot(database):
    with database.begin() as session:
        initial = install_seed_cascade_main(session)
        before = draw_player_slots(initial.main)

        revision = TournamentDrawRevisionStore(
            session
        ).draw_frozen_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="withdraw-unseeded-frozen",
            withdrawn_player_ids=("P20",),
            main_process_window_ordinal=3,
        )

        after = draw_player_slots(revision.successor_draw.main)
        assert revision.main_repair_action == "frozen_slot_fill"
        assert after["P33"].slot_index == before["P20"].slot_index
        assert after["P33"].seed_number is None
        for player_id, slot in before.items():
            if player_id != "P20":
                assert after[player_id] == slot


def test_draw_freeze_supports_main_frozen_with_q_cascade(database):
    with database.begin() as session:
        initial = install_seed_cascade_multi_q(session)
        before_main = draw_player_slots(initial.main)
        before_q = {
            slot.player_id: (section.section_id, slot)
            for section in initial.qualification_brackets
            for slot in section.slots
            if slot.player_id is not None
        }

        revision = TournamentDrawRevisionStore(
            session
        ).draw_frozen_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="main-frozen-q-cascade",
            withdrawn_player_ids=("M01",),
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=2,
        )

        assert revision.main_repair_action == "frozen_slot_fill"
        assert revision.qualification_repair_action == "seed_cascade"
        assert revision.repair_draw_seed is None

        after_main = draw_player_slots(revision.successor_draw.main)
        assert after_main["Q01"].slot_index == before_main["M01"].slot_index
        assert after_main["Q01"].seed_number is None
        for player_id, slot in before_main.items():
            if player_id != "M01":
                assert after_main[player_id] == slot

        assert tuple(
            section.section_id
            for section in revision.successor_draw.qualification_brackets
        ) == ("Q1", "Q2", "Q3")
        after_q = {
            slot.player_id: (section.section_id, slot)
            for section in revision.successor_draw.qualification_brackets
            for slot in section.slots
            if slot.player_id is not None
        }
        assert "Q01" not in after_q
        assert "Q25" in after_q
        assert before_q["Q01"][0] == "Q1"


def test_draw_freeze_supports_main_frozen_with_q_full_redraw(database):
    with database.begin() as session:
        initial = install_seed_cascade_multi_q(session)
        before_main = draw_player_slots(initial.main)

        revision = TournamentDrawRevisionStore(
            session
        ).draw_frozen_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="main-frozen-q-redraw",
            withdrawn_player_ids=("M01",),
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=1,
            repair_draw_seed=424242,
        )

        assert revision.main_repair_action == "frozen_slot_fill"
        assert revision.qualification_repair_action == "full_redraw"
        assert revision.repair_draw_seed == 424242
        after_main = draw_player_slots(revision.successor_draw.main)
        assert after_main["Q01"].slot_index == before_main["M01"].slot_index
        assert after_main["Q01"].seed_number is None
        assert tuple(
            section.section_id
            for section in revision.successor_draw.qualification_brackets
        ) == ("Q1", "Q2", "Q3")


def test_draw_freeze_replacement_exhaustion_creates_late_bye_in_vacated_slot(database):
    with database.begin() as session:
        initial = install_seed_cascade_main(session, player_count=32)
        before = draw_player_slots(initial.main)
        withdrawn_slot = before["P20"].slot_index

        revision = TournamentDrawRevisionStore(
            session
        ).draw_frozen_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="frozen-late-bye",
            withdrawn_player_ids=("P20",),
            main_process_window_ordinal=3,
        )

        slot = revision.successor_draw.main.slots[withdrawn_slot - 1]
        assert slot.entrant_kind == "bye"
        assert slot.player_id is None
        assert slot.seed_number is None
        assert withdrawn_slot in revision.successor_draw.main.bye_slot_indexes
        for player_id, prior in before.items():
            if player_id != "P20":
                assert draw_player_slots(revision.successor_draw.main)[player_id] == prior

        assert TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


def test_draw_freeze_multi_q_fills_exact_section_slot_and_keeps_q_identity(database):
    with database.begin() as session:
        initial = install_seed_cascade_multi_q(session)
        before = {
            slot.player_id: (section.section_id, slot)
            for section in initial.qualification_brackets
            for slot in section.slots
            if slot.player_id is not None
        }

        revision = TournamentDrawRevisionStore(
            session
        ).draw_frozen_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="q-frozen-direct-slot",
            withdrawn_player_ids=("Q01",),
            qualification_process_window_ordinal=3,
        )

        assert revision.qualification_repair_action == "frozen_slot_fill"
        assert revision.successor_draw.main == initial.main
        assert tuple(
            section.section_id
            for section in revision.successor_draw.qualification_brackets
        ) == ("Q1", "Q2", "Q3")

        after = {
            slot.player_id: (section.section_id, slot)
            for section in revision.successor_draw.qualification_brackets
            for slot in section.slots
            if slot.player_id is not None
        }
        before_section, before_slot = before["Q01"]
        after_section, replacement_slot = after["Q25"]
        assert after_section == before_section
        assert replacement_slot.slot_index == before_slot.slot_index
        assert replacement_slot.seed_number is None


def test_saved_revision_restores_active_draw_freeze_revision(database):
    with database.begin() as session:
        initial = install_seed_cascade_main(session)
        draw_store = TournamentDrawAuthorityStore(session)
        saved_before = capture(session)

        revision = TournamentDrawRevisionStore(
            session
        ).draw_frozen_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="saved-draw-freeze",
            withdrawn_player_ids=("P01",),
            main_process_window_ordinal=3,
        )
        saved_after = capture(session)
        component_after = saved_after["content"]["simulation_slot_match_state"]
        assert len(component_after["draw_revisions"]) == 1
        assert component_after["draw_revisions"][0]["revision_fingerprint"] == (
            revision.fingerprint
        )

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

        recaptured_before = capture(session)
        restore_saved_simulation_slots(
            session,
            current_payload=recaptured_before,
            target_payload=saved_after,
            run_id="run",
            branch_id="branch",
        )
        assert draw_store.get(
            run_id="run", branch_id="branch", event_id="event"
        ) == revision.successor_draw
        recaptured_after = capture(session)
        assert (
            recaptured_after["content"]["simulation_slot_match_state"]["fingerprint"]
            == component_after["fingerprint"]
        )


def test_cutoff_aware_seed_revision_preserves_historical_v3_builder_shape(database):
    with database.begin() as session:
        initial = install_seed_cascade_main(session)
        store = TournamentDrawRevisionStore(session)
        revision = store.seed_cascade_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="cutoff-aware-seed-history",
            withdrawn_player_ids=("P01",),
            main_process_window_ordinal=2,
        )
        process = TournamentDrawProcessAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        )
        assert process is not None

        historical = TournamentDrawRevisionBuilder.build_seed_cascade_phase(
            predecessor=initial,
            successor_field=revision.successor_field,
            successor_draw_input=revision.successor_draw_input,
            process_authority=process,
            affected_draw_types=revision.affected_draw_types,
            main_process_window_ordinal=revision.main_process_window_ordinal,
            qualification_process_window_ordinal=(
                revision.qualification_process_window_ordinal
            ),
            withdrawn_player_ids=revision.withdrawn_player_ids,
            sequence=revision.sequence,
            command_id=revision.command_id,
            repair_draw_seed=revision.repair_draw_seed,
        )

        assert revision.schema_version == "tournament_draw_revision.v5"
        assert historical.schema_version == "tournament_draw_revision.v3"
        assert historical.replacement_cutoff_authorities == ()
        assert historical.successor_draw == revision.successor_draw


def test_cutoff_aware_frozen_revision_preserves_historical_v4_builder_shape(database):
    with database.begin() as session:
        initial = install_seed_cascade_main(session)
        store = TournamentDrawRevisionStore(session)
        revision = store.draw_frozen_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="cutoff-aware-frozen-history",
            withdrawn_player_ids=("P20",),
            main_process_window_ordinal=3,
        )
        process = TournamentDrawProcessAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        )
        assert process is not None

        historical = TournamentDrawRevisionBuilder.build_draw_frozen_phase(
            predecessor=initial,
            successor_field=revision.successor_field,
            successor_draw_input=revision.successor_draw_input,
            process_authority=process,
            affected_draw_types=revision.affected_draw_types,
            main_process_window_ordinal=revision.main_process_window_ordinal,
            qualification_process_window_ordinal=(
                revision.qualification_process_window_ordinal
            ),
            withdrawn_player_ids=revision.withdrawn_player_ids,
            sequence=revision.sequence,
            command_id=revision.command_id,
            repair_draw_seed=revision.repair_draw_seed,
        )

        assert revision.schema_version == "tournament_draw_revision.v5"
        assert historical.schema_version == "tournament_draw_revision.v4"
        assert historical.replacement_cutoff_authorities == ()
        assert historical.successor_draw == revision.successor_draw


@pytest.mark.pr_critical
def test_frozen_wc_withdrawal_uses_next_external_rwc_in_exact_physical_slot(database):
    with database.begin() as session:
        initial, original_input, wc = install_frozen_external_rwc_main(session)
        assert original_input.schema_version == "tournament_draw_input_authority.v3"
        original_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "E"
        )
        assert original_slot.entry_status == "wild_card"
        assert original_slot.seed_number is None

        saved_before = capture(session)
        store = TournamentDrawRevisionStore(session)
        first = store.draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-e-to-f",
            withdrawn_player_id="E",
            main_process_window_ordinal=3,
        )

        assert first.schema_version == "tournament_draw_revision.v6"
        assert first.repair_kind == "frozen_wild_card_repair"
        assert first.main_repair_action == "frozen_wild_card_fill"
        assert first.successor_draw_input.schema_version == (
            "tournament_draw_input_authority.v4"
        )
        assert first.successor_draw_input.wild_card_authority_fingerprint == (
            wc.fingerprint
        )
        assert first.successor_draw_input.wild_card_player_ids == ("F",)
        assert first.successor_draw_input.withdrawn_player_ids == ("E",)
        authority = first.wild_card_repair_authority
        assert authority is not None
        assert authority.reserve_ordinal == 2
        assert authority.replacement_player_id == "F"
        assert authority.replacement_cutoff_authority.status == "replacement_open"
        assert first.successor_draw_input.post_draw_wild_card_repair_fingerprints == (
            authority.fingerprint,
        )

        replacement_slot = next(
            slot for slot in first.successor_draw.main.slots if slot.player_id == "F"
        )
        assert replacement_slot.slot_index == original_slot.slot_index
        assert replacement_slot.entry_status == "wild_card"
        assert replacement_slot.seed_number is None
        assert first.successor_draw.qualification == initial.qualification
        assert first.successor_draw.qualification_sections == (
            initial.qualification_sections
        )

        assert store.draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-e-to-f",
            withdrawn_player_id="E",
            main_process_window_ordinal=3,
        ) == first

        second = store.draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-f-to-g",
            withdrawn_player_id="F",
            main_process_window_ordinal=3,
        )
        assert second.sequence == 2
        assert second.wild_card_repair_authority is not None
        assert second.wild_card_repair_authority.reserve_ordinal == 3
        assert second.wild_card_repair_authority.replacement_player_id == "G"
        assert second.successor_draw_input.wild_card_player_ids == ("G",)
        assert second.successor_draw_input.withdrawn_player_ids == ("E", "F")
        assert len(
            second.successor_draw_input.post_draw_wild_card_repair_fingerprints
        ) == 2
        final_slot = next(
            slot for slot in second.successor_draw.main.slots if slot.player_id == "G"
        )
        assert final_slot.slot_index == original_slot.slot_index
        assert final_slot.entry_status == "wild_card"

        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (first, second)

        saved_after = capture(session)
        restore_saved_simulation_slots(
            session,
            current_payload=saved_after,
            target_payload=saved_before,
            run_id="run",
            branch_id="branch",
        )
        assert TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == ()
        assert TournamentDrawAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == initial

        recaptured = capture(session)
        restore_saved_simulation_slots(
            session,
            current_payload=recaptured,
            target_payload=saved_after,
            run_id="run",
            branch_id="branch",
        )
        assert TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (first, second)


@pytest.mark.pr_critical
def test_frozen_wc_promotes_priority_rwc_from_q_and_backfills_exact_q_slot(database):
    with database.begin() as session:
        install_ranking_authority(session)
        TournamentEntryFieldStore(session).stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=standard_applications(),
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=4,
                qualification_draw_size=2,
                qualifier_spots=1,
                wild_card_slots=1,
            ),
            command_id="wc-q-field",
        )
        wc = TournamentWildCardAuthorityStore(session).resolve(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-q-resolve",
            original_wild_card_player_ids=("A",),
            reserve_wild_card_player_ids=("B", "E", "F"),
        )
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-q-input",
            draw_seed=10101,
        )
        initial = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-q-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-q-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )
        assert draw_input.wild_card_player_ids == ("B",)
        assert draw_input.qualification_player_ids == ("D", "E")
        assert wc.adjusted_below_qualification_cut_player_ids == ("F", "G")

        original_wc_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "B"
        )
        original_q_section = next(
            bracket
            for bracket in initial.qualification_brackets
            if any(slot.player_id == "E" for slot in bracket.slots)
        )
        original_q_slot = next(
            slot for slot in original_q_section.slots if slot.player_id == "E"
        )
        assert original_q_slot.seed_number is None

        with pytest.raises(
            ValueError,
            match="requires Q process-window evidence",
        ):
            TournamentDrawRevisionStore(session).draw_frozen_wild_card_withdrawal(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="wc-q-missing-window",
                withdrawn_player_id="B",
                main_process_window_ordinal=3,
            )

        saved_before = capture(session)
        store = TournamentDrawRevisionStore(session)
        revision = store.draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-q-promote",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=3,
        )

        authority = revision.wild_card_repair_authority
        assert authority is not None
        assert authority.schema_version == "tournament_post_draw_wild_card_repair.v2"
        assert authority.replacement_source == "qualification"
        assert authority.reserve_ordinal == 2
        assert authority.replacement_player_id == "E"
        assert authority.qualification_section_id == original_q_section.section_id
        assert authority.qualification_physical_slot_index == original_q_slot.slot_index
        assert authority.qualification_backfill_player_id == "F"
        assert authority.qualification_backfill_ordinal == 1

        assert revision.schema_version == "tournament_draw_revision.v7"
        assert revision.affected_draw_types == ("main", "qualification")
        assert revision.main_repair_action == "frozen_wild_card_fill"
        assert revision.qualification_repair_action == "frozen_rwc_q_backfill"
        assert revision.successor_draw_input.schema_version == (
            "tournament_draw_input_authority.v4"
        )
        assert revision.successor_draw_input.wild_card_player_ids == ("E",)
        assert revision.successor_draw_input.qualification_player_ids == ("D", "F")
        assert revision.successor_draw_input.withdrawn_player_ids == ("B",)

        promoted_slot = next(
            slot for slot in revision.successor_draw.main.slots
            if slot.player_id == "E"
        )
        assert promoted_slot.slot_index == original_wc_slot.slot_index
        assert promoted_slot.entry_status == "wild_card"
        assert promoted_slot.seed_number is None

        backfill_section = next(
            bracket
            for bracket in revision.successor_draw.qualification_brackets
            if bracket.section_id == original_q_section.section_id
        )
        backfill_slot = backfill_section.slots[original_q_slot.slot_index - 1]
        assert backfill_slot.player_id == "F"
        assert backfill_slot.seed_number is None
        assert backfill_slot.slot_index == original_q_slot.slot_index

        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)
        assert store.draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-q-promote",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=3,
        ) == revision

        saved_after = capture(session)
        restore_saved_simulation_slots(
            session,
            current_payload=saved_after,
            target_payload=saved_before,
            run_id="run",
            branch_id="branch",
        )
        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == ()

        recaptured = capture(session)
        restore_saved_simulation_slots(
            session,
            current_payload=recaptured,
            target_payload=saved_after,
            run_id="run",
            branch_id="branch",
        )
        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)



@pytest.mark.pr_critical
def test_frozen_seeded_wc_repair_vacates_seed_instead_of_inheriting_it(database):
    with database.begin() as session:
        initial, draw_input, wc = install_frozen_seeded_wc_main(session)
        assert draw_input.wild_card_player_ids == ("B",)
        assert draw_input.main_seed_player_ids == ("A", "B")
        seeded_wc_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "B"
        )
        assert seeded_wc_slot.entry_status == "wild_card"
        assert seeded_wc_slot.seed_number == 2

        saved_before = capture(session)
        store = TournamentDrawRevisionStore(session)
        revision = store.draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="seeded-wc-to-rwc",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
        )

        authority = revision.wild_card_repair_authority
        assert authority is not None
        assert authority.schema_version == "tournament_post_draw_wild_card_repair.v3"
        assert authority.replacement_source == "external_reserve"
        assert authority.vacated_main_seed_number == 2
        assert authority.vacated_qualification_seed_number is None
        assert authority.replacement_player_id == "E"

        assert revision.successor_draw_input.schema_version == (
            "tournament_draw_input_authority.v5"
        )
        assert revision.successor_draw_input.main_seed_count == 2
        assert revision.successor_draw_input.main_seed_player_ids == ("A",)
        assert revision.successor_draw_input.main_seed_vacancy_numbers == (2,)
        assert revision.successor_draw_input.wild_card_player_ids == ("E",)

        replacement = next(
            slot for slot in revision.successor_draw.main.slots
            if slot.player_id == "E"
        )
        assert replacement.slot_index == seeded_wc_slot.slot_index
        assert replacement.entry_status == "wild_card"
        assert replacement.seed_number is None
        assert replacement.is_seed_protected is False
        assert revision.successor_draw.main.seed_positions == ((1, initial.main.seed_positions[0][1]),)

        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)

        saved_after = capture(session)
        restore_saved_simulation_slots(
            session,
            current_payload=saved_after,
            target_payload=saved_before,
            run_id="run",
            branch_id="branch",
        )
        recaptured = capture(session)
        restore_saved_simulation_slots(
            session,
            current_payload=recaptured,
            target_payload=saved_after,
            run_id="run",
            branch_id="branch",
        )
        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


@pytest.mark.pr_critical
def test_frozen_seeded_q_rwc_vacates_q_seed_and_backfills_same_slot(database):
    with database.begin() as session:
        install_ranking_authority(session)
        TournamentEntryFieldStore(session).stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=standard_applications(),
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=4,
                qualification_draw_size=2,
                qualifier_spots=1,
                wild_card_slots=1,
            ),
            command_id="seeded-q-rwc-field",
        )
        TournamentWildCardAuthorityStore(session).resolve(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="seeded-q-rwc-resolve",
            original_wild_card_player_ids=("A",),
            reserve_wild_card_player_ids=("B", "D", "F"),
        )
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="seeded-q-rwc-input",
            draw_seed=556677,
        )
        initial = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="seeded-q-rwc-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="seeded-q-rwc-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )

        assert draw_input.wild_card_player_ids == ("B",)
        assert draw_input.qualification_player_ids == ("D", "E")
        assert draw_input.qualification_seed_player_ids == ("D",)
        q_bracket = initial.qualification_brackets[0]
        seeded_q_slot = next(slot for slot in q_bracket.slots if slot.player_id == "D")
        assert seeded_q_slot.seed_number == 1
        wc_slot = next(slot for slot in initial.main.slots if slot.player_id == "B")

        store = TournamentDrawRevisionStore(session)
        revision = store.draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="seeded-q-rwc-promote",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=3,
        )

        authority = revision.wild_card_repair_authority
        assert authority is not None
        assert authority.schema_version == "tournament_post_draw_wild_card_repair.v3"
        assert authority.replacement_source == "qualification"
        assert authority.replacement_player_id == "D"
        assert authority.vacated_main_seed_number is None
        assert authority.vacated_qualification_seed_number == 1
        assert authority.qualification_backfill_player_id == "F"

        assert revision.successor_draw_input.schema_version == (
            "tournament_draw_input_authority.v5"
        )
        assert revision.successor_draw_input.wild_card_player_ids == ("D",)
        assert revision.successor_draw_input.qualification_player_ids == ("E", "F")
        assert revision.successor_draw_input.qualification_seed_count == 1
        assert revision.successor_draw_input.qualification_seed_player_ids == ()
        assert revision.successor_draw_input.qualification_seed_vacancy_numbers == (1,)

        promoted = next(
            slot for slot in revision.successor_draw.main.slots
            if slot.player_id == "D"
        )
        assert promoted.slot_index == wc_slot.slot_index
        assert promoted.entry_status == "wild_card"
        assert promoted.seed_number is None

        repaired_q = revision.successor_draw.qualification_brackets[0]
        backfill = repaired_q.slots[seeded_q_slot.slot_index - 1]
        assert backfill.player_id == "F"
        assert backfill.seed_number is None
        assert repaired_q.seed_positions == ()
        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


def _install_unseeded_q_rwc_case(session):
    install_ranking_authority(session)
    TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id="event",
        applications=standard_applications(),
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=2,
            qualifier_spots=1,
            wild_card_slots=1,
        ),
        command_id="phase-q-rwc-field",
    )
    wc = TournamentWildCardAuthorityStore(session).resolve(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="phase-q-rwc-resolve",
        original_wild_card_player_ids=("A",),
        reserve_wild_card_player_ids=("B", "E", "F"),
    )
    draw_input = TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="phase-q-rwc-input",
        draw_seed=313131,
    )
    initial = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="phase-q-rwc-draw",
    )
    TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="phase-q-rwc-process",
        main_process_window_count=3,
        qualification_process_window_count=3,
    )
    assert draw_input.wild_card_player_ids == ("B",)
    assert draw_input.qualification_player_ids == ("D", "E")
    assert draw_input.qualification_seed_player_ids == ("D",)
    assert wc.adjusted_below_qualification_cut_player_ids == ("F", "G")
    return initial


@pytest.mark.pr_critical
def test_q_rwc_before_redraw_cutoff_redraws_q_but_keeps_exact_main_wc_slot(database):
    with database.begin() as session:
        initial = _install_unseeded_q_rwc_case(session)
        original_wc_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "B"
        )
        store = TournamentDrawRevisionStore(session)

        with pytest.raises(
            TournamentDrawRevisionConflict,
            match="full redraw requires repair draw seed",
        ):
            store.draw_frozen_wild_card_withdrawal(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="q-rwc-redraw-missing-seed",
                withdrawn_player_id="B",
                main_process_window_ordinal=3,
                qualification_process_window_ordinal=1,
            )

        revision = store.draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="q-rwc-redraw",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=1,
            repair_draw_seed=424242,
        )

        assert revision.schema_version == "tournament_draw_revision.v8"
        assert revision.main_repair_action == "frozen_wild_card_fill"
        assert revision.qualification_repair_action == "full_redraw"
        assert revision.repair_draw_seed == 424242
        authority = revision.wild_card_repair_authority
        assert authority is not None
        assert authority.replacement_source == "qualification"
        assert authority.replacement_player_id == "E"
        assert authority.qualification_backfill_player_id == "F"
        assert authority.vacated_qualification_seed_number is None

        promoted = next(
            slot for slot in revision.successor_draw.main.slots
            if slot.player_id == "E"
        )
        assert promoted.slot_index == original_wc_slot.slot_index
        assert promoted.entry_status == "wild_card"
        assert promoted.seed_number is None

        assert revision.successor_draw_input.qualification_player_ids == ("D", "F")
        q_players = {
            slot.player_id
            for bracket in revision.successor_draw.qualification_brackets
            for slot in bracket.slots
            if slot.player_id is not None
        }
        assert q_players == {"D", "F"}
        assert tuple(
            bracket.section_id
            for bracket in revision.successor_draw.qualification_brackets
        ) == tuple(
            bracket.section_id for bracket in initial.qualification_brackets
        )
        assert store.draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="q-rwc-redraw",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=1,
            repair_draw_seed=424242,
        ) == revision
        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


@pytest.mark.pr_critical
def test_q_rwc_middle_phase_directly_backfills_unseeded_q_slot(database):
    with database.begin() as session:
        initial = _install_unseeded_q_rwc_case(session)
        original_wc_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "B"
        )
        q_section = initial.qualification_brackets[0]
        original_q_slot = next(
            slot for slot in q_section.slots if slot.player_id == "E"
        )
        assert original_q_slot.seed_number is None

        store = TournamentDrawRevisionStore(session)
        with pytest.raises(
            TournamentDrawRevisionConflict,
            match="outside full redraw cannot use draw seed",
        ):
            store.draw_frozen_wild_card_withdrawal(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="q-rwc-middle-with-seed",
                withdrawn_player_id="B",
                main_process_window_ordinal=3,
                qualification_process_window_ordinal=2,
                repair_draw_seed=999,
            )

        revision = store.draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="q-rwc-middle-direct",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=2,
        )

        assert revision.schema_version == "tournament_draw_revision.v8"
        assert revision.main_repair_action == "frozen_wild_card_fill"
        assert revision.qualification_repair_action == "direct_slot_fill"
        assert revision.repair_draw_seed is None
        assert revision.successor_draw_input.qualification_seed_player_ids == ("D",)

        promoted = next(
            slot for slot in revision.successor_draw.main.slots
            if slot.player_id == "E"
        )
        assert promoted.slot_index == original_wc_slot.slot_index
        assert promoted.entry_status == "wild_card"

        repaired_q = revision.successor_draw.qualification_brackets[0]
        backfill = repaired_q.slots[original_q_slot.slot_index - 1]
        assert backfill.player_id == "F"
        assert backfill.seed_number is None
        seeded = next(slot for slot in repaired_q.slots if slot.player_id == "D")
        assert seeded.seed_number == 1
        assert seeded.slot_index == next(
            slot.slot_index for slot in q_section.slots if slot.player_id == "D"
        )
        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


def _install_seeded_q_rwc_pre_freeze_case(session):
    install_ranking_authority(session)
    TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id="event",
        applications=standard_applications(),
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=2,
            qualifier_spots=1,
            wild_card_slots=1,
        ),
        command_id="seeded-phase-q-rwc-field",
    )
    wc = TournamentWildCardAuthorityStore(session).resolve(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seeded-phase-q-rwc-resolve",
        original_wild_card_player_ids=("A",),
        reserve_wild_card_player_ids=("B", "D", "F"),
    )
    draw_input = TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seeded-phase-q-rwc-input",
        draw_seed=717171,
    )
    initial = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seeded-phase-q-rwc-draw",
    )
    TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="seeded-phase-q-rwc-process",
        main_process_window_count=3,
        qualification_process_window_count=3,
    )
    assert draw_input.wild_card_player_ids == ("B",)
    assert draw_input.qualification_player_ids == ("D", "E")
    assert draw_input.qualification_seed_player_ids == ("D",)
    assert wc.adjusted_below_qualification_cut_player_ids == ("F", "G")
    return initial


@pytest.mark.pr_critical
def test_seeded_q_rwc_before_cutoff_full_redraw_reseeds_new_q_field(database):
    with database.begin() as session:
        initial = _install_seeded_q_rwc_pre_freeze_case(session)
        original_wc_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "B"
        )
        store = TournamentDrawRevisionStore(session)

        revision = store.draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="seeded-q-rwc-full-redraw",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=1,
            repair_draw_seed=818181,
        )

        authority = revision.wild_card_repair_authority
        assert authority is not None
        assert authority.schema_version == "tournament_post_draw_wild_card_repair.v3"
        assert authority.replacement_source == "qualification"
        assert authority.replacement_player_id == "D"
        assert authority.vacated_qualification_seed_number == 1
        assert authority.qualification_backfill_player_id == "F"

        assert revision.schema_version == "tournament_draw_revision.v8"
        assert revision.qualification_repair_action == "full_redraw"
        assert revision.repair_draw_seed == 818181
        assert revision.successor_draw_input.qualification_player_ids == ("E", "F")
        assert revision.successor_draw_input.qualification_seed_player_ids == ("E",)
        assert revision.successor_draw_input.qualification_seed_vacancy_numbers == ()

        promoted = next(
            slot for slot in revision.successor_draw.main.slots
            if slot.player_id == "D"
        )
        assert promoted.slot_index == original_wc_slot.slot_index
        assert promoted.entry_status == "wild_card"
        assert promoted.seed_number is None

        q_slots = {
            slot.player_id: slot
            for bracket in revision.successor_draw.qualification_brackets
            for slot in bracket.slots
            if slot.player_id is not None
        }
        assert set(q_slots) == {"E", "F"}
        assert q_slots["E"].seed_number == 1
        assert q_slots["F"].seed_number is None

        assert store.draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="seeded-q-rwc-full-redraw",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=1,
            repair_draw_seed=818181,
        ) == revision
        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


@pytest.mark.pr_critical
def test_seeded_q_rwc_middle_phase_runs_seed_cascade_without_seed_inheritance(database):
    with database.begin() as session:
        initial = _install_seeded_q_rwc_pre_freeze_case(session)
        original_wc_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "B"
        )
        q_bracket = initial.qualification_brackets[0]
        seeded_d = next(slot for slot in q_bracket.slots if slot.player_id == "D")
        unseeded_e = next(slot for slot in q_bracket.slots if slot.player_id == "E")
        assert seeded_d.seed_number == 1
        assert unseeded_e.seed_number is None

        saved_before = capture(session)
        store = TournamentDrawRevisionStore(session)
        revision = store.draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="seeded-q-rwc-cascade",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=2,
        )

        authority = revision.wild_card_repair_authority
        assert authority is not None
        assert authority.replacement_player_id == "D"
        assert authority.vacated_qualification_seed_number == 1
        assert authority.qualification_backfill_player_id == "F"

        assert revision.schema_version == "tournament_draw_revision.v8"
        assert revision.qualification_repair_action == "seed_cascade"
        assert revision.repair_draw_seed is None
        assert revision.successor_draw_input.qualification_player_ids == ("E", "F")
        assert revision.successor_draw_input.qualification_seed_player_ids == ()
        assert revision.successor_draw_input.qualification_seed_vacancy_numbers == (1,)

        promoted = next(
            slot for slot in revision.successor_draw.main.slots
            if slot.player_id == "D"
        )
        assert promoted.slot_index == original_wc_slot.slot_index
        assert promoted.entry_status == "wild_card"
        assert promoted.seed_number is None

        repaired_q = revision.successor_draw.qualification_brackets[0]
        e_after = next(slot for slot in repaired_q.slots if slot.player_id == "E")
        f_after = next(slot for slot in repaired_q.slots if slot.player_id == "F")
        assert e_after.slot_index == seeded_d.slot_index
        assert e_after.seed_number is None
        assert f_after.slot_index == unseeded_e.slot_index
        assert f_after.seed_number is None
        assert repaired_q.seed_positions == ()

        saved_after = capture(session)
        restore_saved_simulation_slots(
            session,
            current_payload=saved_after,
            target_payload=saved_before,
            run_id="run",
            branch_id="branch",
        )
        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == ()

        recaptured = capture(session)
        restore_saved_simulation_slots(
            session,
            current_payload=recaptured,
            target_payload=saved_after,
            run_id="run",
            branch_id="branch",
        )
        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)

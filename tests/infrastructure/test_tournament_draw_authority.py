"""Canonical Run-owned Tournament Draw authority regression coverage."""

from __future__ import annotations

from types import SimpleNamespace

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
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.domain.tournaments.replacement_cutoff_authority import (
    TournamentPlayedMatchCutoffEvidence,
    TournamentPlayerReplacementCutoffAuthorityBuilder,
)
from beta_engine.domain.tournaments.replacement_source_authority import (
    TournamentDrawStartEvidence,
    TournamentReplacementSourceAuthority,
    TournamentReplacementSourceAuthorityBuilder,
)
from beta_engine.domain.tournaments.lucky_loser_authority import (
    TournamentLuckyLoserOrderAuthorityBuilder,
    TournamentLuckyLoserQualificationMatchEvidence,
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
    SimulationEventGroupModel,
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
from beta_engine.infrastructure.db.tournament_replacement_cutoff_authority import (
    TournamentPlayerReplacementCutoffAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_wild_card_authority import (
    TournamentWildCardAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_lucky_loser_authority import (
    TournamentLuckyLoserOrderAuthorityStore,
    TournamentLuckyLoserOrderUnavailable,
)
from beta_engine.infrastructure.db.tournament_replacement_source_authority import (
    TournamentReplacementSourceAuthorityStore,
)
from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
)
from beta_engine.application.canonical_tournament_topology import (
    project_canonical_draw_to_match_topology,
)
from beta_engine.application.run_owned_match_package import (
    build_run_owned_match_package,
)
from beta_engine.application.authoritative_frozen_main_replacement import (
    AuthoritativeFrozenMainReplacement,
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


@pytest.mark.parametrize(
    ("entrant_count", "expected_capacity", "expected_byes"),
    (
        (2, 2, 0),
        (3, 4, 1),
        (5, 8, 3),
        (13, 16, 3),
        (28, 32, 4),
        (33, 64, 31),
    ),
)
def test_main_entrant_count_derives_classic_capacity(
    entrant_count,
    expected_capacity,
    expected_byes,
):
    capacity = TournamentEntryFieldCapacity.for_main_entrant_count(
        main_entrant_count=entrant_count,
    )

    assert capacity.main_draw_size == expected_capacity
    assert capacity.bye_slots == expected_byes
    assert capacity.direct_main_slots == entrant_count


def test_thirteen_player_main_draw_generates_with_three_byes(database):
    player_ids = tuple(f"P{index:02d}" for index in range(1, 14))
    applications = tuple(app(player_id, "main") for player_id in player_ids)

    with database.begin() as session:
        install_ranking_authority(session, player_ids)
        capacity = TournamentEntryFieldCapacity.for_main_entrant_count(
            main_entrant_count=len(player_ids),
        )
        TournamentEntryFieldStore(session).stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=applications,
            capacity=capacity,
            command_id="initial-arbitrary-field",
        )
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="commit-arbitrary-draw-input",
            draw_seed=13013,
            main_seed_count=4,
            qualification_seed_count=0,
        )
        draw = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="generate-arbitrary-draw",
        )

    assert draw.draw_input_fingerprint == draw_input.fingerprint
    assert draw.main.bracket_size == 16
    assert len(draw.main.nodes) == 15
    assert len(draw.main.bye_slot_indexes) == 3
    assert sum(slot.entrant_kind == "player" for slot in draw.main.slots) == 13
    assert {item.code for item in draw.main_bracket_diagnostics} == {
        "odd_main_entrant_count"
    }
    assert "main_bracket_diagnostics" not in draw.model_dump(mode="json")


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


def install_seed_cascade_multi_q(session, *, q_player_count=25):
    main_ids = tuple(f"M{index:02d}" for index in range(1, 6))
    q_ids = tuple(
        f"Q{index:02d}" for index in range(1, q_player_count + 1)
    )
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


@pytest.mark.pr_critical
def test_seed_cascade_seeded_q_without_backfill_terminates_in_bye(database):
    with database.begin() as session:
        initial = install_seed_cascade_multi_q(
            session,
            q_player_count=24,
        )
        before = {
            slot.player_id: (bracket.section_id, slot)
            for bracket in initial.qualification_brackets
            for slot in bracket.slots
            if slot.player_id is not None
        }
        withdrawn_section_id, withdrawn_slot = before["Q01"]
        assert withdrawn_slot.seed_number is not None

        revision = TournamentDrawRevisionStore(
            session
        ).seed_cascade_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="q-seed-cascade-no-backfill",
            withdrawn_player_ids=("Q01",),
            qualification_process_window_ordinal=2,
        )

        assert revision.repair_kind == "seed_cascade_phase"
        assert revision.affected_draw_types == ("qualification",)
        assert revision.qualification_repair_action == "seed_cascade"
        assert revision.main_repair_action is None
        assert revision.successor_draw.main == initial.main
        assert len(revision.successor_draw_input.qualification_player_ids) == 23
        assert "Q01" not in revision.successor_draw_input.qualification_player_ids

        after_players = {
            slot.player_id
            for bracket in revision.successor_draw.qualification_brackets
            for slot in bracket.slots
            if slot.player_id is not None
        }
        assert after_players == set(
            revision.successor_draw_input.qualification_player_ids
        )

        before_byes = sum(
            len(bracket.bye_slot_indexes)
            for bracket in initial.qualification_brackets
        )
        after_byes = sum(
            len(bracket.bye_slot_indexes)
            for bracket in revision.successor_draw.qualification_brackets
        )
        assert after_byes == before_byes + 1

        repaired_section = next(
            bracket
            for bracket in revision.successor_draw.qualification_brackets
            if bracket.section_id == withdrawn_section_id
        )
        repaired_original_seed_slot = repaired_section.slots[
            withdrawn_slot.slot_index - 1
        ]
        assert repaired_original_seed_slot.entrant_kind == "player"
        assert repaired_original_seed_slot.player_id is not None

        new_bye_refs = {
            (bracket.section_id, slot_index)
            for bracket in revision.successor_draw.qualification_brackets
            for slot_index in bracket.bye_slot_indexes
        } - {
            (bracket.section_id, slot_index)
            for bracket in initial.qualification_brackets
            for slot_index in bracket.bye_slot_indexes
        }
        assert len(new_bye_refs) == 1
        assert (
            withdrawn_section_id,
            withdrawn_slot.slot_index,
        ) not in new_bye_refs

        assert TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


@pytest.mark.pr_critical
def test_seed_cascade_unseeded_main_without_backfill_keeps_bye_in_vacated_slot(
    database,
):
    with database.begin() as session:
        initial = install_seed_cascade_main(session, player_count=32)
        before = draw_player_slots(initial.main)
        withdrawn = before["P20"]
        assert withdrawn.seed_number is None

        revision = TournamentDrawRevisionStore(
            session
        ).seed_cascade_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="main-unseeded-no-backfill",
            withdrawn_player_ids=("P20",),
            main_process_window_ordinal=2,
        )

        assert revision.main_repair_action == "direct_slot_fill"
        slot = revision.successor_draw.main.slots[
            withdrawn.slot_index - 1
        ]
        assert slot.entrant_kind == "bye"
        assert slot.player_id is None
        assert slot.seed_number is None
        assert withdrawn.slot_index in (
            revision.successor_draw.main.bye_slot_indexes
        )
        assert len(revision.successor_draw_input.direct_main_player_ids) == 31

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


@pytest.mark.pr_critical
def test_multi_q_successor_draw_reprojects_into_executable_topology_after_repair(
    database,
):
    with database.begin() as session:
        initial = install_seed_cascade_multi_q(session)

        revision = TournamentDrawRevisionStore(
            session
        ).draw_frozen_phase_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="multi-q-reproject-after-repair",
            withdrawn_player_ids=("M01",),
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=2,
        )

        assert revision.main_repair_action == "frozen_slot_fill"
        assert revision.qualification_repair_action == "seed_cascade"
        assert tuple(
            section.section_id
            for section in revision.successor_draw.qualification_brackets
        ) == ("Q1", "Q2", "Q3")

        active = TournamentDrawAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        )
        assert active == revision.successor_draw
        assert active != initial

        event = CalendarEvent(
            event_id="event",
            season="2000/2001",
            season_week=1,
            calendar_year=2000,
            year_week=1,
            template_id="template",
            event_name="Repair Open",
            category="TEST",
            tour_level="WORLD_TOUR",
            host_country="CZE",
            region="Europe",
            main_draw_size=8,
            qualification_draw_size=24,
            qualifier_spots=3,
        )
        package = build_run_owned_match_package(
            draw=active,
            event=event,
            week=RankingWeek(season_index=0, week=1),
        )
        topology = project_canonical_draw_to_match_topology(
            draw=active,
            package=package,
        )

        assert len(topology.qualifier_promotions) == 3
        assert {
            promotion.qualifier_index
            for promotion in topology.qualifier_promotions
        } == {1, 2, 3}
        assert topology.terminal_group_id in {
            plan.group_id for plan in topology.plans
        }

        executable_ids = {plan.group_id for plan in topology.plans}
        for plan in topology.plans:
            for source in plan.participant_sources or ():
                if source.startswith("winner:"):
                    assert source.removeprefix("winner:") in executable_ids

        # The promoted Q player now owns the exact vacated Main slot, while Q
        # remains independently executable after its seed-cascade repair.
        main_players = {
            slot.player_id
            for slot in active.main.slots
            if slot.player_id is not None
        }
        assert "M01" not in main_players
        assert "Q01" in main_players

        q_players = {
            slot.player_id
            for bracket in active.qualification_brackets
            for slot in bracket.slots
            if slot.player_id is not None
        }
        assert "Q01" not in q_players
        assert "Q25" in q_players
        assert len(q_players) == 24


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


def _install_ll_vacancy_case(session):
    draw_input = install_draw_input(session)
    initial = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="ll-initial-draw",
    )
    TournamentDrawProcessAuthorityStore(session).configure(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="ll-process",
        main_process_window_count=3,
        qualification_process_window_count=3,
    )
    assert len(draw_input.qualification_player_ids) == 2
    return initial, draw_input


def _mock_cutoff_resolution(monkeypatch, *, q_player_ids, qualification_started):
    q_player_ids = tuple(q_player_ids)
    q_set = set(q_player_ids)

    def resolve_many(
        self,
        *,
        run_id,
        branch_id,
        event_id,
        player_ids,
    ):
        out = []
        for player_id in sorted(set(player_ids)):
            played = ()
            if (
                qualification_started
                and player_id in q_set
                and player_id == q_player_ids[0]
            ):
                played = (
                    TournamentPlayedMatchCutoffEvidence(
                        match_id="q-start-match",
                        week_ordinal=0,
                        slot_id="q-start-slot",
                        slot_ordinal=1,
                        group_id="q-start-group",
                        result_fingerprint="a" * 64,
                        opponent_player_id=q_player_ids[1],
                        outcome="loss",
                    ),
                )
            out.append(
                TournamentPlayerReplacementCutoffAuthorityBuilder.build(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                    player_id=player_id,
                    played_matches=played,
                )
            )
        return tuple(out)

    monkeypatch.setattr(
        TournamentPlayerReplacementCutoffAuthorityStore,
        "resolve_many",
        resolve_many,
    )


@pytest.mark.pr_critical
def test_frozen_main_vacancies_create_ll1_then_ll2_by_vacancy_chronology(
    database,
    monkeypatch,
):
    with database.begin() as session:
        initial, draw_input = _install_ll_vacancy_case(session)
        _mock_cutoff_resolution(
            monkeypatch,
            q_player_ids=draw_input.qualification_player_ids,
            qualification_started=True,
        )
        original_c = next(
            slot for slot in initial.main.slots if slot.player_id == "C"
        )
        original_d = next(
            slot for slot in initial.main.slots if slot.player_id == "D"
        )
        store = TournamentDrawRevisionStore(session)

        saved_before = capture(session)
        first = store.draw_frozen_lucky_loser_vacancy(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="create-ll1",
            withdrawn_player_id="C",
            main_process_window_ordinal=3,
        )
        assert first.schema_version == "tournament_draw_revision.v9"
        assert first.repair_kind == "lucky_loser_vacancy"
        assert first.main_repair_action == "frozen_lucky_loser_slot"
        assert first.lucky_loser_vacancy_authority is not None
        assert first.lucky_loser_vacancy_authority.lucky_loser_ordinal == 1
        assert first.lucky_loser_vacancy_authority.placeholder_id == "LL1"
        assert (
            first.lucky_loser_vacancy_authority
            .qualification_start_authority
            .played_matches[0]
            .match_id
            == "q-start-match"
        )
        ll1 = first.successor_draw.main.slots[original_c.slot_index - 1]
        assert ll1.entrant_kind == "lucky_loser_placeholder"
        assert ll1.placeholder_id == "LL1"
        assert ll1.player_id is None
        assert ll1.seed_number is None
        assert first.successor_draw_input.schema_version == (
            "tournament_draw_input_authority.v6"
        )
        assert first.successor_draw_input.lucky_loser_placeholder_ids == ("LL1",)
        assert "C" not in first.successor_draw_input.direct_main_player_ids

        second = store.draw_frozen_lucky_loser_vacancy(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="create-ll2",
            withdrawn_player_id="D",
            main_process_window_ordinal=3,
        )
        assert second.lucky_loser_vacancy_authority is not None
        assert second.lucky_loser_vacancy_authority.lucky_loser_ordinal == 2
        assert second.lucky_loser_vacancy_authority.placeholder_id == "LL2"
        ll2 = second.successor_draw.main.slots[original_d.slot_index - 1]
        assert ll2.entrant_kind == "lucky_loser_placeholder"
        assert ll2.placeholder_id == "LL2"
        assert second.successor_draw_input.lucky_loser_placeholder_ids == (
            "LL1",
            "LL2",
        )
        # Draw Input stores LL chronology; bracket metadata is physical-slot ordered.
        assert second.successor_draw_input.lucky_loser_placeholder_ids == (
            "LL1",
            "LL2",
        )
        assert {
            "LL1": original_c.slot_index,
            "LL2": original_d.slot_index,
        } == dict(second.successor_draw.main.lucky_loser_placeholder_slots)

        assert store.draw_frozen_lucky_loser_vacancy(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="create-ll1",
            withdrawn_player_id="C",
            main_process_window_ordinal=3,
        ) == first

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
        ) == (first, second)


@pytest.mark.pr_critical
def test_lucky_loser_vacancy_does_not_exist_before_qualification_starts(
    database,
    monkeypatch,
):
    with database.begin() as session:
        _, draw_input = _install_ll_vacancy_case(session)
        _mock_cutoff_resolution(
            monkeypatch,
            q_player_ids=draw_input.qualification_player_ids,
            qualification_started=False,
        )
        with pytest.raises(
            TournamentDrawRevisionConflict,
            match="does not exist before Qualification starts",
        ):
            TournamentDrawRevisionStore(session).draw_frozen_lucky_loser_vacancy(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="too-early-ll",
                withdrawn_player_id="C",
                main_process_window_ordinal=3,
            )


def _install_four_player_q_for_ll_order(session):
    install_ranking_authority(session)
    TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id="event",
        applications=standard_applications(),
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=4,
            qualifier_spots=1,
        ),
        command_id="ll-order-field",
    )
    draw_input = TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="ll-order-input",
        draw_seed=919191,
    )
    draw = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="ll-order-draw",
    )
    return draw_input, draw


def _fake_q_receipts(session, monkeypatch, draw, *, include_final):
    bracket = draw.qualification_brackets[0]
    slots = {slot.slot_index: slot.player_id for slot in bracket.slots}
    round_one = sorted(
        [node for node in bracket.nodes if node.round_number == 1],
        key=lambda node: node.round_sequence,
    )
    final = max(
        bracket.nodes,
        key=lambda node: (node.round_number, node.round_sequence),
    )

    results = {}
    semifinal_winners = []
    for index, node in enumerate(round_one, start=1):
        top = slots[int(node.source_top.removeprefix("slot:"))]
        bottom = slots[int(node.source_bottom.removeprefix("slot:"))]
        assert top is not None and bottom is not None
        # Alternate winner side so the fixture does not accidentally encode ranking.
        winner, loser = (top, bottom) if index == 1 else (bottom, top)
        semifinal_winners.append(winner)
        results[node.node_id] = (winner, loser)

    final_winner, final_loser = semifinal_winners
    results[final.node_id] = (final_winner, final_loser)

    selected_ids = {
        node.node_id for node in round_one
    }
    if include_final:
        selected_ids.add(final.node_id)

    for ordinal, match_id in enumerate(sorted(selected_ids), start=1):
        session.add(
            SimulationEventGroupModel(
                run_id="run",
                branch_id="branch",
                week_ordinal=0,
                slot_id="ll-order-slot",
                group_id=f"ll-order-group-{ordinal}",
                command_fingerprint=(f"{ordinal:x}" * 64)[:64],
                match_id=match_id,
                match_input_fingerprint=(f"{ordinal + 8:x}" * 64)[:64],
                result_fingerprint=(f"{ordinal + 4:x}" * 64)[:64],
                payload_json="{}",
            )
        )
    session.flush()

    def fake_load(row):
        winner, loser = results[row.match_id]
        return SimpleNamespace(
            authoritative_input=SimpleNamespace(event_id="event"),
            result=SimpleNamespace(
                match_id=row.match_id,
                winner_player_id=winner,
                loser_player_id=loser,
            ),
        )

    monkeypatch.setattr(
        AuthoritativeSlotMatchExecutor,
        "_load_group",
        staticmethod(fake_load),
    )
    return results, final


def _install_mixed_auto_bye_q_for_ll_order(session):
    players = ("A", "B", "C", "D", "E")
    install_ranking_authority(session, players)
    TournamentEntryFieldStore(session).stage_initial(
        run_id="run",
        branch_id="branch",
        event_id="event",
        applications=(
            app("A", "main"),
            app("C", "main"),
            app("B", "qualification"),
            app("D", "qualification"),
            app("E", "qualification"),
        ),
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=4,
            qualifier_spots=2,
        ),
        command_id="ll-auto-bye-field",
    )
    draw_input = TournamentDrawInputAuthorityStore(session).commit(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="ll-auto-bye-input",
        draw_seed=818181,
    )
    draw = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="ll-auto-bye-draw",
    )
    counts = tuple(
        sum(slot.player_id is not None for slot in bracket.slots)
        for bracket in draw.qualification_brackets
    )
    assert sorted(counts) == [1, 2]
    return draw_input, draw


def _fake_single_real_q_terminal(session, monkeypatch, draw):
    real_bracket = next(
        bracket
        for bracket in draw.qualification_brackets
        if sum(slot.player_id is not None for slot in bracket.slots) == 2
    )
    terminal = max(
        real_bracket.nodes,
        key=lambda node: (node.round_number, node.round_sequence),
    )
    players = [
        slot.player_id
        for slot in real_bracket.slots
        if slot.player_id is not None
    ]
    assert len(players) == 2
    winner, loser = players

    session.add(
        SimulationEventGroupModel(
            run_id="run",
            branch_id="branch",
            week_ordinal=0,
            slot_id="ll-auto-bye-slot",
            group_id="ll-auto-bye-real-terminal",
            command_fingerprint="a" * 64,
            match_id=terminal.node_id,
            match_input_fingerprint="b" * 64,
            result_fingerprint="c" * 64,
            payload_json="{}",
        )
    )
    session.flush()

    def fake_load(row):
        assert row.match_id == terminal.node_id
        return SimpleNamespace(
            authoritative_input=SimpleNamespace(event_id="event"),
            result=SimpleNamespace(
                match_id=row.match_id,
                winner_player_id=winner,
                loser_player_id=loser,
            ),
        )

    monkeypatch.setattr(
        AuthoritativeSlotMatchExecutor,
        "_load_group",
        staticmethod(fake_load),
    )
    return real_bracket, terminal, winner, loser


@pytest.mark.pr_critical
def test_withdrawn_q_winner_turns_exact_linked_main_slot_into_next_lucky_loser(
    database,
    monkeypatch,
):
    with database.begin() as session:
        draw_input, initial = _install_mixed_auto_bye_q_for_ll_order(session)
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="q-winner-ll-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )
        real_bracket, terminal, q_winner, q_loser = _fake_single_real_q_terminal(
            session,
            monkeypatch,
            initial,
        )
        _mock_cutoff_resolution(
            monkeypatch,
            q_player_ids=draw_input.qualification_player_ids,
            qualification_started=True,
        )

        original_resolve = TournamentPlayerReplacementCutoffAuthorityStore.resolve

        def component_resolve(
            self,
            *,
            run_id,
            branch_id,
            event_id,
            player_id,
            draw_type=None,
        ):
            if player_id == q_winner and draw_type == "main":
                return TournamentPlayerReplacementCutoffAuthorityBuilder.build(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                    player_id=player_id,
                    played_matches=(),
                    draw_type="main",
                )
            return original_resolve(
                self,
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                player_id=player_id,
                draw_type=draw_type,
            )

        monkeypatch.setattr(
            TournamentPlayerReplacementCutoffAuthorityStore,
            "resolve",
            component_resolve,
        )

        section_id = real_bracket.section_id
        assert section_id is not None
        original_q_slot = next(
            slot
            for slot in initial.main.slots
            if slot.entrant_kind == "qualifier_placeholder"
            and slot.placeholder_id == section_id
        )
        untouched_q_slots = {
            slot.placeholder_id: slot.slot_index
            for slot in initial.main.slots
            if slot.entrant_kind == "qualifier_placeholder"
            and slot.placeholder_id != section_id
        }

        store = TournamentDrawRevisionStore(session)
        vacancy = store.draw_frozen_lucky_loser_vacancy(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="q-winner-to-ll1",
            withdrawn_player_id=q_winner,
            main_process_window_ordinal=3,
        )

        authority = vacancy.lucky_loser_vacancy_authority
        assert authority is not None
        assert authority.schema_version == "tournament_lucky_loser_vacancy.v2"
        assert authority.placeholder_id == "LL1"
        assert authority.physical_slot_index == original_q_slot.slot_index
        assert authority.vacated_main_seed_number is None
        assert authority.withdrawn_player_cutoff_authority.schema_version == (
            "tournament_player_replacement_cutoff.v2"
        )
        assert authority.withdrawn_player_cutoff_authority.draw_type == "main"
        assert authority.withdrawn_player_cutoff_authority.status == "replacement_open"

        evidence = authority.qualification_winner_evidence
        assert evidence is not None
        assert evidence.section_id == section_id
        assert evidence.terminal_match_id == terminal.node_id
        assert evidence.winner_player_id == q_winner
        assert evidence.evidence_kind == "played_terminal"

        repaired = vacancy.successor_draw.main.slots[original_q_slot.slot_index - 1]
        assert repaired.entrant_kind == "lucky_loser_placeholder"
        assert repaired.placeholder_id == "LL1"
        assert repaired.player_id is None
        assert repaired.seed_number is None
        assert section_id not in dict(
            vacancy.successor_draw.main.qualifier_placeholder_slots
        )
        assert untouched_q_slots.items() <= dict(
            vacancy.successor_draw.main.qualifier_placeholder_slots
        ).items()
        assert dict(vacancy.successor_draw.main.lucky_loser_placeholder_slots) == {
            "LL1": original_q_slot.slot_index
        }

        # Historical Q field remains frozen; only its linked active Main Q slot
        # has become the chronological LL vacancy.
        assert vacancy.successor_draw_input.qualification_player_ids == (
            draw_input.qualification_player_ids
        )
        assert vacancy.successor_draw_input.qualifier_placeholder_ids == (
            draw_input.qualifier_placeholder_ids
        )
        assert q_winner not in vacancy.successor_draw_input.withdrawn_player_ids

        fill = store.fill_next_frozen_lucky_loser(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="fill-q-winner-ll1",
            main_process_window_ordinal=3,
        )
        filled = fill.successor_draw.main.slots[original_q_slot.slot_index - 1]
        assert filled.entrant_kind == "player"
        assert filled.player_id == q_loser
        assert filled.entry_status == "lucky_loser"
        assert filled.lucky_loser_placeholder_id == "LL1"
        assert filled.seed_number is None


@pytest.mark.pr_critical
def test_lucky_loser_order_accepts_mixed_auto_bye_terminal(
    database,
    monkeypatch,
):
    with database.begin() as session:
        _, draw = _install_mixed_auto_bye_q_for_ll_order(session)
        real_bracket, terminal, _, loser = _fake_single_real_q_terminal(
            session,
            monkeypatch,
            draw,
        )

        authority = TournamentLuckyLoserOrderAuthorityStore(session).resolve(
            run_id="run",
            branch_id="branch",
            event_id="event",
        )

        auto_bracket = next(
            bracket
            for bracket in draw.qualification_brackets
            if bracket is not real_bracket
            and sum(slot.player_id is not None for slot in bracket.slots) == 1
        )
        auto_terminal = max(
            auto_bracket.nodes,
            key=lambda node: (node.round_number, node.round_sequence),
        )
        auto_winner = next(
            slot.player_id
            for slot in auto_bracket.slots
            if slot.player_id is not None
        )

        assert authority.schema_version == "tournament_lucky_loser_order.v2"
        assert set(authority.qualification_terminal_match_ids) == {
            terminal.node_id,
            auto_terminal.node_id,
        }
        assert len(authority.qualification_terminal_result_fingerprints) == 2
        assert len(authority.qualification_auto_bye_terminals) == 1
        auto = authority.qualification_auto_bye_terminals[0]
        assert auto.match_id == auto_terminal.node_id
        assert auto.section_id == auto_bracket.section_id
        assert auto.winner_player_id == auto_winner
        assert auto.qualification_bracket_fingerprint == auto_bracket.fingerprint
        assert authority.ordered_player_ids == (loser,)
        assert authority.candidates[0].elimination_match_id == terminal.node_id
        assert authority.candidates[0].qualification_round_reached == 1


@pytest.mark.pr_critical
def test_lucky_loser_order_auto_bye_does_not_mask_unresolved_real_terminal(
    database,
):
    with database.begin() as session:
        _, draw = _install_mixed_auto_bye_q_for_ll_order(session)
        assert any(
            sum(slot.player_id is not None for slot in bracket.slots) == 1
            for bracket in draw.qualification_brackets
        )

        with pytest.raises(
            TournamentLuckyLoserOrderUnavailable,
            match="until Qualification is complete",
        ):
            TournamentLuckyLoserOrderAuthorityStore(session).resolve(
                run_id="run",
                branch_id="branch",
                event_id="event",
            )


@pytest.mark.pr_critical
def test_lucky_loser_order_all_auto_bye_sections_can_complete_without_candidates(
    database,
):
    with database.begin() as session:
        players = ("A", "B", "C", "D")
        install_ranking_authority(session, players)
        TournamentEntryFieldStore(session).stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=(
                app("A", "main"),
                app("C", "main"),
                app("B", "qualification"),
                app("D", "qualification"),
            ),
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=4,
                qualification_draw_size=4,
                qualifier_spots=2,
            ),
            command_id="ll-all-auto-bye-field",
        )
        TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="ll-all-auto-bye-input",
            draw_seed=828282,
        )
        draw = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="ll-all-auto-bye-draw",
        )
        assert all(
            sum(slot.player_id is not None for slot in bracket.slots) == 1
            for bracket in draw.qualification_brackets
        )

        authority = TournamentLuckyLoserOrderAuthorityStore(session).resolve(
            run_id="run",
            branch_id="branch",
            event_id="event",
        )

        assert authority.schema_version == "tournament_lucky_loser_order.v2"
        assert len(authority.qualification_auto_bye_terminals) == 2
        assert authority.candidates == ()
        assert authority.ordered_player_ids == ()
        assert len(authority.qualification_terminal_match_ids) == 2
        assert len(authority.qualification_terminal_result_fingerprints) == 2


@pytest.mark.pr_critical
def test_lucky_loser_order_prefers_q_round_then_frozen_tournament_ranking(
    database,
    monkeypatch,
):
    with database.begin() as session:
        _, draw = _install_four_player_q_for_ll_order(session)
        results, final = _fake_q_receipts(
            session,
            monkeypatch,
            draw,
            include_final=True,
        )
        authority = TournamentLuckyLoserOrderAuthorityStore(session).resolve(
            run_id="run",
            branch_id="branch",
            event_id="event",
        )

        final_loser = results[final.node_id][1]
        semifinal_losers = [
            results[node.node_id][1]
            for node in draw.qualification_brackets[0].nodes
            if node.round_number == 1
        ]
        ranking = TournamentRankingSnapshotAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        )
        assert ranking is not None
        rank_by_player = {
            row.player_id: row.rank for row in ranking.ranking_snapshot.rows
        }
        expected_semifinal_order = sorted(
            semifinal_losers,
            key=lambda player_id: rank_by_player[player_id],
        )

        assert authority.schema_version == "tournament_lucky_loser_order.v1"
        assert authority.ordered_player_ids == (
            final_loser,
            *expected_semifinal_order,
        )
        assert authority.candidates[0].qualification_round_reached == 2
        assert tuple(
            candidate.qualification_round_reached
            for candidate in authority.candidates[1:]
        ) == (1, 1)
        assert tuple(
            candidate.tournament_ranking for candidate in authority.candidates[1:]
        ) == tuple(
            sorted(rank_by_player[player_id] for player_id in semifinal_losers)
        )
        assert authority.qualification_terminal_match_ids == (final.node_id,)


@pytest.mark.pr_critical
def test_lucky_loser_order_waits_for_completed_qualification_terminal(
    database,
    monkeypatch,
):
    with database.begin() as session:
        _, draw = _install_four_player_q_for_ll_order(session)
        _fake_q_receipts(
            session,
            monkeypatch,
            draw,
            include_final=False,
        )
        with pytest.raises(
            TournamentLuckyLoserOrderUnavailable,
            match="until Qualification is complete",
        ):
            TournamentLuckyLoserOrderAuthorityStore(session).resolve(
                run_id="run",
                branch_id="branch",
                event_id="event",
            )


@pytest.mark.pr_critical
def test_multi_q_lucky_loser_order_is_global_and_fills_exact_main_vacancy(
    database,
    monkeypatch,
):
    with database.begin() as session:
        player_ids = tuple(chr(ord("A") + index) for index in range(12))
        direct_main_ids = player_ids[:4]
        qualification_ids = player_ids[4:]

        ranking_authority = install_ranking_authority(session, player_ids)
        TournamentEntryFieldStore(session).stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=tuple(
                app(
                    player_id,
                    "main" if player_id in direct_main_ids else "qualification",
                )
                for player_id in player_ids
            ),
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=8,
                qualification_draw_size=8,
                qualifier_spots=4,
            ),
            command_id="multi-q-ll-field",
        )
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="multi-q-ll-input",
            draw_seed=989898,
        )
        initial = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="multi-q-ll-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="multi-q-ll-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )

        assert tuple(
            bracket.section_id for bracket in initial.qualification_brackets
        ) == ("Q1", "Q2", "Q3", "Q4")
        assert all(
            len(bracket.nodes) == 1
            for bracket in initial.qualification_brackets
        )

        results = {}
        losers = []
        for ordinal, bracket in enumerate(initial.qualification_brackets, start=1):
            terminal = bracket.nodes[0]
            section_players = [
                slot.player_id
                for slot in bracket.slots
                if slot.player_id is not None
            ]
            assert len(section_players) == 2
            winner, loser = section_players
            losers.append(loser)
            results[terminal.node_id] = (winner, loser)
            session.add(
                SimulationEventGroupModel(
                    run_id="run",
                    branch_id="branch",
                    week_ordinal=0,
                    slot_id="multi-q-ll-slot",
                    group_id=f"multi-q-ll-group-{ordinal}",
                    command_fingerprint=(f"{ordinal:x}" * 64)[:64],
                    match_id=terminal.node_id,
                    match_input_fingerprint=(f"{ordinal + 8:x}" * 64)[:64],
                    result_fingerprint=(f"{ordinal + 4:x}" * 64)[:64],
                    payload_json="{}",
                )
            )
        session.flush()

        def fake_load(row):
            winner, loser = results[row.match_id]
            return SimpleNamespace(
                authoritative_input=SimpleNamespace(event_id="event"),
                result=SimpleNamespace(
                    match_id=row.match_id,
                    winner_player_id=winner,
                    loser_player_id=loser,
                ),
            )

        monkeypatch.setattr(
            AuthoritativeSlotMatchExecutor,
            "_load_group",
            staticmethod(fake_load),
        )
        _mock_cutoff_resolution(
            monkeypatch,
            q_player_ids=draw_input.qualification_player_ids,
            qualification_started=True,
        )

        rank_by_player = {
            row.player_id: row.rank
            for row in ranking_authority.ranking_snapshot.rows
        }
        expected_order = tuple(
            sorted(losers, key=lambda player_id: rank_by_player[player_id])
        )

        order = TournamentLuckyLoserOrderAuthorityStore(session).resolve(
            run_id="run",
            branch_id="branch",
            event_id="event",
        )
        assert order.ordered_player_ids == expected_order
        assert tuple(
            candidate.qualification_round_reached
            for candidate in order.candidates
        ) == (1, 1, 1, 1)
        assert {
            candidate.elimination_match_id
            for candidate in order.candidates
        } == {
            bracket.nodes[0].node_id
            for bracket in initial.qualification_brackets
        }

        withdrawn = direct_main_ids[0]
        withdrawn_slot = next(
            slot.slot_index
            for slot in initial.main.slots
            if slot.player_id == withdrawn
        )
        store = TournamentDrawRevisionStore(session)
        vacancy = store.draw_frozen_lucky_loser_vacancy(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="multi-q-ll-vacancy",
            withdrawn_player_id=withdrawn,
            main_process_window_ordinal=3,
        )
        assert vacancy.lucky_loser_vacancy_authority is not None
        assert vacancy.lucky_loser_vacancy_authority.placeholder_id == "LL1"

        fill = store.fill_next_frozen_lucky_loser(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="multi-q-ll-fill",
            main_process_window_ordinal=3,
        )
        authority = fill.lucky_loser_fill_authority
        assert authority is not None
        assert authority.placeholder_id == "LL1"
        assert authority.order_authority.ordered_player_ids == expected_order
        assert authority.selected_candidate.player_id == expected_order[0]
        assert authority.selected_candidate.priority_ordinal == 1
        assert authority.skipped_candidate_player_ids == ()
        assert authority.prior_assigned_player_ids == ()

        filled_slot = fill.successor_draw.main.slots[withdrawn_slot - 1]
        assert filled_slot.slot_index == withdrawn_slot
        assert filled_slot.entrant_kind == "player"
        assert filled_slot.player_id == expected_order[0]
        assert filled_slot.entry_status == "lucky_loser"
        assert filled_slot.seed_number is None
        assert filled_slot.placeholder_id is None
        assert filled_slot.lucky_loser_placeholder_id == "LL1"

        assert fill.successor_draw_input.lucky_loser_player_ids == (
            expected_order[0],
        )
        assert fill.successor_draw.main.lucky_loser_placeholder_slots == ()


@pytest.mark.pr_critical
def test_lucky_loser_fill_skips_unavailable_then_prior_assigned_without_reordering(
    database,
    monkeypatch,
):
    with database.begin() as session:
        draw_input, initial = _install_four_player_q_for_ll_order(session)
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="ll-fill-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )
        _fake_q_receipts(
            session,
            monkeypatch,
            initial,
            include_final=True,
        )
        _mock_cutoff_resolution(
            monkeypatch,
            q_player_ids=draw_input.qualification_player_ids,
            qualification_started=True,
        )

        direct_main = draw_input.direct_main_player_ids
        assert len(direct_main) >= 2
        original_slots = {
            player_id: next(
                slot.slot_index
                for slot in initial.main.slots
                if slot.player_id == player_id
            )
            for player_id in direct_main[:2]
        }

        store = TournamentDrawRevisionStore(session)
        first_vacancy = store.draw_frozen_lucky_loser_vacancy(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="ll-fill-vacancy-1",
            withdrawn_player_id=direct_main[0],
            main_process_window_ordinal=3,
        )
        second_vacancy = store.draw_frozen_lucky_loser_vacancy(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="ll-fill-vacancy-2",
            withdrawn_player_id=direct_main[1],
            main_process_window_ordinal=3,
        )
        assert second_vacancy.successor_draw_input.lucky_loser_placeholder_ids == (
            "LL1",
            "LL2",
        )

        order = TournamentLuckyLoserOrderAuthorityStore(session).resolve_for_draw(
            run_id="run",
            branch_id="branch",
            event_id="event",
            draw=second_vacancy.successor_draw,
        )
        assert len(order.ordered_player_ids) >= 3
        unavailable = (order.ordered_player_ids[0],)

        first_fill = store.fill_next_frozen_lucky_loser(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="fill-ll1",
            main_process_window_ordinal=3,
            unavailable_player_ids=unavailable,
        )
        first_authority = first_fill.lucky_loser_fill_authority
        assert first_authority is not None
        assert first_authority.placeholder_id == "LL1"
        assert first_authority.selected_candidate.player_id == (
            order.ordered_player_ids[1]
        )
        assert first_authority.selected_candidate.priority_ordinal == 2
        assert first_authority.skipped_candidate_player_ids == unavailable
        assert first_authority.prior_assigned_player_ids == ()
        assert first_fill.schema_version == "tournament_draw_revision.v10"
        assert first_fill.successor_draw_input.schema_version == (
            "tournament_draw_input_authority.v7"
        )
        assert first_fill.successor_draw_input.lucky_loser_player_ids == (
            order.ordered_player_ids[1],
        )

        ll1 = next(
            slot
            for slot in first_fill.successor_draw.main.slots
            if slot.lucky_loser_placeholder_id == "LL1"
        )
        assert ll1.slot_index == original_slots[direct_main[0]]
        assert ll1.entrant_kind == "player"
        assert ll1.player_id == order.ordered_player_ids[1]
        assert ll1.entry_status == "lucky_loser"
        assert ll1.seed_number is None
        assert ll1.placeholder_id is None

        second_fill = store.fill_next_frozen_lucky_loser(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="fill-ll2",
            main_process_window_ordinal=3,
            unavailable_player_ids=unavailable,
        )
        second_authority = second_fill.lucky_loser_fill_authority
        assert second_authority is not None
        assert second_authority.placeholder_id == "LL2"
        assert second_authority.order_authority == first_authority.order_authority
        assert second_authority.prior_assigned_player_ids == (
            order.ordered_player_ids[1],
        )
        assert second_authority.skipped_candidate_player_ids == (
            order.ordered_player_ids[0],
            order.ordered_player_ids[1],
        )
        assert second_authority.selected_candidate.player_id == (
            order.ordered_player_ids[2]
        )
        assert second_authority.selected_candidate.priority_ordinal == 3
        assert second_fill.successor_draw_input.lucky_loser_player_ids == (
            order.ordered_player_ids[1],
            order.ordered_player_ids[2],
        )

        ll2 = next(
            slot
            for slot in second_fill.successor_draw.main.slots
            if slot.lucky_loser_placeholder_id == "LL2"
        )
        assert ll2.slot_index == original_slots[direct_main[1]]
        assert ll2.player_id == order.ordered_player_ids[2]
        assert ll2.entry_status == "lucky_loser"
        assert ll2.seed_number is None
        assert second_fill.successor_draw.main.lucky_loser_placeholder_slots == ()

        assert store.fill_next_frozen_lucky_loser(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="fill-ll1",
            main_process_window_ordinal=3,
            unavailable_player_ids=unavailable,
        ) == first_fill

        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (
            first_vacancy,
            second_vacancy,
            first_fill,
            second_fill,
        )


@pytest.mark.pr_critical
def test_lucky_loser_fill_fails_closed_when_candidate_pool_is_exhausted(
    database,
    monkeypatch,
):
    with database.begin() as session:
        draw_input, initial = _install_four_player_q_for_ll_order(session)
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="ll-exhaust-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )
        _fake_q_receipts(
            session,
            monkeypatch,
            initial,
            include_final=True,
        )
        _mock_cutoff_resolution(
            monkeypatch,
            q_player_ids=draw_input.qualification_player_ids,
            qualification_started=True,
        )
        store = TournamentDrawRevisionStore(session)
        store.draw_frozen_lucky_loser_vacancy(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="ll-exhaust-vacancy",
            withdrawn_player_id=draw_input.direct_main_player_ids[0],
            main_process_window_ordinal=3,
        )
        current = TournamentDrawAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="event",
        )
        assert current is not None
        order = TournamentLuckyLoserOrderAuthorityStore(session).resolve_for_draw(
            run_id="run",
            branch_id="branch",
            event_id="event",
            draw=current,
        )

        with pytest.raises(
            TournamentDrawRevisionConflict,
            match="external reserve fallback required",
        ):
            store.fill_next_frozen_lucky_loser(
                run_id="run",
                branch_id="branch",
                event_id="event",
                command_id="ll-exhausted",
                main_process_window_ordinal=3,
                unavailable_player_ids=order.ordered_player_ids,
            )


def _source_chain_fixture(session):
    draw_input = install_draw_input(session)
    draw = TournamentDrawAuthorityStore(session).generate(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="source-chain-draw",
    )
    cutoff = TournamentPlayerReplacementCutoffAuthorityBuilder.build(
        run_id="run",
        branch_id="branch",
        event_id="event",
        player_id="C",
        played_matches=(),
    )
    ranking = TournamentRankingSnapshotAuthorityStore(session).get(
        run_id="run",
        branch_id="branch",
        event_id="event",
    )
    assert ranking is not None
    q = draw.qualification_brackets[0]
    terminal = max(
        q.nodes,
        key=lambda node: (node.round_number, node.round_sequence),
    )
    ll_order = TournamentLuckyLoserOrderAuthorityBuilder.build(
        draw=draw,
        tournament_ranking_authority=ranking,
        completed_qualification_matches=(
            TournamentLuckyLoserQualificationMatchEvidence(
                match_id=terminal.node_id,
                section_id=q.section_id or "Q1",
                round_number=terminal.round_number,
                winner_player_id="B",
                loser_player_id="E",
                result_fingerprint="1" * 64,
            ),
        ),
    )
    q_start = TournamentDrawStartEvidence(
        match_id=terminal.node_id,
        result_fingerprint="1" * 64,
    )
    return draw_input, draw, cutoff, ll_order, q_start


@pytest.mark.pr_critical
def test_replacement_source_chain_pre_q_uses_q_list_then_post_q_uses_ll_and_reserves(
    database,
):
    with database.begin() as session:
        draw_input, draw, cutoff, ll_order, q_start = _source_chain_fixture(session)

        pre_q = TournamentReplacementSourceAuthorityBuilder.build(
            predecessor=draw,
            predecessor_draw_input=draw_input,
            withdrawn_player_id="C",
            replacement_cutoff_authority=cutoff,
            qualification_start_evidence=None,
            main_start_evidence=None,
            base_wild_card_authority=None,
            lucky_loser_order_authority=None,
            external_reserve_player_ids=("F", "G"),
        )
        assert pre_q.source == "qualification_promotion"
        assert pre_q.selected_player_id == "B"
        assert pre_q.source_ordinal == 1

        q_running = TournamentReplacementSourceAuthorityBuilder.build(
            predecessor=draw,
            predecessor_draw_input=draw_input,
            withdrawn_player_id="C",
            replacement_cutoff_authority=cutoff,
            qualification_start_evidence=q_start,
            main_start_evidence=None,
            base_wild_card_authority=None,
            lucky_loser_order_authority=None,
            external_reserve_player_ids=("F", "G"),
        )
        assert q_running.source == "lucky_loser_pending"
        assert q_running.selected_player_id is None

        post_q = TournamentReplacementSourceAuthorityBuilder.build(
            predecessor=draw,
            predecessor_draw_input=draw_input,
            withdrawn_player_id="C",
            replacement_cutoff_authority=cutoff,
            qualification_start_evidence=q_start,
            main_start_evidence=None,
            base_wild_card_authority=None,
            lucky_loser_order_authority=ll_order,
            external_reserve_player_ids=("F", "G"),
        )
        assert post_q.source == "lucky_loser"
        assert post_q.selected_player_id == "E"
        assert post_q.source_ordinal == 1
        assert post_q.lucky_loser_order_authority == ll_order

        after_ll_exhaustion = TournamentReplacementSourceAuthorityBuilder.build(
            predecessor=draw,
            predecessor_draw_input=draw_input,
            withdrawn_player_id="C",
            replacement_cutoff_authority=cutoff,
            qualification_start_evidence=q_start,
            main_start_evidence=None,
            base_wild_card_authority=None,
            lucky_loser_order_authority=ll_order,
            external_reserve_player_ids=("B", "F", "G"),
            unavailable_player_ids=("E",),
        )
        assert after_ll_exhaustion.source == "external_reserve"
        assert after_ll_exhaustion.selected_player_id == "F"
        assert after_ll_exhaustion.source_ordinal == 2

        exhausted_before_main = TournamentReplacementSourceAuthorityBuilder.build(
            predecessor=draw,
            predecessor_draw_input=draw_input,
            withdrawn_player_id="C",
            replacement_cutoff_authority=cutoff,
            qualification_start_evidence=q_start,
            main_start_evidence=None,
            base_wild_card_authority=None,
            lucky_loser_order_authority=ll_order,
            external_reserve_player_ids=("F", "G"),
            unavailable_player_ids=("E", "F", "G"),
        )
        assert exhausted_before_main.source == "bye"
        assert exhausted_before_main.selected_player_id is None


@pytest.mark.pr_critical
def test_replacement_source_chain_wc_rwc_priority_precedes_ordinary_phase_source(
    database,
):
    with database.begin() as session:
        draw, draw_input, wc = install_frozen_external_rwc_main(session)
        cutoff = TournamentPlayerReplacementCutoffAuthorityBuilder.build(
            run_id="run",
            branch_id="branch",
            event_id="event",
            player_id="E",
            played_matches=(),
        )
        source = TournamentReplacementSourceAuthorityBuilder.build(
            predecessor=draw,
            predecessor_draw_input=draw_input,
            withdrawn_player_id="E",
            replacement_cutoff_authority=cutoff,
            qualification_start_evidence=None,
            main_start_evidence=None,
            base_wild_card_authority=wc,
            lucky_loser_order_authority=None,
            external_reserve_player_ids=(),
        )
        assert source.source == "reserve_wild_card"
        assert source.selected_player_id == "F"
        assert source.source_ordinal == 2
        assert source.base_wild_card_authority_fingerprint == wc.fingerprint


@pytest.mark.pr_critical
def test_replacement_source_chain_closed_cutoff_wins_over_all_replacement_sources(
    database,
):
    with database.begin() as session:
        draw_input, draw, _, ll_order, q_start = _source_chain_fixture(session)
        cutoff = TournamentPlayerReplacementCutoffAuthorityBuilder.build(
            run_id="run",
            branch_id="branch",
            event_id="event",
            player_id="C",
            played_matches=(
                TournamentPlayedMatchCutoffEvidence(
                    match_id="main-start",
                    week_ordinal=5,
                    slot_id="main-slot",
                    slot_ordinal=1,
                    group_id="main-group",
                    result_fingerprint="2" * 64,
                    opponent_player_id="A",
                    outcome="win",
                ),
            ),
        )
        source = TournamentReplacementSourceAuthorityBuilder.build(
            predecessor=draw,
            predecessor_draw_input=draw_input,
            withdrawn_player_id="C",
            replacement_cutoff_authority=cutoff,
            qualification_start_evidence=q_start,
            main_start_evidence=TournamentDrawStartEvidence(
                match_id="main-start",
                result_fingerprint="2" * 64,
            ),
            base_wild_card_authority=None,
            lucky_loser_order_authority=ll_order,
            external_reserve_player_ids=("F", "G"),
        )
        assert source.source == "walkover"
        assert source.selected_player_id is None


@pytest.mark.pr_critical
def test_replacement_source_store_resolves_pre_q_promotion_from_persisted_state(
    database,
):
    with database.begin() as session:
        install_draw_input(session)
        TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="source-store-draw",
        )
        source = TournamentReplacementSourceAuthorityStore(session).resolve(
            run_id="run",
            branch_id="branch",
            event_id="event",
            withdrawn_player_id="C",
        )
        assert source.source == "qualification_promotion"
        assert source.selected_player_id == "B"
        assert source.external_reserve_player_ids == ("F", "G")


@pytest.mark.pr_critical
def test_replacement_source_chain_fails_closed_after_main_start_if_no_source_remains(
    database,
):
    with database.begin() as session:
        draw_input, draw, cutoff, ll_order, q_start = _source_chain_fixture(session)
        with pytest.raises(
            ValueError,
            match="policy is not yet explicit",
        ):
            TournamentReplacementSourceAuthorityBuilder.build(
                predecessor=draw,
                predecessor_draw_input=draw_input,
                withdrawn_player_id="C",
                replacement_cutoff_authority=cutoff,
                qualification_start_evidence=q_start,
                main_start_evidence=TournamentDrawStartEvidence(
                    match_id="some-main-match",
                    result_fingerprint="3" * 64,
                ),
                base_wild_card_authority=None,
                lucky_loser_order_authority=ll_order,
                external_reserve_player_ids=("F", "G"),
                unavailable_player_ids=("E", "F", "G"),
            )


@pytest.mark.pr_critical
def test_frozen_ordinary_fallback_late_bye_reprojects_without_dangling_feeder(
    database,
):
    with database.begin() as session:
        draw_input, draw, cutoff, ll_order, q_start = _source_chain_fixture(session)
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="late-bye-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )

        original_slot = next(
            slot for slot in draw.main.slots if slot.player_id == "C"
        )
        source = TournamentReplacementSourceAuthorityBuilder.build(
            predecessor=draw,
            predecessor_draw_input=draw_input,
            withdrawn_player_id="C",
            replacement_cutoff_authority=cutoff,
            qualification_start_evidence=q_start,
            main_start_evidence=None,
            base_wild_card_authority=None,
            lucky_loser_order_authority=ll_order,
            external_reserve_player_ids=("F", "G"),
            unavailable_player_ids=("E", "F", "G"),
        )
        assert source.source == "bye"
        assert source.selected_player_id is None

        revision = TournamentDrawRevisionStore(
            session
        ).apply_frozen_ordinary_fallback(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="late-bye-fallback",
            main_process_window_ordinal=3,
            replacement_source_authority=source,
        )

        assert revision.schema_version == "tournament_draw_revision.v11"
        assert revision.repair_kind == "frozen_ordinary_fallback"
        assert revision.main_repair_action == "frozen_source_bye"

        late_bye_slot = revision.successor_draw.main.slots[
            original_slot.slot_index - 1
        ]
        assert late_bye_slot.slot_index == original_slot.slot_index
        assert late_bye_slot.entrant_kind == "bye"
        assert late_bye_slot.player_id is None
        assert late_bye_slot.seed_number is None

        event = CalendarEvent(
            event_id="event",
            season="2000/2001",
            season_week=1,
            calendar_year=2000,
            year_week=1,
            template_id="template",
            event_name="Late BYE Open",
            category="TEST",
            tour_level="WORLD_TOUR",
            host_country="CZE",
            region="Europe",
            main_draw_size=4,
            qualification_draw_size=4,
            qualifier_spots=1,
        )
        package = build_run_owned_match_package(
            draw=revision.successor_draw,
            event=event,
            week=RankingWeek(season_index=0, week=1),
        )
        topology = project_canonical_draw_to_match_topology(
            draw=revision.successor_draw,
            package=package,
        )

        # 1 Q node + 3 Main nodes exist canonically, but the repaired Main BYE
        # node is non-executable and collapses onto the Q terminal feeder.
        assert len(package.qualification_matches) == 1
        assert len(package.main_draw_matches) == 3
        assert len(topology.bye_match_ids) == 1
        assert len(topology.plans) == 3

        bye_match_id = topology.bye_match_ids[0]
        executable_ids = {plan.group_id for plan in topology.plans}
        assert bye_match_id not in executable_ids
        assert topology.terminal_group_id in executable_ids
        assert len(topology.qualifier_promotions) == 1
        promotion = topology.qualifier_promotions[0]
        assert promotion.target_match_id == bye_match_id

        # The repaired BYE target itself is non-executable. Its downstream path must
        # depend on the Qualification feeder directly, never on winner:<bye-match>.
        assert any(
            f"winner:{promotion.source_match_id}" in (plan.participant_sources or ())
            for plan in topology.plans
        )

        for plan in topology.plans:
            for participant_source in plan.participant_sources or ():
                assert participant_source != f"winner:{bye_match_id}"
                if participant_source.startswith("winner:"):
                    assert (
                        participant_source.removeprefix("winner:")
                        in executable_ids
                    )

        # Canonical result history still owns the BYE node even though the
        # schedule universe correctly omits it.
        projected_bye = next(
            match
            for match in package.main_draw_matches
            if match.match_id == bye_match_id
        )
        assert projected_bye.status == "bye_auto_advance_pending"


@pytest.mark.pr_critical
def test_frozen_ordinary_fallback_external_reserve_fills_exact_main_slot(database):
    with database.begin() as session:
        draw_input, draw, cutoff, ll_order, q_start = _source_chain_fixture(session)
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="fallback-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )
        original_slot = next(
            slot for slot in draw.main.slots if slot.player_id == "C"
        )
        source = TournamentReplacementSourceAuthorityBuilder.build(
            predecessor=draw,
            predecessor_draw_input=draw_input,
            withdrawn_player_id="C",
            replacement_cutoff_authority=cutoff,
            qualification_start_evidence=q_start,
            main_start_evidence=None,
            base_wild_card_authority=None,
            lucky_loser_order_authority=ll_order,
            external_reserve_player_ids=("F", "G"),
            unavailable_player_ids=("E",),
        )
        assert source.source == "external_reserve"
        assert source.selected_player_id == "F"

        store = TournamentDrawRevisionStore(session)
        revision = store.apply_frozen_ordinary_fallback(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="external-fallback",
            main_process_window_ordinal=3,
            replacement_source_authority=source,
        )

        assert revision.schema_version == "tournament_draw_revision.v11"
        assert revision.repair_kind == "frozen_ordinary_fallback"
        assert revision.main_repair_action == "frozen_external_reserve_fill"
        assert revision.replacement_source_authority == source
        assert revision.successor_draw_input.schema_version == (
            "tournament_draw_input_authority.v8"
        )
        assert revision.successor_draw_input.replacement_source_authority_fingerprints == (
            source.fingerprint,
        )
        assert "C" not in revision.successor_draw_input.direct_main_player_ids
        assert revision.successor_draw_input.direct_main_player_ids[-1] == "F"

        replacement = next(
            slot for slot in revision.successor_draw.main.slots
            if slot.player_id == "F"
        )
        assert replacement.slot_index == original_slot.slot_index
        assert replacement.seed_number is None
        assert replacement.entry_status is None
        assert revision.successor_draw.qualification_brackets == draw.qualification_brackets

        assert store.apply_frozen_ordinary_fallback(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="external-fallback",
            main_process_window_ordinal=3,
            replacement_source_authority=source,
        ) == revision
        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


@pytest.mark.pr_critical
def test_frozen_main_replacement_orchestrator_dispatches_pre_q_promotion(database):
    with database.begin() as session:
        install_draw_input(session)
        initial = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="orchestrator-q-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="orchestrator-q-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )
        original_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "C"
        )

        service = AuthoritativeFrozenMainReplacement(session)
        result = service.execute(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="orchestrate-q",
            withdrawn_player_id="C",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=3,
        )
        assert result.source == "qualification_promotion"
        assert result.source_authority is not None
        assert len(result.draw_revisions) == 1
        revision = result.draw_revisions[0]
        assert revision.schema_version == "tournament_draw_revision.v14"
        assert revision.repair_kind == "source_bound_pre_q_promotion"
        assert revision.replacement_source_authority == result.source_authority
        assert revision.successor_draw_input.schema_version == (
            "tournament_draw_input_authority.v8"
        )
        assert (
            revision.successor_draw_input.replacement_source_authority_fingerprints[-1]
            == result.source_authority.fingerprint
        )
        promoted = next(
            slot for slot in revision.successor_draw.main.slots
            if slot.player_id == "B"
        )
        assert promoted.slot_index == original_slot.slot_index
        assert promoted.seed_number is None
        q_players = {
            slot.player_id
            for bracket in revision.successor_draw.qualification_brackets
            for slot in bracket.slots
            if slot.player_id is not None
        }
        assert q_players == {"E", "F"}

        retry = service.execute(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="orchestrate-q",
            withdrawn_player_id="C",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=3,
        )
        assert retry.source == "qualification_promotion"
        assert retry.source_authority == result.source_authority
        assert retry.draw_revisions == result.draw_revisions


@pytest.mark.pr_critical
def test_pre_q_promotion_skips_unavailable_q_source_without_re_resolving(database):
    with database.begin() as session:
        install_draw_input(session)
        initial = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="source-aware-q-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="source-aware-q-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )
        original_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "C"
        )

        result = AuthoritativeFrozenMainReplacement(session).execute(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="source-aware-q",
            withdrawn_player_id="C",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=3,
            unavailable_player_ids=("B",),
        )

        assert result.source == "qualification_promotion"
        source = result.source_authority
        assert source is not None
        assert source.selected_player_id == "E"
        assert source.source_ordinal == 2
        assert source.unavailable_player_ids == ("B",)

        revision = result.draw_revisions[0]
        assert revision.schema_version == "tournament_draw_revision.v14"
        promoted = revision.successor_draw.main.slots[
            original_slot.slot_index - 1
        ]
        assert promoted.player_id == "E"
        assert promoted.entry_status is None
        assert promoted.seed_number is None
        q_players = {
            slot.player_id
            for bracket in revision.successor_draw.qualification_brackets
            for slot in bracket.slots
            if slot.player_id is not None
        }
        assert q_players == {"B", "F"}
        assert revision.replacement_source_authority == source
        assert TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


@pytest.mark.pr_critical
def test_exhausted_wc_pre_q_promotion_releases_wc_and_skips_unavailable_rwc(
    database,
):
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
            command_id="wc-pre-q-field",
        )
        wc = TournamentWildCardAuthorityStore(session).resolve(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-pre-q-resolve",
            original_wild_card_player_ids=("A",),
            reserve_wild_card_player_ids=("B", "E", "F"),
        )
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-pre-q-input",
            draw_seed=424242,
        )
        initial = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-pre-q-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-pre-q-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )
        assert draw_input.wild_card_player_ids == ("B",)
        assert draw_input.qualification_player_ids == ("D", "E")
        assert wc.adjusted_below_qualification_cut_player_ids == ("F", "G")

        original_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "B"
        )
        result = AuthoritativeFrozenMainReplacement(session).execute(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-pre-q-promote",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=3,
            unavailable_player_ids=("F", "E"),
        )

        assert result.source == "qualification_promotion"
        source = result.source_authority
        assert source is not None
        assert source.selected_player_id == "D"
        assert source.unavailable_player_ids == ("E", "F")
        assert source.base_wild_card_authority_fingerprint == wc.fingerprint

        revision = result.draw_revisions[0]
        assert revision.schema_version == "tournament_draw_revision.v14"
        assert revision.repair_kind == "source_bound_pre_q_promotion"
        assert revision.successor_draw_input.schema_version == (
            "tournament_draw_input_authority.v9"
        )
        assert revision.successor_draw_input.wild_card_player_ids == ()
        assert revision.successor_draw_input.released_wild_card_slot_ordinals == (1,)
        assert revision.successor_draw_input.direct_main_player_ids[-1] == "D"
        assert revision.successor_draw_input.replacement_source_authority_fingerprints[-1] == (
            source.fingerprint
        )

        promoted = revision.successor_draw.main.slots[
            original_slot.slot_index - 1
        ]
        assert promoted.player_id == "D"
        assert promoted.entry_status is None
        assert promoted.seed_number is None
        q_players = {
            slot.player_id
            for bracket in revision.successor_draw.qualification_brackets
            for slot in bracket.slots
            if slot.player_id is not None
        }
        assert q_players == {"E", "G"}

        assert TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)

        retry = AuthoritativeFrozenMainReplacement(session).execute(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-pre-q-promote",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=3,
            unavailable_player_ids=("E", "F"),
        )
        assert retry.source == "qualification_promotion"
        assert retry.source_authority == source
        assert retry.draw_revisions == (revision,)


@pytest.mark.pr_critical
def test_source_bound_pre_q_seed_cascade_without_backfill_ends_in_q_bye(
    database,
):
    with database.begin() as session:
        applications = (
            app("A", "main"),
            app("C", "main"),
            app("D", "main"),
            app("B", "qualification"),
            app("E", "qualification"),
        )
        draw_input = install_draw_input(
            session,
            applications=applications,
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=4,
                qualification_draw_size=2,
                qualifier_spots=1,
            ),
            draw_seed=515151,
            main_seed_count=1,
            qualification_seed_count=1,
        )
        initial = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="source-bound-no-q-backfill-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="source-bound-no-q-backfill-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )
        assert draw_input.qualification_player_ids == ("B", "E")

        original_main = next(
            slot for slot in initial.main.slots if slot.player_id == "C"
        )
        original_q_b = next(
            slot
            for bracket in initial.qualification_brackets
            for slot in bracket.slots
            if slot.player_id == "B"
        )
        assert original_q_b.seed_number == 1

        result = AuthoritativeFrozenMainReplacement(session).execute(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="source-bound-no-q-backfill",
            withdrawn_player_id="C",
            main_process_window_ordinal=3,
            qualification_process_window_ordinal=2,
        )

        assert result.source == "qualification_promotion"
        source = result.source_authority
        assert source is not None
        assert source.selected_player_id == "B"
        assert source.external_reserve_player_ids == ()

        revision = result.draw_revisions[0]
        assert revision.schema_version == "tournament_draw_revision.v14"
        assert revision.qualification_repair_action == "seed_cascade"
        promoted = revision.successor_draw.main.slots[
            original_main.slot_index - 1
        ]
        assert promoted.player_id == "B"
        assert promoted.entry_status is None
        assert promoted.seed_number is None

        q_bracket = revision.successor_draw.qualification_brackets[0]
        q_players = {
            slot.player_id
            for slot in q_bracket.slots
            if slot.player_id is not None
        }
        assert q_players == {"E"}
        assert len(q_bracket.bye_slot_indexes) == 1
        q_seed_origin = q_bracket.slots[original_q_b.slot_index - 1]
        assert q_seed_origin.player_id == "E"
        assert q_seed_origin.seed_number is None
        assert q_seed_origin.entrant_kind == "player"

        bye_slot = next(
            slot for slot in q_bracket.slots if slot.entrant_kind == "bye"
        )
        assert bye_slot.slot_index != original_q_b.slot_index
        assert revision.successor_draw_input.qualification_player_ids == ("E",)
        assert revision.successor_draw_input.qualification_seed_vacancy_numbers == (1,)

        assert TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


@pytest.mark.pr_critical
def test_frozen_main_replacement_orchestrator_dispatches_rwc(database):
    with database.begin() as session:
        initial, _, _ = install_frozen_external_rwc_main(session)
        original_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "E"
        )
        service = AuthoritativeFrozenMainReplacement(session)
        result = service.execute(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="orchestrate-rwc",
            withdrawn_player_id="E",
            main_process_window_ordinal=3,
        )
        assert result.source == "reserve_wild_card"
        revision = result.draw_revisions[0]
        replacement = next(
            slot for slot in revision.successor_draw.main.slots
            if slot.player_id == "F"
        )
        assert replacement.slot_index == original_slot.slot_index
        assert replacement.entry_status == "wild_card"


@pytest.mark.pr_critical
def test_frozen_wc_fallback_releases_wc_status_for_external_reserve(database):
    with database.begin() as session:
        initial, draw_input, wc = install_frozen_external_rwc_main(session)
        original_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "E"
        )
        cutoff = TournamentPlayerReplacementCutoffAuthorityBuilder.build(
            run_id="run",
            branch_id="branch",
            event_id="event",
            player_id="E",
            played_matches=(),
        )
        source = TournamentReplacementSourceAuthority(
            run_id="run",
            branch_id="branch",
            event_id="event",
            withdrawn_player_id="E",
            predecessor_draw_fingerprint=initial.fingerprint,
            predecessor_draw_input_fingerprint=draw_input.fingerprint,
            physical_slot_index=original_slot.slot_index,
            source="external_reserve",
            selected_player_id="F",
            source_ordinal=1,
            qualification_start_evidence=TournamentDrawStartEvidence(
                match_id="q-start",
                result_fingerprint="1" * 64,
            ),
            replacement_cutoff_authority=cutoff,
            external_reserve_player_ids=("F", "G"),
            base_wild_card_authority_fingerprint=wc.fingerprint,
        )

        store = TournamentDrawRevisionStore(session)
        revision = store.apply_frozen_ordinary_fallback(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-external-fallback",
            main_process_window_ordinal=3,
            replacement_source_authority=source,
        )

        assert revision.schema_version == "tournament_draw_revision.v12"
        assert revision.successor_draw_input.schema_version == (
            "tournament_draw_input_authority.v9"
        )
        assert revision.successor_draw_input.released_wild_card_slot_ordinals == (1,)
        assert revision.successor_draw_input.wild_card_player_ids == ()
        assert "F" in revision.successor_draw_input.direct_main_player_ids
        assert "E" in revision.successor_draw_input.withdrawn_player_ids

        replacement = revision.successor_draw.main.slots[
            original_slot.slot_index - 1
        ]
        assert replacement.player_id == "F"
        assert replacement.entry_status is None
        assert replacement.seed_number is None
        assert revision.replacement_source_authority == source

        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)


@pytest.mark.pr_critical
def test_frozen_main_replacement_orchestrates_exhausted_wc_to_bye(database):
    with database.begin() as session:
        initial, _, _ = install_frozen_external_rwc_main(session)
        original_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "E"
        )
        service = AuthoritativeFrozenMainReplacement(session)

        result = service.execute(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="orchestrate-wc-bye",
            withdrawn_player_id="E",
            main_process_window_ordinal=3,
            unavailable_player_ids=("F", "G"),
        )

        assert result.source == "bye"
        assert len(result.draw_revisions) == 1
        revision = result.draw_revisions[0]
        assert revision.schema_version == "tournament_draw_revision.v12"
        assert revision.successor_draw_input.schema_version == (
            "tournament_draw_input_authority.v9"
        )
        assert revision.successor_draw_input.wild_card_player_ids == ()
        assert revision.successor_draw_input.released_wild_card_slot_ordinals == (1,)
        assert revision.successor_draw_input.late_bye_count == 1

        slot = revision.successor_draw.main.slots[original_slot.slot_index - 1]
        assert slot.entrant_kind == "bye"
        assert slot.player_id is None
        assert slot.entry_status is None
        assert original_slot.slot_index in revision.successor_draw.main.bye_slot_indexes

        retry = service.execute(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="orchestrate-wc-bye",
            withdrawn_player_id="E",
            main_process_window_ordinal=3,
            unavailable_player_ids=("F", "G"),
        )
        assert retry.source == "bye"
        assert retry.draw_revisions == result.draw_revisions


@pytest.mark.pr_critical
def test_released_first_wc_preserves_second_wc_original_ordinal(database):
    with database.begin() as session:
        player_ids = tuple("ABCDEFGHIJ")
        install_ranking_authority(session, player_ids)
        TournamentEntryFieldStore(session).stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=tuple(app(player_id, "main") for player_id in player_ids),
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=8,
                wild_card_slots=2,
            ),
            command_id="two-wc-field",
        )
        wc = TournamentWildCardAuthorityStore(session).resolve(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="two-wc-resolve",
            original_wild_card_player_ids=("A", "B"),
            reserve_wild_card_player_ids=("G", "H", "I", "J"),
        )
        assert wc.active_wild_card_player_ids == ("G", "H")
        TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="two-wc-input",
            draw_seed=991122,
        )
        TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="two-wc-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="two-wc-process",
            main_process_window_count=3,
        )

        first = AuthoritativeFrozenMainReplacement(session).execute(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="release-wc-one",
            withdrawn_player_id="G",
            main_process_window_ordinal=3,
            unavailable_player_ids=("I", "J"),
        ).draw_revisions[0]
        assert first.schema_version == "tournament_draw_revision.v12"
        assert first.successor_draw_input.wild_card_player_ids == ("H",)
        assert first.successor_draw_input.released_wild_card_slot_ordinals == (1,)

        second = TournamentDrawRevisionStore(
            session
        ).draw_frozen_wild_card_withdrawal(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="repair-second-wc",
            withdrawn_player_id="H",
            main_process_window_ordinal=3,
        )
        authority = second.wild_card_repair_authority
        assert authority is not None
        assert authority.wildcard_index == 2
        assert authority.reserve_ordinal == 3
        assert authority.replacement_player_id == "I"
        assert second.successor_draw_input.schema_version == (
            "tournament_draw_input_authority.v9"
        )
        assert second.successor_draw_input.wild_card_player_ids == ("I",)
        assert second.successor_draw_input.released_wild_card_slot_ordinals == (1,)


@pytest.mark.pr_critical
def test_exhausted_wc_routes_to_source_bound_lucky_loser_vacancy(
    database,
    monkeypatch,
):
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
            command_id="wc-ll-field",
        )
        wc = TournamentWildCardAuthorityStore(session).resolve(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-ll-resolve",
            original_wild_card_player_ids=("A",),
            reserve_wild_card_player_ids=("B", "E", "F"),
        )
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-ll-input",
            draw_seed=31337,
        )
        initial = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-ll-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="wc-ll-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )
        assert draw_input.wild_card_player_ids == ("B",)
        assert draw_input.qualification_player_ids == ("D", "E")

        _mock_cutoff_resolution(
            monkeypatch,
            q_player_ids=draw_input.qualification_player_ids,
            qualification_started=True,
        )
        cutoff = TournamentPlayerReplacementCutoffAuthorityBuilder.build(
            run_id="run",
            branch_id="branch",
            event_id="event",
            player_id="B",
            played_matches=(),
        )
        source = TournamentReplacementSourceAuthorityBuilder.build(
            predecessor=initial,
            predecessor_draw_input=draw_input,
            withdrawn_player_id="B",
            replacement_cutoff_authority=cutoff,
            qualification_start_evidence=TournamentDrawStartEvidence(
                match_id="q-start-match",
                result_fingerprint="a" * 64,
            ),
            main_start_evidence=None,
            base_wild_card_authority=wc,
            lucky_loser_order_authority=None,
            external_reserve_player_ids=(
                wc.adjusted_below_qualification_cut_player_ids
            ),
            unavailable_player_ids=("E", "F"),
        )
        assert source.source == "lucky_loser_pending"
        assert source.base_wild_card_authority_fingerprint == wc.fingerprint

        def resolve_source(self, **kwargs):
            assert kwargs["withdrawn_player_id"] == "B"
            assert kwargs["unavailable_player_ids"] == ("E", "F")
            return source

        monkeypatch.setattr(
            TournamentReplacementSourceAuthorityStore,
            "resolve",
            resolve_source,
        )

        original_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "B"
        )
        service = AuthoritativeFrozenMainReplacement(session)
        result = service.execute(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="orchestrate-wc-ll",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
            unavailable_player_ids=("F", "E"),
        )

        assert result.source == "lucky_loser_pending"
        assert result.source_authority == source
        assert len(result.draw_revisions) == 1
        revision = result.draw_revisions[0]
        assert revision.schema_version == "tournament_draw_revision.v13"
        assert revision.repair_kind == "lucky_loser_vacancy"
        assert revision.replacement_source_authority == source
        assert revision.successor_draw_input.schema_version == (
            "tournament_draw_input_authority.v9"
        )
        assert revision.successor_draw_input.wild_card_player_ids == ()
        assert revision.successor_draw_input.released_wild_card_slot_ordinals == (1,)
        assert revision.successor_draw_input.replacement_source_authority_fingerprints == (
            source.fingerprint,
        )
        assert revision.successor_draw_input.lucky_loser_placeholder_ids == ("LL1",)

        slot = revision.successor_draw.main.slots[original_slot.slot_index - 1]
        assert slot.entrant_kind == "lucky_loser_placeholder"
        assert slot.placeholder_id == "LL1"
        assert slot.player_id is None
        assert slot.entry_status is None
        assert slot.seed_number is None

        assert TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="event",
        ) == (revision,)

        retry = service.execute(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="orchestrate-wc-ll",
            withdrawn_player_id="B",
            main_process_window_ordinal=3,
            unavailable_player_ids=("E", "F"),
        )
        assert retry.source == "lucky_loser_pending"
        assert retry.source_authority == source
        assert retry.draw_revisions == result.draw_revisions


@pytest.mark.pr_critical
def test_frozen_main_replacement_orchestrator_dispatches_source_aware_bye(database):
    with database.begin() as session:
        install_draw_input(session)
        initial = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="orchestrator-bye-draw",
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="orchestrator-bye-process",
            main_process_window_count=3,
            qualification_process_window_count=3,
        )
        original_slot = next(
            slot for slot in initial.main.slots if slot.player_id == "C"
        )
        result = AuthoritativeFrozenMainReplacement(session).execute(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="orchestrate-bye",
            withdrawn_player_id="C",
            main_process_window_ordinal=3,
            unavailable_player_ids=("B", "E", "F", "G"),
        )
        assert result.source == "bye"
        revision = result.draw_revisions[0]
        assert revision.schema_version == "tournament_draw_revision.v11"
        slot = revision.successor_draw.main.slots[original_slot.slot_index - 1]
        assert slot.entrant_kind == "bye"
        assert slot.player_id is None
        assert slot.seed_number is None
        assert revision.successor_draw_input.late_bye_count == 1
        assert original_slot.slot_index in revision.successor_draw.main.bye_slot_indexes


@pytest.mark.pr_critical
def test_pre_q_source_chain_reaches_below_cut_before_post_q_external_reserve(database):
    with database.begin() as session:
        draw_input, draw, cutoff, _, _ = _source_chain_fixture(session)
        source = TournamentReplacementSourceAuthorityBuilder.build(
            predecessor=draw,
            predecessor_draw_input=draw_input,
            withdrawn_player_id="C",
            replacement_cutoff_authority=cutoff,
            qualification_start_evidence=None,
            main_start_evidence=None,
            base_wild_card_authority=None,
            lucky_loser_order_authority=None,
            external_reserve_player_ids=("F", "G"),
            unavailable_player_ids=("B", "E"),
        )
        assert source.source == "qualification_promotion"
        assert source.selected_player_id == "F"
        assert source.source_ordinal == 3

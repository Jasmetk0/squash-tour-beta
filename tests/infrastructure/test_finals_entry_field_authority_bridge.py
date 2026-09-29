"""Persistence bridge from Finals participant selection into shared Entry Field."""

import pytest
from sqlalchemy import delete

from beta_engine.application.finals_race_replacement import (
    FinalsReplacementDecisionCommand,
    FinalsReplacementPreviewCommand,
    WorldTourFinalsReplacementService,
)
from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionConfiguration,
    WorldTourFinalsRaceConfiguration,
    WorldTourFinalsRaceInput,
    WorldTourFinalsRacePlayer,
    calculate_world_tour_finals_race,
    select_world_tour_finals_participants,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.finals_participant_selection import (
    WorldTourFinalsParticipantSelectionStore,
)
from beta_engine.infrastructure.db.finals_race_authority import (
    WorldTourFinalsRaceAuthorityStore,
)
from beta_engine.infrastructure.db.finals_race_replacement import (
    WorldTourFinalsReplacementStore,
)
from beta_engine.infrastructure.db.models import (
    Base,
    RunBranchModel,
    RunContainerModel,
    TournamentDrawAuthorityModel,
    TournamentDrawInputAuthorityModel,
    TournamentEntryFieldVersionModel,
    TournamentFormatAuthorityModel,
    TournamentTopologyAuthorityModel,
    WorldTourFinalsRaceConfigurationModel,
    WorldTourFinalsRaceSnapshotModel,
    WorldTourFinalsParticipantSelectionConfigurationModel,
    WorldTourFinalsParticipantSelectionSnapshotModel,
    WorldTourFinalsEffectiveParticipantStateModel,
    WorldTourFinalsReplacementAuthorityModel,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    capture_saved_simulation_slots,
    restore_saved_simulation_slots,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_process_authority import (
    TournamentDrawProcessAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_revision import (
    TournamentDrawRevisionStore,
)
from beta_engine.infrastructure.db.tournament_format_authority import (
    TournamentFormatAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_topology_authority import (
    TournamentTopologyAuthorityStore,
)
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldConflict,
    TournamentEntryFieldStore,
)


def fp(char: str) -> str:
    return char * 64


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'finals-entry-field.db'}")
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


def install_selection(factory, *, capacity: int = 6, race_population: int | None = None):
    race_config = WorldTourFinalsRaceConfiguration(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        finals_event_id="FINALS",
        eligible_categories=("DIAMOND",),
        best_n=2,
        cutoff_week=RankingWeek(season_index=0, week=10),
        cutoff_official_ranking_fingerprint=fp("a"),
        cutoff_transition_fingerprint=fp("b"),
        calendar_content_fingerprint=fp("c"),
        adopted_by_command_id="configure-finals-race",
    )
    race = calculate_world_tour_finals_race(
        WorldTourFinalsRaceInput(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            cutoff_week=race_config.cutoff_week,
            cutoff_official_ranking_fingerprint=(
                race_config.cutoff_official_ranking_fingerprint
            ),
            eligibility_fingerprint=race_config.eligibility_fingerprint,
            policy_id=race_config.policy_id,
            best_n=race_config.best_n,
            players=tuple(
                WorldTourFinalsRacePlayer(
                    player_id=f"p{index}",
                    tie_break_token=f"token-{index:02d}",
                )
                for index in range(1, (race_population or capacity) + 1)
            ),
            eligible_results=(),
        )
    )
    config = WorldTourFinalsParticipantSelectionConfiguration(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        finals_event_id="FINALS",
        participant_capacity=capacity,
        direct_entry_event_ids=(),
        race_snapshot_fingerprint=race.fingerprint,
        calendar_content_fingerprint=race_config.calendar_content_fingerprint,
        adopted_by_command_id="configure-finals-participants",
    )
    snapshot = select_world_tour_finals_participants(
        configuration=config,
        race_snapshot=race,
        direct_entry_winners=(),
    )
    with factory.begin() as session:
        race_store = WorldTourFinalsRaceAuthorityStore(session)
        race_store.put_configuration(race_config)
        race_store.put_snapshot(race)
        participant_store = WorldTourFinalsParticipantSelectionStore(session)
        participant_store.put_configuration(config)
        participant_store.put_snapshot(snapshot)
    return snapshot

def install_finals_knockout_draw(factory):
    selected = install_selection(factory, capacity=6, race_population=9)
    with factory.begin() as session:
        field = TournamentEntryFieldStore(
            session
        ).stage_initial_from_finals_participant_selection(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            target_season_index=0,
            command_id="build-finals-entry-field",
        )
        TournamentFormatAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="configure-finals-knockout",
            format_kind="knockout",
        )
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="commit-finals-draw-input",
            draw_seed=123,
        )
        draw = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="generate-finals-draw",
        )
        process = TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="configure-finals-draw-process",
            main_process_window_count=5,
        )
    return selected, field, draw_input, draw, process


def preview_and_accept_post_draw_replacement(
    factory,
    *,
    withdrawn_player_id: str,
    main_process_window_ordinal: int,
    repair_draw_seed: int | None,
    command_suffix: str,
):
    service = WorldTourFinalsReplacementService(factory)
    preview = service.preview(
        FinalsReplacementPreviewCommand(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            withdrawn_player_id=withdrawn_player_id,
            withdrawal_reason="injury",
            vacancy_id=f"vacancy-{command_suffix}",
            expected_effective_state_fingerprint=None,
            command_id=f"preview-{command_suffix}",
        )
    )
    effective = service.inspect(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
    )
    assert effective is not None
    accepted = service.decide(
        FinalsReplacementDecisionCommand(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            vacancy_id=f"vacancy-{command_suffix}",
            expected_preview_fingerprint=preview.fingerprint,
            expected_effective_state_fingerprint=effective.fingerprint,
            decision="accept",
            main_process_window_ordinal=main_process_window_ordinal,
            repair_draw_seed=repair_draw_seed,
            command_id=f"accept-{command_suffix}",
        )
    )
    assert accepted.status == "accepted"
    return accepted


@pytest.mark.pr_critical
def test_store_materializes_and_replays_finals_selection_as_shared_entry_field(database):
    selected = install_selection(database, capacity=6)

    with database.begin() as session:
        store = TournamentEntryFieldStore(session)
        field = store.stage_initial_from_finals_participant_selection(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            target_season_index=0,
            command_id="build-finals-entry-field",
        )
        assert field.direct_main_player_ids == tuple(
            player.player_id for player in selected.participants
        )
        assert field.capacity.main_draw_size == 6
        assert field.capacity.geometry_kind == "fixed_participant_field"
        assert field.source_authority_fingerprint == selected.fingerprint

        assert store.history(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == (field,)

        assert store.stage_initial_from_finals_participant_selection(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            target_season_index=0,
            command_id="build-finals-entry-field",
        ) == field


@pytest.mark.pr_critical
def test_finals_entry_field_rejects_generic_withdrawal_and_classic_draw_input(database):
    install_selection(database, capacity=6)

    with database.begin() as session:
        store = TournamentEntryFieldStore(session)
        field = store.stage_initial_from_finals_participant_selection(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            target_season_index=0,
            command_id="build-finals-entry-field",
        )

        with pytest.raises(
            TournamentEntryFieldConflict,
            match="separate Finals replacement authority",
        ):
            store.stage_pre_draw_repair_from_frozen_inputs(
                run_id="run",
                branch_id="branch",
                event_id="FINALS",
                expected_field_fingerprint=field.fingerprint,
                withdrawn_player_ids=("p6",),
                command_id="wrong-generic-withdrawal",
            )

        with pytest.raises(
            ValueError,
            match="configured tournament-format authority",
        ):
            TournamentDrawInputAuthorityStore(session).commit(
                run_id="run",
                branch_id="branch",
                event_id="FINALS",
                command_id="wrong-classic-draw",
                draw_seed=123,
            )

@pytest.mark.pr_critical
def test_finals_pure_knockout_adapts_race_seeding_into_ordinary_draw_pipeline(database):
    selected = install_selection(database, capacity=6)

    with database.begin() as session:
        field = TournamentEntryFieldStore(
            session
        ).stage_initial_from_finals_participant_selection(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            target_season_index=0,
            command_id="build-finals-entry-field",
        )
        format_authority = TournamentFormatAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="configure-finals-knockout",
            format_kind="knockout",
        )

        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="commit-finals-draw-input",
            draw_seed=123,
        )

        race_order = tuple(player.player_id for player in selected.participants)
        assert draw_input.schema_version == "tournament_draw_input_authority.v10"
        assert draw_input.source_kind == "finals_participant_selection"
        assert draw_input.tournament_ranking_authority_fingerprint is None
        assert draw_input.ranking_snapshot_fingerprint is None
        assert draw_input.finals_participant_selection_fingerprint == selected.fingerprint
        assert draw_input.finals_race_snapshot_fingerprint == selected.race_snapshot_fingerprint
        assert (
            draw_input.tournament_format_authority_fingerprint
            == format_authority.fingerprint
        )
        assert draw_input.entry_field_fingerprint == field.fingerprint
        assert draw_input.direct_main_player_ids == race_order
        assert draw_input.capacity.geometry_kind == "classic_bracket"
        assert draw_input.capacity.main_draw_size == 8
        assert draw_input.capacity.bye_slots == 2
        assert draw_input.main_seed_count == 2
        assert draw_input.main_seed_player_ids == race_order[:2]
        assert draw_input.qualification_seed_count == 0

        assert TournamentDrawInputAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == draw_input

        draw = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="generate-finals-draw",
        )
        assert draw.main.bracket_size == 8
        assert len(draw.main.bye_slot_indexes) == 2
        assert {
            slot.seed_number: slot.player_id
            for slot in draw.main.slots
            if slot.seed_number is not None
        } == {1: race_order[0], 2: race_order[1]}

        topology = TournamentTopologyAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="generate-finals-topology",
        )
        assert topology.knockout_draw_fingerprint == draw.fingerprint


@pytest.mark.pr_critical
def test_accepted_finals_race_replacement_updates_entry_field_and_knockout_draw(database):
    selected = install_selection(database, capacity=6, race_population=9)

    with database.begin() as session:
        initial_field = TournamentEntryFieldStore(
            session
        ).stage_initial_from_finals_participant_selection(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            target_season_index=0,
            command_id="build-finals-entry-field",
        )

    service = WorldTourFinalsReplacementService(database)
    preview = service.preview(
        FinalsReplacementPreviewCommand(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            withdrawn_player_id="p3",
            withdrawal_reason="injury",
            vacancy_id="vacancy-p3",
            expected_effective_state_fingerprint=None,
            command_id="preview-p3",
        )
    )
    assert preview.offered_candidate_player_id == "p7"
    initial_effective = service.inspect(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
    )
    assert initial_effective is not None

    declined = service.decide(
        FinalsReplacementDecisionCommand(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            vacancy_id="vacancy-p3",
            expected_preview_fingerprint=preview.fingerprint,
            expected_effective_state_fingerprint=initial_effective.fingerprint,
            decision="decline",
            command_id="decline-p7",
        )
    )
    assert declined.offered_candidate_player_id == "p8"

    accepted = service.decide(
        FinalsReplacementDecisionCommand(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            vacancy_id="vacancy-p3",
            expected_preview_fingerprint=declined.fingerprint,
            expected_effective_state_fingerprint=initial_effective.fingerprint,
            decision="accept",
            command_id="accept-p8",
        )
    )
    assert accepted.status == "accepted"

    effective = service.inspect(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
    )
    assert effective is not None
    assert tuple(player.player_id for player in effective.participants) == (
        "p1",
        "p2",
        "p4",
        "p5",
        "p6",
        "p8",
    )
    assert "p3" in effective.withdrawn_player_ids
    assert tuple(player.player_id for player in selected.participants) == (
        "p1",
        "p2",
        "p3",
        "p4",
        "p5",
        "p6",
    )

    with database.begin() as session:
        field_history = TournamentEntryFieldStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        )
        assert len(field_history) == 2
        replacement_field = field_history[-1]
        assert replacement_field.base_field_fingerprint == initial_field.fingerprint
        assert (
            replacement_field.source_kind
            == "finals_effective_participant_state"
        )
        assert (
            replacement_field.finals_effective_participant_state_fingerprint
            == effective.fingerprint
        )
        assert replacement_field.direct_main_player_ids == (
            "p1",
            "p2",
            "p4",
            "p5",
            "p6",
            "p8",
        )

        format_authority = TournamentFormatAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="configure-finals-knockout-after-replacement",
            format_kind="knockout",
        )
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="commit-finals-replacement-draw-input",
            draw_seed=456,
        )
        assert draw_input.schema_version == "tournament_draw_input_authority.v11"
        assert draw_input.source_kind == "finals_effective_participant_state"
        assert (
            draw_input.finals_effective_participant_state_fingerprint
            == effective.fingerprint
        )
        assert draw_input.finals_participant_selection_fingerprint == selected.fingerprint
        assert draw_input.tournament_ranking_authority_fingerprint is None
        assert draw_input.ranking_snapshot_fingerprint is None
        assert (
            draw_input.tournament_format_authority_fingerprint
            == format_authority.fingerprint
        )
        assert draw_input.direct_main_player_ids == replacement_field.direct_main_player_ids
        assert draw_input.capacity.main_draw_size == 8
        assert draw_input.capacity.bye_slots == 2
        assert draw_input.main_seed_count == 2
        assert draw_input.main_seed_player_ids == ("p1", "p2")

        draw = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="generate-finals-replacement-draw",
        )
        assert draw.main.bracket_size == 8
        assert len(draw.main.bye_slot_indexes) == 2
        assert {
            slot.seed_number: slot.player_id
            for slot in draw.main.slots
            if slot.seed_number is not None
        } == {1: "p1", 2: "p2"}


@pytest.mark.pr_critical
def test_saved_revision_roundtrip_preserves_finals_replacement_draw_chain(database):
    selected = install_selection(database, capacity=6, race_population=9)

    with database.begin() as session:
        TournamentEntryFieldStore(
            session
        ).stage_initial_from_finals_participant_selection(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            target_season_index=0,
            command_id="build-finals-entry-field",
        )

    service = WorldTourFinalsReplacementService(database)
    preview = service.preview(
        FinalsReplacementPreviewCommand(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            withdrawn_player_id="p3",
            withdrawal_reason="injury",
            vacancy_id="vacancy-p3-save",
            command_id="preview-p3-save",
        )
    )
    initial = service.inspect(
        run_id="run", branch_id="branch", target_season_index=0
    )
    assert initial is not None
    declined = service.decide(
        FinalsReplacementDecisionCommand(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            vacancy_id="vacancy-p3-save",
            expected_preview_fingerprint=preview.fingerprint,
            expected_effective_state_fingerprint=initial.fingerprint,
            decision="decline",
            command_id="decline-p7-save",
        )
    )
    service.decide(
        FinalsReplacementDecisionCommand(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            vacancy_id="vacancy-p3-save",
            expected_preview_fingerprint=declined.fingerprint,
            expected_effective_state_fingerprint=initial.fingerprint,
            decision="accept",
            command_id="accept-p8-save",
        )
    )
    effective = service.inspect(
        run_id="run", branch_id="branch", target_season_index=0
    )
    assert effective is not None

    with database.begin() as session:
        format_authority = TournamentFormatAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="configure-finals-save",
            format_kind="knockout",
        )
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="commit-finals-save",
            draw_seed=789,
        )
        draw = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="generate-finals-save",
        )
        field_history = TournamentEntryFieldStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        )
        replacement_history = WorldTourFinalsReplacementStore(
            session
        ).authority_history(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            finals_event_id="FINALS",
            vacancy_id="vacancy-p3-save",
        )

        target_payload = {"content": {}}
        capture_saved_simulation_slots(
            session,
            target_payload,
            run_id="run",
            branch_id="branch",
        )

        session.execute(
            delete(TournamentDrawAuthorityModel).where(
                TournamentDrawAuthorityModel.run_id == "run",
                TournamentDrawAuthorityModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(TournamentDrawInputAuthorityModel).where(
                TournamentDrawInputAuthorityModel.run_id == "run",
                TournamentDrawInputAuthorityModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(TournamentFormatAuthorityModel).where(
                TournamentFormatAuthorityModel.run_id == "run",
                TournamentFormatAuthorityModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(TournamentEntryFieldVersionModel).where(
                TournamentEntryFieldVersionModel.run_id == "run",
                TournamentEntryFieldVersionModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(WorldTourFinalsReplacementAuthorityModel).where(
                WorldTourFinalsReplacementAuthorityModel.run_id == "run",
                WorldTourFinalsReplacementAuthorityModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(WorldTourFinalsEffectiveParticipantStateModel).where(
                WorldTourFinalsEffectiveParticipantStateModel.run_id == "run",
                WorldTourFinalsEffectiveParticipantStateModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(WorldTourFinalsParticipantSelectionSnapshotModel).where(
                WorldTourFinalsParticipantSelectionSnapshotModel.run_id == "run",
                WorldTourFinalsParticipantSelectionSnapshotModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(WorldTourFinalsParticipantSelectionConfigurationModel).where(
                WorldTourFinalsParticipantSelectionConfigurationModel.run_id == "run",
                WorldTourFinalsParticipantSelectionConfigurationModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(WorldTourFinalsRaceSnapshotModel).where(
                WorldTourFinalsRaceSnapshotModel.run_id == "run",
                WorldTourFinalsRaceSnapshotModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(WorldTourFinalsRaceConfigurationModel).where(
                WorldTourFinalsRaceConfigurationModel.run_id == "run",
                WorldTourFinalsRaceConfigurationModel.branch_id == "branch",
            )
        )
        session.flush()

        current_payload = {"content": {}}
        capture_saved_simulation_slots(
            session,
            current_payload,
            run_id="run",
            branch_id="branch",
        )
        restore_saved_simulation_slots(
            session,
            current_payload=current_payload,
            target_payload=target_payload,
            run_id="run",
            branch_id="branch",
        )

        restored_store = WorldTourFinalsReplacementStore(session)
        assert restored_store.latest_state(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
        ) == effective
        assert restored_store.authority_history(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            finals_event_id="FINALS",
            vacancy_id="vacancy-p3-save",
        ) == replacement_history
        assert TournamentEntryFieldStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == field_history
        assert TournamentFormatAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == format_authority
        assert TournamentDrawInputAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == draw_input
        assert TournamentDrawAuthorityStore(session).get_initial(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == draw
        assert (
            TournamentDrawInputAuthorityStore(session)
            .get(run_id="run", branch_id="branch", event_id="FINALS")
            .finals_participant_selection_fingerprint
            == selected.fingerprint
        )


@pytest.mark.pr_critical
def test_finals_post_draw_full_redraw_uses_effective_race_field(database):
    _, _, original_input, original_draw, _ = install_finals_knockout_draw(database)

    preview_and_accept_post_draw_replacement(
        database,
        withdrawn_player_id="p3",
        main_process_window_ordinal=1,
        repair_draw_seed=987654,
        command_suffix="full-redraw",
    )

    with database.begin() as session:
        revision = TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        )[-1]
        assert revision.repair_kind == "full_redraw"
        assert revision.predecessor_draw_fingerprint == original_draw.fingerprint
        assert revision.successor_draw_input.source_kind == (
            "finals_effective_participant_state"
        )
        assert revision.successor_draw_input.fingerprint != original_input.fingerprint
        assert "p3" not in revision.successor_draw_input.direct_main_player_ids
        assert "p7" in revision.successor_draw_input.direct_main_player_ids
        assert revision.successor_draw.draw_input_fingerprint == (
            revision.successor_draw_input.fingerprint
        )
        assert revision.replacement_cutoff_authorities[0].status == "replacement_open"


@pytest.mark.pr_critical
def test_finals_post_draw_seed_cascade_uses_canonical_phase(database):
    install_finals_knockout_draw(database)

    preview_and_accept_post_draw_replacement(
        database,
        withdrawn_player_id="p1",
        main_process_window_ordinal=4,
        repair_draw_seed=None,
        command_suffix="seed-cascade",
    )

    with database.begin() as session:
        revision = TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        )[-1]
        assert revision.repair_kind == "seed_cascade_phase"
        assert revision.main_repair_action is not None
        assert "p1" not in revision.successor_draw_input.direct_main_player_ids
        assert "p7" in revision.successor_draw_input.direct_main_player_ids
        assert revision.repair_draw_seed is None
        assert revision.replacement_cutoff_authorities[0].status == "replacement_open"


@pytest.mark.pr_critical
def test_finals_post_draw_freeze_fills_exact_slot_without_seed_inheritance(database):
    _, _, _, original_draw, _ = install_finals_knockout_draw(database)
    original_slot = next(
        slot for slot in original_draw.main.slots if slot.player_id == "p1"
    )
    assert original_slot.seed_number == 1

    preview_and_accept_post_draw_replacement(
        database,
        withdrawn_player_id="p1",
        main_process_window_ordinal=5,
        repair_draw_seed=None,
        command_suffix="draw-freeze",
    )

    with database.begin() as session:
        revision = TournamentDrawRevisionStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        )[-1]
        assert revision.repair_kind == "draw_frozen_phase"
        replacement_slot = next(
            slot
            for slot in revision.successor_draw.main.slots
            if slot.player_id == "p7"
        )
        assert replacement_slot.slot_index == original_slot.slot_index
        assert replacement_slot.idealized_slot_number == (
            original_slot.idealized_slot_number
        )
        assert replacement_slot.seed_number is None
        assert replacement_slot.is_seed_protected is False
        assert replacement_slot.entry_status is None
        assert revision.repair_draw_seed is None
        assert revision.replacement_cutoff_authorities[0].status == "replacement_open"


@pytest.mark.pr_critical
def test_finals_selection_blocks_generic_ranking_application_entry_creation(database):
    install_selection(database, capacity=6)

    with database.begin() as session:
        store = TournamentEntryFieldStore(session)
        with pytest.raises(
            TournamentEntryFieldConflict,
            match="must materialize the Entry Field from its own frozen authority",
        ):
            store.stage_initial_from_persisted_submissions(
                run_id="run",
                branch_id="branch",
                event_id="FINALS",
                capacity=TournamentEntryFieldCapacity(main_draw_size=8),
                command_id="wrong-ranking-entry-field",
            )


@pytest.mark.pr_critical
def test_saved_revision_restores_complete_finals_authority_chain_and_entry_field(database):
    selected = install_selection(database, capacity=6)
    with database.begin() as session:
        field = TournamentEntryFieldStore(
            session
        ).stage_initial_from_finals_participant_selection(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            target_season_index=0,
            command_id="build-finals-entry-field",
        )
        format_authority = TournamentFormatAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="configure-finals-knockout",
            format_kind="knockout",
        )
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="commit-finals-draw-input",
            draw_seed=123,
        )
        draw = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="generate-finals-draw",
        )
        topology = TournamentTopologyAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="generate-finals-topology",
        )
        target_payload = {"content": {}}
        capture_saved_simulation_slots(
            session,
            target_payload,
            run_id="run",
            branch_id="branch",
        )

        session.execute(
            delete(TournamentTopologyAuthorityModel).where(
                TournamentTopologyAuthorityModel.run_id == "run",
                TournamentTopologyAuthorityModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(TournamentDrawAuthorityModel).where(
                TournamentDrawAuthorityModel.run_id == "run",
                TournamentDrawAuthorityModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(TournamentDrawInputAuthorityModel).where(
                TournamentDrawInputAuthorityModel.run_id == "run",
                TournamentDrawInputAuthorityModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(TournamentFormatAuthorityModel).where(
                TournamentFormatAuthorityModel.run_id == "run",
                TournamentFormatAuthorityModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(TournamentEntryFieldVersionModel).where(
                TournamentEntryFieldVersionModel.run_id == "run",
                TournamentEntryFieldVersionModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(WorldTourFinalsParticipantSelectionSnapshotModel).where(
                WorldTourFinalsParticipantSelectionSnapshotModel.run_id == "run",
                WorldTourFinalsParticipantSelectionSnapshotModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(WorldTourFinalsParticipantSelectionConfigurationModel).where(
                WorldTourFinalsParticipantSelectionConfigurationModel.run_id == "run",
                WorldTourFinalsParticipantSelectionConfigurationModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(WorldTourFinalsRaceSnapshotModel).where(
                WorldTourFinalsRaceSnapshotModel.run_id == "run",
                WorldTourFinalsRaceSnapshotModel.branch_id == "branch",
            )
        )
        session.execute(
            delete(WorldTourFinalsRaceConfigurationModel).where(
                WorldTourFinalsRaceConfigurationModel.run_id == "run",
                WorldTourFinalsRaceConfigurationModel.branch_id == "branch",
            )
        )
        session.flush()

        current_payload = {"content": {}}
        capture_saved_simulation_slots(
            session,
            current_payload,
            run_id="run",
            branch_id="branch",
        )
        assert "simulation_slot_match_state" not in current_payload["content"]

        restore_saved_simulation_slots(
            session,
            current_payload=current_payload,
            target_payload=target_payload,
            run_id="run",
            branch_id="branch",
        )

        restored_selection = WorldTourFinalsParticipantSelectionStore(
            session
        ).get_snapshot(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
        )
        assert restored_selection == selected
        assert WorldTourFinalsRaceAuthorityStore(session).get_snapshot(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
        ) is not None
        assert TournamentEntryFieldStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == (field,)
        assert TournamentFormatAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == format_authority
        assert TournamentDrawInputAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == draw_input
        assert TournamentDrawAuthorityStore(session).get_initial(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == draw
        assert TournamentTopologyAuthorityStore(session).get(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == topology

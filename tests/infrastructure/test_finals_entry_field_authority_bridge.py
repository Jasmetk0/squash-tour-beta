"""Persistence bridge from Finals participant selection into shared Entry Field."""

import pytest
from sqlalchemy import delete

from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionConfiguration,
    WorldTourFinalsRaceConfiguration,
    WorldTourFinalsRaceInput,
    WorldTourFinalsRacePlayer,
    calculate_world_tour_finals_race,
    select_world_tour_finals_participants,
    decide_race_replacement,
    initial_effective_participant_state,
    preview_race_replacement,
)
from beta_engine.application.canonical_tournament_preparation import (
    CanonicalTournamentPreparationService,
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


def install_selection(factory, *, capacity: int = 6, race_count: int | None = None):
    race_count = race_count or capacity
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
                for index in range(1, race_count + 1)
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


@pytest.mark.pr_critical
def test_store_materializes_and_replays_finals_selection_as_shared_entry_field(
    database,
):
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

        assert (
            store.stage_initial_from_finals_participant_selection(
                run_id="run",
                branch_id="branch",
                event_id="FINALS",
                target_season_index=0,
                command_id="build-finals-entry-field",
            )
            == field
        )


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
        assert (
            draw_input.finals_participant_selection_fingerprint == selected.fingerprint
        )
        assert (
            draw_input.finals_race_snapshot_fingerprint
            == selected.race_snapshot_fingerprint
        )
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

        assert (
            TournamentDrawInputAuthorityStore(session).get(
                run_id="run",
                branch_id="branch",
                event_id="FINALS",
            )
            == draw_input
        )

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
def test_accepted_race_replacement_drives_entry_draw_input_and_draw(database):
    selected = install_selection(database, capacity=6, race_count=9)
    with database.begin() as session:
        initial_field = TournamentEntryFieldStore(
            session
        ).stage_initial_from_finals_participant_selection(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            target_season_index=0,
            command_id="initial-field",
        )
        TournamentFormatAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="format",
            format_kind="knockout",
        )
        race = WorldTourFinalsRaceAuthorityStore(session).get_snapshot(
            run_id="run", branch_id="branch", target_season_index=0
        )
        assert race is not None
        replacement_store = WorldTourFinalsReplacementStore(session)
        effective = replacement_store.put_state(
            initial_effective_participant_state(
                selected, command_id="initial-effective"
            )
        )
        preview = preview_race_replacement(
            race=race,
            selection=selected,
            effective=effective,
            withdrawn_player_id="p3",
            withdrawal_reason="medical",
            vacancy_id="v1",
            command_id="preview",
        )
        replacement_store.put_authority(preview)
        pending = CanonicalTournamentPreparationService.inspect_in_session(
            session, run_id="run", branch_id="branch", event_id="FINALS"
        )
        assert pending.phase == "finals_replacement_required"
        assert pending.blockers == ("finals_replacement_awaiting_decision",)
        declined, _ = decide_race_replacement(
            preview=preview,
            race=race,
            selection=selected,
            effective=effective,
            decision="decline",
            command_id="decline-p7",
        )
        replacement_store.put_authority(declined)
        accepted, successor = decide_race_replacement(
            preview=declined,
            race=race,
            selection=selected,
            effective=effective,
            decision="accept",
            command_id="accept-p8",
        )
        assert successor is not None
        replacement_store.put_authority(accepted)
        replacement_store.put_state(successor)
        stale = CanonicalTournamentPreparationService.inspect_in_session(
            session, run_id="run", branch_id="branch", event_id="FINALS"
        )
        assert stale.blockers == ("finals_accepted_replacement_entry_field_stale",)
        field = TournamentEntryFieldStore(session).stage_from_finals_effective_state(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            target_season_index=0,
            effective_state_fingerprint=successor.fingerprint,
            command_id="effective-field",
        )
        assert field.base_field_fingerprint == initial_field.fingerprint
        assert field.direct_main_player_ids == ("p1", "p2", "p4", "p5", "p6", "p8")
        assert tuple(player.player_id for player in selected.participants) == (
            "p1",
            "p2",
            "p3",
            "p4",
            "p5",
            "p6",
        )
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="effective-input",
            draw_seed=123,
        )
        assert draw_input.source_kind == "finals_effective_participant_state"
        assert (
            draw_input.finals_effective_participant_state_fingerprint
            == successor.fingerprint
        )
        assert draw_input.tournament_ranking_authority_fingerprint is None
        assert (
            draw_input.capacity.main_draw_size,
            draw_input.capacity.bye_slots,
            draw_input.main_seed_count,
        ) == (8, 2, 2)
        assert draw_input.main_seed_player_ids == ("p1", "p2")
        assert draw_input.withdrawn_player_ids == ("p3",)
        draw = TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="effective-draw",
        )
        assert draw.main.bracket_size == 8
        assert len(draw.main.bye_slot_indexes) == 2
        saved = {"content": {}}
        capture_saved_simulation_slots(session, saved, run_id="run", branch_id="branch")
        session.execute(delete(WorldTourFinalsReplacementAuthorityModel))
        session.execute(delete(WorldTourFinalsEffectiveParticipantStateModel))
        session.execute(delete(TournamentDrawAuthorityModel))
        session.execute(delete(TournamentDrawInputAuthorityModel))
        session.execute(delete(TournamentFormatAuthorityModel))
        session.execute(delete(TournamentEntryFieldVersionModel))
        session.execute(delete(WorldTourFinalsParticipantSelectionSnapshotModel))
        session.execute(delete(WorldTourFinalsParticipantSelectionConfigurationModel))
        session.execute(delete(WorldTourFinalsRaceSnapshotModel))
        session.execute(delete(WorldTourFinalsRaceConfigurationModel))
        current = {"content": {}}
        capture_saved_simulation_slots(
            session, current, run_id="run", branch_id="branch"
        )
        restore_saved_simulation_slots(
            session,
            current_payload=current,
            target_payload=saved,
            run_id="run",
            branch_id="branch",
        )
        restored_states = WorldTourFinalsReplacementStore(session).state_history(
            run_id="run", branch_id="branch", target_season_index=0
        )
        restored_history = WorldTourFinalsReplacementStore(session).authority_history(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            finals_event_id="FINALS",
            vacancy_id="v1",
        )
        assert tuple(state.fingerprint for state in restored_states) == (
            effective.fingerprint,
            successor.fingerprint,
        )
        assert tuple(item.fingerprint for item in restored_history) == (
            preview.fingerprint,
            declined.fingerprint,
            accepted.fingerprint,
        )
        assert (
            TournamentEntryFieldStore(session)
            .latest(run_id="run", branch_id="branch", event_id="FINALS")
            .fingerprint
            == field.fingerprint
        )
        assert (
            TournamentDrawInputAuthorityStore(session)
            .get(run_id="run", branch_id="branch", event_id="FINALS")
            .fingerprint
            == draw_input.fingerprint
        )
        assert (
            TournamentDrawAuthorityStore(session)
            .get(run_id="run", branch_id="branch", event_id="FINALS")
            .fingerprint
            == draw.fingerprint
        )


@pytest.mark.pr_critical
@pytest.mark.parametrize(
    ("window", "repair_seed", "expected_action"),
    ((1, 999, "full_redraw"), (2, None, "seed_cascade"), (3, None, "frozen_slot_fill")),
)
def test_finals_post_draw_replacement_reuses_canonical_phase_semantics(
    database, window, repair_seed, expected_action
):
    selected = install_selection(database, capacity=6, race_count=9)
    with database.begin() as session:
        TournamentEntryFieldStore(
            session
        ).stage_initial_from_finals_participant_selection(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            target_season_index=0,
            command_id="initial-field",
        )
        TournamentFormatAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="format",
            format_kind="knockout",
        )
        TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="input",
            draw_seed=123,
        )
        draw = TournamentDrawAuthorityStore(session).generate(
            run_id="run", branch_id="branch", event_id="FINALS", command_id="draw"
        )
        TournamentDrawProcessAuthorityStore(session).configure(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="process",
            main_process_window_count=3,
        )
        withdrawn = next(slot for slot in draw.main.slots if slot.player_id == "p1")
        race = WorldTourFinalsRaceAuthorityStore(session).get_snapshot(
            run_id="run", branch_id="branch", target_season_index=0
        )
        store = WorldTourFinalsReplacementStore(session)
        initial = store.put_state(
            initial_effective_participant_state(
                selected, command_id="initial-effective"
            )
        )
        preview = preview_race_replacement(
            race=race,
            selection=selected,
            effective=initial,
            withdrawn_player_id="p1",
            withdrawal_reason="medical",
            vacancy_id="v1",
            command_id="preview",
        )
        accepted, successor = decide_race_replacement(
            preview=preview,
            race=race,
            selection=selected,
            effective=initial,
            decision="accept",
            command_id="accept-p7",
        )
        assert successor is not None
        store.put_authority(preview)
        store.put_authority(accepted)
        store.put_state(successor)
        revision = TournamentDrawRevisionStore(session).finals_race_replacement(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="repair",
            replacement_authority=accepted,
            effective_state=successor,
            main_process_window_ordinal=window,
            repair_draw_seed=repair_seed,
        )
        assert revision.main_repair_action == expected_action
        if window == 3:
            replacement_slot = revision.successor_draw.main.slots[
                withdrawn.slot_index - 1
            ]
            assert replacement_slot.player_id == "p7"
            assert replacement_slot.seed_number is None
        assert revision.finals_race_snapshot_fingerprint == race.fingerprint
        assert (
            TournamentDrawRevisionStore(session).active_draw(
                run_id="run", branch_id="branch", event_id="FINALS"
            )
            == revision.successor_draw
        )
        preparation = CanonicalTournamentPreparationService.inspect_in_session(
            session, run_id="run", branch_id="branch", event_id="FINALS"
        )
        assert preparation.phase == "draw_ready"
        assert preparation.blockers == ()
        if window == 3:
            saved = {"content": {}}
            capture_saved_simulation_slots(
                session, saved, run_id="run", branch_id="branch"
            )
            assert (
                saved["content"]["simulation_slot_match_state"]["draw_revisions"][0][
                    "revision_fingerprint"
                ]
                == revision.fingerprint
            )


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
def test_saved_revision_restores_complete_finals_authority_chain_and_entry_field(
    database,
):
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
                WorldTourFinalsParticipantSelectionConfigurationModel.branch_id
                == "branch",
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
        assert (
            WorldTourFinalsRaceAuthorityStore(session).get_snapshot(
                run_id="run",
                branch_id="branch",
                target_season_index=0,
            )
            is not None
        )
        assert TournamentEntryFieldStore(session).history(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
        ) == (field,)
        assert (
            TournamentFormatAuthorityStore(session).get(
                run_id="run",
                branch_id="branch",
                event_id="FINALS",
            )
            == format_authority
        )
        assert (
            TournamentDrawInputAuthorityStore(session).get(
                run_id="run",
                branch_id="branch",
                event_id="FINALS",
            )
            == draw_input
        )
        assert (
            TournamentDrawAuthorityStore(session).get_initial(
                run_id="run",
                branch_id="branch",
                event_id="FINALS",
            )
            == draw
        )
        assert (
            TournamentTopologyAuthorityStore(session).get(
                run_id="run",
                branch_id="branch",
                event_id="FINALS",
            )
            == topology
        )

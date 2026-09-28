"""Persistence bridge from Finals participant selection into shared Entry Field."""

import pytest

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
from beta_engine.infrastructure.db.models import (
    Base,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
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


def install_selection(factory, *, capacity: int = 6):
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
                for index in range(1, capacity + 1)
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

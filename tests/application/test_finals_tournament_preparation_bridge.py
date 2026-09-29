"""Tournament Preparation recognizes Finals participant-selection authority."""

import pytest

from beta_engine.application.canonical_tournament_preparation import (
    CanonicalTournamentPreparationService,
)
from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionConfiguration,
    WorldTourFinalsParticipantSelectionSnapshot,
    WorldTourFinalsSelectedPlayer,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.finals_participant_selection import (
    WorldTourFinalsParticipantSelectionStore,
)
from beta_engine.infrastructure.db.models import (
    Base,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_format_authority import (
    TournamentFormatAuthorityStore,
)


def fp(char: str) -> str:
    return char * 64


@pytest.fixture
def prepared(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'finals-preparation.db'}")
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
        session.flush()
        config = WorldTourFinalsParticipantSelectionConfiguration(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            finals_event_id="FINALS",
            participant_capacity=6,
            direct_entry_event_ids=(),
            race_snapshot_fingerprint=fp("a"),
            calendar_content_fingerprint=fp("b"),
            adopted_by_command_id="configure-finals-participants",
        )
        snapshot = WorldTourFinalsParticipantSelectionSnapshot(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            finals_event_id="FINALS",
            participant_capacity=6,
            configuration_fingerprint=config.fingerprint,
            race_snapshot_fingerprint=config.race_snapshot_fingerprint,
            direct_entry_winner_event_ids=(),
            participants=tuple(
                WorldTourFinalsSelectedPlayer(
                    player_id=f"p{index}",
                    race_rank=index,
                    race_points=1000 - index,
                    seed=index,
                    qualification_source="race",
                )
                for index in range(1, 7)
            ),
        )
        store = WorldTourFinalsParticipantSelectionStore(session)
        store.put_configuration(config)
        store.put_snapshot(snapshot)
    yield factory, snapshot
    engine.dispose()


@pytest.mark.pr_critical
def test_preparation_uses_finals_selection_instead_of_requesting_official_ranking(prepared):
    factory, selected = prepared
    state = CanonicalTournamentPreparationService(factory).inspect(
        run_id="run",
        branch_id="branch",
        event_id="FINALS",
    )

    assert state.phase == "entry_field_required"
    assert state.next_required_action == "build_entry_field"
    assert state.blockers == ("tournament_entry_field_required",)
    assert state.ranking_snapshot_ready is False
    assert state.entry_source_kind == "finals_participant_selection"
    assert state.entry_source_authority_fingerprint == selected.fingerprint
    assert state.entry_field_ready is False
    assert state.entry_capacity_suggestion is None


@pytest.mark.pr_critical
def test_preparation_stops_finals_at_format_authority_after_shared_entry_field(prepared):
    factory, selected = prepared
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

    state = CanonicalTournamentPreparationService(factory).inspect(
        run_id="run",
        branch_id="branch",
        event_id="FINALS",
    )

    assert state.phase == "tournament_format_required"
    assert state.next_required_action == "configure_tournament_format"
    assert state.blockers == ("tournament_format_authority_required",)
    assert state.entry_field_ready is True
    assert state.entry_source_kind == "finals_participant_selection"
    assert state.entry_source_authority_fingerprint == selected.fingerprint
    assert state.entry_seed_order_player_ids == field.direct_main_player_ids
    assert state.main_draw_size == 6
    assert state.can_apply_pre_draw_withdrawal is False
    assert state.can_commit_draw_input is False
    assert state.can_generate_draw is False
    assert state.ready_for_match_schedule is False


@pytest.mark.pr_critical
def test_preparation_routes_pure_knockout_finals_through_ordinary_draw_actions(prepared):
    factory, selected = prepared
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

    service = CanonicalTournamentPreparationService(factory)
    state = service.inspect(
        run_id="run",
        branch_id="branch",
        event_id="FINALS",
    )
    assert state.phase == "draw_input_ready"
    assert state.next_required_action == "review_pre_draw_or_commit_draw_input"
    assert state.blockers == ()
    assert state.ranking_snapshot_ready is False
    assert state.entry_source_authority_fingerprint == selected.fingerprint
    assert state.entry_seed_order_player_ids == field.direct_main_player_ids
    assert state.can_apply_pre_draw_withdrawal is False
    assert state.can_commit_draw_input is True
    assert state.can_generate_draw is False

    with factory.begin() as session:
        draw_input = TournamentDrawInputAuthorityStore(session).commit(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="commit-finals-draw-input",
            draw_seed=123,
        )
    assert draw_input.capacity.main_draw_size == 8
    assert draw_input.capacity.bye_slots == 2

    state = service.inspect(
        run_id="run",
        branch_id="branch",
        event_id="FINALS",
    )
    assert state.phase == "draw_generation_ready"
    assert state.next_required_action == "generate_draw"
    assert state.can_commit_draw_input is False
    assert state.can_generate_draw is True

    with factory.begin() as session:
        TournamentDrawAuthorityStore(session).generate(
            run_id="run",
            branch_id="branch",
            event_id="FINALS",
            command_id="generate-finals-draw",
        )

    state = service.inspect(
        run_id="run",
        branch_id="branch",
        event_id="FINALS",
    )
    assert state.phase == "draw_ready"
    assert state.next_required_action == "none"
    assert state.can_generate_draw is False
    assert state.ready_for_match_schedule is True

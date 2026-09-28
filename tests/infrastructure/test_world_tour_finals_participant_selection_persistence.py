"""Persistence for canonical World Tour Finals participant selection."""

import pytest

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
    WorldTourFinalsParticipantSelectionConflict,
    WorldTourFinalsParticipantSelectionStore,
)
from beta_engine.infrastructure.db.models import (
    Base,
    RunBranchModel,
    RunContainerModel,
)


def fp(char: str) -> str:
    return char * 64


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(
            url=f"sqlite:///{tmp_path / 'finals-participants.db'}"
        )
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


def configuration(*, capacity=4):
    return WorldTourFinalsParticipantSelectionConfiguration(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        finals_event_id="FINALS",
        participant_capacity=capacity,
        direct_entry_event_ids=("DIRECT-A",),
        race_snapshot_fingerprint=fp("a"),
        calendar_content_fingerprint=fp("b"),
        adopted_by_command_id="configure-participants",
    )


def snapshot(config, *, last_player="p4"):
    participants = (
        WorldTourFinalsSelectedPlayer(
            player_id="p1",
            race_rank=1,
            race_points=1000,
            seed=1,
            qualification_source="race",
        ),
        WorldTourFinalsSelectedPlayer(
            player_id="p2",
            race_rank=2,
            race_points=900,
            seed=2,
            qualification_source="direct_entry",
            direct_entry_event_ids=("DIRECT-A",),
        ),
        WorldTourFinalsSelectedPlayer(
            player_id="p3",
            race_rank=3,
            race_points=800,
            seed=3,
            qualification_source="race",
        ),
        WorldTourFinalsSelectedPlayer(
            player_id=last_player,
            race_rank=4,
            race_points=700,
            seed=4,
            qualification_source="race",
        ),
    )
    return WorldTourFinalsParticipantSelectionSnapshot(
        run_id=config.run_id,
        branch_id=config.branch_id,
        target_season_index=config.target_season_index,
        finals_event_id=config.finals_event_id,
        participant_capacity=config.participant_capacity,
        configuration_fingerprint=config.fingerprint,
        race_snapshot_fingerprint=config.race_snapshot_fingerprint,
        direct_entry_winner_event_ids=("DIRECT-A",),
        participants=participants,
    )


@pytest.mark.pr_critical
def test_selection_authority_is_idempotent_and_conflicts_fail_closed(database):
    config = configuration()
    with database.begin() as session:
        store = WorldTourFinalsParticipantSelectionStore(session)
        assert store.put_configuration(config) == config
        assert store.put_configuration(config) == config

        stored = store.get_configuration(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
        )
        assert stored == config

        conflicting_config = config.model_copy(
            update={"direct_entry_event_ids": ()}
        )
        with pytest.raises(
            WorldTourFinalsParticipantSelectionConflict,
            match="configuration",
        ):
            store.put_configuration(conflicting_config)

        selected = snapshot(config)
        assert store.put_snapshot(selected) == selected
        assert store.put_snapshot(selected) == selected
        assert (
            store.get_snapshot(
                run_id="run",
                branch_id="branch",
                target_season_index=0,
            )
            == selected
        )

        with pytest.raises(
            WorldTourFinalsParticipantSelectionConflict,
            match="snapshot",
        ):
            store.put_snapshot(snapshot(config, last_player="other"))


@pytest.mark.pr_critical
def test_selection_snapshot_requires_matching_stored_configuration(database):
    config = configuration()
    with database.begin() as session:
        store = WorldTourFinalsParticipantSelectionStore(session)
        with pytest.raises(ValueError, match="requires stored configuration"):
            store.put_snapshot(snapshot(config))

        store.put_configuration(config)
        mismatched = snapshot(config).model_copy(
            update={"race_snapshot_fingerprint": fp("c")}
        )
        with pytest.raises(ValueError, match="does not match"):
            store.put_snapshot(mismatched)

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest

from beta_engine.application.run_container_creation_service import RunContainerCreationService
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.standalone_match_service import (
    StandaloneMatchAddPlayerCommand,
    StandaloneMatchService,
    StandaloneMatchSimulateCommand,
)
from beta_engine.domain.players.initial_pool import (
    CustomInitialPoolPlayerCreate,
    GeneratedPlayerAttributes,
)
from beta_engine.domain.players.models import HiddenCareerTraits
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    AdoptedTournamentAuthorityModel,
    AuthoritativeSimulationCommandModel,
    InitialWorldStateModel,
    PlayerLifecycleWeekStateModel,
    PlayerSportingWeekStateModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    StandaloneMatchWorkspaceModel,
    TournamentDrawAuthorityModel,
    TournamentDrawInputAuthorityModel,
    TournamentEntryFieldVersionModel,
    TournamentWildCardAuthorityModel,
    WeekSimulationScheduleModel,
)


def _id_factory(*values: str) -> Callable[[str], str]:
    identities: Iterator[str] = iter(values)
    return lambda _kind: next(identities)


def _repository(database_url: str) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=database_url))
    repository = SimulationPersistenceRepository(
        engine=engine,
        session_factory=create_session_factory(engine),
    )
    repository.bootstrap_schema()
    return repository


def _player(player_id: str, name: str, *, technique: int) -> CustomInitialPoolPlayerCreate:
    return CustomInitialPoolPlayerCreate(
        player_id=player_id,
        name=name,
        country_code="CZE",
        nationality="CZE",
        birth_year=1976,
        birth_year_week=1,
        current_ability=80,
        potential_ability=86,
        potential_tier="A",
        career_stage="prime",
        play_style="balanced",
        archetype="all_court",
        attributes=GeneratedPlayerAttributes(
            technique=technique,
            movement=80,
            physical=79,
            mental=81,
            consistency=80,
            clutch=80,
            recovery=80,
        ),
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=90,
            growth_curve="steady",
            professionalism=0.8,
            ambition=0.8,
            travel_tolerance=0.8,
            schedule_aggression=0.6,
            injury_proneness=0.2,
            resilience=0.8,
        ),
        created_for_season="2000/2001",
        actor="admin",
        reason="Master §31.3 standalone acceptance",
    )


@pytest.mark.pr_critical
def test_empty_run_two_manual_players_can_play_one_saved_standalone_match(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'standalone.db'}")
    created = RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory("run", "branch", "revision-1", "draft"),
    ).create_empty_run(display_name="Standalone acceptance")
    assert created.status == "working"
    assert repository.list_simulation_runs() == []

    service = StandaloneMatchService(repository._session_factory)
    empty = service.inspect(run_id="run", branch_id="branch")
    assert empty.status == "empty"

    one = service.add_player(
        run_id="run",
        branch_id="branch",
        command=StandaloneMatchAddPlayerCommand(player=_player("P-A", "Player A", technique=82)),
    )
    assert one.status == "authoring"
    assert one.workspace is not None
    assert [player.player_id for player in one.workspace.players] == ["P-A"]

    ready = service.add_player(
        run_id="run",
        branch_id="branch",
        command=StandaloneMatchAddPlayerCommand(
            player=_player("P-B", "Player B", technique=78),
            expected_workspace_fingerprint=one.workspace.fingerprint,
        ),
    )
    assert ready.status == "ready"
    assert ready.workspace is not None
    assert [player.player_id for player in ready.workspace.players] == ["P-A", "P-B"]

    command = StandaloneMatchSimulateCommand(
        command_id="standalone-command-1",
        expected_workspace_fingerprint=ready.workspace.fingerprint,
        seed=777,
        operator_label="Pre-alpha acceptance",
        audit_reason="Prove empty Run -> two manual players -> one standalone match.",
    )
    completed = service.simulate(run_id="run", branch_id="branch", command=command)
    assert completed.status == "complete"
    assert completed.workspace is None
    assert completed.frozen_world_fingerprint
    assert completed.result is not None
    assert completed.result["winner_player_id"] in {"P-A", "P-B"}
    assert completed.result["loser_player_id"] in {"P-A", "P-B"}
    assert completed.result["winner_player_id"] != completed.result["loser_player_id"]

    retry = service.simulate(run_id="run", branch_id="branch", command=command)
    assert retry == completed
    assert service.inspect(run_id="run", branch_id="branch") == completed

    with repository._session_factory() as session:
        assert session.query(StandaloneMatchWorkspaceModel).count() == 0
        assert session.query(InitialWorldStateModel).count() == 1
        assert session.query(PlayerLifecycleWeekStateModel).count() == 1
        assert session.query(PlayerSportingWeekStateModel).count() == 1
        assert session.query(SimulationSlotModel).count() == 1
        assert session.query(SimulationEventGroupModel).count() == 1
        assert session.query(AuthoritativeSimulationCommandModel).count() == 1

        # Operation-scoped modularity: this flow never creates Calendar/Tournament/Draw authority.
        assert session.query(AdoptedTournamentAuthorityModel).count() == 0
        assert session.query(WeekSimulationScheduleModel).count() == 0
        assert session.query(TournamentEntryFieldVersionModel).count() == 0
        assert session.query(TournamentWildCardAuthorityModel).count() == 0
        assert session.query(TournamentDrawInputAuthorityModel).count() == 0
        assert session.query(TournamentDrawAuthorityModel).count() == 0

    preview = repository.preview_simulation_save(run_id="run", branch_id="branch")
    assert preview["can_save"] is True
    assert preview["simulation_fingerprint"]
    saved = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory("revision-2", "audit-2"),
    ).save_simulation(
        run_id="run",
        branch_id="branch",
        expected_draft_version=preview["draft_version"],
        expected_simulation_fingerprint=preview["simulation_fingerprint"],
    )
    assert saved.saved_revision.kind == "authoritative_simulation"
    content = saved.saved_revision.payload["content"]
    assert "initial_world" in content
    assert "player_lifecycle" in content
    assert "player_sporting_state" in content
    assert "simulation_slot_match_state" in content

from __future__ import annotations

import pytest
from sqlalchemy import select

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import (
    DatabaseSettings, LegacyRunCloneError, LegacyRunCloneTargetExistsError,
    SimulationPersistenceRepository, create_session_factory, create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    BranchCheckpointModel, BranchStateModel, LegacySimulationRunMappingModel,
    RunBranchModel, RunContainerModel, SeasonStateModel, SimulationRunModel,
)


def _service(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'clone.db'}"))
    repository = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="source", season=2027, seed=47, config_version="v1", config_fingerprint="cfg")
    return repository, service


def test_clone_namespace_creates_only_remapped_legacy_data(tmp_path) -> None:
    repository, service = _service(tmp_path)
    before = repository.inspect_legacy_run_clone_inventory(simulation_run_id="source")

    result = service.clone_legacy_simulation_run_namespace(
        source_simulation_run_id="source", target_simulation_run_id="target", target_seed=99
    )

    assert result.created_mapping is False
    assert result.created_branch is False
    assert result.source_product_run_id == "source"
    assert result.target_product_run_id is None
    assert result.source_inventory_hash == before.inventory.inventory_hash
    assert repository.get_simulation_run(run_id="source").seed == 47
    target = repository.get_simulation_run(run_id="target")
    assert target is not None and target.seed == 99
    assert target.parent_run_id == "source" and target.source_type == "branch_clone"
    assert target.world_id == repository.get_simulation_run(run_id="source").world_id
    assert repository.load_season_state(run_id="target") is not None
    assert repository.inspect_legacy_run_clone_inventory(simulation_run_id="target").clone_safe is True
    with repository._session_factory() as session:
        assert session.get(LegacySimulationRunMappingModel, "target") is None
        assert session.get(RunContainerModel, "target") is None
        assert session.execute(select(RunBranchModel).where(RunBranchModel.legacy_simulation_run_id == "target")).scalars().all() == []
        assert session.execute(select(BranchStateModel).where(BranchStateModel.branch_id == "target")).scalars().all() == []
        assert session.execute(select(BranchCheckpointModel).where(BranchCheckpointModel.checkpoint_id == "target")).scalars().all() == []


def test_clone_namespace_rejects_existing_or_same_target_without_partial_target(tmp_path) -> None:
    repository, service = _service(tmp_path)
    with pytest.raises(LegacyRunCloneError, match="differ"):
        service.clone_legacy_simulation_run_namespace(source_simulation_run_id="source", target_simulation_run_id="source")
    service.clone_legacy_simulation_run_namespace(source_simulation_run_id="source", target_simulation_run_id="target")
    with pytest.raises(LegacyRunCloneTargetExistsError):
        service.clone_legacy_simulation_run_namespace(source_simulation_run_id="source", target_simulation_run_id="target")
    with repository._session_factory() as session:
        assert session.get(SimulationRunModel, "target") is not None
        assert session.get(SeasonStateModel, "target") is not None


def test_clone_namespace_copies_non_empty_supported_sections_and_content_hash(tmp_path) -> None:
    from beta_engine.infrastructure.db.models import (
        AdminActionModel, CompletedEventMetadataModel, CompletedEventModel, CompletedTournamentInputModel,
        FinalsQualificationModel, FinalsResultModel, NextSeasonPlayerModel, PlayerSeasonTransitionModel,
        RaceSnapshotModel, RankingSnapshotModel, RunGeneratedPlayerProvenanceModel,
        RunTalentCountryAllocationModel, RunTalentPlanModel, SeasonRolloverModel,
    )
    repository, service = _service(tmp_path)
    with repository._session_factory.begin() as s:
        s.add_all([
            CompletedEventModel(run_id="source", event_sequence=1, event_id="E1"),
            CompletedEventMetadataModel(run_id="source", event_id="E1", season=2027, week=1, template_id="T1", tournament_result_json='{"winner":"P1"}'),
            CompletedTournamentInputModel(run_id="source", event_sequence=1, event_id="E1", payload_json='{"points":100}'),
            RankingSnapshotModel(run_id="source", snapshot_sequence=1, snapshot_kind="tournament", source_event_id="E1", as_of_season=2027, as_of_week=1, payload_json='{"P1":1}'),
            RaceSnapshotModel(run_id="source", snapshot_sequence=1, snapshot_kind="tournament", source_event_id="E1", as_of_season=2027, as_of_week=1, payload_json='{"P1":100}'),
            AdminActionModel(run_id="source", event_id="E1", action_sequence=1, action_kind="assign", payload_json='{}'),
            RunTalentPlanModel(run_id="source", season=2028, seed=1, total_talents=1, dataset_status="ok", config_version="v1", config_fingerprint="cfg"),
            RunTalentCountryAllocationModel(run_id="source", season=2028, country_code="USA", planned_count=1, quality_weights_json='{}', actual_band_counts_json='{}', bias_profile_json='{}'),
            RunGeneratedPlayerProvenanceModel(run_id="source", season=2028, player_id="P1", country_code="USA"),
            FinalsQualificationModel(run_id="source", season=2027, source_as_of_season=2027, source_as_of_week=61, payload_json='{}'),
            FinalsResultModel(run_id="source", season=2027, event_id="F", source_as_of_season=2027, source_as_of_week=61, payload_json='{}'),
            SeasonRolloverModel(run_id="source", from_season=2027, to_season=2028, transitioned_players=1, metadata_json='{}'),
            PlayerSeasonTransitionModel(run_id="source", from_season=2027, to_season=2028, player_id="P1", payload_json='{}'),
            NextSeasonPlayerModel(run_id="source", from_season=2027, to_season=2028, player_id="P1", payload_json='{}'),
        ])
    source = repository.inspect_legacy_run_clone_inventory(simulation_run_id="source")
    result = service.clone_legacy_simulation_run_namespace(source_simulation_run_id="source", target_simulation_run_id="target")
    target = repository.inspect_legacy_run_clone_inventory(simulation_run_id="target")
    source_counts = {x.name: x.count for x in source.inventory.sections if x.copy_policy == "copy"}
    target_counts = {x.name: x.count for x in target.inventory.sections if x.copy_policy == "copy"}
    result_counts = {x.name: x.count for x in result.cloned_section_counts}
    assert source_counts == target_counts == result_counts
    assert result.normalized_clone_equivalence_hash == repository._normalized_clone_content_hash(
        session=repository._session_factory(), run_id="target"
    )
    # IDs are database-generated but every durable copied value is namespace-remapped.
    with repository._session_factory() as s:
        source_event = s.execute(select(CompletedEventModel).where(CompletedEventModel.run_id == "source")).scalar_one()
        target_event = s.execute(select(CompletedEventModel).where(CompletedEventModel.run_id == "target")).scalar_one()
        assert source_event.id != target_event.id
        assert (target_event.event_sequence, target_event.event_id) == (source_event.event_sequence, source_event.event_id)
        assert s.execute(select(RunGeneratedPlayerProvenanceModel).where(RunGeneratedPlayerProvenanceModel.run_id == "target", RunGeneratedPlayerProvenanceModel.player_id == "P1")).scalar_one().player_id == "P1"


def test_clone_namespace_rejects_unsafe_preflight_sources(tmp_path) -> None:
    from beta_engine.infrastructure.db import UnsafeLegacyRunCloneSourceError
    from beta_engine.infrastructure.db.models import RunProspectModel
    repository, service = _service(tmp_path)
    with pytest.raises(Exception, match="was not found"):
        service.clone_legacy_simulation_run_namespace(source_simulation_run_id="missing", target_simulation_run_id="target")
    with repository._session_factory.begin() as s:
        s.get(SeasonStateModel, "source").active_tournament_json = '{"event_id":"E1"}'
    with pytest.raises(UnsafeLegacyRunCloneSourceError, match="active_tournament_present"):
        service.clone_legacy_simulation_run_namespace(source_simulation_run_id="source", target_simulation_run_id="target")
    with repository._session_factory.begin() as s:
        s.get(SeasonStateModel, "source").active_tournament_json = None
        s.add(RunProspectModel(prospect_id="P", run_id="source", world_id="fax_official", season_start_year=2027, season_label="2027", season_week=1, calendar_year=2027, year_week=1, birth_year=2012, birth_year_week=1, age=15, country_code="EGY", cohort_policy_version="v", profile_version="v", display_name="P", identity_seed="a", profile_seed="b", development_seed="c", potential_seed="d", trait_seed="e"))
    with pytest.raises(UnsafeLegacyRunCloneSourceError, match="run_prospects"):
        service.clone_legacy_simulation_run_namespace(source_simulation_run_id="source", target_simulation_run_id="target")

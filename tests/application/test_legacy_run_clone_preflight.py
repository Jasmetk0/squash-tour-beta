from __future__ import annotations

from dataclasses import asdict

import pytest
from sqlalchemy import select

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    UnsupportedCloneSourceError,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.checkpoint_boundaries import (
    BRANCH_CHECKPOINT_KIND_ADMIN_ACTION_APPLIED,
    BRANCH_CHECKPOINT_KIND_BOOTSTRAP_START,
    BRANCH_CHECKPOINT_KIND_EVENT_COMPLETED,
    BRANCH_CHECKPOINT_KIND_SEASON_ROLLOVER,
    BRANCH_CHECKPOINT_KIND_WEEK_COMPLETED,
)
from beta_engine.infrastructure.db.models import (
    BranchCheckpointModel,
    BranchStateModel,
    RunBranchModel,
    RunProspectModel,
    SeasonStateModel,
    SimulationRunModel,
)


def _setup(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'clone-preflight.db'}"))
    repository = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="legacy-source", season=2027, seed=47, config_version="v1", config_fingerprint="cfg")
    return repository, service, repository.list_run_branches(run_id="legacy-source")[0]


def _snapshot(repository):
    with repository._session_factory() as session:
        return {
            "simulation_runs": [row.run_id for row in session.execute(select(SimulationRunModel)).scalars()],
            "season_state": [row.run_id for row in session.execute(select(SeasonStateModel)).scalars()],
            "branches": [row.branch_id for row in session.execute(select(RunBranchModel)).scalars()],
            "branch_states": [row.branch_id for row in session.execute(select(BranchStateModel)).scalars()],
            "branch_checkpoints": [row.checkpoint_id for row in session.execute(select(BranchCheckpointModel)).scalars()],
            "prospects": [row.prospect_id for row in session.execute(select(RunProspectModel)).scalars()],
        }


def test_clone_preflight_inventory_is_deterministic_read_only_and_identifies_context(tmp_path) -> None:
    repository, service, branch = _setup(tmp_path)
    before = _snapshot(repository)

    first = service.inspect_legacy_run_clone_inventory(simulation_run_id="legacy-source", branch_id=branch.branch_id)
    second = repository.inspect_legacy_run_clone_inventory(simulation_run_id="legacy-source", branch_id=branch.branch_id)

    assert first == second
    assert first.clone_safe is True
    assert first.inventory.inventory_hash == second.inventory.inventory_hash
    assert first.inventory.source_product_run_id == "legacy-source"
    assert first.inventory.source_branch_id == branch.branch_id
    sections = {section.name: section for section in first.inventory.sections}
    assert sections["simulation_run"].count == 1
    assert sections["season_state"].count == 1
    assert len(sections["simulation_run"].content_hash) == 64
    assert sections["branch_checkpoints"].copy_policy == "excluded_metadata"
    assert _snapshot(repository) == before


def test_clone_preflight_rejects_unknown_or_missing_state(tmp_path) -> None:
    repository, _, _ = _setup(tmp_path)
    with pytest.raises(UnsupportedCloneSourceError, match="was not found"):
        repository.inspect_legacy_run_clone_inventory(simulation_run_id="missing")
    with repository._session_factory.begin() as session:
        session.delete(session.get(SeasonStateModel, "legacy-source"))
    result = repository.inspect_legacy_run_clone_inventory(simulation_run_id="legacy-source")
    assert result.clone_safe is False
    assert "season_state_missing" in result.unsupported_reasons


def test_clone_preflight_accepts_initial_and_current_capture_as_readiness_context_only(tmp_path) -> None:
    repository, _, branch = _setup(tmp_path)
    initial = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="legacy-source")
    current = repository.capture_current_checkpoint_for_legacy_simulation_run(simulation_run_id="legacy-source")

    for checkpoint in (initial, current):
        result = repository.inspect_legacy_run_clone_inventory(
            simulation_run_id="legacy-source", branch_id=branch.branch_id, checkpoint_id=checkpoint.checkpoint_id
        )
        assert result.clone_safe is True
        assert result.inventory.source_checkpoint_kind == checkpoint.kind
        assert checkpoint.payload["limitations"]["forkable"] is False


@pytest.mark.parametrize("kind", [
    BRANCH_CHECKPOINT_KIND_EVENT_COMPLETED,
    BRANCH_CHECKPOINT_KIND_WEEK_COMPLETED,
    BRANCH_CHECKPOINT_KIND_ADMIN_ACTION_APPLIED,
    BRANCH_CHECKPOINT_KIND_SEASON_ROLLOVER,
    BRANCH_CHECKPOINT_KIND_BOOTSTRAP_START,
])
def test_clone_preflight_marks_future_checkpoint_kinds_unsupported(tmp_path, kind) -> None:
    repository, _, branch = _setup(tmp_path)
    with repository._session_factory.begin() as session:
        session.add(BranchCheckpointModel(
            checkpoint_id=f"checkpoint-{kind}", run_id="legacy-source", branch_id=branch.branch_id,
            parent_checkpoint_id=None, sequence=1, kind=kind, season=2027, week=None, event_id=None,
            event_sequence=None, command_id=f"command-{kind}", command_kind="test", command_boundary="test",
            config_version="v1", config_fingerprint="cfg", world_id="fax_official", world_fingerprint=None,
            global_seed=47, branch_seed=47, seed_namespace_json="{}", payload_schema_version="v1",
            content_hash_algorithm="sha256", content_hash="0" * 64, payload_json="{}",
        ))
    result = repository.inspect_legacy_run_clone_inventory(
        simulation_run_id="legacy-source", branch_id=branch.branch_id, checkpoint_id=f"checkpoint-{kind}"
    )
    assert result.clone_safe is False
    assert f"checkpoint_kind_{kind}_is_not_clone_safe_yet" in result.unsupported_reasons


def test_clone_preflight_fails_closed_for_active_tournament_and_legacy_scoped_prospects(tmp_path) -> None:
    repository, _, _ = _setup(tmp_path)
    with repository._session_factory.begin() as session:
        session.get(SeasonStateModel, "legacy-source").active_tournament_json = '{"event_id":"E1"}'
        session.add(RunProspectModel(
            prospect_id="P1", run_id="legacy-source", world_id="fax_official", season_start_year=2027,
            season_label="2027", season_week=1, calendar_year=2027, year_week=1, birth_year=2012,
            birth_year_week=1, age=15, country_code="EGY", country_name="Egypt", status="prospect",
            source_type="weekly_15yo_cohort", cohort_policy_version="v1", profile_version="v1",
            first_name="A", last_name="B", display_name="A B", short_name="A B", identity_seed="a",
            profile_seed="b", development_seed="c", potential_seed="d", trait_seed="e",
        ))
    result = repository.inspect_legacy_run_clone_inventory(simulation_run_id="legacy-source")
    assert result.clone_safe is False
    assert "active_tournament_present" in result.unsupported_reasons
    assert "run_prospects_are_legacy_run_scoped_and_not_clone_safe_yet" in result.unsupported_reasons
    assert next(item for item in result.inventory.sections if item.name == "run_prospects").count == 1

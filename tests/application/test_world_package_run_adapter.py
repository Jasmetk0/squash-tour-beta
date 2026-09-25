from __future__ import annotations

from collections.abc import Iterator

import pytest

from beta_engine.application.run_container_creation_service import RunContainerCreationService
from beta_engine.application.run_package_service import RunPackageService
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.application.world_package_run_adapter import (
    WORLD_COUNTRY_ENTITY_KIND,
    WorldPackageRunAdapter,
)
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore
from beta_engine.world_packages import OFFICIAL_FAX_WORLD_ID
from tests.support.world_packages import copy_builtin_world_packages


def _ids(*values: str):
    stream: Iterator[str] = iter(values)
    return lambda _: next(stream)


def _repo(url: str = "sqlite://") -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    repository = SimulationPersistenceRepository(
        engine=engine, session_factory=create_session_factory(engine)
    )
    repository.bootstrap_schema()
    return repository


def _empty(repository: SimulationPersistenceRepository) -> None:
    RunContainerCreationService(
        repository, _ids("run", "branch", "r0", "draft")
    ).create_empty_run(display_name="World adapter")


@pytest.mark.pr_critical
def test_directory_world_package_becomes_independent_run_country_snapshot(tmp_path):
    world_root = copy_builtin_world_packages(tmp_path / "world-packages")
    registry = WorldPackageRegistryService(world_packages_root=world_root)
    adapter = WorldPackageRunAdapter(registry_service=registry)
    source_record = registry.get_package(OFFICIAL_FAX_WORLD_ID)
    assert source_record is not None

    document = adapter.build_document(OFFICIAL_FAX_WORLD_ID)
    assert document.package_id == OFFICIAL_FAX_WORLD_ID
    assert document.source_version == 1
    assert document.provenance["source_world_fingerprint"] == source_record.fingerprint
    country_entities = [
        entity for entity in document.entities if entity.entity_kind == WORLD_COUNTRY_ENTITY_KIND
    ]
    assert len(country_entities) == source_record.country_count

    url = f"sqlite:///{tmp_path / 'world-adapter.db'}"
    repository = _repo(url)
    _empty(repository)
    service = RunPackageService(repository)
    preview = service.preview(
        run_id="run", branch_id="branch", document=document
    )
    applied = service.confirm(
        run_id="run",
        branch_id="branch",
        document=document,
        command_id="apply-world",
        expected_head_revision_id="r0",
        expected_draft_version=0,
        expected_state_fingerprint=None,
        expected_preview_fingerprint=preview.preview_fingerprint,
    )
    projection = adapter.project_countries(
        applied.state, package_id=OFFICIAL_FAX_WORLD_ID
    )
    assert len(projection.countries) == source_record.country_count
    assert {
        country.code for country in projection.countries
    } == {
        entity.source_entity_id for entity in country_entities
    }
    before_projection_fingerprint = projection.content_fingerprint
    before_state_fingerprint = applied.state.fingerprint

    source_store = WorldPackageCountryStore(world_root / OFFICIAL_FAX_WORLD_ID)
    source_country = source_store.load_country(projection.countries[0].code)
    source_store.replace_country(
        source_country.model_copy(update={"notes": "changed after Run application"})
    )
    changed_document = adapter.build_document(OFFICIAL_FAX_WORLD_ID)
    assert changed_document.source_fingerprint != document.source_fingerprint

    live = service.get(run_id="run", branch_id="branch")
    assert live is not None
    assert live.fingerprint == before_state_fingerprint
    assert (
        adapter.project_countries(
            live, package_id=OFFICIAL_FAX_WORLD_ID
        ).content_fingerprint
        == before_projection_fingerprint
    )

    saved = RunWorkingDraftService(repository, _ids("r1", "audit")).save(
        run_id="run", branch_id="branch", expected_draft_version=1
    )
    assert (
        saved.saved_revision.payload["content"]["run_package_state"]["fingerprint"]
        == before_state_fingerprint
    )

    reopened = RunPackageService(_repo(url)).get(run_id="run", branch_id="branch")
    assert reopened is not None
    assert (
        adapter.project_countries(
            reopened, package_id=OFFICIAL_FAX_WORLD_ID
        ).content_fingerprint
        == before_projection_fingerprint
    )


@pytest.mark.pr_critical
def test_run_world_projection_fails_closed_for_semantically_invalid_country(tmp_path):
    world_root = copy_builtin_world_packages(tmp_path / "world-packages")
    adapter = WorldPackageRunAdapter(
        registry_service=WorldPackageRegistryService(world_packages_root=world_root)
    )
    document = adapter.build_document(OFFICIAL_FAX_WORLD_ID)
    repository = _repo()
    _empty(repository)
    service = RunPackageService(repository)
    preview = service.preview(
        run_id="run", branch_id="branch", document=document
    )
    applied = service.confirm(
        run_id="run",
        branch_id="branch",
        document=document,
        command_id="apply-world",
        expected_head_revision_id="r0",
        expected_draft_version=0,
        expected_state_fingerprint=None,
        expected_preview_fingerprint=preview.preview_fingerprint,
    )
    country_entity = next(
        entity
        for entity in applied.state.entities
        if entity.entity_kind == WORLD_COUNTRY_ENTITY_KIND
    )
    broken_payload = dict(country_entity.payload)
    broken_payload["code"] = "ZZZ"
    edited = service.edit_entity(
        run_id="run",
        branch_id="branch",
        run_local_id=country_entity.run_local_id,
        payload=broken_payload,
        expected_draft_version=1,
        expected_state_fingerprint=applied.state.fingerprint,
    )
    with pytest.raises(ValueError, match="source identity"):
        adapter.project_countries(edited, package_id=OFFICIAL_FAX_WORLD_ID)

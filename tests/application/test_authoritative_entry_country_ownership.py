from __future__ import annotations

import pytest

from beta_engine.domain.run_packages import (
    AppliedPackageVersion,
    PackageType,
    RunPackageEntity,
    RunPackageState,
)
from beta_engine.infrastructure.db.run_package_state import put_run_package_state
from test_authoritative_slot_matches import _driver_fixture


@pytest.mark.pr_critical
def test_package_backed_entry_country_projection_uses_run_world_package(tmp_path):
    driver, factory, _ = _driver_fixture(tmp_path / "entry-run-world-countries")
    country = (
        driver.match_service.draw_service.entry_list_service.countries_service
        .list_countries()[0]
    )
    source_fingerprint = "a" * 64
    entity = RunPackageEntity(
        run_local_id=1,
        source_package_id="world-test",
        source_package_version=1,
        source_package_fingerprint=source_fingerprint,
        source_entity_id=country.code,
        entity_kind="world.country.v1",
        entity_schema_version=1,
        scope="countries",
        payload=country.model_dump(mode="json"),
        source_baseline_fingerprint="b" * 64,
    )
    version = AppliedPackageVersion(
        package_type=PackageType.WORLD,
        package_id="world-test",
        source_version=1,
        source_fingerprint=source_fingerprint,
        document_explicit_scope=("countries",),
        applied_entity_ids=(country.code,),
        provenance={},
    )

    with factory.begin() as session:
        put_run_package_state(
            session,
            RunPackageState(
                run_id="run",
                branch_id="branch",
                entities=(entity,),
                package_versions=(version,),
            ),
        )
        projected = driver._run_owned_entry_country_snapshots(
            session,
            run_id="run",
            branch_id="branch",
        )

    assert projected is not None
    assert tuple(item.code for item in projected) == (country.code,)
    assert projected[0] == country

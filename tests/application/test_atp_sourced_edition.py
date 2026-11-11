"""Selected sporting profile scope and copied-baseline integrity guards."""
from types import SimpleNamespace

import pytest

from beta_engine.application.atp_sourced_edition import saved_profiles
from beta_engine.application.atp_sporting_package_adapter import build_atp_sporting_package
from beta_engine.domain.run_packages import RunPackageEntity

pytestmark = pytest.mark.pr_critical


def state():
    doc = build_atp_sporting_package()
    entities = tuple(RunPackageEntity(
        run_local_id=i, source_package_id=doc.package_id, source_package_version=doc.source_version,
        source_package_fingerprint=doc.source_fingerprint, source_entity_id=e.source_entity_id,
        entity_kind=e.entity_kind, entity_schema_version=e.entity_schema_version, scope=e.scope,
        payload=e.payload, references=e.references, source_baseline_fingerprint=e.fingerprint,
    ) for i, e in enumerate(doc.entities, 1))
    return SimpleNamespace(entities=entities, package_versions=[SimpleNamespace(
        package_id=doc.package_id, source_version=doc.source_version,
        package_type=doc.package_type, source_fingerprint=doc.source_fingerprint,
    )])


def test_unrelated_edited_profile_does_not_block_selected_valid_occurrence():
    s = state()
    s.entities = (s.entities[0], s.entities[1].model_copy(update={"provenance": "manual"}))
    assert set(saved_profiles(s, occurrence_id="atp_2025_atp_finals")) == {"atp_2025_atp_finals"}
    with pytest.raises(ValueError, match="edited"):
        saved_profiles(s, occurrence_id="atp_2025_next_gen_atp_finals")


def test_modified_points_cannot_impersonate_an_original_saved_profile():
    s = state()
    entity = s.entities[0]
    s.entities = (entity.model_copy(update={"payload": {**entity.payload, "played_group_win_points": 999}}),)
    with pytest.raises(ValueError, match="edited"):
        saved_profiles(s, occurrence_id="atp_2025_atp_finals")

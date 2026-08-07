from pathlib import Path

from beta_engine.application.world_package_registry_service import REQUIRED_WORLD_PACKAGE_FILES
from tests.support.fax_reference import (
    FAX_REFERENCE_V1_SOURCE_TREE_HASH,
    FAX_REFERENCE_VERSION,
    FAX_SOURCE_FILES,
    FaxReferenceSource,
    compute_source_tree_hash,
)


def test_fax_reference_is_versioned_deterministic_and_isolated(
    fax_reference_source: FaxReferenceSource,
) -> None:
    assert fax_reference_source.version == FAX_REFERENCE_VERSION
    assert fax_reference_source.world_id == "official_fax_world"
    assert fax_reference_source.source_tree_hash == FAX_REFERENCE_V1_SOURCE_TREE_HASH
    assert compute_source_tree_hash(fax_reference_source.root) == FAX_REFERENCE_V1_SOURCE_TREE_HASH
    assert all(not (path.stat().st_mode & 0o222) for path in fax_reference_source.root.glob("*.json"))


def test_disposable_fax_source_does_not_mutate_reference(
    fax_reference_source: FaxReferenceSource,
    disposable_fax_source: Path,
) -> None:
    before = fax_reference_source.source_tree_hash
    world = disposable_fax_source / "world.json"
    world.write_text(world.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert compute_source_tree_hash(fax_reference_source.root) == before


def test_reference_manifest_tracks_production_required_world_package_files() -> None:
    assert FAX_SOURCE_FILES == REQUIRED_WORLD_PACKAGE_FILES

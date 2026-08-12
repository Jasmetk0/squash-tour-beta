from pathlib import Path

import pytest

from tests.support.fax_reference import (
    FAX_REFERENCE_V1_SOURCE_TREE_HASH,
    FAX_REFERENCE_VERSION,
    FAX_SOURCE_FILES,
    FaxReferenceSource,
    compute_source_tree_hash,
)


@pytest.mark.smoke
def test_fax_reference_is_versioned_deterministic_and_isolated(
    fax_reference_source: FaxReferenceSource,
) -> None:
    assert fax_reference_source.version == FAX_REFERENCE_VERSION
    assert fax_reference_source.world_id == "official_fax_world"
    assert fax_reference_source.source_tree_hash == FAX_REFERENCE_V1_SOURCE_TREE_HASH
    assert compute_source_tree_hash(fax_reference_source.root) == FAX_REFERENCE_V1_SOURCE_TREE_HASH
    assert all(not (path.stat().st_mode & 0o222) for path in fax_reference_source.root.rglob("*.json"))


def test_disposable_fax_source_does_not_mutate_reference(
    fax_reference_source: FaxReferenceSource,
    disposable_fax_source: Path,
) -> None:
    before = fax_reference_source.source_tree_hash
    world = disposable_fax_source / "world.json"
    world.write_text(world.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert compute_source_tree_hash(fax_reference_source.root) == before


@pytest.mark.smoke
def test_reference_manifest_covers_typed_country_semantics() -> None:
    assert "world.json" in FAX_SOURCE_FILES
    assert (FAX_REFERENCE_V1_SOURCE_TREE_HASH == compute_source_tree_hash(Path("config/world_packages/official_fax_world")))

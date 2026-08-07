from pathlib import Path

from tests.support.fax_reference import FAX_REFERENCE_VERSION, FaxReferenceSource, source_fingerprint


def test_fax_reference_is_versioned_deterministic_and_isolated(
    fax_reference_source: FaxReferenceSource,
) -> None:
    assert fax_reference_source.version == FAX_REFERENCE_VERSION
    assert fax_reference_source.world_id == "official_fax_world"
    assert source_fingerprint(fax_reference_source.root) == fax_reference_source.fingerprint
    assert all(not (path.stat().st_mode & 0o222) for path in fax_reference_source.root.glob("*.json"))


def test_disposable_fax_source_does_not_mutate_reference(
    fax_reference_source: FaxReferenceSource,
    disposable_fax_source: Path,
) -> None:
    before = fax_reference_source.fingerprint
    world = disposable_fax_source / "world.json"
    world.write_text(world.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert source_fingerprint(fax_reference_source.root) == before

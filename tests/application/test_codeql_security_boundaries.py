"""Regression checks for the World Package filesystem trust boundary.

CodeQL #14-#33: external identifiers must never select or delete paths
outside their owning package, even when directories are symlinks.
"""
from pathlib import Path

import pytest

from beta_engine.domain.countries import CountriesConfig, Country
from beta_engine.application.package_evidence_files import safe_package_file
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore


pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("world_id", [
    "..", "../custom", "../../secrets", "/tmp/escape",
    "custom/valid", "custom\\\\valid", "a"*65, "", ".", "space id",
])
def test_world_package_identifiers_cannot_escape_registry(tmp_path: Path, world_id: str) -> None:
    registry = WorldPackageRegistryService(world_packages_root=tmp_path / "packages")
    assert registry.get_package(world_id) is None
    assert registry.package_dir(world_id) is None


def test_world_package_registry_rejects_link_to_external_directory(tmp_path: Path) -> None:
    registry_root = tmp_path / "packages"
    (registry_root / "custom").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    link = registry_root / "custom" / "unsafe_link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available on this platform")
    registry = WorldPackageRegistryService(world_packages_root=registry_root)
    assert registry.package_dir("unsafe_link") is None
    assert registry.get_package("unsafe_link") is None
    assert registry.list_packages() == []


@pytest.mark.parametrize("code", [
    "..", "../AAA", "/tmp/AAA", "AAA/../../", "aaA", "ABC123", "", "AB",
])
def test_country_directory_rejects_untrusted_identifiers(tmp_path: Path, code: str) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    with pytest.raises(ValueError, match="invalid country code"):
        store._country_root(code)


def test_country_directory_rejects_symlink(tmp_path: Path) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    store.countries_root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (store.countries_root / "AAA").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available on this platform")
    with pytest.raises(ValueError, match="symlink"):
        store._country_root("AAA")


def test_finalize_delete_rejects_outside_or_linked_backup(tmp_path: Path) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    store.countries_root.mkdir(parents=True)
    outside = tmp_path / ".AAA-delete-backup-unsafe"
    outside.mkdir()
    (outside / "sentinel.txt").write_text("untouched")
    with pytest.raises(ValueError, match="backup location"):
        store.finalize_delete(outside)
    assert (outside / "sentinel.txt").read_text() == "untouched"
    fake = store.countries_root / ".AAA-delete-backup-unsafe"
    try:
        fake.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available on this platform")
    with pytest.raises(ValueError, match="backup location"):
        store.finalize_delete(fake)
    assert (outside / "sentinel.txt").read_text() == "untouched"


def test_generated_country_backup_is_deletable(tmp_path: Path) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    store.countries_root.mkdir(parents=True)
    backup = store.countries_root / ".AAA-delete-backup-abcdef123"
    backup.mkdir()
    (backup / "country.json").write_text("{}")
    store.finalize_delete(backup)
    assert not backup.exists()


def test_package_evidence_rejects_traversal_and_symlink(tmp_path: Path) -> None:
    root = tmp_path / "package"
    root.mkdir()
    nested = root / "generation"
    nested.mkdir()
    (nested / "source.json").write_text("{}")
    assert safe_package_file(root, "generation/source.json") == (nested / "source.json").resolve()
    for name in ("../outside.json", "/etc/passwd", r"generation\\\\..\\\\outside", "generation/../outside"):
        with pytest.raises(ValueError):
            safe_package_file(root, name)
    outside = tmp_path / "secret.json"
    outside.write_text("{}")
    link = nested / "link.json"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("file symlinks are not available on this platform")
    with pytest.raises(ValueError, match="symlink"):
        safe_package_file(root, "generation/link.json")



def test_package_evidence_rejects_symlink_root(tmp_path: Path) -> None:
    root = tmp_path / "real_package"
    root.mkdir()
    (root / "world.json").write_text("{}")
    link = tmp_path / "alias_package"
    try:
        link.symlink_to(root, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available on this platform")
    with pytest.raises(ValueError, match="root must not be a symlink"):
        safe_package_file(link, "world.json")



def test_country_deletion_backup_rejects_linked_countries_root(tmp_path: Path) -> None:
    outside = tmp_path / "external_countries"
    outside.mkdir()
    backup = outside / ".AAA-delete-backup-abcdef"
    backup.mkdir()
    (backup / "sentinel").write_text("keep")
    root = tmp_path / "world"
    root.mkdir()
    try:
        (root / "countries").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available on this platform")
    store = WorldPackageCountryStore(root)
    with pytest.raises(ValueError, match="backup location"):
        store.finalize_delete(store.countries_root / backup.name)
    assert (backup / "sentinel").read_text() == "keep"



def test_country_attributes_directory_symlink_is_rejected(tmp_path: Path) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    root = store.countries_root / "AAA"
    root.mkdir(parents=True)
    outside = tmp_path / "external_attributes"
    outside.mkdir()
    (outside / "population.json").write_text('{"safe": true}')
    try:
        (root / "attributes").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available on this platform")
    with pytest.raises(ValueError, match="attributes directory must not be a symlink"):
        store.load_country("AAA")
    assert (outside / "population.json").read_text() == '{"safe": true}'


def test_country_index_file_symlink_is_rejected(tmp_path: Path) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    store.countries_root.mkdir(parents=True)
    outside = tmp_path / "external_index.json"
    outside.write_text('{"country_codes": ["AAA"]}')
    try:
        store.index_path.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("file symlinks are not available on this platform")
    with pytest.raises(ValueError, match="symlink"):
        store.load_index()
    assert outside.read_text() == '{"country_codes": ["AAA"]}'



def test_registry_json_load_blocks_external_and_symlink_sources(tmp_path: Path) -> None:
    package_root = tmp_path / "world_packages"
    package_root.mkdir()
    outside = tmp_path / "private.json"
    outside.write_text('{"secret": "must-not-load"}')
    registry = WorldPackageRegistryService(world_packages_root=package_root)
    with pytest.raises(ValueError, match="outside the registered root"):
        registry._read_json(outside)
    nested = package_root / "custom"
    nested.mkdir()
    link = nested / "outside.json"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("file symlinks are not available on this platform")
    with pytest.raises(ValueError, match="symlink"):
        registry._read_json(link)
    real_file = nested / "real.json"
    real_file.write_text('{"authorized": true}')
    assert registry._read_json(real_file) == {"authorized": True}


def test_registry_json_load_blocks_symlinked_subdirectory(tmp_path: Path) -> None:
    package_root = tmp_path / "world_packages"
    package_root.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "world.json").write_text('{"secret": "outside"}')
    try:
        (package_root / "custom").symlink_to(outside_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available on this platform")
    registry = WorldPackageRegistryService(world_packages_root=package_root)
    with pytest.raises(ValueError, match="symlink"):
        registry._read_json(package_root / "custom" / "world.json")



def test_history_file_reader_rejects_linked_package_root(tmp_path: Path) -> None:
    from beta_engine.infrastructure.world_package_storage import _safe_package_owned_file

    root = tmp_path / "real_package"
    root.mkdir()
    (root / "rating.json").write_text("{}")
    alias = tmp_path / "package_alias"
    try:
        alias.symlink_to(root, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available on this platform")
    with pytest.raises(ValueError, match="package root must not be a symlink"):
        _safe_package_owned_file(alias, "rating.json")


def test_externalized_history_write_rejects_linked_generation_parent(
    tmp_path: Path, monkeypatch
) -> None:
    from types import SimpleNamespace
    from beta_engine.domain.countries.rating_history import RATING_SCALE_V2

    store = WorldPackageCountryStore(tmp_path / "world")
    store.package_root.mkdir()
    target = tmp_path / "outside"
    target.mkdir()
    (target / "country_histories").mkdir()
    try:
        (store.package_root / "generation").symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available on this platform")
    monkeypatch.setattr(
        WorldPackageCountryStore,
        "load_country",
        lambda self, code: SimpleNamespace(
            code=code, rating_scale=RATING_SCALE_V2, rating_history=object()
        ),
    )
    with pytest.raises(ValueError, match="destination uses a symlink"):
        store.externalize_rating_history("AAA")
    assert not list((target / "country_histories").iterdir())


def test_registry_discovers_only_actual_child_directories(tmp_path: Path) -> None:
    root = tmp_path / "world_packages"
    allowed = root / "custom" / "valid_world"
    allowed.mkdir(parents=True)
    registry = WorldPackageRegistryService(world_packages_root=root)
    assert registry.package_dir("VALID_WORLD") == allowed
    assert registry.package_dir("../valid_world") is None
    assert registry.package_dir("custom/valid_world") is None


def test_finalize_delete_keeps_other_backup_directories(tmp_path: Path) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    store.countries_root.mkdir(parents=True)
    wanted = store.countries_root / ".AAA-delete-backup-abcdef123"
    keep = store.countries_root / ".BBB-delete-backup-abcdef123"
    wanted.mkdir()
    keep.mkdir()
    (wanted / "data").write_text("delete")
    (keep / "data").write_text("keep")
    store.finalize_delete(wanted)
    assert not wanted.exists()
    assert (keep / "data").read_text() == "keep"
    with pytest.raises(FileNotFoundError):
        store.finalize_delete(wanted)
    assert (keep / "data").read_text() == "keep"



def test_country_package_root_symlink_is_rejected(tmp_path: Path) -> None:
    genuine = tmp_path / "genuine_world"
    (genuine / "countries" / "AAA").mkdir(parents=True)
    alias = tmp_path / "alias_world"
    try:
        alias.symlink_to(genuine, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available on this platform")
    store = WorldPackageCountryStore(alias)
    with pytest.raises(ValueError, match="symlink"):
        store._country_root("AAA")
    with pytest.raises(ValueError, match="backup location"):
        store.finalize_delete(alias / "countries" / ".AAA-delete-backup-abcdef")


def test_deletion_backup_rejects_noncanonical_parent_alias(tmp_path: Path) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    store.countries_root.mkdir(parents=True)
    backup = store.countries_root / ".AAA-delete-backup-abcdef"
    backup.mkdir()
    (backup / "sentinel").write_text("keep")
    # A lexical '..' component must not become acceptable merely because
    # resolving the path would point back into the country directory.
    wrong_parent = store.countries_root / "scratch" / ".." / backup.name
    with pytest.raises(ValueError, match="backup location"):
        store.finalize_delete(wrong_parent)
    assert (backup / "sentinel").read_text() == "keep"



def test_country_index_refuses_symlinked_package_root(tmp_path: Path) -> None:
    genuine = tmp_path / "source_package"
    (genuine / "countries").mkdir(parents=True)
    (genuine / "countries" / "index.json").write_text(
        '{"schema_version":"world_package_countries_index.v1","country_codes":["AAA"]}'
    )
    alias = tmp_path / "linked_package"
    try:
        alias.symlink_to(genuine, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available on this platform")
    with pytest.raises(ValueError, match="root must not be a symlink"):
        WorldPackageCountryStore(alias).load_index()


def test_country_replacement_cannot_delete_symlinked_backup(tmp_path: Path) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    store.countries_root.mkdir(parents=True)
    external = tmp_path / "external_dir"
    external.mkdir()
    (external / "sentinel").write_text("untouched")
    linked_backup = store.countries_root / ".AAA-backup"
    try:
        linked_backup.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available on this platform")
    with pytest.raises(ValueError, match="invalid country replacement backup"):
        store._replacement_backup("AAA")
    assert (external / "sentinel").read_text() == "untouched"



def _country_for_relative_root(code: str) -> Country:
    return Country(
        code=code, name="Country " + code, region="EUROPE",
        population=1_234_567, squash_popularity=4, squash_access=3,
        development_quality=5, competition_quality=4,
        elite_support=3, squash_tradition=2,
    )


def _relative_root_store(tmp_path: Path, monkeypatch) -> WorldPackageCountryStore:
    monkeypatch.chdir(tmp_path)
    store = WorldPackageCountryStore(Path("relative_world"))
    store.replace_dataset(
        CountriesConfig(
            dataset_status="test",
            countries=[_country_for_relative_root("AAA"), _country_for_relative_root("BBB")],
        )
    )
    return store


def test_relative_package_root_country_delete_and_rollback(tmp_path: Path, monkeypatch) -> None:
    import sys
    store = _relative_root_store(tmp_path, monkeypatch)
    original_index = store.index_path.read_bytes()
    original_country = store.load_country("AAA")

    index_backup, backup = store.delete_country("AAA")
    assert index_backup == original_index
    if sys.version_info >= (3, 12):
        assert backup.is_absolute(), "Python 3.12+ mkdtemp must return an absolute path"
    assert backup.is_dir()
    assert not (store.countries_root / "AAA").exists()

    store.rollback_delete("AAA", index_backup, backup)
    assert store.index_path.read_bytes() == original_index
    assert store.load_country("AAA") == original_country
    assert not backup.exists()


def test_relative_package_root_country_delete_and_finalize(tmp_path: Path, monkeypatch) -> None:
    store = _relative_root_store(tmp_path, monkeypatch)
    _, backup = store.delete_country("AAA")
    store.finalize_delete(backup)
    assert not backup.exists()
    assert "AAA" not in store.load_index().country_codes
    assert "BBB" in store.load_index().country_codes


def test_relative_root_rejects_alias_backup_even_if_it_points_inside(tmp_path: Path, monkeypatch) -> None:
    store = _relative_root_store(tmp_path, monkeypatch)
    backup = store.countries_root / ".AAA-delete-backup-abcdef"
    backup.mkdir()
    (backup / "sentinel").write_text("keep")
    path_with_alias = store.countries_root.absolute() / "somewhere" / ".." / backup.name
    with pytest.raises(ValueError, match="backup location"):
        store.finalize_delete(path_with_alias)
    assert (backup / "sentinel").read_text() == "keep"


def test_failed_replacement_backup_validation_leaves_no_staging(tmp_path: Path) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    store.replace_dataset(CountriesConfig(dataset_status="test", countries=[
        _country_for_relative_root("AAA"), _country_for_relative_root("BBB"),
    ]))
    external = tmp_path / "outside"
    external.mkdir()
    (external / "sentinel").write_text("keep")
    link = store.countries_root / ".AAA-backup"
    try:
        link.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available on this platform")

    original_index = store.index_path.read_bytes()
    original_country = store.load_country("AAA")
    with pytest.raises(ValueError, match="invalid country replacement backup"):
        store.replace_country(original_country)
    assert not list(store.countries_root.glob(".AAA-stage-*"))
    assert store.index_path.read_bytes() == original_index
    assert store.load_country("AAA") == original_country
    assert (external / "sentinel").read_text() == "keep"

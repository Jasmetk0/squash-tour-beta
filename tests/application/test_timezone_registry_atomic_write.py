"""Real package storage must not follow or remove an unrelated temporary path."""
import shutil
from pathlib import Path

import pytest

from beta_engine.application.world_package_clone_service import WorldPackageCloneService
from beta_engine.application.world_package_countries_service import (
    WorldPackageCountriesService,
    WorldPackageMutationError,
)
from beta_engine.application.world_package_registry_service import (
    WorldPackageRegistryService,
)
from beta_engine.application.world_package_validation_service import (
    WorldPackageValidationResult,
    WorldPackageValidationService,
)
from beta_engine.domain.timezone_areas import TimezoneArea

pytestmark = pytest.mark.pr_critical


@pytest.fixture
def editable(tmp_path):
    root = tmp_path / 'packages'
    shutil.copytree('config/world_packages/official_fax_world', root / 'official_fax_world')
    registry = WorldPackageRegistryService(world_packages_root=root)
    validation = WorldPackageValidationService(registry)
    assert WorldPackageCloneService(registry, validation).clone_official_world(
        new_world_id='editable', name='Editable', description=None, dry_run=False,
    ).ok
    return registry, validation, root / 'custom' / 'editable'


@pytest.mark.parametrize('linked', [False, True])
def test_unrelated_temporary_file_is_neither_followed_nor_removed(editable, tmp_path, linked):
    registry, validation, root = editable
    outside = tmp_path / 'outside.json'
    outside.write_bytes(b'outside must remain unchanged')
    collision = root / 'geography' / '.timezone_areas.json.tmp'
    if linked:
        collision.symlink_to(outside)
    else:
        collision.write_bytes(b'unrelated temporary work')
    before = registry.get_package('editable')
    result = WorldPackageCountriesService(registry, validation).replace_timezone_areas(
        'editable', [TimezoneArea(code='WEST', name='West', position=0)], before.fingerprint,
    )
    assert result.timezone_areas[0].code == 'WEST'
    assert outside.read_bytes() == b'outside must remain unchanged'
    assert collision.is_symlink() if linked else collision.read_bytes() == b'unrelated temporary work'
    assert not (root / 'geography' / 'timezone_areas.json').is_symlink()


@pytest.mark.parametrize('existing', [False, True])
def test_rejected_registry_restores_exact_bytes_and_cleans_own_temporary_file(editable, monkeypatch, existing):
    registry, validation, root = editable
    service = WorldPackageCountriesService(registry, validation)
    if existing:
        service.replace_timezone_areas('editable', [TimezoneArea(code='OLD', name='Old', position=0)],
                                       registry.get_package('editable').fingerprint)
    path = root / 'geography' / 'timezone_areas.json'
    original = path.read_bytes() if existing else None
    fingerprint = registry.get_package('editable').fingerprint
    before_files = set(path.parent.iterdir())
    monkeypatch.setattr(WorldPackageValidationService, 'validate_package', lambda *_: WorldPackageValidationResult(
        'editable', 'errors', 1, 0, 0, [],
    ))
    with pytest.raises(WorldPackageMutationError, match='registry edit would leave'):
        service.replace_timezone_areas('editable', [TimezoneArea(code='NEW', name='New', position=0)], fingerprint)
    assert path.read_bytes() == original if existing else not path.exists()
    assert set(path.parent.iterdir()) == before_files
    assert registry.get_package('editable').fingerprint == fingerprint


def test_failed_install_preserves_original_and_removes_only_own_temporary_file(editable, monkeypatch):
    registry, validation, root = editable
    service = WorldPackageCountriesService(registry, validation)
    service.replace_timezone_areas('editable', [TimezoneArea(code='OLD', name='Old', position=0)],
                                   registry.get_package('editable').fingerprint)
    path = root / 'geography' / 'timezone_areas.json'
    original = path.read_bytes()
    before_files = set(path.parent.iterdir())
    fingerprint = registry.get_package('editable').fingerprint
    original_replace = Path.replace

    def fail_registry_install(source, target):
        if Path(target) == path:
            raise OSError('injected registry install failure')
        return original_replace(source, target)

    monkeypatch.setattr(Path, 'replace', fail_registry_install)
    with pytest.raises(WorldPackageMutationError, match='injected registry install failure'):
        service.replace_timezone_areas('editable', [TimezoneArea(code='NEW', name='New', position=0)], fingerprint)
    assert path.read_bytes() == original
    assert set(path.parent.iterdir()) == before_files
    assert registry.get_package('editable').fingerprint == fingerprint

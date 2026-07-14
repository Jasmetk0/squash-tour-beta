"""Clone service for repository-stored world packages."""

from __future__ import annotations

import json
import re
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from beta_engine.application.world_package_registry_service import (
    OFFICIAL_FAX_WORLD_ID,
    REQUIRED_WORLD_PACKAGE_FILES,
    WorldPackageRegistryRecord,
    WorldPackageRegistryService,
)
from beta_engine.application.world_package_validation_service import WorldPackageValidationResult, WorldPackageValidationService

CUSTOM_WORLD_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_]{2,63}$")


@dataclass(frozen=True)
class WorldPackageCloneError:
    field: str | None
    message: str


@dataclass(frozen=True)
class WorldPackageCloneResult:
    ok: bool
    dry_run: bool
    source_world_id: str
    new_world_id: str
    target_path: str
    created_files: list[str]
    package: WorldPackageRegistryRecord | None = None
    validation: WorldPackageValidationResult | None = None
    errors: list[WorldPackageCloneError] = field(default_factory=list)


@dataclass(slots=True)
class WorldPackageCloneService:
    registry_service: WorldPackageRegistryService
    validation_service: WorldPackageValidationService

    def clone_official_world(self, *, new_world_id: str, name: str, description: str | None, dry_run: bool) -> WorldPackageCloneResult:
        normalized_world_id = str(new_world_id or "").strip()
        target_dir = self.registry_service.worlds_root / "custom" / normalized_world_id
        errors = self._validate_request(normalized_world_id, str(name or ""), target_dir)
        if errors:
            return self._result(False, dry_run, normalized_world_id, target_dir, errors=errors)

        source_paths = self.registry_service.package_paths(OFFICIAL_FAX_WORLD_ID)
        if source_paths is None or not all(path.is_file() for path in source_paths.values()):
            return self._result(False, dry_run, normalized_world_id, target_dir, errors=[WorldPackageCloneError("source_world_id", "official_fax_world package is missing or incomplete.")])

        if dry_run:
            return self._result(True, True, normalized_world_id, target_dir)

        temp_dir = target_dir.parent / f".{target_dir.name}.tmp-{uuid.uuid4().hex}"
        try:
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            if target_dir.exists():
                return self._result(False, dry_run, normalized_world_id, target_dir, errors=[WorldPackageCloneError("new_world_id", f"target directory already exists: {target_dir}")])
            temp_dir.mkdir(parents=False)
            self._write_clone_files(temp_dir, source_paths, new_world_id=normalized_world_id, name=name.strip(), description=description)
            temp_dir.rename(target_dir)
        except Exception as exc:  # noqa: BLE001 - convert filesystem failures into API errors and clean up.
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if target_dir.exists() and self.registry_service.get_package(normalized_world_id) is None:
                shutil.rmtree(target_dir, ignore_errors=True)
            return self._result(False, dry_run, normalized_world_id, target_dir, errors=[WorldPackageCloneError(None, f"clone failed: {exc}")])

        package = self.registry_service.get_package(normalized_world_id)
        validation = self.validation_service.validate_package(normalized_world_id)
        if package is None:
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            return self._result(False, dry_run, normalized_world_id, target_dir, errors=[WorldPackageCloneError("new_world_id", "cloned package could not be discovered by the registry.")])
        return self._result(True, False, normalized_world_id, target_dir, package=package, validation=validation)

    def _validate_request(self, new_world_id: str, name: str, target_dir: Path) -> list[WorldPackageCloneError]:
        errors: list[WorldPackageCloneError] = []
        if not new_world_id:
            errors.append(WorldPackageCloneError("new_world_id", "new_world_id is required."))
        elif not CUSTOM_WORLD_ID_PATTERN.fullmatch(new_world_id):
            errors.append(WorldPackageCloneError("new_world_id", "new_world_id must match ^[a-z0-9][a-z0-9_]{2,63}$ and contain only lowercase letters, numbers, and underscores."))
        elif new_world_id == OFFICIAL_FAX_WORLD_ID:
            errors.append(WorldPackageCloneError("new_world_id", "new_world_id must not be official_fax_world."))
        elif self.registry_service.get_package(new_world_id) is not None:
            errors.append(WorldPackageCloneError("new_world_id", f"world package '{new_world_id}' already exists."))
        elif target_dir.exists():
            errors.append(WorldPackageCloneError("new_world_id", f"target directory already exists: {target_dir}"))

        if not name.strip():
            errors.append(WorldPackageCloneError("name", "name is required."))
        return errors

    def _write_clone_files(self, temp_dir: Path, source_paths: dict[str, Path], *, new_world_id: str, name: str, description: str | None) -> None:
        world_metadata = {
            "world_id": new_world_id,
            "name": name,
            "description": (description if description is not None and description.strip() else "Custom world cloned from Official FAX World."),
            "type": "custom",
            "status": "active",
            "source": "custom_config",
            "editable": True,
            "deletable": True,
            "archivable": True,
            "version": "v1",
            "content_schema_version": "1",
            "cloned_from_world_id": OFFICIAL_FAX_WORLD_ID,
        }
        (temp_dir / "world.json").write_text(json.dumps(world_metadata, indent=2) + "\n", encoding="utf-8")
        for key in ("countries", "continents", "regions", "travel_regions"):
            shutil.copy2(source_paths[key], temp_dir / f"{key}.json")

    def _result(self, ok: bool, dry_run: bool, new_world_id: str, target_dir: Path, *, package: WorldPackageRegistryRecord | None = None, validation: WorldPackageValidationResult | None = None, errors: list[WorldPackageCloneError] | None = None) -> WorldPackageCloneResult:
        return WorldPackageCloneResult(
            ok=ok,
            dry_run=dry_run,
            source_world_id=OFFICIAL_FAX_WORLD_ID,
            new_world_id=new_world_id,
            target_path=str(target_dir),
            created_files=list(REQUIRED_WORLD_PACKAGE_FILES),
            package=package,
            validation=validation,
            errors=errors or [],
        )

"""Canonical FAX source fixture helpers.

The repository config is the source. Tests receive isolated copies so no test can
write through to built-in data, and mutation tests receive a separate writable copy.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore

FAX_REFERENCE_VERSION = "fax-reference-v1"
FAX_REFERENCE_SEED = 20270807
FAX_WORLD_ID = "official_fax_world"
FAX_SOURCE_FILES = ("world.json", "geography/continents.json", "geography/regions.json", "geography/travel_regions.json")
# Deliberately versioned from the canonical typed directory representation;
# this differs from the retired aggregate-file hash without changing semantics.
FAX_REFERENCE_V1_SOURCE_TREE_HASH = "dd1bf58958384375b59e68ff92e79828c531c0b538702852ce3a3c840b108ae5"


@dataclass(frozen=True)
class FaxReferenceSource:
    version: str
    seed: int
    world_id: str
    root: Path
    source_tree_hash: str


def _canonical_bytes(root: Path) -> bytes:
    normalized: dict[str, object] = {
        name: json.loads((root / name).read_text(encoding="utf-8"))
        for name in FAX_SOURCE_FILES
    }
    # Countries are represented by the same assembled typed semantic payload
    # used by the production World Package fingerprint, not a shallow manifest.
    normalized["countries"] = WorldPackageCountryStore(root).semantic_payload()
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def compute_source_tree_hash(root: Path) -> str:
    return hashlib.sha256(_canonical_bytes(root)).hexdigest()


def copy_reference_source(*, repository_root: Path, destination: Path) -> FaxReferenceSource:
    source = repository_root / "config" / "world_packages" / FAX_WORLD_ID
    shutil.copytree(source, destination)
    for path in destination.rglob("*"):
        if path.is_file():
            path.chmod(0o444)
    return FaxReferenceSource(
        version=FAX_REFERENCE_VERSION,
        seed=FAX_REFERENCE_SEED,
        world_id=FAX_WORLD_ID,
        root=destination,
        source_tree_hash=compute_source_tree_hash(destination),
    )


def make_disposable_source(reference: FaxReferenceSource, destination: Path) -> Path:
    """Make a writable, test-local source copy derived from a reference copy."""
    shutil.copytree(reference.root, destination)
    for path in destination.rglob("*"):
        if path.is_file():
            path.chmod(0o644)
    return destination

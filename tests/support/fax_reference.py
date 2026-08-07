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

from beta_engine.application.world_package_registry_service import REQUIRED_WORLD_PACKAGE_FILES

FAX_REFERENCE_VERSION = "fax-reference-v1"
FAX_REFERENCE_SEED = 20270807
FAX_WORLD_ID = "official_fax_world"
FAX_SOURCE_FILES = REQUIRED_WORLD_PACKAGE_FILES
FAX_REFERENCE_V1_SOURCE_TREE_HASH = "1f33ed8018fc5053c2d92de954db35eee141550ce363c467e277dbc93a254308"


@dataclass(frozen=True)
class FaxReferenceSource:
    version: str
    seed: int
    world_id: str
    root: Path
    source_tree_hash: str


def _canonical_bytes(root: Path) -> bytes:
    normalized = {
        name: json.loads((root / name).read_text(encoding="utf-8"))
        for name in FAX_SOURCE_FILES
    }
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def compute_source_tree_hash(root: Path) -> str:
    return hashlib.sha256(_canonical_bytes(root)).hexdigest()


def copy_reference_source(*, repository_root: Path, destination: Path) -> FaxReferenceSource:
    source = repository_root / "config" / "worlds" / FAX_WORLD_ID
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

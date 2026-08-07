from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tests.support.fax_reference import (  # noqa: E402
    FAX_REFERENCE_V1_SOURCE_TREE_HASH,
    FaxReferenceSource,
    copy_reference_source,
    make_disposable_source,
    compute_source_tree_hash,
)


@pytest.fixture
def fax_reference_source(tmp_path: Path) -> FaxReferenceSource:
    """Read-only, isolated projection of the one canonical built-in FAX source."""
    reference = copy_reference_source(repository_root=ROOT, destination=tmp_path / "fax-reference-v1")
    assert reference.source_tree_hash == FAX_REFERENCE_V1_SOURCE_TREE_HASH
    yield reference
    assert compute_source_tree_hash(reference.root) == FAX_REFERENCE_V1_SOURCE_TREE_HASH


@pytest.fixture
def disposable_fax_source(fax_reference_source: FaxReferenceSource, tmp_path: Path) -> Path:
    """Writable temporary source derived from, never aliased to, the reference."""
    return make_disposable_source(fax_reference_source, tmp_path / "fax-editable")

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.support.fax_reference import FaxReferenceSource, copy_reference_source, make_disposable_source

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def fax_reference_source(tmp_path: Path) -> FaxReferenceSource:
    """Read-only, isolated projection of the one canonical built-in FAX source."""
    return copy_reference_source(repository_root=ROOT, destination=tmp_path / "fax-reference-v1")


@pytest.fixture
def disposable_fax_source(fax_reference_source: FaxReferenceSource, tmp_path: Path) -> Path:
    """Writable temporary source derived from, never aliased to, the reference."""
    return make_disposable_source(fax_reference_source, tmp_path / "fax-editable")

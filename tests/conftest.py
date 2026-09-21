from __future__ import annotations

import json
import os
import subprocess
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


def _pull_request_changed_test_paths() -> set[str] | None:
    """Resolve only test modules changed by the current GitHub pull request.

    Local pytest, manual Full Test Suite runs and non-PR automation remain
    unfiltered. During pre-alpha PR CI this keeps validation scoped to tests the
    PR actually changes; the final pre-alpha gate still runs the complete suite.
    """

    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        return None
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        base_sha = event["pull_request"]["base"]["sha"]
    except (OSError, KeyError, json.JSONDecodeError, TypeError):
        return None

    present = subprocess.run(
        ["git", "cat-file", "-e", f"{base_sha}^{{commit}}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if present.returncode != 0:
        subprocess.run(
            ["git", "fetch", "--no-tags", "--depth=1", "origin", base_sha],
            cwd=ROOT,
            check=True,
        )

    changed = subprocess.run(
        ["git", "diff", "--name-only", base_sha, "HEAD", "--", "tests"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return {
        path
        for path in changed
        if path.startswith("tests/")
        and path.endswith(".py")
        and Path(path).name.startswith("test_")
    }


def pytest_collection_modifyitems(config, items):
    changed_tests = _pull_request_changed_test_paths()
    if changed_tests is None:
        return

    selected = []
    deselected = []
    for item in items:
        try:
            rel = item.path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            deselected.append(item)
            continue
        (selected if rel in changed_tests else deselected).append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
    items[:] = selected

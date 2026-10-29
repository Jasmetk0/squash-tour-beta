"""The performance report measures model data, not just serialized input size."""

from dataclasses import dataclass

import pytest

from beta_engine.domain.rankings.official import FrozenInput
from scripts.profile_native_save import retained_bytes, workspace_path

pytestmark = pytest.mark.pr_critical


def test_heap_walk_includes_dataclass_data_and_counts_shared_references_once():
    @dataclass(frozen=True, slots=True)
    class Data:
        payload: bytes

    class Model(FrozenInput):
        data: Data

    payload = b'x' * (1024 * 1024)
    data = Data(payload)
    model = Model(data=data)
    measured = retained_bytes([model])
    assert measured >= len(payload)
    # Another reference to the same graph adds only the outer container space.
    assert 0 <= retained_bytes([model, model, data, payload]) - measured < 1024


def test_measurement_paths_are_confined_after_resolving_traversal_and_symlinks(tmp_path, monkeypatch):
    from argparse import ArgumentTypeError

    monkeypatch.chdir(tmp_path)
    work = tmp_path / 'work'
    work.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (work / 'escape').symlink_to(outside, target_is_directory=True)
    assert workspace_path('work/sample') == work / 'sample'
    assert workspace_path(str(work / '-argument')) == work / '-argument'
    for value in ('work', 'work/../outside', 'work/escape/output', str(outside)):
        with pytest.raises(ArgumentTypeError):
            workspace_path(value)

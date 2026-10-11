from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.diagnostics.pre_alpha_performance import (
    PROFILE_SCHEMA,
    build_profile,
)


def test_build_profile_preserves_measurement_without_inventing_threshold() -> None:
    profile = build_profile(
        label="release-candidate-1",
        pytest_exit_code=0,
        elapsed_seconds=12.3456789,
        python_heap_current_bytes=1024,
        python_heap_peak_bytes=4096,
        nodeids=("tests/a.py::test_a", "tests/b.py::test_b"),
    )

    payload = profile.to_dict()
    assert payload["schema"] == PROFILE_SCHEMA
    assert payload["label"] == "release-candidate-1"
    assert payload["passed"] is True
    assert payload["elapsed_seconds"] == 12.345679
    assert payload["python_heap_current_bytes"] == 1024
    assert payload["python_heap_peak_bytes"] == 4096
    assert payload["nodeids"] == ("tests/a.py::test_a", "tests/b.py::test_b")
    assert payload["created_at_utc"].endswith("+00:00")
    assert payload["python_version"]
    assert payload["platform"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"label": " ", "nodeids": ("x",)}, "profile label"),
        ({"elapsed_seconds": -0.1, "nodeids": ("x",)}, "elapsed_seconds"),
        (
            {
                "python_heap_current_bytes": 10,
                "python_heap_peak_bytes": 9,
                "nodeids": ("x",),
            },
            "current heap bytes",
        ),
        ({"nodeids": (" ",)}, "at least one pytest nodeid"),
    ],
)
def test_build_profile_rejects_invalid_measurements(kwargs: dict, message: str) -> None:
    arguments = {
        "label": "test",
        "pytest_exit_code": 0,
        "elapsed_seconds": 1.0,
        "python_heap_current_bytes": 1,
        "python_heap_peak_bytes": 2,
        "nodeids": ("tests/example.py::test_example",),
    }
    arguments.update(kwargs)

    with pytest.raises(ValueError, match=message):
        build_profile(**arguments)

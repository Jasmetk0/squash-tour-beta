from __future__ import annotations

import pytest

from beta_engine.domain.run_branches import (
    BranchDisplayNameValidationError,
    first_available_timeline_name,
    normalize_branch_display_name,
)


def test_branch_display_name_is_trimmed_without_changing_case() -> None:
    assert normalize_branch_display_name("  My Timeline  ") == "My Timeline"


@pytest.mark.parametrize("value", ["", " ", "\n\t"])
def test_blank_branch_display_name_is_rejected(value: str) -> None:
    with pytest.raises(BranchDisplayNameValidationError, match="must not be blank"):
        normalize_branch_display_name(value)


def test_first_available_timeline_name_fills_the_first_canonical_gap() -> None:
    assert first_available_timeline_name([]) == "Timeline 1"
    assert (
        first_available_timeline_name(
            ["Timeline 1", "Timeline 3", "timeline 2", "Timeline 02"]
        )
        == "Timeline 2"
    )
    assert (
        first_available_timeline_name(["Timeline 1", "Timeline 2", "Custom branch"])
        == "Timeline 3"
    )

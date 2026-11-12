"""Guard: Entry tuning overrides in tests must not rewrite the shared config file."""

from pathlib import Path

import pytest

from test_authoritative_entry_decision_slot import _force_positive_entry_tuning
from test_authoritative_slot_matches import _driver_fixture

SHARED = Path("config/balance/entry_tuning.json")

pytestmark = pytest.mark.pr_critical


def test_positive_entry_tuning_override_uses_an_isolated_copy(tmp_path):
    before = SHARED.read_bytes()
    driver, _factory, _week = _driver_fixture(tmp_path / "isolated-tuning")
    _force_positive_entry_tuning(driver, tmp_path)
    service = driver.match_service.draw_service.entry_list_service
    assert service.entry_tuning_path == tmp_path / "entry_tuning.json"
    assert '"baseline_bias": 10.0' in service.entry_tuning_path.read_text(encoding="utf-8")
    assert SHARED.read_bytes() == before

from __future__ import annotations

from types import SimpleNamespace

import pytest

from beta_engine.application.pre_alpha_fax_entry_validation_policy_gate import (
    AUTOMATIC_APPLICATION_VALIDATION_POLICY_ID,
    PreAlphaFaxEntryValidationPolicyGateService,
)
from beta_engine.domain.rankings.official import RankingWeek


pytestmark = pytest.mark.pr_critical


class _Driver:
    def __init__(self, *, frozen: bool, resolved: bool = False):
        self.frozen = frozen
        self.resolved = resolved

    def position(self, *, run_id: str, branch_id: str):
        return SimpleNamespace(
            current_week=RankingWeek(season_index=0, week=1),
            current_slot_kind="entry",
            slot_ordinal=3,
            position_fingerprint="a" * 64,
        )

    def inspect_entry_decision_slot(
        self, *, run_id: str, branch_id: str, decision_slot_ordinal: int
    ):
        if not self.frozen:
            raise ValueError("Entry decision slot is missing")
        return {
            "slot_fingerprint": "b" * 64,
            "authority": {"decisions": [{}, {}, {}]},
            "validation_resolved": self.resolved,
            "validation_fingerprint": ("c" * 64 if self.resolved else None),
        }


def test_policy_gate_reports_unresolved_validation_after_entry_slot_freezes() -> None:
    gate = PreAlphaFaxEntryValidationPolicyGateService(
        _Driver(frozen=True)
    ).inspect(run_id="run", branch_id="branch")

    assert gate.policy_id == AUTOMATIC_APPLICATION_VALIDATION_POLICY_ID
    assert gate.policy_status == "unresolved"
    assert gate.master_status == "open"
    assert gate.blocks_unattended_release is True
    assert gate.current_entry_slot_frozen is True
    assert gate.current_entry_decision_count == 3
    assert gate.current_entry_validation_resolved is False
    assert gate.current_blocker_code == "application_validation_policy_unresolved"
    assert len(gate.gate_fingerprint) == 64


def test_policy_gate_distinguishes_missing_entry_slot_from_missing_policy() -> None:
    gate = PreAlphaFaxEntryValidationPolicyGateService(
        _Driver(frozen=False)
    ).inspect(run_id="run", branch_id="branch")

    assert gate.current_entry_slot_frozen is False
    assert gate.current_blocker_code == "entry_decision_slot_required"

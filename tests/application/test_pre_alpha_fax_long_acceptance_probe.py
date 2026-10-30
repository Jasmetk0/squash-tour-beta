from __future__ import annotations

from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.pre_alpha_fax_long_acceptance_probe import (
    PreAlphaFaxLongAcceptanceProbeRequest,
    PreAlphaFaxLongAcceptanceProbeService,
)


class _ProfileService:
    def inspect(self, *, run_id: str, branch_id: str):
        return SimpleNamespace(
            ready_for_long_acceptance=True,
            profile_fingerprint="a" * 64,
            issues=(),
        )


class _BlockedDriver:
    def inspect_pending_full_simulations(self, **kwargs):
        return {"operations": []}

    def preview_full_simulation(self, request):
        raise ValueError("authoritative sporting week state is missing")


class _ProgressDriver:
    def inspect_pending_full_simulations(self, **kwargs):
        return {"operations": []}

    def preview_full_simulation(self, request):
        return {
            "start_week": {"season_index": 0, "week": 1},
            "expected_position_fingerprint": "b" * 64,
            "expected_revision_id": "revision-1",
            "preview_fingerprint": "c" * 64,
        }

    def simulate_full_simulation(self, command):
        return {
            "schema_version": "authoritative_full_simulation_progress.v1",
            "status": "blocked",
            "run_id": command.run_id,
            "branch_id": command.branch_id,
            "start_week": {"season_index": 0, "week": 1},
            "current_week": {"season_index": 0, "week": 1},
            "final_week": {"season_index": 49, "week": 61},
            "completed_seasons": [],
            "completed_season_count": 0,
            "final_completed_weeks": [],
            "final_completed_week_count": 0,
            "checkpoint": "season_preparation_required",
            "blockers": ["ranking_snapshot_required"],
            "detail": "Prepare the current season.",
            "position": None,
        }


class _EntryPolicyBlockedDriver(_ProgressDriver):
    def simulate_full_simulation(self, command):
        return {
            "schema_version": "authoritative_full_simulation_progress.v1",
            "status": "blocked",
            "run_id": command.run_id,
            "branch_id": command.branch_id,
            "start_week": {"season_index": 0, "week": 1},
            "current_week": {"season_index": 0, "week": 1},
            "final_week": {"season_index": 49, "week": 61},
            "completed_seasons": [],
            "completed_season_count": 0,
            "final_completed_weeks": [],
            "final_completed_week_count": 0,
            "checkpoint": "entry_process_required",
            "blockers": ["application_validation_required"],
            "detail": "Resolve current Entry process.",
            "position": None,
        }

    def position(self, *, run_id: str, branch_id: str):
        return SimpleNamespace(
            current_week=__import__(
                "beta_engine.domain.rankings.official",
                fromlist=["RankingWeek"],
            ).RankingWeek(season_index=0, week=1),
            current_slot_kind="entry",
            slot_ordinal=1,
            position_fingerprint="d" * 64,
        )

    def inspect_entry_decision_slot(
        self, *, run_id: str, branch_id: str, decision_slot_ordinal: int
    ):
        return {
            "slot_fingerprint": "e" * 64,
            "authority": {"decisions": [{}, {}]},
            "validation_resolved": False,
            "validation_fingerprint": None,
        }


def _request():
    return PreAlphaFaxLongAcceptanceProbeRequest(
        command_id="fax-long-probe-1",
        operator_label="Pre-alpha acceptance",
        audit_reason="Find the first canonical blocker on the copied-FAX release fixture.",
    )


def test_probe_reports_missing_initial_sporting_position_as_structured_blocker() -> None:
    report = PreAlphaFaxLongAcceptanceProbeService(
        driver=_BlockedDriver(),
        profile_service=_ProfileService(),
    ).run(run_id="run-a", branch_id="branch-a", request=_request())

    assert report.execution_status == "blocked"
    assert report.checkpoint == "full_simulation_preview_unavailable"
    assert report.blockers == ("full_simulation_preview_unavailable",)
    assert "sporting week state is missing" in (report.detail or "")
    assert report.full_simulation_preview_fingerprint is None
    assert report.execution_fingerprint is None


def test_probe_preserves_real_full_simulation_checkpoint_and_blockers() -> None:
    report = PreAlphaFaxLongAcceptanceProbeService(
        driver=_ProgressDriver(),
        profile_service=_ProfileService(),
    ).run(run_id="run-a", branch_id="branch-a", request=_request())

    assert report.execution_status == "blocked"
    assert report.checkpoint == "season_preparation_required"
    assert report.blockers == ("ranking_snapshot_required",)
    assert report.current_week == {"season_index": 0, "week": 1}
    assert report.full_simulation_preview_fingerprint == "c" * 64
    assert report.execution_fingerprint is not None


def test_probe_classifies_unresolved_application_validation_policy() -> None:
    report = PreAlphaFaxLongAcceptanceProbeService(
        driver=_EntryPolicyBlockedDriver(),
        profile_service=_ProfileService(),
    ).run(run_id="run-a", branch_id="branch-a", request=_request())

    assert report.checkpoint == "entry_process_required"
    assert report.release_policy_blocker == "application_validation_policy_unresolved"
    assert report.release_policy_gate_fingerprint is not None



class _PendingDriver(_ProgressDriver):
    def __init__(self):
        from beta_engine.application.authoritative_run_simulation_driver import (
            AuthoritativeFullSimulationCommand,
        )
        from beta_engine.domain.simulation_slots import fingerprint
        self.review = {
            "schema_version": "authoritative_full_simulation_preview.v1",
            "run_id": "run-a", "branch_id": "branch-a",
            "start_week": {"season_index": 0, "week": 1},
            "final_week": {"season_index": 49, "week": 61},
            "expected_position_fingerprint": "b" * 64,
            "expected_revision_id": "revision-1",
        }
        self.review["preview_fingerprint"] = fingerprint(self.review)
        request = _request()
        self.command = AuthoritativeFullSimulationCommand(
            **request.model_dump(), run_id="run-a", branch_id="branch-a",
            expected_start_week=self.review["start_week"],
            expected_position_fingerprint="b" * 64, expected_revision_id="revision-1",
            expected_preview_fingerprint=self.review["preview_fingerprint"],
        )
        self.operation = {
            "command": self.command.model_dump(mode="json"), "review": self.review,
            "target_revision": 0, "effective_boundary_target": None,
            "effective_target_week": {"season_index": 49, "week": 61},
        }
        self.executed = []

    def inspect_pending_full_simulations(self, **kwargs):
        return {"operations": [self.operation]}

    def preview_full_simulation(self, request):
        raise AssertionError("An existing parent must reuse its original reviewed command")

    def simulate_full_simulation(self, command):
        self.executed.append(command)
        return super().simulate_full_simulation(command)


def test_probe_continuation_reuses_the_full_original_command():
    driver = _PendingDriver()
    report = PreAlphaFaxLongAcceptanceProbeService(driver, _ProfileService()).run(
        run_id="run-a", branch_id="branch-a", request=_request(),
    )
    assert driver.executed == [driver.command]
    assert report.full_simulation_preview_fingerprint == driver.command.expected_preview_fingerprint
    assert report.execution_fingerprint is not None


@pytest.mark.parametrize("field", ["operator_label", "audit_reason"])
def test_probe_continuation_rejects_command_id_reuse_with_changed_audit(field):
    driver = _PendingDriver()
    from beta_engine.application.pre_alpha_fax_long_acceptance_probe import (
        PreAlphaFaxLongAcceptanceProbeRequest,
    )
    request = PreAlphaFaxLongAcceptanceProbeRequest(**{**_request().model_dump(), field: "Changed audit"})
    with pytest.raises(ValueError, match="different request"):
        PreAlphaFaxLongAcceptanceProbeService(driver, _ProfileService()).run(
            run_id="run-a", branch_id="branch-a", request=request,
        )
    assert driver.executed == []


@pytest.mark.parametrize("damage", ["review", "target_revision", "boundary", "week", "final_week", "scope"])
def test_probe_does_not_reinterpret_corrupt_or_retargeted_parent(damage):
    driver = _PendingDriver()
    if damage == "review":
        driver.operation["review"]["expected_revision_id"] = "unreviewed"
    elif damage == "target_revision":
        driver.operation["target_revision"] = 1
    elif damage == "boundary":
        driver.operation["effective_boundary_target"] = {"kind": "week_end"}
    elif damage == "week":
        driver.operation["effective_target_week"] = {"season_index": 0, "week": 2}
    elif damage == "final_week":
        driver.operation["review"]["final_week"] = {"season_index": 0, "week": 2}
    else:
        driver.operation["command"]["branch_id"] = "foreign"
    with pytest.raises(ValueError, match="corrupt|retargeted|different request"):
        PreAlphaFaxLongAcceptanceProbeService(driver, _ProfileService()).run(
            run_id="run-a", branch_id="branch-a", request=_request(),
        )
    assert driver.executed == []

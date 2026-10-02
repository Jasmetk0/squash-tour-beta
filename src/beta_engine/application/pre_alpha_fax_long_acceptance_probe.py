"""First executable probe of the Master v72 copied-FAX long acceptance.

The probe deliberately reuses AuthoritativeRunSimulationDriver. It does not invent
automatic Entry/Draw policy. It advances the real Full Simulation parent until that
driver either completes or exposes its first explicit canonical checkpoint/blocker.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeFullSimulationCommand,
    AuthoritativeFullSimulationPreviewRequest,
    AuthoritativeRunSimulationDriver,
)
from beta_engine.application.pre_alpha_fax_acceptance_profile import (
    PreAlphaFaxAcceptanceProfile,
    PreAlphaFaxAcceptanceProfileService,
)
from beta_engine.domain.simulation_slots import fingerprint


class PreAlphaFaxLongAcceptanceProbeRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    command_id: str = Field(min_length=1, max_length=128)
    operator_label: str = Field(min_length=1, max_length=128)
    audit_reason: str = Field(min_length=1, max_length=2000)


class PreAlphaFaxLongAcceptanceProbeReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["pre_alpha_fax_long_acceptance_probe.v1"] = (
        "pre_alpha_fax_long_acceptance_probe.v1"
    )
    run_id: str
    branch_id: str
    acceptance_profile_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_ready: bool
    full_simulation_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    full_simulation_command_id: str
    execution_schema_version: str
    execution_status: Literal["blocked", "complete"]
    checkpoint: str | None = None
    blockers: tuple[str, ...] = ()
    completed_season_count: int = Field(ge=0)
    current_week: dict | None = None
    detail: str | None = None
    execution_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


@dataclass(slots=True)
class PreAlphaFaxLongAcceptanceProbeService:
    driver: AuthoritativeRunSimulationDriver
    profile_service: PreAlphaFaxAcceptanceProfileService

    def run(
        self,
        *,
        run_id: str,
        branch_id: str,
        request: PreAlphaFaxLongAcceptanceProbeRequest,
    ) -> PreAlphaFaxLongAcceptanceProbeReport:
        profile: PreAlphaFaxAcceptanceProfile = self.profile_service.inspect(
            run_id=run_id,
            branch_id=branch_id,
        )
        if not profile.ready_for_long_acceptance:
            blockers = ", ".join(
                issue.code for issue in profile.issues if issue.severity == "error"
            )
            raise ValueError(
                "Copied-FAX long acceptance cannot start before the input gate passes: "
                + blockers
            )

        preview_request = AuthoritativeFullSimulationPreviewRequest(
            command_id=request.command_id,
            run_id=run_id,
            branch_id=branch_id,
            operator_label=request.operator_label,
            audit_reason=request.audit_reason,
        )
        preview = self.driver.preview_full_simulation(preview_request)
        command = AuthoritativeFullSimulationCommand(
            **preview_request.model_dump(mode="json"),
            expected_start_week=preview["start_week"],
            expected_position_fingerprint=preview[
                "expected_position_fingerprint"
            ],
            expected_revision_id=preview["expected_revision_id"],
            expected_preview_fingerprint=preview["preview_fingerprint"],
        )
        execution = self.driver.simulate_full_simulation(command)
        schema = str(execution.get("schema_version", ""))
        status = str(execution.get("status", ""))
        if status not in {"blocked", "complete"}:
            raise ValueError(
                "Full Simulation returned an unsupported acceptance-probe status"
            )

        execution_fp = fingerprint(execution)
        return PreAlphaFaxLongAcceptanceProbeReport(
            run_id=run_id,
            branch_id=branch_id,
            acceptance_profile_fingerprint=profile.profile_fingerprint,
            input_ready=True,
            full_simulation_preview_fingerprint=preview["preview_fingerprint"],
            full_simulation_command_id=request.command_id,
            execution_schema_version=schema,
            execution_status=status,
            checkpoint=execution.get("checkpoint"),
            blockers=tuple(execution.get("blockers", ())),
            completed_season_count=int(
                execution.get("completed_season_count", 0)
            ),
            current_week=execution.get("current_week"),
            detail=execution.get("detail"),
            execution_fingerprint=execution_fp,
        )

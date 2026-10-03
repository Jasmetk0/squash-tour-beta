"""Machine-readable pre-alpha release gate for unresolved Entry validation policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import fingerprint


AUTOMATIC_APPLICATION_VALIDATION_POLICY_ID = (
    "automatic_application_eligibility_deadline.v1"
)


class PreAlphaFaxEntryValidationPolicyGate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[
        "pre_alpha_fax_entry_validation_policy_gate.v1"
    ] = "pre_alpha_fax_entry_validation_policy_gate.v1"
    run_id: str
    branch_id: str
    policy_id: Literal[
        "automatic_application_eligibility_deadline.v1"
    ] = AUTOMATIC_APPLICATION_VALIDATION_POLICY_ID
    policy_status: Literal["unresolved"] = "unresolved"
    master_status: Literal["open"] = "open"
    blocks_unattended_release: Literal[True] = True
    current_week: RankingWeek
    current_slot_kind: Literal["entry", "match"] | None
    current_slot_ordinal: int | None = Field(default=None, ge=1)
    current_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_entry_slot_frozen: bool
    current_entry_slot_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    current_entry_decision_count: int = Field(default=0, ge=0)
    current_entry_validation_resolved: bool
    current_validation_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    current_blocker_code: Literal[
        "entry_decision_slot_required",
        "application_validation_policy_unresolved",
        "current_slot_not_entry",
    ]
    detail: str
    gate_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass(slots=True)
class PreAlphaFaxEntryValidationPolicyGateService:
    driver: AuthoritativeRunSimulationDriver

    def inspect(
        self,
        *,
        run_id: str,
        branch_id: str,
    ) -> PreAlphaFaxEntryValidationPolicyGate:
        position = self.driver.position(run_id=run_id, branch_id=branch_id)

        frozen = False
        slot_fp = None
        decision_count = 0
        validation_resolved = False
        validation_fp = None

        if position.current_slot_kind == "entry" and position.slot_ordinal is not None:
            try:
                inspection = self.driver.inspect_entry_decision_slot(
                    run_id=run_id,
                    branch_id=branch_id,
                    decision_slot_ordinal=position.slot_ordinal,
                )
            except ValueError as exc:
                if "Entry decision slot is missing" not in str(exc):
                    raise
                blocker = "entry_decision_slot_required"
                detail = (
                    "Current Entry slot has not yet been frozen through the production "
                    "shared-snapshot Entry decision authority."
                )
            else:
                frozen = True
                slot_fp = inspection["slot_fingerprint"]
                decision_count = len(inspection["authority"]["decisions"])
                validation_resolved = bool(inspection["validation_resolved"])
                validation_fp = inspection["validation_fingerprint"]
                if validation_resolved:
                    blocker = "current_slot_not_entry"
                    detail = (
                        "Current Entry slot already has explicit validation evidence, "
                        "but unattended release simulation remains globally blocked "
                        "because the automatic eligibility/deadline policy is unresolved."
                    )
                else:
                    blocker = "application_validation_policy_unresolved"
                    detail = (
                        "Current Entry decisions are frozen, but no automatic "
                        "eligibility/deadline policy exists to resolve them without "
                        "explicit Admin review."
                    )
        else:
            blocker = "current_slot_not_entry"
            detail = (
                "The current simulation slot is not an unresolved Entry slot. "
                "The automatic application eligibility/deadline policy is still "
                "globally unresolved for future Entry slots."
            )

        body = {
            "run_id": run_id,
            "branch_id": branch_id,
            "policy_id": AUTOMATIC_APPLICATION_VALIDATION_POLICY_ID,
            "policy_status": "unresolved",
            "master_status": "open",
            "blocks_unattended_release": True,
            "current_week": position.current_week.model_dump(mode="json"),
            "current_slot_kind": position.current_slot_kind,
            "current_slot_ordinal": position.slot_ordinal,
            "current_position_fingerprint": position.position_fingerprint,
            "current_entry_slot_frozen": frozen,
            "current_entry_slot_fingerprint": slot_fp,
            "current_entry_decision_count": decision_count,
            "current_entry_validation_resolved": validation_resolved,
            "current_validation_fingerprint": validation_fp,
            "current_blocker_code": blocker,
            "detail": detail,
        }
        return PreAlphaFaxEntryValidationPolicyGate(
            **body,
            gate_fingerprint=fingerprint(body),
        )

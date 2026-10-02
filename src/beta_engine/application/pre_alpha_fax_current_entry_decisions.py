"""Reviewed copied-FAX current Entry decision-slot bootstrap.

This slice uses the production AuthoritativeRunSimulationDriver Entry generator. It
freezes shared-snapshot application decisions for the exact current Entry slot and
stops before application-validity policy, which remains intentionally unresolved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeEntryDecisionSlotCommand,
    AuthoritativeRunSimulationDriver,
)
from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import fingerprint
from beta_engine.infrastructure.db.run_package_state import get_run_package_state


class PreAlphaFaxCurrentEntryDecisionPreview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[
        "pre_alpha_fax_current_entry_decision_preview.v1"
    ] = "pre_alpha_fax_current_entry_decision_preview.v1"
    run_id: str
    branch_id: str
    current_week: RankingWeek
    decision_slot_ordinal: int = Field(ge=1)
    event_ids: tuple[str, ...]
    seed: int
    expected_revision_id: str
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entry_batch_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    application_decisions_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    slot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision_count: int = Field(ge=0)
    persisted: bool
    preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class PreAlphaFaxCurrentEntryDecisionApplyRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    command_id: str = Field(min_length=1, max_length=128)
    expected_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class PreAlphaFaxCurrentEntryDecisionApplyResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[
        "pre_alpha_fax_current_entry_decision_apply.v1"
    ] = "pre_alpha_fax_current_entry_decision_apply.v1"
    run_id: str
    branch_id: str
    current_week: RankingWeek
    decision_slot_ordinal: int = Field(ge=1)
    event_ids: tuple[str, ...]
    decision_count: int = Field(ge=0)
    slot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    adoption: Literal["committed", "exact_retry"]
    validation_required: Literal[True] = True
    validation_policy_status: Literal["automatic_policy_unresolved"] = (
        "automatic_policy_unresolved"
    )
    application_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass(slots=True)
class PreAlphaFaxCurrentEntryDecisionService:
    driver: AuthoritativeRunSimulationDriver

    def _current_world_tour_event_ids(
        self,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
    ) -> tuple[str, ...]:
        with self.driver.factory() as session:
            state = get_run_package_state(
                session,
                run_id=run_id,
                branch_id=branch_id,
            )
            if state is None:
                raise ValueError(
                    "Copied-FAX current Entry decision requires Run Package state"
                )
            season = f"{2000 + week.season_index}/{2001 + week.season_index}"
            projection = CalendarPackageRunAdapter.project_calendar(
                state,
                package_id=CalendarPackageRunAdapter.package_id_for_season(season),
            )
            return tuple(
                sorted(
                    event.event_id
                    for event in projection.calendar.events
                    if event.season_week == week.week
                    and event.tour_level == "WORLD_TOUR"
                )
            )

    def preview(
        self,
        *,
        run_id: str,
        branch_id: str,
        seed: int = 12345,
    ) -> PreAlphaFaxCurrentEntryDecisionPreview:
        position = self.driver.position(run_id=run_id, branch_id=branch_id)
        if position.current_slot_kind != "entry" or position.slot_ordinal is None:
            raise ValueError(
                "Copied-FAX Entry decision bootstrap requires the current authoritative slot to be Entry"
            )
        event_ids = self._current_world_tour_event_ids(
            run_id=run_id,
            branch_id=branch_id,
            week=position.current_week,
        )
        if not event_ids:
            raise ValueError(
                "Copied-FAX current Entry decision has no current-week World Tour Editions"
            )
        raw = self.driver.preview_entry_decision_slot(
            run_id=run_id,
            branch_id=branch_id,
            event_ids=event_ids,
            decision_slot_ordinal=position.slot_ordinal,
            seed=seed,
        )
        frozen = {
            "run_id": run_id,
            "branch_id": branch_id,
            "current_week": position.current_week.model_dump(mode="json"),
            "decision_slot_ordinal": position.slot_ordinal,
            "event_ids": list(event_ids),
            "seed": seed,
            "expected_revision_id": raw["expected_revision_id"],
            "expected_position_fingerprint": position.position_fingerprint,
            "entry_batch_fingerprint": raw["entry_batch_fingerprint"],
            "application_decisions_fingerprint": raw[
                "application_decisions_fingerprint"
            ],
            "slot_fingerprint": raw["slot_fingerprint"],
            "decision_count": raw["decision_count"],
            "persisted": raw["persisted"],
        }
        return PreAlphaFaxCurrentEntryDecisionPreview(
            **frozen,
            preview_fingerprint=fingerprint(frozen),
        )

    def apply(
        self,
        *,
        run_id: str,
        branch_id: str,
        request: PreAlphaFaxCurrentEntryDecisionApplyRequest,
        seed: int = 12345,
    ) -> PreAlphaFaxCurrentEntryDecisionApplyResult:
        preview = self.preview(
            run_id=run_id,
            branch_id=branch_id,
            seed=seed,
        )
        if preview.preview_fingerprint != request.expected_preview_fingerprint:
            raise ValueError(
                "Copied-FAX current Entry decision preview changed since review"
            )

        position = self.driver.position(run_id=run_id, branch_id=branch_id)
        if position.position_fingerprint != preview.expected_position_fingerprint:
            raise ValueError(
                "Copied-FAX current Entry Position changed since review"
            )

        result = self.driver.commit_entry_decision_slot(
            AuthoritativeEntryDecisionSlotCommand(
                command_id=request.command_id,
                run_id=run_id,
                branch_id=branch_id,
                expected_week=preview.current_week,
                expected_revision_id=preview.expected_revision_id,
                decision_slot_ordinal=preview.decision_slot_ordinal,
                event_ids=preview.event_ids,
                seed=preview.seed,
                expected_entry_batch_fingerprint=preview.entry_batch_fingerprint,
                expected_slot_fingerprint=preview.slot_fingerprint,
            )
        )
        payload = {
            "run_id": run_id,
            "branch_id": branch_id,
            "current_week": preview.current_week.model_dump(mode="json"),
            "decision_slot_ordinal": preview.decision_slot_ordinal,
            "event_ids": list(preview.event_ids),
            "decision_count": int(result["decision_count"]),
            "slot_fingerprint": result["slot_fingerprint"],
            "adoption": result["adoption"],
            "validation_required": True,
            "validation_policy_status": "automatic_policy_unresolved",
        }
        return PreAlphaFaxCurrentEntryDecisionApplyResult(
            **payload,
            application_fingerprint=fingerprint(payload),
        )

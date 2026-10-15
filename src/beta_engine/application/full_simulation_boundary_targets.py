"""Reviewed precise boundaries over existing authorities; no new sporting scheduler.

All execution checks run after BEGIN IMMEDIATE and use committed data only.
The selector is immutable; current completion is deliberately not its identity.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator
from sqlalchemy import select

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.simulation_slots import fingerprint
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel,
    OwnedTournamentRankingSourceModel,
    ResolvedApplicationValidationSlotModel,
    RunEntryDecisionSlotAuthorityModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)


class BoundaryUnavailable(Exception):
    """A reviewed boundary changed; wait for explicit operator review, without sport."""


class FullSimulationBoundaryTarget(FrozenInput):
    schema_version: Literal["full_simulation_boundary_target.v1"] = (
        "full_simulation_boundary_target.v1"
    )
    kind: Literal["before_slot", "before_final", "after_tournament"]
    week: RankingWeek
    schedule_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    slot_ordinal: int | None = Field(default=None, strict=True, ge=1)
    slot_id: str | None = Field(default=None, min_length=1)
    group_ids: tuple[str, ...] = ()
    slot_kind: Literal["entry", "match"] | None = None
    event_id: str | None = Field(default=None, min_length=1)
    edition_id: str | None = Field(default=None, min_length=1)
    event_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    topology_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    selector_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("group_ids", mode="before")
    @classmethod
    def json_group_tuple(cls, value):
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_selector(self):
        if self.kind == "after_tournament":
            if (
                any(
                    v is not None
                    for v in (
                        self.slot_ordinal,
                        self.slot_id,
                        self.slot_kind,
                        self.topology_fingerprint,
                    )
                )
                or self.group_ids
            ):
                raise ValueError("Tournament completion has no invented final slot")
        else:
            if (
                self.slot_ordinal is None
                or self.slot_id is None
                or self.slot_kind is None
            ):
                raise ValueError("Before boundary requires an exact global slot")
            if (self.slot_kind == "match") != bool(self.group_ids):
                raise ValueError("Match boundary requires exact group identities")
            if tuple(sorted(set(self.group_ids))) != self.group_ids:
                raise ValueError("Slot groups must be canonical")
        if self.kind == "before_slot":
            if any(
                v is not None
                for v in (
                    self.event_id,
                    self.edition_id,
                    self.event_fingerprint,
                    self.topology_fingerprint,
                )
            ):
                raise ValueError(
                    "Global slot boundary is independent of tournament labels"
                )
        elif (
            not self.event_id
            or self.edition_id != self.event_id
            or not self.event_fingerprint
        ):
            # Current owned-source authority uses edition_id == calendar event_id.
            raise ValueError(
                "Boundary requires exact supported Calendar Edition identity"
            )
        if self.kind == "before_final" and (
            self.slot_kind != "match" or not self.topology_fingerprint
        ):
            raise ValueError("Final requires frozen executable topology")
        body = self.model_dump(mode="json", exclude={"selector_fingerprint"})
        if fingerprint(body) != self.selector_fingerprint:
            raise ValueError("Boundary selector fingerprint mismatch")
        return self


def selector(**values):
    body = FullSimulationBoundaryTarget.model_construct(**values).model_dump(
        mode="json", exclude={"selector_fingerprint"}
    )
    return FullSimulationBoundaryTarget.model_validate(
        {**body, "selector_fingerprint": fingerprint(body)}
    )


def effective_boundary(frozen):
    value = frozen.get("effective_boundary_target")
    events, revision = frozen.get("target_events", []), frozen.get("target_revision", 0)
    if not isinstance(events, list) or any(
        not isinstance(event, dict) for event in events
    ):
        raise ValueError("Full Simulation boundary audit shape is corrupt")
    if value is None:
        if events and events[-1].get("boundary_target") is not None:
            raise ValueError("Effective boundary target is missing")
        return None
    target = FullSimulationBoundaryTarget.model_validate(value)
    if (
        type(revision) is not int
        or revision < 1
        or len(events) != revision
        or events[-1].get("boundary_target") != target.model_dump(mode="json")
        or frozen.get("effective_target_week") != frozen.get("final_week")
    ):
        raise ValueError("Effective boundary target audit mismatch")
    return target


def validate_boundary_event(event):
    value = event.get("boundary_target")
    if value is None:
        return False
    target = FullSimulationBoundaryTarget.model_validate(value)
    body = event.get("boundary_review")
    if (
        not isinstance(body, dict)
        or body.get("selector") != target.model_dump(mode="json")
        or body.get("run_id") is None
        or body.get("branch_id") is None
        or body.get("parent_command_id") is None
        or event.get("boundary_review_fingerprint") != fingerprint(body)
        or event.get("target_week") != {"season_index": 49, "week": 61}
        or event.get("applied_at_week") != target.week.model_dump(mode="json")
        or not isinstance(event.get("operator_label"), str)
        or not event["operator_label"].strip()
        or not isinstance(event.get("audit_reason"), str)
        or not event["audit_reason"].strip()
        or "relative_target" in event
    ):
        raise ValueError("Boundary target review provenance is corrupt")
    return True


def _state(driver, session, run_id, branch_id, week):
    scope = {"run_id": run_id, "branch_id": branch_id, "week": week}
    schedule = driver._execution_schedule(session, **scope)
    if schedule is not None:
        packages = driver._packages(
            week, session=session, run_id=run_id, branch_id=branch_id, required=False
        )
        driver._validate_schedule(session, schedule, packages)
    entries = session.scalars(
        select(RunEntryDecisionSlotAuthorityModel)
        .where(
            RunEntryDecisionSlotAuthorityModel.run_id == run_id,
            RunEntryDecisionSlotAuthorityModel.branch_id == branch_id,
            RunEntryDecisionSlotAuthorityModel.week_ordinal == week.ordinal,
        )
        .order_by(RunEntryDecisionSlotAuthorityModel.decision_slot_ordinal)
    ).all()
    from beta_engine.infrastructure.db.run_entry_decision_slots import _load

    authorities = [_load(row) for row in entries]
    slots = {}
    if schedule:
        for spec in schedule.slots:
            slots[spec.ordinal] = {
                "slot_ordinal": spec.ordinal,
                "slot_id": f"week-{week.ordinal}:slot:{spec.ordinal}",
                "slot_kind": "match",
                "group_ids": tuple(sorted(spec.group_ids)),
            }
    for authority in authorities:
        ordinal = authority.decision_slot_ordinal
        if ordinal in slots:
            raise ValueError("Entry and match slot collision")
        slots[ordinal] = {
            "slot_ordinal": ordinal,
            "slot_id": f"week-{week.ordinal}:entry-slot:{ordinal}",
            "slot_kind": "entry",
            "group_ids": (),
        }
    schedule_fp = fingerprint(
        {
            "schedule": schedule.fingerprint if schedule else None,
            "entry": [a.fingerprint for a in authorities],
            "wild_card": driver._wc_slot_ordinals(session, **scope),
        }
    )
    return scope, schedule, slots, schedule_fp


def _events(driver, session, scope):
    week = scope["week"]
    calendar, _, _ = driver._calendar_authority(
        session,
        run_id=scope["run_id"],
        branch_id=scope["branch_id"],
        season=f"{2000 + week.season_index}/{2001 + week.season_index}",
    )
    if calendar is None:
        return {}
    events = [e for e in calendar.events if e.season_week == week.week]
    if len({e.event_id for e in events}) != len(events):
        raise ValueError("Ambiguous Calendar Edition identity")
    return {e.event_id: e for e in events}


def _final(driver, session, scope, event_id):
    # A complete hybrid tree explicitly owns terminal_match_id, including a
    # two-round knockout. Group schedule's last round is NEVER a final.
    brackets = {
        e.event_id: b
        for e, b in driver._hybrid_knockout_brackets_for_week(session, **scope)
    }
    if event_id in brackets:
        bracket = brackets[event_id]
        return bracket.terminal_match_id, bracket.fingerprint
    draw = driver._canonical_draw_binding(session, **scope, event_id=event_id)
    if draw is None:
        raise ValueError("final_topology_not_frozen")
    packages = driver._packages(
        scope["week"],
        session=session,
        run_id=scope["run_id"],
        branch_id=scope["branch_id"],
        required=False,
    )
    matches = [p for p in packages if p.event_id == event_id]
    if len(matches) != 1:
        raise ValueError("final_topology_not_executable")
    from beta_engine.application.canonical_tournament_topology import (
        project_canonical_draw_to_match_topology,
    )

    projection = project_canonical_draw_to_match_topology(draw=draw, package=matches[0])
    return projection.terminal_group_id, projection.fingerprint


def _slot_started(session, scope, ordinal):
    if session.scalar(
        select(SimulationSlotModel).where(
            SimulationSlotModel.run_id == scope["run_id"],
            SimulationSlotModel.branch_id == scope["branch_id"],
            SimulationSlotModel.week_ordinal == scope["week"].ordinal,
            SimulationSlotModel.slot_ordinal >= ordinal,
        )
    ):
        return True
    return (
        session.scalar(
            select(ResolvedApplicationValidationSlotModel).where(
                ResolvedApplicationValidationSlotModel.run_id == scope["run_id"],
                ResolvedApplicationValidationSlotModel.branch_id == scope["branch_id"],
                ResolvedApplicationValidationSlotModel.week_ordinal
                == scope["week"].ordinal,
                ResolvedApplicationValidationSlotModel.decision_slot_ordinal >= ordinal,
            )
        )
        is not None
    )


def _parent_schedule_compatible(
    session, *, run_id, branch_id, parent_command_id, week, schedule
):
    """Do not pretend an older frozen Next Week can execute a new hybrid range.

    This slice does not rewrite a wider child's reviewed scope. A fresh parent
    reviewed after bracket materialization can use that real schedule normally.
    """
    import json

    from beta_engine.application.full_simulation_summary import _children

    pending, seen = [parent_command_id], set()
    while pending:
        command_id = pending.pop()
        if command_id in seen:
            raise ValueError("Boundary parent child graph is cyclic or duplicated")
        seen.add(command_id)
        row = session.get(
            AuthoritativeSimulationCommandModel, (run_id, branch_id, command_id)
        )
        if row is None or row.status != "pending":
            continue
        payload = json.loads(row.result_json)
        if (
            payload.get("schema_version") == "authoritative_week_operation.v1"
            and payload.get("week") == week.model_dump(mode="json")
            and (
                schedule is None
                or payload.get("schedule_fingerprint") != schedule.fingerprint
            )
        ):
            return False
        pending.extend(_children(payload, run_id, branch_id))
    return True


def boundary_options(driver, session, *, run_id, branch_id, parent_command_id):
    week = driver._current_week(session, run_id, branch_id)
    scope, schedule, slots, schedule_fp = _state(
        driver, session, run_id, branch_id, week
    )
    options, unavailable = [], []
    compatible = _parent_schedule_compatible(
        session,
        run_id=run_id,
        branch_id=branch_id,
        parent_command_id=parent_command_id,
        week=week,
        schedule=schedule,
    )
    if not compatible:
        return {
            "schema_version": "full_simulation_boundary_options.v1",
            "run_id": run_id,
            "branch_id": branch_id,
            "parent_command_id": parent_command_id,
            "week": week.model_dump(mode="json"),
            "options": [],
            "unavailable": [
                {
                    "event_id": event_id,
                    "kind": "all",
                    "reason": "parent_week_schedule_review_changed",
                }
                for event_id in _events(driver, session, scope)
            ],
        }
    for ordinal, slot in sorted(slots.items()):
        if not _slot_started(session, scope, ordinal):
            options.append(
                selector(
                    kind="before_slot",
                    week=week,
                    schedule_fingerprint=schedule_fp,
                    **slot,
                )
            )
    events = _events(driver, session, scope)
    scheduled_events = (
        {s.event_id for s in schedule.slots if s.event_id} if schedule else set()
    )
    for event_id, event in events.items():
        if event_id not in scheduled_events:
            unavailable.append(
                {
                    "event_id": event_id,
                    "kind": "all",
                    "reason": "edition_schedule_unavailable",
                }
            )
            continue
        common = {
            "week": week,
            "schedule_fingerprint": schedule_fp,
            "event_id": event_id,
            "edition_id": event_id,
            "event_fingerprint": fingerprint(event.model_dump(mode="json")),
        }
        source = OwnedTournamentRankingSourceStore(session).get(
            run_id=run_id, branch_id=branch_id, edition_id=event_id
        )
        from beta_engine.infrastructure.db.tournament_topology_authority import (
            TournamentTopologyAuthorityStore,
        )

        topology = TournamentTopologyAuthorityStore(session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        hybrid_unfrozen = (
            topology is not None
            and topology.format_kind == "groups_knockout"
            and not any(
                event.event_id == event_id
                for event, _ in driver._hybrid_knockout_brackets_for_week(
                    session, **scope
                )
            )
        )
        if source is None and not hybrid_unfrozen:
            options.append(selector(kind="after_tournament", **common))
        elif source is None:
            unavailable.append(
                {
                    "event_id": event_id,
                    "kind": "after_tournament",
                    "reason": "hybrid_knockout_not_frozen",
                }
            )
        else:
            unavailable.append(
                {
                    "event_id": event_id,
                    "kind": "after_tournament",
                    "reason": "edition_already_closed",
                }
            )
        try:
            group_id, topology_fp = _final(driver, session, scope, event_id)
            final_slots = [
                s
                for s in schedule.slots
                if group_id in s.group_ids
                and s.event_id == event_id
                and s.draw_phase == "main"
            ]
            if len(final_slots) != 1:
                raise ValueError("final_slot_unavailable_or_ambiguous")
            final = final_slots[0]
            if _slot_started(session, scope, final.ordinal):
                raise ValueError("final_slot_already_started")
            options.append(
                selector(
                    kind="before_final",
                    topology_fingerprint=topology_fp,
                    **common,
                    **slots[final.ordinal],
                )
            )
        except ValueError as exc:
            # No placeholder is returned; caller can review only supported options.
            unavailable.append(
                {"event_id": event_id, "kind": "before_final", "reason": str(exc)}
            )
    return {
        "schema_version": "full_simulation_boundary_options.v1",
        "run_id": run_id,
        "branch_id": branch_id,
        "parent_command_id": parent_command_id,
        "week": week.model_dump(mode="json"),
        "options": [o.model_dump(mode="json") for o in options],
        "unavailable": unavailable,
    }


def require_selection(driver, session, command):
    target = command.boundary_target
    options = boundary_options(
        driver,
        session,
        run_id=command.run_id,
        branch_id=command.branch_id,
        parent_command_id=command.target_command_id,
    )
    if target.model_dump(mode="json") not in options["options"]:
        raise ValueError(
            "Boundary selection is stale, already passed or unavailable; review current canonical schedule"
        )
    body = {
        "run_id": command.run_id,
        "branch_id": command.branch_id,
        "parent_command_id": command.target_command_id,
        "selector": target.model_dump(mode="json"),
    }
    return body


def _complete_match_slot(session, scope, spec):
    row = session.get(
        SimulationSlotModel,
        (scope["run_id"], scope["branch_id"], scope["week"].ordinal, spec["slot_id"]),
    )
    if row is None or row.status != "complete":
        return False
    from beta_engine.application.authoritative_slot_matches import (
        AuthoritativeSlotMatchExecutor,
    )

    plan = AuthoritativeSlotMatchExecutor._load_plan(row)
    terminal = AuthoritativeSlotMatchExecutor._load_checkpoint(row)
    expected = (
        scope["run_id"],
        scope["branch_id"],
        scope["week"],
        spec["slot_id"],
        spec["slot_ordinal"],
    )
    if (
        (plan.run_id, plan.branch_id, plan.week, plan.slot_id, plan.ordinal) != expected
        or (
            terminal.run_id,
            terminal.branch_id,
            terminal.week,
            terminal.slot_id,
            terminal.slot_ordinal,
        )
        != expected
        or terminal.slot_start_fingerprint != row.slot_start_fingerprint
        or plan.group_ids != spec["group_ids"]
    ):
        raise ValueError("Completed boundary slot identity is corrupt")
    groups = set(
        session.scalars(
            select(SimulationEventGroupModel.group_id).where(
                SimulationEventGroupModel.run_id == scope["run_id"],
                SimulationEventGroupModel.branch_id == scope["branch_id"],
                SimulationEventGroupModel.week_ordinal == scope["week"].ordinal,
                SimulationEventGroupModel.slot_id == spec["slot_id"],
            )
        ).all()
    )
    if groups != set(spec["group_ids"]):
        raise ValueError(
            "Completed boundary slot lacks its complete simultaneous group receipts"
        )
    return True


def boundary_evidence(driver, session, frozen, *, run_id, branch_id):
    target = effective_boundary(frozen)
    if target is None:
        return None
    current = driver._current_week(session, run_id, branch_id)
    if current != target.week:
        raise BoundaryUnavailable(
            "Selected boundary week is no longer current; explicit review required"
        )
    scope, schedule, slots, schedule_fp = _state(
        driver, session, run_id, branch_id, target.week
    )
    if not _parent_schedule_compatible(
        session,
        run_id=run_id,
        branch_id=branch_id,
        parent_command_id=frozen.get("resume_command", {}).get("command_id", ""),
        week=target.week,
        schedule=schedule,
    ):
        raise BoundaryUnavailable(
            "An earlier Next Week review froze a different schedule. Safely stop this parent and review a new operation after topology preparation."
        )
    if target.kind != "after_tournament" and schedule_fp != target.schedule_fingerprint:
        raise BoundaryUnavailable(
            "Selected global schedule changed; explicit review required"
        )
    if target.kind != "before_slot":
        event = _events(driver, session, scope).get(target.event_id)
        if (
            event is None
            or fingerprint(event.model_dump(mode="json")) != target.event_fingerprint
        ):
            raise BoundaryUnavailable(
                "Selected Calendar Edition changed; explicit review required"
            )
    evidence = {
        "schema_version": "full_simulation_boundary_evidence.v1",
        "target": target.model_dump(mode="json"),
        "week": current.model_dump(mode="json"),
        "schedule_fingerprint": schedule_fp,
    }
    if target.kind == "after_tournament":
        source = OwnedTournamentRankingSourceStore(session).get(
            run_id=run_id, branch_id=branch_id, edition_id=target.edition_id
        )
        if source is None:
            return None
        row = session.get(
            OwnedTournamentRankingSourceModel, (run_id, branch_id, target.edition_id)
        )
        if (
            source.binding.event_id != target.event_id
            or source.binding.completed_week != target.week
            or source.adopted_by_command_id != row.adopted_by_command_id
        ):
            raise ValueError("Target tournament closure ownership is corrupt")
        # An owned source and its slot must both be durably committed. A source
        # cannot close a partial simultaneous slot.
        event_specs = (
            [s for s in schedule.slots if s.event_id == target.event_id]
            if schedule
            else []
        )
        if not event_specs:
            raise BoundaryUnavailable("Selected edition has no authoritative slots")
        for spec in event_specs:
            if not _complete_match_slot(session, scope, slots[spec.ordinal]):
                return None
        evidence.update(
            source_fingerprint=source.fingerprint,
            source_command_id=source.adopted_by_command_id,
            edition_id=source.binding.edition_id,
            event_id=source.binding.event_id,
        )
        return evidence
    if target.kind != "after_tournament" and slots.get(target.slot_ordinal) != {
        "slot_ordinal": target.slot_ordinal,
        "slot_id": target.slot_id,
        "slot_kind": target.slot_kind,
        "group_ids": target.group_ids,
    }:
        raise ValueError(
            "Stored boundary slot identity does not match canonical schedule"
        )
    if target.kind == "before_final":
        group_id, topology_fp = _final(driver, session, scope, target.event_id)
        if (
            topology_fp != target.topology_fingerprint
            or group_id not in target.group_ids
        ):
            raise BoundaryUnavailable(
                "Selected final topology changed; explicit review required"
            )
    if _slot_started(session, scope, target.slot_ordinal):
        raise BoundaryUnavailable(
            "Selected slot already started; cannot retroactively reach target"
        )
    for ordinal, slot in slots.items():
        if ordinal >= target.slot_ordinal:
            continue
        if slot["slot_kind"] == "entry":
            complete = session.get(
                ResolvedApplicationValidationSlotModel,
                (run_id, branch_id, target.week.ordinal, ordinal),
            )
            if complete is None:
                return None
            from beta_engine.infrastructure.db.application_validation_slots import (
                _load as load_validation,
            )
            from beta_engine.infrastructure.db.run_entry_decision_slots import (
                _load as load_entry,
            )

            resolved = load_validation(complete)
            authored = session.get(
                RunEntryDecisionSlotAuthorityModel,
                (run_id, branch_id, target.week.ordinal, ordinal),
            )
            if (
                authored is None
                or load_entry(authored).fingerprint != resolved.slot.fingerprint
            ):
                raise ValueError(
                    "Boundary prefix Entry validation ownership is corrupt"
                )
        elif not _complete_match_slot(session, scope, slot):
            return None
    evidence.update(
        slot_id=target.slot_id,
        slot_ordinal=target.slot_ordinal,
        group_ids=list(target.group_ids),
    )
    return evidence


def validate_trigger(frozen, evidence):
    target = effective_boundary(frozen)
    if target is None or not isinstance(evidence, dict):
        raise ValueError("Precise target trigger is missing")
    if (
        evidence.get("schema_version") != "full_simulation_boundary_evidence.v1"
        or evidence.get("target") != target.model_dump(mode="json")
        or evidence.get("week") != target.week.model_dump(mode="json")
    ):
        raise ValueError("Precise target trigger identity is corrupt")
    if target.kind == "after_tournament":
        import re

        if (
            evidence.get("event_id") != target.event_id
            or evidence.get("edition_id") != target.edition_id
            or not isinstance(evidence.get("source_command_id"), str)
            or not evidence["source_command_id"]
            or not re.fullmatch(r"[0-9a-f]{64}", evidence.get("source_fingerprint", ""))
        ):
            raise ValueError("Tournament closure trigger is corrupt")
    elif (
        evidence.get("schedule_fingerprint") != target.schedule_fingerprint
        or evidence.get("slot_id") != target.slot_id
        or evidence.get("slot_ordinal") != target.slot_ordinal
        or evidence.get("group_ids") != list(target.group_ids)
    ):
        raise ValueError("Before-slot trigger is corrupt")
    return evidence

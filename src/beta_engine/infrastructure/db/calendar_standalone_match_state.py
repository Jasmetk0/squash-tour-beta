"""Run-calendar-owned MatchEngine results and immutable Saved Revision projection.

No conversion to historical 61-week RankingWeek or legacy SimulationSlot keys.
A completed standalone exhibition is real sporting evidence, not a tournament,
published points, or an implicit Week Transition.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.matches.models import MatchContext, MatchResult
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.models import CalendarStandaloneMatchModel

COMPONENT_KEY = "calendar_standalone_match"


class CalendarStandaloneMatch(FrozenInput):
    schema_version: Literal["calendar_standalone_match.v1"] = "calendar_standalone_match.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1, max_length=128)
    command_id: str = Field(min_length=1, max_length=128)
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_saved_head: str = Field(min_length=1)
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    week: RunWeekPosition
    seed: int
    input_context: MatchContext
    result: MatchResult
    operator_label: str = Field(min_length=1)
    audit_reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_match(self):
        if (self.week.season_index, self.week.week) != (0, 1):
            raise ValueError("Standalone match v1 supports opening Week 1 only")
        if self.input_context.match_id != self.match_id or self.result.match_id != self.match_id:
            raise ValueError("Calendar match identity mismatch")
        if (
            self.result.player_a_id != self.input_context.player_a.player.player_id
            or self.result.player_b_id != self.input_context.player_b.player.player_id
            or {self.result.winner_player_id, self.result.loser_player_id}
            != {self.result.player_a_id, self.result.player_b_id}
        ):
            raise ValueError("Calendar match participants or winner differ from input")
        if self.result.rally_log is None or not self.result.rally_log.events:
            raise ValueError("Calendar match requires authoritative played rally history")
        if self.result.timeline_log is None or self.result.stamina_log is None:
            raise ValueError("Calendar match requires complete MatchEngine logs")
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


def load_match_rows(session: Session, *, run_id: str, branch_id: str) -> tuple[CalendarStandaloneMatch, ...]:
    rows = session.scalars(
        select(CalendarStandaloneMatchModel)
        .where(CalendarStandaloneMatchModel.run_id == run_id,
               CalendarStandaloneMatchModel.branch_id == branch_id)
        .order_by(CalendarStandaloneMatchModel.match_id)
    ).all()
    states = []
    for row in rows:
        state = CalendarStandaloneMatch.model_validate_json(row.payload_json)
        if (
            (state.run_id, state.branch_id, state.match_id, state.command_id,
             state.request_fingerprint, state.fingerprint)
            != (run_id, branch_id, row.match_id, row.command_id,
                row.request_fingerprint, row.fingerprint)
        ):
            raise ValueError("Calendar match SQLite identity/hash mismatch")
        states.append(state)
    return tuple(states)


def put_match(session: Session, state: CalendarStandaloneMatch) -> None:
    if session.get(CalendarStandaloneMatchModel, (state.run_id, state.branch_id, state.match_id)):
        raise ValueError("Calendar match already exists")
    session.add(CalendarStandaloneMatchModel(
        run_id=state.run_id, branch_id=state.branch_id, match_id=state.match_id,
        command_id=state.command_id, request_fingerprint=state.request_fingerprint,
        fingerprint=state.fingerprint, payload_json=state.model_dump_json(),
    ))
    session.flush()


def capture_saved_calendar_match(session: Session, payload: dict, *, run_id: str, branch_id: str) -> None:
    states = load_match_rows(session, run_id=run_id, branch_id=branch_id)
    if states:
        # Exactly one operation-scoped completed standalone match in this slice.
        if len(states) != 1:
            raise ValueError("Calendar standalone match v1 supports exactly one match")
        state = states[0]
        payload["content"][COMPONENT_KEY] = {
            "fingerprint": state.fingerprint,
            "state": state.model_dump(mode="json"),
        }


def load_saved_calendar_match(payload: dict, *, run_id: str, branch_id: str) -> CalendarStandaloneMatch | None:
    component = payload.get("content", {}).get(COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "state"}:
        raise ValueError("Invalid Saved calendar standalone match component")
    state = CalendarStandaloneMatch.model_validate(component["state"])
    if (state.run_id, state.branch_id, state.fingerprint) != (
        run_id, branch_id, component["fingerprint"]
    ):
        raise ValueError("Saved calendar standalone match identity/hash mismatch")
    if payload.get("run", {}).get("run_calendar") != state.week.calendar.to_metadata():
        # A Run-wide horizon extension keeps earlier match W, basis and source
        # untouched. The old signed match clock remains independently verifiable.
        from beta_engine.domain.calendar.run_calendar import RunCalendar
        metadata = payload.get("run", {}).get("run_calendar")
        if not isinstance(metadata, dict):
            raise ValueError("Saved calendar match has no Run calendar")
        current = RunCalendar.from_metadata(metadata)
        original = state.week.calendar
        if (
            (current.weeks_per_year, current.season_start_year_week, current.start_year)
            != (original.weeks_per_year, original.season_start_year_week, original.start_year)
            or current.season_count <= original.season_count
        ):
            raise ValueError("Saved calendar match clock cannot be reinterpreted")
    return state


def restore_saved_calendar_match(
    session: Session, *, current_payload: dict, target_payload: dict,
    run_id: str, branch_id: str,
) -> None:
    current = load_saved_calendar_match(current_payload, run_id=run_id, branch_id=branch_id)
    target = load_saved_calendar_match(target_payload, run_id=run_id, branch_id=branch_id)
    live = load_match_rows(session, run_id=run_id, branch_id=branch_id)
    if tuple(s.fingerprint for s in live) != (
        (current.fingerprint,) if current else ()
    ):
        raise ValueError("Live calendar match differs from current Saved head")
    for state in live:
        session.delete(session.get(CalendarStandaloneMatchModel, (run_id, branch_id, state.match_id)))
    session.flush()
    if target is not None:
        put_match(session, target)

"""Reviewed, atomic native sporting-week preparation for bounded exhibitions.

This advances the sporting owner only. It does not publish Official Rankings,
change the legacy scheduler clock, heal Health facts, or run lifecycle/intake.
"""

from dataclasses import dataclass

from pydantic import Field
from sqlalchemy import text

from beta_engine.application.calendar_continuation_service import (
    CalendarContinuationService,
)
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_sporting_week import (
    CalendarAnnualDevelopmentPolicy,
    CalendarSportingWeekAdvance,
    append_sporting_week,
    develop_and_recover,
    played_counts,
    records_fingerprint,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
    replace_checkpoint,
)


class CalendarSportingWeekCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    expected_saved_head: str = Field(min_length=1, max_length=128)
    expected_checkpoint_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    seed: int
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)


class CalendarSportingWeekCommit(FrozenInput):
    command: CalendarSportingWeekCommand
    expected_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    explicit_confirmation: bool


@dataclass(slots=True)
class CalendarSportingWeekService:
    repository: object

    def _preview(self, clock, revision, world, state, saved, evidence, command):
        if (
            state is None
            or saved is None
            or state.fingerprint != saved.fingerprint
            or command.expected_checkpoint_fingerprint != state.fingerprint
            or command.expected_saved_head != revision.saved_head_revision_id
        ):
            raise ValueError(
                "Save the terminal sporting state and review its exact HEAD before weekly preparation"
            )
        if state.week.week == clock.weeks_per_year:
            raise ValueError(
                "Season Transition remains unsupported on this exhibition timeline"
            )
        knockout = getattr(evidence, "knockout", evidence)
        completed = RunWeekPosition(
            calendar=clock, season_index=state.week.season_index, week=state.week.week
        )
        target = RunWeekPosition(
            calendar=clock, season_index=completed.season_index, week=completed.week + 1
        )
        policy = CalendarAnnualDevelopmentPolicy()
        counts = played_counts(state, knockout)
        developed, recovered = develop_and_recover(
            state,
            world,
            completed_week=completed,
            seed=command.seed,
            policy=policy,
            counts=counts,
        )
        event = CalendarSportingWeekAdvance(
            run_id=state.run_id,
            branch_id=state.branch_id,
            command_id=command.command_id,
            source_saved_head=command.expected_saved_head,
            source_checkpoint_fingerprint=state.fingerprint,
            completed_week=completed,
            target_week=target,
            seed=command.seed,
            operator_label=command.operator_label,
            audit_reason=command.audit_reason,
            request_fingerprint=canonical_hash(
                {
                    "run_id": state.run_id,
                    "branch_id": state.branch_id,
                    "command": command.model_dump(mode="json"),
                }
            ),
            policy=policy,
            played_counts=counts,
            developed_players_fingerprint=records_fingerprint(developed),
            recovered_players_fingerprint=records_fingerprint(recovered),
        )
        successor = append_sporting_week(state, world, knockout, event)
        changes = [
            {
                "player_id": a.player_id,
                "changed_attributes": sum(
                    v != w for (_, v), (_, w) in zip(a.attributes, b.attributes)
                ),
                "form_before": a.current_form,
                "form_after": b.current_form,
                "sharpness_before": a.match_sharpness,
                "sharpness_after": b.match_sharpness,
                "fatigue_before": a.long_term_fatigue,
                "fatigue_after": b.long_term_fatigue,
            }
            for a, b in zip(state.players, recovered)
            if a != b
        ]
        body = {
            "schema_version": "calendar_sporting_week_preview.v1",
            "advance": event.model_dump(mode="json"),
            "advance_fingerprint": event.fingerprint,
            "checkpoint_fingerprint": successor.fingerprint,
            "player_count": len(state.players),
            "changed_player_count": len(changes),
            "attribute_change_count": sum(c["changed_attributes"] for c in changes),
            "changes": changes,
        }
        body["preview_fingerprint"] = canonical_hash(body)
        return body, successor

    def preview(self, *, run_id, branch_id, command):
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            clock, revision, world, _, state, saved, evidence = (
                CalendarContinuationService(self.repository)._context(
                    session, run_id=run_id, branch_id=branch_id
                )
            )
            return self._preview(
                clock, revision, world, state, saved, evidence, command
            )[0]

    def commit(self, *, run_id, branch_id, request):
        if request.explicit_confirmation is not True:
            raise ValueError(
                "Explicit confirmation of the reviewed sporting-only advance is required"
            )
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            clock, revision, world, _, state, saved, evidence = (
                CalendarContinuationService(self.repository)._context(
                    session, run_id=run_id, branch_id=branch_id
                )
            )
            cmd = request.command
            if state:
                existing = next(
                    (
                        e
                        for e in state.weekly_advances
                        if e.command_id == cmd.command_id
                    ),
                    None,
                )
                if existing:
                    # Reconstruct the original reviewed predecessor for exact retries,
                    # including retries after Save, later matches, or horizon extension.
                    from beta_engine.domain.players.calendar_continuation_match import (
                        append_continuation,
                    )
                    from beta_engine.domain.players.calendar_engine_player import (
                        calendar_engine_player,
                    )
                    from beta_engine.domain.players.calendar_sporting_checkpoint import (
                        build_calendar_sporting_checkpoint,
                    )
                    from beta_engine.domain.players.calendar_followup_knockout import (
                        CalendarFollowupKnockout, append_followup_knockout,
                    )

                    knockout = getattr(evidence, "knockout", evidence)
                    prefix = build_calendar_sporting_checkpoint(
                        world, knockout, calendar_engine_player
                    )
                    for event in (*state.continuations, *state.week_events):
                        if event is existing:
                            break
                        prefix = (
                            append_sporting_week(prefix, world, knockout, event)
                            if isinstance(event, CalendarSportingWeekAdvance)
                            else append_followup_knockout(prefix, world, event)
                            if isinstance(event, CalendarFollowupKnockout)
                            else append_continuation(prefix, world, event)
                        )
                    from types import SimpleNamespace

                    original, _ = self._preview(
                        existing.completed_week.calendar,
                        SimpleNamespace(
                            saved_head_revision_id=existing.source_saved_head
                        ),
                        world,
                        prefix,
                        prefix,
                        evidence,
                        cmd,
                    )
                    if (
                        original["advance"] != existing.model_dump(mode="json")
                        or original["preview_fingerprint"]
                        != request.expected_preview_fingerprint
                    ):
                        raise ValueError(
                            "Sporting advance identity reused with different command/review"
                        )
                    return original
            preview, successor = self._preview(
                clock, revision, world, state, saved, evidence, cmd
            )
            if preview["preview_fingerprint"] != request.expected_preview_fingerprint:
                raise ValueError("Sporting advance changed since review")
            replace_checkpoint(session, previous=state, successor=successor)
            return preview

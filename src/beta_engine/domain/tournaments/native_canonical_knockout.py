"""Versioned native same-week canonical Q/Main inputs; results stay in v13 slots."""

from __future__ import annotations

import json
from functools import cached_property
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_continuation_match import (
    CalendarContinuationMatch,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.rankings.points import is_valid_ranking_point
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.canonical_knockout_feeders import (
    CanonicalKnockoutFeederPlan,
    freeze_knockout_feeder_plan,
    project_knockout_progress,
)
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
)
from beta_engine.domain.tournaments.fax_reference_bracket_topology import (
    build_fax_reference_bracket_topology,
)
from beta_engine.domain.tournaments.fax_reference_player_draw import (
    FaxReferencePlayerDraw,
)
from beta_engine.domain.tournaments.models import SeasonCalendarEvent


class NativeCanonicalRoundSchedule(FrozenInput):
    schema_version: Literal["native_canonical_round_schedule.v1"] = (
        "native_canonical_round_schedule.v1"
    )
    qualification: tuple[int, ...]
    main: tuple[int, ...]

    @model_validator(mode="after")
    def chronology(self):
        slots = (*self.qualification, *self.main)
        if (
            not self.qualification
            or not self.main
            or any(type(s) is not int or s < 1 for s in slots)
            or slots != tuple(sorted(set(slots)))
        ):
            raise ValueError(
                "Explicit Q/Main round slots must be positive, unique and strictly chronological"
            )
        return self


class NativeCanonicalDrawBinding(FrozenInput):
    """Store each Draw only once in its Edition authority, never a second ledger."""

    schema_version: Literal["native_canonical_draw_binding.v1"] = (
        "native_canonical_draw_binding.v1"
    )
    saved_revision_id: str = Field(min_length=1)
    saved_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_plan_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    run_package_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calendar_projection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_event: SeasonCalendarEvent
    draw_input: TournamentDrawInputAuthority
    calendar: RunCalendar
    schedule: NativeCanonicalRoundSchedule

    @classmethod
    def from_plan(cls, plan, schedule):
        return cls(
            saved_revision_id=plan.source_saved_revision_id,
            saved_content_hash=plan.source_saved_content_hash,
            source_plan_fingerprint=plan.fingerprint,
            run_package_state_fingerprint=plan.source.run_package_state_fingerprint,
            calendar_projection_fingerprint=plan.source.calendar_projection_fingerprint,
            source_event=plan.source.source_event,
            draw_input=plan.source.draw_input,
            calendar=plan.calendar,
            schedule=schedule,
        )

    def plan(self, draw: TournamentDrawAuthority) -> CanonicalKnockoutFeederPlan:
        source = FaxReferencePlayerDraw(
            run_package_state_fingerprint=self.run_package_state_fingerprint,
            calendar_projection_fingerprint=self.calendar_projection_fingerprint,
            source_event=self.source_event,
            draw_input=self.draw_input,
            draw=draw,
        )
        plan = freeze_knockout_feeder_plan(
            source=source,
            source_saved_revision_id=self.saved_revision_id,
            source_saved_content_hash=self.saved_content_hash,
            calendar=self.calendar,
        )
        if plan.fingerprint != self.source_plan_fingerprint:
            raise ValueError(
                "Native canonical Draw differs from its exact Saved feeder plan"
            )
        if len(self.schedule.main) != draw.main.bracket_size.bit_length() - 1 or any(
            len(self.schedule.qualification) != q.bracket_size.bit_length() - 1
            for q in draw.qualification_brackets
        ):
            raise ValueError(
                "Native canonical schedule must explicitly cover every physical round"
            )
        return plan

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def is_canonical_edition(authority):
    return authority.edition.schema_version == "calendar_tournament_edition.v4"


def saved_ranked_point_table(event):
    """Validate the exact reachable stages; never infer awards from defaults."""
    if event.ranking_status != "ranked":
        raise ValueError("Native canonical point projection requires a Ranked source")
    required = build_fax_reference_bracket_topology(event).ranked_point_stages
    table = event.ranking_points_table
    missing = [stage for stage in required if stage not in table]
    invalid = [
        stage for stage in required
        if stage in table and not is_valid_ranking_point(table[stage])
    ]
    if missing or invalid:
        raise ValueError(
            f"Saved Ranked point table incomplete; missing={missing}, invalid={invalid}"
        )
    return {stage: table[stage] for stage in required}


def validate_ranked_publication_week(week):
    if week.calendar.weeks_per_year != 61 or week.season_index >= 50:
        raise ValueError("Canonical Ranked awards require the existing 61-week ranking clock")
    if week.ordinal + 1 == week.calendar.weeks_per_year * week.calendar.season_count:
        raise ValueError("Canonical Ranked awards require a following publication week")


def canonical_edition_plan(authority, matches):
    plan = authority.canonical_binding.plan(authority.draw)
    # Edition IDs can share a prefix. Only exact executable nodes belong here.
    selected = tuple(
        matches[node.match_id]
        for node in plan.topology.plans
        if node.match_id in matches
    )
    progress = native_progress(plan, selected)
    ready = {m.match_id: m.player_ids for m in progress.ready_matches}
    accepted = {
        m.match_id: (m.result.player_a_id, m.result.player_b_id) for m in selected
    }
    metadata = {
        n.node_id: (b.draw_type, n.round_number)
        for b in (*authority.draw.qualification_brackets, authority.draw.main)
        for n in b.nodes
    }
    return tuple(
        (
            p.match_id,
            (
                authority.canonical_binding.schedule.qualification
                if metadata[p.match_id][0] == "qualification"
                else authority.canonical_binding.schedule.main
            )[metadata[p.match_id][1] - 1],
            ready.get(p.match_id, accepted.get(p.match_id, ())),
            5,
        )
        for p in plan.topology.plans
    )


class NativeCanonicalTournamentResult(FrozenInput):
    schema_version: Literal["native_canonical_tournament_result.v1", "native_canonical_tournament_result.v2"] = (
        "native_canonical_tournament_result.v1"
    )
    run_id: str
    branch_id: str
    tournament_id: str
    week: RunWeekPosition
    command_id: str
    source_saved_head: str
    source_checkpoint_fingerprint: str
    seed: int
    operator_label: str
    audit_reason: str
    request_fingerprint: str
    entrant_ids: tuple[str, ...]
    matches: tuple[CalendarContinuationMatch, ...]
    edition_authority_fingerprint: str
    binding: NativeCanonicalDrawBinding
    draw: TournamentDrawAuthority
    scope: Literal["configured_canonical_knockout"] = "configured_canonical_knockout"
    prepared_awards: tuple = ()

    @model_validator(mode="after")
    def actual_terminal(self):
        plan = self.binding.plan(self.draw)
        progress = native_progress(plan, self.matches)
        expected = tuple(
            sorted(
                (
                    *self.binding.draw_input.direct_main_player_ids,
                    *self.binding.draw_input.wild_card_player_ids,
                    *self.binding.draw_input.qualification_player_ids,
                )
            )
        )
        if (
            (self.run_id, self.branch_id, self.tournament_id, self.source_saved_head)
            != (
                self.draw.run_id,
                self.draw.branch_id,
                self.draw.event_id,
                self.binding.saved_revision_id,
            )
            or self.entrant_ids != expected
            or not progress.champion_player_id
            or progress.ready_matches
        ):
            raise ValueError(
                "Canonical native terminal is incomplete or detached from its source"
            )
        ranked = self.schema_version == "native_canonical_tournament_result.v2"
        if self.prepared_awards or self.binding.source_event.ranking_status != (
            "ranked" if ranked else "unranked"
        ):
            raise ValueError(
                "Canonical native result version differs from its Saved ranking status"
            )
        if ranked:
            validate_ranked_publication_week(self.week)
        return self

    @cached_property
    def ranking_awards(self):
        """Derived on demand from the exact ledger; no second persisted award store."""
        if self.schema_version != "native_canonical_tournament_result.v2":
            return ()
        from beta_engine.application.native_canonical_ranked_awards import (
            prepare_native_canonical_ranked_awards,
        )

        return prepare_native_canonical_ranked_awards(
            plan=self.binding.plan(self.draw), matches=self.matches
        ).awards.awards

    @property
    def winner_player_id(self):
        terminal = self.binding.plan(self.draw).topology.terminal_group_id
        return next(
            m.result.winner_player_id for m in self.matches if m.match_id == terminal
        )

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))

    @property
    def sporting_fingerprint(self):
        return self.fingerprint


def completed_canonical_result(authority, slots, *, owner=None):
    plan = authority.canonical_binding.plan(authority.draw)
    event_id = authority.edition.edition_id
    selected = []
    for slot in slots:
        # Use the frozen slot owner, so an invalid node assigned to this Edition
        # still reaches the feeder validator. Ignore only other Editions' matches.
        scheduled_ids = {
            match.match_id for match in slot.scheduled if match.edition_id == event_id
        }
        if scheduled_ids:
            selected.extend(m for m in slot.accepted if m.match_id in scheduled_ids)
    # Never hide a duplicated ledger record by collapsing it to a dictionary.
    progress = native_progress(plan, tuple(selected))
    records = {m.match_id: m for m in selected}
    if not progress.champion_player_id:
        return None
    first = next(s for s in slots if any(m.edition_id == event_id for m in s.scheduled))
    if owner is not None and owner != first.branch_id:
        raise ValueError(
            "Canonical native fork continuation requires its versioned source remapping"
        )
    return NativeCanonicalTournamentResult(
        schema_version=(
            "native_canonical_tournament_result.v2"
            if authority.edition.ranked
            else "native_canonical_tournament_result.v1"
        ),
        run_id=first.run_id,
        branch_id=first.branch_id,
        tournament_id=authority.edition.edition_id,
        week=first.week,
        command_id="global-tournament:" + authority.execution_fingerprint,
        source_saved_head=plan.source_saved_revision_id,
        source_checkpoint_fingerprint=first.source_checkpoint_fingerprint,
        seed=authority.edition.simulation_seed,
        operator_label="Global Simulation Slots",
        audit_reason="Actual canonical Q/Main matches from the shared frozen ledger",
        request_fingerprint=authority.execution_fingerprint,
        entrant_ids=tuple(
            sorted(
                (
                    *plan.source.draw_input.direct_main_player_ids,
                    *plan.source.draw_input.wild_card_player_ids,
                    *plan.source.draw_input.qualification_player_ids,
                )
            )
        ),
        matches=tuple(records[mid] for mid in sorted(records)),
        edition_authority_fingerprint=authority.execution_fingerprint,
        binding=authority.canonical_binding,
        draw=authority.draw,
    )


def canonical_announcement_week(binding):
    raw = binding.source_event.event_level_overrides.get("native_announcement_week")
    if raw is None:
        raise ValueError(
            "Saved source requires an explicit historical native_announcement_week; no date is inferred"
        )
    week = RunWeekPosition.model_validate_json(json.dumps(raw))
    source_clock, current = week.calendar, binding.calendar
    if (
        source_clock.weeks_per_year,
        source_clock.season_start_year_week,
        source_clock.start_year,
        source_clock.schema_version,
    ) != (
        current.weeks_per_year,
        current.season_start_year_week,
        current.start_year,
        current.schema_version,
    ) or source_clock.season_count > current.season_count:
        raise ValueError("Saved announcement uses a different or later Run calendar")
    # This is a NEW operational Edition under the actual Saved clock. Preserve
    # the source's original date bytes; only project its identical ordinal into
    # a compatible extended horizon, never clamp or reinterpret its time basis.
    return RunWeekPosition(
        calendar=current, season_index=week.season_index, week=week.week
    )


def native_progress(plan, matches):
    clock = max(
        (m.week.calendar for m in matches),
        default=plan.calendar,
        key=lambda c: c.season_count,
    )
    return project_knockout_progress(plan=plan, matches=matches, runtime_calendar=clock)

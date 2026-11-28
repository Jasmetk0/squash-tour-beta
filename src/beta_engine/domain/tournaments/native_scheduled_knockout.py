"""Native cross-week Q/Main Edition bound to one copied Saved ATP knockout profile.

The Saved profile supplies geometry, seeds, Wild Card capacity and points; the
explicit Run round schedule supplies chronology. Entry, Wild Cards and the Draw
are made through the ordinary native Tour commands. Matches stay in the shared
global slot ledger; this module owns no second result or award store.
"""

from __future__ import annotations

from functools import cached_property
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_continuation_match import (
    CalendarContinuationMatch,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.atp_knockout_profile import ATPKnockoutProfile
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
)
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity
from beta_engine.domain.tournaments.knockout_run_schedule import (
    KnockoutRoundPosition,
    KnockoutRunSchedule,
)

SCHEDULED_EDITION_SCHEMA = "calendar_tournament_edition.v5"
SCHEDULED_RESULT_SCHEMA = "native_scheduled_knockout_result.v1"
SCHEDULED_DRAW_INPUT_SCHEMA = "tournament_draw_input_authority.v3"


class NativeScheduledKnockoutBinding(FrozenInput):
    """Exact copied profile + reviewed round schedule; never current server files."""

    schema_version: Literal["native_scheduled_knockout_binding.v1"] = (
        "native_scheduled_knockout_binding.v1"
    )
    source_saved_revision_id: str = Field(min_length=1)
    source_saved_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_profile_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    profile_payload_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    profile: ATPKnockoutProfile
    schedule: KnockoutRunSchedule

    @model_validator(mode="after")
    def validate_binding(self):
        if canonical_hash(self.profile.model_dump(mode="json")) != self.profile_payload_fingerprint:
            raise ValueError("Scheduled Edition sporting profile changed after Saved review")
        if self.profile.qualification_date_status != "verified":
            raise ValueError(
                "Native cross-week knockout requires sourced, verified Qualification dates"
            )
        if self.profile.byes:
            raise ValueError("Native scheduled knockout V1 supports only BYE-free source fields")
        geometry = self.profile.geometry()
        self.schedule.validate_capacities(
            main_capacity=geometry["main"]["bracket_capacity"],
            qualification_capacities=tuple(
                s["bracket_capacity"] for s in geometry["qualification_sections"]
            ),
        )
        if not self.schedule.qualification:
            raise ValueError("Native scheduled knockout requires its Qualification rounds")
        return self

    @property
    def capacity(self) -> TournamentEntryFieldCapacity:
        return TournamentEntryFieldCapacity.for_main_entrant_count(
            main_entrant_count=self.profile.main_entrants,
            qualification_draw_size=self.profile.qualification_entrants,
            qualifier_spots=self.profile.qualifier_spots,
            wild_card_slots=self.profile.wild_cards,
        )

    @property
    def first_round(self) -> KnockoutRoundPosition:
        return self.schedule.qualification[0]

    @property
    def final_round(self) -> KnockoutRoundPosition:
        return self.schedule.main[-1]

    @property
    def play_week_ordinals(self) -> frozenset[int]:
        return frozenset(
            r.week.ordinal for r in (*self.schedule.qualification, *self.schedule.main)
        )

    def plan(self, *, draw_input: TournamentDrawInputAuthority, draw: TournamentDrawAuthority):
        from beta_engine.domain.tournaments.scheduled_knockout_feeders import (
            ScheduledKnockoutFeederPlan,
        )

        return ScheduledKnockoutFeederPlan(
            source_saved_revision_id=self.source_saved_revision_id,
            source_saved_content_hash=self.source_saved_content_hash,
            source_profile_fingerprint=self.source_profile_fingerprint,
            profile=self.profile,
            profile_payload_fingerprint=self.profile_payload_fingerprint,
            draw_input=draw_input,
            draw=draw,
            schedule=self.schedule,
        )

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def is_scheduled_edition(authority) -> bool:
    return authority.edition.schema_version == SCHEDULED_EDITION_SCHEMA


def scheduled_point_table(profile: ATPKnockoutProfile) -> dict[str, int]:
    from beta_engine.application.scheduled_knockout_results import (
        scheduled_point_distribution,
    )

    return dict(sorted(scheduled_point_distribution(profile).items()))


def scheduled_announcement_week(binding: NativeScheduledKnockoutBinding) -> RunWeekPosition:
    """Native minimum: public one complete week before the first Q round.

    The copied knockout profile has no announcement date. This keeps the
    existing native lead (public at the preceding Week Transition) instead of
    inventing an ATP entry deadline; see the Draft for the open product option.
    """
    first = binding.first_round.week
    if first.ordinal < 1:
        raise ValueError("Scheduled knockout announcement precedes the Run")
    p = first.calendar.position_at_ordinal(first.ordinal - 1)
    return RunWeekPosition(calendar=first.calendar, season_index=p.season_index, week=p.season_week)


_PLAN_MEMO: dict[int, tuple] = {}


def scheduled_draw_input(authority) -> TournamentDrawInputAuthority:
    from beta_engine.domain.tournaments.draw_input_authority import (
        TournamentDrawInputAuthorityBuilder,
    )

    return TournamentDrawInputAuthorityBuilder.build(
        authority=authority.ranking_authority,
        field=authority.field,
        field_sequence=1,
        command_id=authority.draw_command_id,
        draw_seed=authority.draw_seed,
        main_seed_count=authority.scheduled_binding.profile.seeds_count,
        qualification_seed_count=None,
        schema_version=SCHEDULED_DRAW_INPUT_SCHEMA,
        wild_card_authority=authority.wild_card_authority,
    )


def scheduled_edition_plan(authority):
    """Reconstruct the frozen plan from the Edition's own committed authority.

    Memoized per immutable authority object; the identity check prevents a
    recycled ``id`` from returning a different Edition's plan.
    """
    known = _PLAN_MEMO.get(id(authority))
    if known is not None and known[0] is authority:
        return known[1]
    if authority.draw is None:
        raise ValueError("Scheduled knockout has no committed Draw")
    plan = authority.scheduled_binding.plan(
        draw_input=scheduled_draw_input(authority), draw=authority.draw
    )
    _PLAN_MEMO[id(authority)] = (authority, plan)
    while len(_PLAN_MEMO) > 64:
        _PLAN_MEMO.pop(next(iter(_PLAN_MEMO)))
    return plan


def scheduled_expected_positions(plan) -> dict[str, KnockoutRoundPosition]:
    from beta_engine.domain.tournaments.knockout_run_schedule import plan_knockout_run_matches
    import json

    rows = plan_knockout_run_matches(draw=plan.draw, schedule=plan.schedule)["matches"]
    return {
        r["match_id"]: KnockoutRoundPosition.model_validate_json(json.dumps(r["position"]))
        for r in rows
    }


def scheduled_runtime_position(position: KnockoutRoundPosition, calendar) -> KnockoutRoundPosition:
    return KnockoutRoundPosition(
        week=RunWeekPosition(
            calendar=calendar,
            season_index=position.week.season_index,
            week=position.week.week,
        ),
        slot=position.slot,
    )


def scheduled_slot_rows(authority, accepted, *, week):
    """(match_id, slot, players, best_of) of this Run week's executable matches.

    ``accepted`` maps match id to already accepted ledger records. Earlier
    rounds must be complete; a later week's rounds are never offered early.
    """
    from beta_engine.domain.tournaments.scheduled_knockout_feeders import (
        scheduled_knockout_progress,
    )

    plan = scheduled_edition_plan(authority)
    expected = scheduled_expected_positions(plan)
    matches = tuple(accepted[mid] for mid in sorted(expected) if mid in accepted)
    positions = {
        m.match_id: scheduled_runtime_position(expected[m.match_id], m.week.calendar)
        for m in matches
    }
    pending = sorted(
        (pos.chronological_key, mid) for mid, pos in expected.items() if mid not in accepted
    )
    if not pending:
        return ()
    first_key = pending[0][0]
    first = next(expected[mid] for key, mid in pending if key == first_key)
    if first.week.ordinal < week.ordinal:
        raise ValueError("An earlier scheduled knockout week is incomplete")
    current = scheduled_runtime_position(first, week.calendar)
    progress, due = scheduled_knockout_progress(
        plan=plan, matches=matches, positions=positions, current=current
    )
    ready = {m.match_id: m.player_ids for m in due}
    done = {m.match_id: (m.result.player_a_id, m.result.player_b_id) for m in matches}
    return tuple(
        (mid, pos.slot, ready.get(mid, done.get(mid, ())), 5)
        for mid, pos in sorted(expected.items(), key=lambda item: (item[1].chronological_key, item[0]))
        if pos.week.ordinal == week.ordinal
    )


class NativeScheduledTournamentResult(FrozenInput):
    """Terminal view derived from the global slot ledger; no second store."""

    schema_version: Literal["native_scheduled_knockout_result.v1"] = SCHEDULED_RESULT_SCHEMA
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
    binding: NativeScheduledKnockoutBinding
    draw_input: TournamentDrawInputAuthority
    draw: TournamentDrawAuthority
    scope: Literal["scheduled_atp_knockout"] = "scheduled_atp_knockout"
    prepared_awards: tuple = ()

    @model_validator(mode="after")
    def actual_terminal(self):
        plan = self.plan
        expected = tuple(sorted((
            *self.draw_input.direct_main_player_ids,
            *self.draw_input.wild_card_player_ids,
            *self.draw_input.qualification_player_ids,
        )))
        terminal = plan.topology.terminal_group_id
        final = next((m for m in self.matches if m.match_id == terminal), None)
        if (
            (self.run_id, self.branch_id, self.tournament_id, self.source_saved_head)
            != (self.draw.run_id, self.draw.branch_id, self.draw.event_id, self.binding.source_saved_revision_id)
            or self.entrant_ids != expected
            or self.prepared_awards
            or final is None
            or final.week != self.week
            or tuple(m.match_id for m in self.matches) != tuple(sorted({m.match_id for m in self.matches}))
        ):
            raise ValueError("Scheduled native terminal is incomplete or detached from its source")
        # Full result/feeder validation; raises unless all 43 nodes are complete.
        self.ranking_results
        return self

    @cached_property
    def plan(self):
        return self.binding.plan(draw_input=self.draw_input, draw=self.draw)

    @property
    def positions(self):
        expected = scheduled_expected_positions(self.plan)
        return {
            m.match_id: scheduled_runtime_position(expected[m.match_id], m.week.calendar)
            for m in self.matches
        }

    @property
    def runtime_calendar(self):
        return max((m.week.calendar for m in self.matches), key=lambda c: c.season_count)

    @cached_property
    def ranking_results(self):
        """(ScheduledKnockoutResult, CalendarRankingResult rows), Q+Main counted once."""
        from beta_engine.application.scheduled_knockout_results import (
            scheduled_knockout_ranking_results,
        )

        return scheduled_knockout_ranking_results(
            plan=self.plan, matches=self.matches, positions=self.positions,
            runtime_calendar=self.runtime_calendar,
        )

    @cached_property
    def ranking_awards(self):
        from beta_engine.application.canonical_tournament_points import (
            build_knockout_player_point_awards,
        )
        from beta_engine.application.scheduled_knockout_results import (
            scheduled_point_distribution,
        )
        from beta_engine.application.season_point_awards_service import (
            FrozenPointAwardAuthority,
        )

        result, _rows = self.ranking_results
        return build_knockout_player_point_awards(
            result=result,
            point_authority=FrozenPointAwardAuthority(
                ranking_status="ranked",
                point_distribution=scheduled_point_distribution(self.binding.profile),
                point_distribution_source="saved_atp_knockout_profile.v1",
            ),
            seed=self.draw_input.draw_seed,
        )

    @property
    def winner_player_id(self):
        terminal = self.plan.topology.terminal_group_id
        return next(m.result.winner_player_id for m in self.matches if m.match_id == terminal)

    @property
    def qualification_winner_ids(self):
        return self.ranking_results[0].qualification_winner_ids

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))

    @property
    def sporting_fingerprint(self):
        return self.fingerprint


def completed_scheduled_result(authority, slots, *, owner=None):
    """Terminal result once every executable node is accepted in the ledger."""
    event_id = authority.edition.edition_id
    selected = []
    first = None
    for slot in slots:
        scheduled_ids = {m.match_id for m in slot.scheduled if m.edition_id == event_id}
        if scheduled_ids:
            first = first or slot
            selected.extend(m for m in slot.accepted if m.match_id in scheduled_ids)
    if first is None or authority.draw is None:
        return None
    plan = scheduled_edition_plan(authority)
    if len({m.match_id for m in selected}) != len(selected):
        raise ValueError("Scheduled knockout ledger repeats an accepted match")
    if len(selected) != len(plan.topology.plans):
        return None
    if owner is not None and owner != first.branch_id:
        raise ValueError("Scheduled native fork continuation requires its versioned source remapping")
    records = {m.match_id: m for m in selected}
    final = records[plan.topology.terminal_group_id]
    return NativeScheduledTournamentResult(
        run_id=first.run_id,
        branch_id=first.branch_id,
        tournament_id=event_id,
        week=final.week,
        command_id="global-tournament:" + authority.execution_fingerprint,
        source_saved_head=plan.source_saved_revision_id,
        source_checkpoint_fingerprint=first.source_checkpoint_fingerprint,
        seed=authority.edition.simulation_seed,
        operator_label="Global Simulation Slots",
        audit_reason="Actual scheduled Q/Main matches from the shared frozen ledger",
        request_fingerprint=authority.execution_fingerprint,
        entrant_ids=tuple(sorted((
            *plan.draw_input.direct_main_player_ids,
            *plan.draw_input.wild_card_player_ids,
            *plan.draw_input.qualification_player_ids,
        ))),
        matches=tuple(records[mid] for mid in sorted(records)),
        edition_authority_fingerprint=authority.execution_fingerprint,
        binding=authority.scheduled_binding,
        draw_input=plan.draw_input,
        draw=authority.draw,
    )

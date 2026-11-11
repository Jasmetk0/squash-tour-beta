"""Frozen Saved Draw → readiness from the existing actual-match ledger.

This pure projection owns no results, player state, time progression or Save.
The native slot consumer must authenticate its ledger and enforce scheduling,
Health and points prerequisites before playing/accepting any returned match.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.calendar_continuation_match import (
    CalendarContinuationMatch,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.canonical_knockout_topology import (
    CanonicalTournamentTopologyProjection,
    project_canonical_draw_nodes,
)
from beta_engine.domain.tournaments.fax_reference_player_draw import (
    FaxReferencePlayerDraw,
)


class CanonicalKnockoutFeederPlan(FrozenInput):
    schema_version: Literal["canonical_knockout_feeder_plan.v1"] = (
        "canonical_knockout_feeder_plan.v1"
    )
    source_saved_revision_id: str = Field(min_length=1)
    source_saved_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: FaxReferencePlayerDraw
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calendar: RunCalendar
    topology: CanonicalTournamentTopologyProjection

    @model_validator(mode="after")
    def validate_frozen_draw(self) -> CanonicalKnockoutFeederPlan:
        # A caller may retain a mutable nested CalendarEvent: never trust that it
        # stayed frozen merely because the outer Pydantic object is frozen.
        source = FaxReferencePlayerDraw.model_validate_json(
            self.source.model_dump_json()
        )
        if source.fingerprint != self.source_fingerprint:
            raise ValueError("Frozen feeder source fingerprint changed")
        if self.topology != project_canonical_draw_nodes(draw=source.draw):
            raise ValueError("Frozen feeder topology differs from its canonical Draw")
        year = int(str(source.source_event.season).split("/")[0])
        self.calendar.ordinal(
            year - self.calendar.start_year, source.source_event.season_week
        )
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))

    def match_seed(self, match_id: str) -> int:
        if match_id not in {p.match_id for p in self.topology.plans}:
            raise ValueError("Seed requires a real executable Draw node, never BYE")
        # Stable sporting identity, excluding command IDs, collection order,
        # active head, Branch display/ownership and the current progress prefix.
        return int(
            canonical_hash(
                {
                    "schema_version": "canonical_knockout_match_seed.v1",
                    "root": self.source.draw_input.draw_seed,
                    "edition": self.source.draw.event_id,
                    "season": str(self.source.source_event.season),
                    "match": match_id,
                }
            )[:15],
            16,
        )


def freeze_knockout_feeder_plan(
    *,
    source: FaxReferencePlayerDraw,
    source_saved_revision_id: str,
    source_saved_content_hash: str,
    calendar: RunCalendar,
) -> CanonicalKnockoutFeederPlan:
    # Own a fresh snapshot; mutation of the live DTO must not retcon this plan.
    snapshot = FaxReferencePlayerDraw.model_validate_json(source.model_dump_json())
    return CanonicalKnockoutFeederPlan(
        source_saved_revision_id=source_saved_revision_id,
        source_saved_content_hash=source_saved_content_hash,
        source=snapshot,
        source_fingerprint=snapshot.fingerprint,
        calendar=calendar,
        topology=project_canonical_draw_nodes(draw=snapshot.draw),
    )


class ReadyCanonicalKnockoutMatch(FrozenInput):
    match_id: str
    draw_type: Literal["qualification", "main"]
    section_id: str | None
    round_number: int = Field(ge=1)
    player_ids: tuple[str, str]
    seed: int


class CanonicalKnockoutProgress(FrozenInput):
    schema_version: Literal["canonical_knockout_progress.v1"] = (
        "canonical_knockout_progress.v1"
    )
    readiness_scope: Literal["feeder_dependencies_only"] = "feeder_dependencies_only"
    native_slot_execution_ready: Literal[False] = False
    source_plan_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted_match_ids: tuple[str, ...]
    ready_matches: tuple[ReadyCanonicalKnockoutMatch, ...]
    qualification_winners: tuple[tuple[str, str], ...]
    bye_advances: tuple[tuple[str, str], ...]
    main_blocked_by_qualification: bool
    champion_player_id: str | None


def project_knockout_progress(
    *,
    plan: CanonicalKnockoutFeederPlan,
    matches: tuple[CalendarContinuationMatch, ...],
    runtime_calendar: RunCalendar | None = None,
) -> CanonicalKnockoutProgress:
    """Validate event-only records; input order never determines feeder winners.

    Record cryptographic/MatchEngine replay and canonical player-state validation
    remain owned by the existing ledger loader/slot executor. We validate graph,
    owner, source, seed, players and chronological dependencies, not calibration.
    """
    plan.validate_frozen_draw()
    year = int(str(plan.source.source_event.season).split("/")[0])
    return _project_draw_progress(
        plan=plan, draw=plan.source.draw, source_season_index=year-plan.calendar.start_year,
        matches=matches, runtime_calendar=runtime_calendar,
    )


def _project_draw_progress(*, plan, draw, source_season_index, matches, runtime_calendar=None):
    """Shared source-neutral graph rules; public adapters validate source identity."""
    # The new native consumer may continue under a strict horizon extension.
    # Historical callers omit this argument and retain exact-calendar semantics.
    def compatible(clock):
        return (
            clock.weeks_per_year,
            clock.season_start_year_week,
            clock.start_year,
            clock.schema_version,
        ) == (
            plan.calendar.weeks_per_year,
            plan.calendar.season_start_year_week,
            plan.calendar.start_year,
            plan.calendar.schema_version,
        ) and clock.season_count >= plan.calendar.season_count

    if runtime_calendar is not None and not compatible(runtime_calendar):
        raise ValueError(
            "Canonical runtime calendar may only extend the source horizon"
        )
    topology = plan.topology
    records = {m.match_id: m for m in matches}
    executable = {p.match_id: p for p in topology.plans}
    if len(records) != len(matches) or not set(records) <= set(executable):
        raise ValueError("Duplicate, foreign or BYE match in canonical feeder ledger")
    if len({(m.week.ordinal, m.sequence) for m in matches}) != len(matches):
        raise ValueError("Canonical feeder ledger repeats chronological sequence")
    done: dict[str, str] = dict(topology.bye_winners)
    terminals = {
        b.section_id: max(b.nodes, key=lambda n: n.round_number).node_id
        for b in draw.qualification_brackets
    }
    q_complete = all(mid in done or mid in records for mid in terminals.values())
    if not q_complete and any(
        mid in records for mid in (n.node_id for n in draw.main.nodes)
    ):
        raise ValueError("Main cannot start before the complete Qualification")
    ready = []
    metadata = [
        (b, node)
        for b in (*draw.qualification_brackets, draw.main)
        for node in sorted(b.nodes, key=lambda n: (n.round_number, n.round_sequence))
    ]
    for bracket, node in metadata:
        match_id = node.node_id
        if match_id not in executable:
            continue  # BYE is only a source collapse, never a match or result.
        item = executable[match_id]
        dependencies = tuple(
            s.removeprefix("winner:")
            for s in item.participant_sources
            if s.startswith("winner:")
        )
        ids = tuple(
            s.removeprefix("player:")
            if s.startswith("player:")
            else done.get(s.removeprefix("winner:"))
            for s in item.participant_sources
        )
        permitted = all(ids) and (bracket.draw_type == "qualification" or q_complete)
        record = records.get(match_id)
        if record is None:
            if permitted:
                if len(set(ids)) != 2:
                    raise ValueError("Canonical feeder resolves duplicate opponents")
                ready.append(
                    ReadyCanonicalKnockoutMatch(
                        match_id=match_id,
                        draw_type=bracket.draw_type,
                        section_id=bracket.section_id,
                        round_number=node.round_number,
                        player_ids=ids,
                        seed=plan.match_seed(match_id),
                    )
                )
            continue
        if not permitted:
            raise ValueError("Recorded canonical match has an unresolved feeder")
        if (record.run_id, record.branch_id, record.source_saved_head) != (
            draw.run_id,
            draw.branch_id,
            plan.source_saved_revision_id,
        ) or (
            record.week.calendar != plan.calendar
            if runtime_calendar is None
            else not compatible(record.week.calendar)
            or record.week.calendar.season_count > runtime_calendar.season_count
        ):
            raise ValueError(
                "Canonical match differs from frozen Run/Branch/Calendar/Saved source"
            )
        if record.week.season_index != source_season_index:
            raise ValueError("Canonical match belongs to another source season")
        if record.seed != plan.match_seed(match_id):
            raise ValueError(
                "Canonical match seed differs from frozen sporting identity"
            )
        if (record.result.player_a_id, record.result.player_b_id) != ids:
            raise ValueError(
                "Canonical match did not consume its exact feeder opponents"
            )
        record.validate_evidence()
        if record.schema_version != "calendar_continuation_match.v2":
            raise ValueError(
                "Canonical knockout requires existing BO5 continuation evidence v2"
            )
        predecessors = list(dependencies)
        if bracket.draw_type == "main":
            predecessors += list(terminals.values())
        for predecessor in set(predecessors):
            prior = records.get(predecessor)
            if prior is None:
                if predecessor in topology.bye_match_ids:
                    continue
                raise ValueError("Canonical match has a missing accepted predecessor")
            if (prior.week.ordinal, prior.sequence) >= (
                record.week.ordinal,
                record.sequence,
            ):
                raise ValueError(
                    "Canonical match precedes a required feeder/Qualification result"
                )
            if (
                prior.source_checkpoint_fingerprint
                == record.source_checkpoint_fingerprint
            ):
                raise ValueError(
                    "Dependent rounds cannot share the predecessor's frozen input snapshot"
                )
        done[match_id] = record.result.winner_player_id
    return CanonicalKnockoutProgress(
        source_plan_fingerprint=plan.fingerprint,
        accepted_match_ids=tuple(sorted(records)),
        ready_matches=tuple(sorted(ready, key=lambda m: m.match_id)),
        qualification_winners=tuple(
            (q, done[mid]) for q, mid in terminals.items() if mid in done
        ),
        bye_advances=topology.bye_winners,
        main_blocked_by_qualification=not q_complete,
        champion_player_id=done.get(topology.terminal_group_id),
    )

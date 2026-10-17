"""Read-only, Saved/SQLite-attested MatchEngine knockout ranking source (FAX only).

The *actual committed Simulation Slot/Group* is the source of every match
receipt. Unlike caller-supplied engine witnesses, this adapter independently
loads and validates the signed Saved component, and matches it byte-for-byte
with the Run/Branch's persisted live group. It never executes RNG or writes
sports/rankings, and cannot reinterpret legacy 61-week Slot ordinals as W52/W80.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.application.run_calendar_read_authority import (
    resolve_saved_run_calendar,
)
from beta_engine.domain.rankings.calendar_official import (
    CalendarOfficialRankingSnapshot,
    CalendarRankingPlayer,
    CalendarRankingWeek,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.tournaments.calendar_knockout_engine_witness import (
    CalendarEngineKnockoutEvidence,
    CalendarEngineMatchWitness,
    prepare_calendar_engine_knockout_versions,
)
from beta_engine.domain.tournaments.calendar_knockout_ranking_evidence import (
    CalendarKnockoutRankingEvidence,
)
from beta_engine.infrastructure.db.authoritative_group_state import (
    AuthoritativeGroupResult,
    load_authoritative_group,
)
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    RunBranchModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    load_saved_simulation_slot_component,
)


_GROUP_FIELDS = (
    "run_id", "branch_id", "week_ordinal", "slot_id", "group_id",
    "command_fingerprint", "match_id", "match_input_fingerprint",
    "result_fingerprint", "payload_json",
)


def _same_group(left: SimulationEventGroupModel, right: SimulationEventGroupModel) -> bool:
    return all(getattr(left, field) == getattr(right, field) for field in _GROUP_FIELDS)


def saved_slot_verified_knockout_evidence(
    session: Session,
    *,
    bracket: CalendarKnockoutRankingEvidence,
    expected_saved_head_revision_id: str,
) -> CalendarEngineKnockoutEvidence:
    """Attest a complete main-only Edition from signed Saved Slot/Group receipts.

    Supported ONLY for canonical FAX W61/offset37/start2000/50-season sporting
    ownership; other Run calendars have no compatible real match writer yet.
    The caller must already hold a physical SQLite read snapshot. Every match
    must be in a *complete* saved slot and an identical live completed group;
    missing, orphan, extra, cross-week or W/O event groups fail closed.

    Bracket geometry/point policy are caller-provided and still cannot
    authorize official ranking publication: only winners/results are now
    cryptographically tied to Saved match receipts.
    """
    if not session.in_transaction():
        raise ValueError("Saved match witness requires a caller read transaction")
    connection = session.connection()
    raw = connection.connection.driver_connection
    if connection.dialect.name != "sqlite" or raw is None or not raw.in_transaction:
        raise ValueError("Saved match witness requires a physical SQLite read snapshot")
    bracket = CalendarKnockoutRankingEvidence.model_validate_json(
        bracket.model_dump_json()
    )
    run_id, branch_id = bracket.run_id, bracket.branch_id
    if not expected_saved_head_revision_id:
        raise ValueError("Saved match witness requires an exact Saved HEAD")
    branch = session.get(RunBranchModel, branch_id)
    if branch is None or branch.run_id != run_id:
        raise ValueError("Saved match witness Run/Branch scope is unavailable")
    if branch.saved_head_revision_id != expected_saved_head_revision_id:
        raise ValueError("Saved match witness uses a stale Saved HEAD")
    if branch.forked_from_branch_id is not None:
        raise ValueError("Saved match witness fork needs a dedicated ancestry adapter")

    clock = resolve_saved_run_calendar(
        session, run_id=run_id, branch_id=branch_id,
    )
    if (
        clock.schema_version != "run_calendar.v1"
        or (clock.weeks_per_year, clock.season_start_year_week,
            clock.start_year, clock.season_count) != (61, 37, 2000, 50)
    ):
        raise ValueError(
            "Saved Slot match receipts only support the FAX W61 writer clock"
        )
    if bracket.run_calendar != clock.to_metadata():
        raise ValueError("Saved knockout bracket disagrees with the Run clock")
    completed_ordinal = clock.ordinal(
        bracket.completed_week.season_index, bracket.completed_week.week,
    )
    revision = session.get(BranchSavedRevisionModel, expected_saved_head_revision_id)
    if (
        revision is None or revision.run_id != run_id
        or revision.branch_id != branch_id
    ):
        raise ValueError("Signed Saved match origin is unavailable")
    # Exact revision hash is checked by resolve_saved_run_calendar() above.
    payload = json.loads(revision.payload_json)
    component = load_saved_simulation_slot_component(
        payload, run_id=run_id, branch_id=branch_id,
    )
    if component is None or not component.get("groups"):
        raise ValueError("Signed Saved Revision has no completed match evidence")

    # Validate *all* saved Slot semantics/hashes via the restore-grade loader.
    # Live rows must also agree exactly, including original command receipt,
    # frozen input, result and effects payload.
    slots = {
        (v["week_ordinal"], v["slot_id"]): SimulationSlotModel(**v)
        for v in component["slots"]
    }
    saved_event = {}
    for value in component["groups"]:
        row = SimulationEventGroupModel(**value)
        loaded = load_authoritative_group(row)
        if loaded.authoritative_input.event_id != bracket.edition_id:
            continue
        if not isinstance(loaded, AuthoritativeGroupResult):
            raise ValueError("Saved Edition contains unsupported W/O group")
        if (
            row.week_ordinal != completed_ordinal
            or loaded.authoritative_input.week.ordinal != completed_ordinal
        ):
            raise ValueError("Saved Edition contains a cross-week match")
        if row.match_id in saved_event:
            raise ValueError("Saved Edition has duplicate match receipt identity")
        slot = slots.get((row.week_ordinal, row.slot_id))
        if slot is None or slot.status != "complete":
            raise ValueError("Saved Edition match has no completed Simulation Slot")
        live = session.get(
            SimulationEventGroupModel,
            (run_id, branch_id, row.week_ordinal, row.slot_id, row.group_id),
        )
        if live is None or not _same_group(row, live):
            raise ValueError("Saved match receipt differs from the live group")
        saved_event[row.match_id] = (row, loaded)

    expected_ids = {m.match_id for m in bracket.matches}
    if not saved_event or set(saved_event) != expected_ids:
        raise ValueError("Saved Edition's completed match universe differs from bracket")

    # Even a live-only event group cannot be silently accepted. If it was
    # committed after the Saved HEAD, the resulting Edition is not fully saved.
    live_rows = session.scalars(
        select(SimulationEventGroupModel).where(
            SimulationEventGroupModel.run_id == run_id,
            SimulationEventGroupModel.branch_id == branch_id,
        )
    ).all()
    live_event = {
        row.match_id for row in live_rows
        if load_authoritative_group(row).authoritative_input.event_id
        == bracket.edition_id
    }
    if live_event != expected_ids:
        raise ValueError("Live Edition has unsaved or missing match receipts")

    witnesses = tuple(
        CalendarEngineMatchWitness(
            match_input_fingerprint=saved_event[m.match_id][0].match_input_fingerprint,
            authoritative_result_fingerprint=saved_event[m.match_id][0].result_fingerprint,
            result=saved_event[m.match_id][1].result,
        )
        for m in bracket.matches
    )
    return CalendarEngineKnockoutEvidence(
        bracket=bracket, witnesses=witnesses,
    )


def preview_saved_slot_verified_knockout_ranking(
    session: Session,
    *,
    bracket: CalendarKnockoutRankingEvidence,
    expected_saved_head_revision_id: str,
    week: CalendarRankingWeek,
    policy: OfficialRankingPolicy,
    players: tuple[CalendarRankingPlayer, ...],
    previous: CalendarOfficialRankingSnapshot | None = None,
):
    """Read-only ranked candidate: authenticated *matches*, not point policy.

    No staging/Official/Saved mutation and no non-FAX sporting permission.
    """
    from beta_engine.application.calendar_official_ranking_preview import (
        preview_calendar_official_ranking_from_saved_source_versions,
    )

    evidence = saved_slot_verified_knockout_evidence(
        session, bracket=bracket,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
    )
    clock = resolve_saved_run_calendar(
        session, run_id=bracket.run_id, branch_id=bracket.branch_id,
    )
    versions = prepare_calendar_engine_knockout_versions(
        evidence, run_calendar=clock,
        expected_evidence_fingerprint=evidence.fingerprint,
    )
    candidate, resolved = preview_calendar_official_ranking_from_saved_source_versions(
        session, run_id=bracket.run_id, branch_id=bracket.branch_id,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
        week=week, policy=policy, players=players,
        result_versions=versions, previous=previous,
    )
    return candidate, resolved, evidence

"""Shared Next Slot / Next Match preparation and transactional write adapter."""

from types import SimpleNamespace

from beta_engine.domain.tournaments.calendar_global_slots import (
    GlobalCompetitionCheckpoint,
    accept_slot,
    bracket,
    freeze_slot,
    next_schedule,
)


def slot_inspection(state, checkpoint):
    number, due, opened = next_schedule(state, checkpoint)
    if number is None:
        return None
    accepted = opened.accepted if opened else ()
    if opened and opened.inherited_match_ids:
        inherited = {m.match_id: m for m in checkpoint.played_continuations}
        accepted = (*accepted, *(inherited[mid] for mid in opened.inherited_match_ids))
    scheduled = opened.scheduled if opened else ()
    rows = [
        {
            "edition_id": a.edition.edition_id,
            "match_id": f"{a.edition.edition_id}:{bracket(a)[i]}",
            "player_a_id": ids[0] if ids else None,
            "player_b_id": ids[1] if ids else None,
            "completed": False,
        }
        for a, i, ids in due
    ]
    rows += [
        {
            "edition_id": next(
                s.edition_id for s in scheduled if s.match_id == m.match_id
            ),
            "match_id": m.match_id,
            "player_a_id": m.result.player_a_id,
            "player_b_id": m.result.player_b_id,
            "winner_player_id": m.result.winner_player_id,
            "completed": True,
        }
        for m in accepted
    ]
    seen = {}
    for row in rows:
        for pid in (row["player_a_id"], row["player_b_id"]):
            if pid:
                seen.setdefault(pid, []).append(row["match_id"])
    conflicts = [
        {"player_id": pid, "match_ids": sorted(mids)}
        for pid, mids in sorted(seen.items())
        if len(mids) > 1
    ]
    return {
        "conflicts": conflicts,
        "schema_version": "calendar_global_slot_inspection.v1",
        "number": number,
        "snapshot_fingerprint": opened.snapshot_fingerprint if opened else None,
        "completed": len(accepted),
        "remaining": len(due),
        "matches": sorted(rows, key=lambda m: m["match_id"]),
    }


def prepare_global_slot(
    session, ctx, state, command, *, signed=None, native_inputs=None
):
    from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
    from beta_engine.infrastructure.db.run_prospect_source_state import (
        load_saved_run_prospect_source,
    )

    _clock, revision, world, health, cp, _, _ = ctx
    if (
        not isinstance(cp, GlobalCompetitionCheckpoint)
        and getattr(cp, "schema_version", None) != "native_fork_competition.v1"
    ):
        raise ValueError(
            "Configure a shared-slot Edition before using Next Slot / Next Match"
        )
    if command.edition_id is not None or set(command.data) - {"match_id"}:
        raise ValueError(
            "Global simulation selects the nearest Branch slot, not an Edition"
        )
    if command.action == "next-slot" and command.data:
        raise ValueError("Next Slot cannot select an individual match")
    lifecycle = (
        native_inputs[0]
        if native_inputs is not None
        else get_lifecycle(
            session, run_id=state.run_id, branch_id=state.branch_id, week=cp.week
        )
    )
    source = (
        native_inputs[1]
        if native_inputs is not None
        else load_saved_run_prospect_source(
            revision.saved_revision.payload, run_id=state.run_id
        )
    )
    source = (
        source.for_week(cp.week.ordinal)
        if source is not None
        else SimpleNamespace(records=())
    )
    slot = freeze_slot(
        state,
        cp,
        world=world,
        lifecycle=lifecycle,
        health=health,
        source=source,
        head=command.expected_saved_head,
    )
    if signed is not None:
        # All draws must be present in the actual authenticated Saved source.
        frozen = {a.edition.edition_id: a for a in signed.editions}
        if any(
            a.edition.edition_id not in frozen
            or frozen[a.edition.edition_id].execution_fingerprint
            != a.execution_fingerprint
            or frozen[a.edition.edition_id].draw != a.draw
            for a in slot.authorities
        ):
            raise ValueError("Manual Save of every due Edition draw is required first")
    match_id = command.data.get("match_id")
    if command.action == "next-match":
        match_id = match_id or slot.remaining[0].match_id
        if not isinstance(match_id, str) or match_id not in {
            m.match_id for m in slot.remaining
        }:
            raise ValueError(
                "Selected match is not unresolved in the nearest global slot"
            )
    selected = [
        s.match_id for s in slot.remaining if match_id is None or s.match_id == match_id
    ]
    for item in slot.remaining:
        if item.match_id in selected and any(
            p.numeric_calibration_required for p in item.health.player_profiles
        ):
            raise ValueError(
                f"Global slot {slot.number}, {item.match_id}: unresolved numeric Health effects"
            )
    for pid, ids in slot.conflicts.items():
        if set(selected).intersection(ids):
            raise ValueError(
                f"Global slot {slot.number}: player {pid} collides in {', '.join(ids)}"
            )
    return slot, {
        "action": command.action,
        "manual_save_required": True,
        "slot": slot.number,
        "snapshot_fingerprint": slot.snapshot_fingerprint,
        "selected_match_ids": selected,
        "completed": len(slot.accepted),
        "remaining": len(slot.remaining),
    }


def apply_global_slot(session, ctx, state, command, *, persist, native_inputs=None):
    from beta_engine.application.calendar_tour_service import _fault_injection_point
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
        replace_checkpoint,
    )

    slot, impact = prepare_global_slot(
        session, ctx, state, command, native_inputs=native_inputs
    )
    cp = ctx[4]
    match_id = (
        impact["selected_match_ids"][0] if command.action == "next-match" else None
    )
    if native_inputs is not None and len(native_inputs) > 2:
        frozen_slot, successor = native_inputs[2]
        if frozen_slot != slot:
            raise ValueError("Precomputed global slot differs from actual inputs")
        completed_slot = (
            successor.global_slots[-1]
            if getattr(successor, "schema_version", None)
            == "native_fork_competition.v1"
            else successor.events[-1]
        )
    else:
        successor, completed_slot = accept_slot(cp, slot, match_id=match_id)
    if persist:
        replace_checkpoint(session, previous=cp, successor=successor)
        _fault_injection_point("after_global_slot_matches_write")
    events = {e.tournament_id: e for e in successor.tournaments}
    starts = {
        a.edition.edition_id: next(
            s.source_saved_head
            for s in slot.scheduled
            if s.edition_id == a.edition.edition_id
        )
        for a in slot.authorities
    }
    editions = tuple(
        a.model_copy(
            update={
                "played_saved_head": a.played_saved_head
                or starts[a.edition.edition_id],
                "tournament_fingerprint": events[a.edition.edition_id].fingerprint
                if a.edition.edition_id in events
                else None,
            }
        )
        if a.edition.edition_id in starts
        else a
        for a in state.editions
    )
    planned = state.model_copy(
        update={
            "checkpoint_fingerprint": successor.fingerprint,
            "slot_cursor": slot.number,
            "editions": editions,
        }
    )
    completed_editions = {
        eid: {
            "fingerprint": event.fingerprint,
            "winner_player_id": event.matches[-1].result.winner_player_id,
            "prepared_awards": [
                a.model_dump(mode="json") for a in event.prepared_awards
            ],
            "match_ids": [m.match_id for m in event.matches],
        }
        for eid, event in events.items()
        if eid in starts
        and not next(
            a for a in state.editions if a.edition.edition_id == eid
        ).tournament_fingerprint
    }
    identities = {
        p.player_id: {"name": p.name, "country_code": p.nationality}
        for m in completed_slot.accepted
        for p in m.canonical_projections
    }
    for eid in completed_editions:
        identities.update(
            {
                p.player_id: {"name": p.name, "country_code": p.nationality}
                for m in events[eid].matches
                for p in m.canonical_projections
            }
        )
    result = {
        "completed_editions": completed_editions,
        "participant_identities": identities,
        "command_id": command.command_id,
        "action": command.action,
        "manual_save_required": True,
        "impact": impact,
        "slot": completed_slot.number,
        "week": completed_slot.week.model_dump(mode="json"),
        "snapshot_fingerprint": completed_slot.snapshot_fingerprint,
        "completed": len(completed_slot.accepted),
        "remaining": len(completed_slot.remaining),
        "match_ids": impact["selected_match_ids"],
        "checkpoint_fingerprint": successor.fingerprint,
    }
    return planned, result

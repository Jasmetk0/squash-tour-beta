"""Strict v3 Tour receipt replay over a fully authenticated v11 component."""

import json

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.calendar_native_tour import CalendarNativeTourState
from beta_engine.domain.tournaments.calendar_native_tour_week import (
    prepare_native_tour_week,
)
from beta_engine.domain.tournaments.calendar_tour import CalendarTourTransition


def public_native_event(state, command, target, ranking_fingerprint):
    return {
        "kind": "season_transition_completed"
        if command.action == "season-transition"
        else "week_transition_completed",
        "week": target.model_dump(mode="json"),
        "ranking_fingerprint": ranking_fingerprint,
        "source_command_id": command.command_id,
        "announced_edition_ids": [
            a.edition.edition_id
            for a in state.editions
            if a.edition.announcement_week.ordinal == target.ordinal
        ],
    }


def verify_native_tour(state, checkpoint, world, *, payload):
    from beta_engine.application.calendar_tour_service import CalendarTourCommit
    from beta_engine.infrastructure.db.calendar_standalone_match_state import (
        _parse_saved_calendar_match_evidence,
    )
    from beta_engine.infrastructure.db.calendar_tour import verify_tour
    from beta_engine.infrastructure.db.player_health_state import load_saved_health
    from beta_engine.infrastructure.db.player_lifecycle_state import (
        load_saved_lifecycle,
    )
    from beta_engine.infrastructure.db.run_prospect_source_state import (
        load_saved_run_prospect_source,
    )

    if not isinstance(state, CalendarNativeTourState) or world is None:
        raise ValueError(
            "Native birth checkpoint requires coupled Tour transition receipt authority"
        )
    root = state.native_root_tour
    if root.checkpoint_fingerprint != checkpoint.source_checkpoint.fingerprint:
        raise ValueError("Native Tour historical root differs from its sporting root")
    verify_tour(root, checkpoint.source_checkpoint, world)
    life = load_saved_lifecycle(payload, run_id=state.run_id, branch_id=state.branch_id)
    health = load_saved_health(payload, run_id=state.run_id, branch_id=state.branch_id)
    source = load_saved_run_prospect_source(payload, run_id=state.run_id)
    evidence = _parse_saved_calendar_match_evidence(
        payload, run_id=state.run_id, branch_id=state.branch_id
    )
    knockout = getattr(evidence, "knockout", evidence)
    transitions = state.transitions[len(root.transitions) :]
    receipts = state.receipts[len(root.receipts) :]
    if len(transitions) != len(checkpoint.native_weeks) or len(receipts) != len(
        transitions
    ):
        raise ValueError("Native sporting weeks and confirmed Tour receipts differ")
    previous, cp = root, checkpoint.source_checkpoint
    for index, (entry, transition, receipt) in enumerate(
        zip(checkpoint.native_weeks, transitions, receipts)
    ):
        request = CalendarTourCommit.model_validate_json(json.dumps(receipt.request))
        command = request.command
        if (
            command.action not in {"transition", "season-transition"}
            or command.data
            or command.edition_id is not None
            or command.command_id != receipt.command_id
            or command.expected_tour_fingerprint != previous.fingerprint
            or command.expected_checkpoint_fingerprint != cp.fingerprint
        ):
            raise ValueError(
                "Native Tour command differs from its real preceding owners"
            )
        count = (
            state.native_root_health_state_count if index == 0 else cp.week.ordinal + 1
        )
        prepared = prepare_native_tour_week(
            state=previous,
            checkpoint=cp,
            world=world,
            source=source,
            lifecycle=life[: cp.week.ordinal + 1],
            health=health[:count],
            clock=entry.advance.target_week.calendar,
            knockout=knockout,
            command=command.model_dump(mode="json"),
        )
        if prepared is None:
            raise ValueError("Native Tour cannot claim an absent birth transition")
        impact, next_cp = prepared
        preview = {
            "schema_version": "calendar_tour_command_preview.v1",
            "run_id": state.run_id,
            "branch_id": state.branch_id,
            "command": command.model_dump(mode="json"),
            "week": cp.week.model_dump(mode="json"),
            "edition": None,
            "impact": impact,
        }
        expected_result = {
            "command_id": command.command_id,
            "action": command.action,
            "manual_save_required": True,
            "impact": impact,
        }
        if (
            canonical_hash(preview) != request.expected_preview_fingerprint
            or canonical_hash(expected_result) != canonical_hash(receipt.result)
            or next_cp.native_weeks[-1] != entry
        ):
            raise ValueError(
                "Native Tour receipt does not rebuild from its actual complete transition"
            )
        expected_transition = CalendarTourTransition(
            command_id=command.command_id,
            completed_week=RunWeekPosition.model_validate_json(
                json.dumps(impact["completed_week"])
            ),
            target_week=next_cp.week,
            sporting_advance_fingerprint=entry.advance.fingerprint,
            ranking_fingerprint=impact["ranking_fingerprint"],
            health_fingerprint=impact["health_fingerprint"],
            ages=impact["ages"],
            retired_player_ids=impact["retired_player_ids"],
            public_event=public_native_event(
                previous, command, next_cp.week, impact["ranking_fingerprint"]
            ),
        )
        ranking_index = len(root.rankings) + index
        if (
            transition != expected_transition
            or state.rankings[ranking_index].model_dump(mode="json")
            != impact["ranking"]
        ):
            raise ValueError(
                "Native public/ranking publication differs from the confirmed transition"
            )
        previous = state.model_copy(
            update={
                "week": next_cp.week,
                "checkpoint_fingerprint": next_cp.fingerprint,
                "lifecycle_fingerprint": entry.lifecycle_fingerprint,
                "rankings": state.rankings[: ranking_index + 1],
                "transitions": state.transitions[: len(root.transitions) + index + 1],
                "receipts": state.receipts[: len(root.receipts) + index + 1],
            }
        )
        cp = next_cp
    if previous != state or cp != checkpoint:
        raise ValueError("Native Tour head differs from its complete confirmed history")

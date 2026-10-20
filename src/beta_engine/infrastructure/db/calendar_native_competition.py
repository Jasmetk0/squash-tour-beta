"""Independent command/MatchEngine replay of the complete post-admission chain."""

import json
from types import SimpleNamespace

from beta_engine.domain.players.calendar_native_competition import (
    competition_checkpoint,
)
from beta_engine.domain.players.calendar_native_sporting_checkpoint import (
    CalendarNativeSportingWeek,
)
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.calendar_native_tour import (
    CalendarNativeCompetitionTourState,
)
from beta_engine.domain.tournaments.calendar_tour import (
    parse_tour_json,
)


def root_payload(payload, checkpoint, tour):
    content = dict(payload["content"])
    for key in ("player_lifecycle", "player_health_state"):
        body = content[key]["states"][: checkpoint.week.ordinal + 1]
        content[key] = {"states": body, "fingerprint": canonical_hash(body)}
    content["calendar_player_sporting_checkpoint"] = {
        "state": checkpoint.model_dump(mode="json"),
        "fingerprint": checkpoint.fingerprint,
    }
    content["calendar_tour_authority"] = {
        "state": tour.model_dump(mode="json"),
        "fingerprint": tour.fingerprint,
    }
    return {**payload, "content": content}


def verify_competition_payload(payload, checkpoint, evidence=None):
    from beta_engine.application.calendar_tour_service import (
        CalendarTourCommit,
        CalendarTourService,
    )
    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from beta_engine.domain.tournaments.calendar_native_tour_week import (
        prepare_native_tour_week,
    )
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
        saved_checkpoint,
    )
    from beta_engine.infrastructure.db.calendar_standalone_match_state import (
        _parse_saved_calendar_match_evidence,
    )
    from beta_engine.infrastructure.db.calendar_tour import saved_tour
    from beta_engine.infrastructure.db.initial_world_state import (
        load_saved_initial_world,
    )
    from beta_engine.infrastructure.db.player_health_state import load_saved_health
    from beta_engine.infrastructure.db.player_lifecycle_state import (
        load_saved_lifecycle,
    )
    from beta_engine.infrastructure.db.run_prospect_source_state import (
        load_saved_run_prospect_source,
    )

    run_id, branch_id = checkpoint.run_id, checkpoint.branch_id
    component = payload["content"].get("calendar_tour_authority", {})
    state = parse_tour_json(json.dumps(component.get("state")))
    if not isinstance(state, CalendarNativeCompetitionTourState) or (
        state.run_id,
        state.branch_id,
        state.fingerprint,
        state.checkpoint_fingerprint,
    ) != (run_id, branch_id, component.get("fingerprint"), checkpoint.fingerprint):
        raise ValueError("Native competition identity or coupled Tour owner differs")
    root_cp, root_tour = checkpoint.competition_root, state.competition_root_tour
    old = root_payload(payload, root_cp, root_tour)
    if evidence is None:
        evidence = _parse_saved_calendar_match_evidence(
            payload, run_id=run_id, branch_id=branch_id
        )
    if (
        saved_checkpoint(old, evidence, run_id=run_id, branch_id=branch_id) != root_cp
        or saved_tour(old, run_id=run_id, branch_id=branch_id, checkpoint=root_cp)
        != root_tour
    ):
        raise ValueError("Native competition historical root differs")
    world = load_saved_initial_world(payload, run_id=run_id, branch_id=branch_id)
    life = load_saved_lifecycle(payload, run_id=run_id, branch_id=branch_id)
    health = load_saved_health(payload, run_id=run_id, branch_id=branch_id)
    source = load_saved_run_prospect_source(payload, run_id=run_id)
    previous, cp = root_tour, root_cp
    event_index = 0
    receipts = state.receipts[len(root_tour.receipts) :]
    if not receipts:
        raise ValueError("Native competition lacks confirmed commands")
    service = CalendarTourService(None)
    for receipt in receipts:
        request = CalendarTourCommit.model_validate_json(json.dumps(receipt.request))
        command = request.command
        if (
            command.command_id != receipt.command_id
            or command.expected_tour_fingerprint != previous.fingerprint
            or command.expected_checkpoint_fingerprint != cp.fingerprint
            or command.action in {"initialize", "policy"}
        ):
            raise ValueError(
                "Native competition command differs from its preceding owners"
            )
        authority = next(
            (
                a
                for a in previous.editions
                if a.edition.edition_id == command.edition_id
            ),
            None,
        )
        next_cp = cp
        impact = None
        # Each historical command retains its effective horizon, never today's
        # defaults. Saved-origin validation separately authenticates that clock.
        clock = cp.week.calendar
        if command.action == "create-edition":
            clock = RunCalendar.from_metadata(command.data["week"]["calendar"])
        if command.action in {"transition", "season-transition", "play"}:
            if event_index >= len(checkpoint.events):
                raise ValueError("Native competition lacks actual sporting event")
            event = checkpoint.events[event_index]
            clock = (
                event.advance.target_week.calendar
                if isinstance(event, CalendarNativeSportingWeek)
                else event.week.calendar
            )
        if command.action in {"transition", "season-transition"}:
            if command.data or command.edition_id is not None:
                raise ValueError("Natural transition cannot contain Edition inputs")
            ctx = (clock, None, world, health[cp.week.ordinal], cp, cp, evidence)
            blockers = service._transition_blockers(
                previous, ctx, season=command.action == "season-transition"
            )
            if blockers:
                raise ValueError(
                    "Historical transition was blocked: " + ", ".join(blockers)
                )
            impact, next_cp = prepare_native_tour_week(
                state=previous,
                checkpoint=cp,
                world=world,
                source=source,
                lifecycle=life[: cp.week.ordinal + 1],
                health=health[: cp.week.ordinal + 1],
                clock=clock,
                knockout=getattr(evidence, "knockout", evidence),
                command=command.model_dump(mode="json"),
            )
            if next_cp.events[-1] != event:
                raise ValueError(
                    "Native sporting week differs from genuine match counts/development"
                )
            event_index += 1
        elif command.action == "play":
            if (
                authority is None
                or authority.draw is None
                or authority.tournament_fingerprint
            ):
                raise ValueError("Native play requires its actual unplayed draw")
            impact = {
                "action": "play",
                "manual_save_required": True,
                "edition_authority_fingerprint": authority.execution_fingerprint,
                "entrant_ids": [s.player_id for s in authority.draw.main.slots],
                "point_table": authority.edition.point_table,
            }
        ctx = (
            clock,
            SimpleNamespace(saved_revision=SimpleNamespace(payload=payload)),
            world,
            health[cp.week.ordinal],
            cp,
            cp,
            evidence,
        )
        if command.action not in {"create-edition", "transition", "season-transition"}:
            if authority is None:
                raise ValueError("Native command lacks Edition")
            offsets = {
                "submit": 0,
                "approve": 1,
                "draw": 2,
                "play": 3,
                "confirm-result": authority.edition.main_entrant_count + 2,
            }
            if authority.edition.start_slot + offsets[
                command.action
            ] < previous.slot_cursor or any(
                a.edition.week.ordinal == cp.week.ordinal
                and a.edition.start_slot < authority.edition.start_slot
                and not a.result_confirmed
                for a in previous.editions
            ):
                raise ValueError("Native command precedes unresolved Simulation Slot")
        native_inputs = (life[cp.week.ordinal], source)
        if command.action == "play":
            from beta_engine.domain.players.calendar_native_competition import (
                play_native_tournament,
            )

            replayed_event, next_cp = play_native_tournament(
                checkpoint=cp,
                world=world,
                lifecycle=life[cp.week.ordinal],
                health=health[cp.week.ordinal],
                source=source.for_week(cp.week.ordinal),
                clock=clock,
                authority=authority,
                command=command,
                knockout=getattr(evidence, "knockout", evidence),
            )
            if next_cp.events[-1] != event:
                raise ValueError(
                    "Native played history differs from actual MatchEngine replay"
                )
            event_index += 1
            native_inputs = (*native_inputs, (replayed_event, next_cp))
        planned, result = service._apply(
            None,
            ctx,
            previous,
            authority,
            command,
            persist=False,
            transition_candidate=(impact, next_cp),
            _native_inputs=native_inputs,
        )
        if cp is root_cp and planned.schema_version == "calendar_tour_authority.v4":
            next_cp = competition_checkpoint(cp)
        if impact is None:
            impact = result
        preview = {
            "schema_version": "calendar_tour_command_preview.v1",
            "run_id": run_id,
            "branch_id": branch_id,
            "command": command.model_dump(mode="json"),
            "week": cp.week.model_dump(mode="json"),
            "edition": authority.model_dump(mode="json") if authority else None,
            "impact": impact,
        }
        if canonical_hash(
            preview
        ) != request.expected_preview_fingerprint or canonical_hash(
            result
        ) != canonical_hash(receipt.result):
            raise ValueError("Native competition confirmation/result does not rebuild")
        previous = planned.model_copy(
            update={"receipts": planned.receipts + (receipt,)}
        )
        cp = next_cp
    if event_index != len(checkpoint.events) or cp != checkpoint or previous != state:
        raise ValueError("Native competition differs from complete confirmed history")

"""Independent command/MatchEngine replay of the complete post-admission chain."""

import json
import hashlib
from pydantic_core import to_json
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


def _raw_global_inputs(payload):
    content = payload['content']
    binding = canonical_hash({
        'run_id': payload.get('run', {}).get('run_id'),
        'branch_id': payload.get('branch', {}).get('branch_id'),
        'calendar': payload.get('run', {}).get('run_calendar'),
        'population_clock_origin': payload.get('run', {}).get('run_calendar_content_origin'),
        **{key: content.get(key) for key in ('initial_world', 'calendar_standalone_match', 'run_prospect_source')},
    })
    histories = []
    for key in ('player_lifecycle', 'player_health_state'):
        component = content.get(key)
        if (not isinstance(component, dict)
            or set(component) != {'states', 'fingerprint'}
            or not isinstance(component['states'], list)
            or canonical_hash(component['states']) != component['fingerprint']):
            raise ValueError('Global source history has an invalid actual value fingerprint')
        histories.append(tuple(canonical_hash(state) for state in component['states']))
    return binding, *histories


def has_replayed_global_components(payload, proofs):
    """Reuse exact values produced by an earlier full replay in this one walk.

    This certifies component math only. The repository still authenticates each
    physical revision, owner, full dependency graph and reachable command source.
    No declared component fingerprint is sufficient: hash every actual value.
    """
    known = (proofs or {}).get('_prefixes', {}).get('_global_replayed_values', {})
    if not known:
        return False
    content = payload.get('content', {})
    cp, tour = content.get('calendar_player_sporting_checkpoint', {}), content.get('calendar_tour_authority', {})
    if (set(cp) != {'state', 'fingerprint'} or set(tour) != {'state', 'fingerprint'}
        or not isinstance(cp['state'], dict) or not isinstance(tour['state'], dict)
        or cp['state'].get('schema_version') != 'calendar_sporting_checkpoint.v13'
        or tour['state'].get('schema_version') != 'calendar_tour_authority.v5'):
        return False
    identity = cp['fingerprint'], tour['fingerprint']
    evidence = known.get(identity)
    if evidence is None:
        return False
    # The declared fingerprint only selects a candidate. Hash EVERY actual
    # value and compare with the independently replayed value's digest. This
    # optional ordered-JSON digest is not a persisted hash or a source proof.
    auxiliary = (proofs or {}).get('_prefixes', {}).get('_global_checkpoint_json_values', {}).get(identity[0])
    try:
        same_checkpoint = auxiliary is not None and hashlib.sha256(to_json(cp['state'], inf_nan_mode='constants')).digest() == auxiliary
    except (TypeError, ValueError):
        same_checkpoint = False
    if not same_checkpoint and canonical_hash(cp['state']) != identity[0]:
        return False
    if canonical_hash(tour['state']) != identity[1]:
        return False
    actual = _raw_global_inputs(payload)
    return actual == evidence


def replayed_global_tour_value(payload, proofs, *, run_id, branch_id):
    """A private decode value, never a physical/source authorization proof.

    The full replay already constructed these frozen intermediate values. Bind
    the complete actual component again and rehash the retained model to reject
    nested mutation. The caller still owns every physical Saved/source gate.
    """
    from beta_engine.domain.tournaments.calendar_global_slots import GlobalTourState

    component = payload.get('content', {}).get('calendar_tour_authority', {})
    if (not isinstance(component, dict) or set(component) != {'state', 'fingerprint'}
        or not isinstance(component.get('state'), dict)):
        return None
    actual = canonical_hash(component['state'])
    value = (proofs or {}).get('_prefixes', {}).get('_global_replayed_tours', {}).get(actual)
    if (not isinstance(value, GlobalTourState)
        or (value.run_id, value.branch_id) != (run_id, branch_id)
        or actual != component['fingerprint'] or value.fingerprint != actual):
        return None
    return value


def replayed_global_checkpoint_value(payload, proofs, *, run_id, branch_id):
    """Private decoded value only; every physical and source gate stays required."""
    from beta_engine.domain.tournaments.calendar_global_slots import GlobalCompetitionCheckpoint

    known = (proofs or {}).get('_prefixes', {}).get('_global_replayed_checkpoints', {})
    if not known:
        return None
    component = payload.get('content', {}).get('calendar_player_sporting_checkpoint', {})
    if (not isinstance(component, dict) or set(component) != {'state', 'fingerprint'}
        or not isinstance(component.get('state'), dict)):
        return None
    actual = canonical_hash(component['state'])
    value = known.get(actual)
    if (not isinstance(value, GlobalCompetitionCheckpoint)
        or (value.run_id, value.branch_id) != (run_id, branch_id)
        or actual != component['fingerprint'] or value.fingerprint != actual):
        return None
    return value


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


def verify_competition_payload(payload, checkpoint, evidence=None, *, verified_global_prefix=None, source_proofs=None):
    from beta_engine.domain.tournaments.calendar_global_slots import global_replay_projection_scope

    with global_replay_projection_scope():
        return _verify_competition_payload(payload, checkpoint, evidence,
            verified_global_prefix=verified_global_prefix, source_proofs=source_proofs)


def _verify_competition_payload(payload, checkpoint, evidence=None, *, verified_global_prefix=None, source_proofs=None):
    from beta_engine.domain.tournaments.calendar_global_slots import _replay_projections
    projection = _replay_projections.get()
    if projection is not None and source_proofs is not None:
        projection['collect_checkpoint_value_hashes'] = True
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
    from beta_engine.domain.tournaments.calendar_global_slots import GlobalTourState, GlobalCompetitionCheckpoint, upgrade
    if not isinstance(state, (CalendarNativeCompetitionTourState, GlobalTourState)) or (
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
    prefix = authenticated_global_prefix(payload, checkpoint, state, verified_global_prefix)
    world = load_saved_initial_world(payload, run_id=run_id, branch_id=branch_id)
    life = load_saved_lifecycle(payload, run_id=run_id, branch_id=branch_id)
    health = load_saved_health(payload, run_id=run_id, branch_id=branch_id)
    source = load_saved_run_prospect_source(payload, run_id=run_id)
    if source is None and isinstance(checkpoint, GlobalCompetitionCheckpoint):
        from beta_engine.infrastructure.db.run_prospect_source_state import RunProspectSourceSnapshot
        source = RunProspectSourceSnapshot("run_prospect_source.v1", run_id, (), canonical_hash([]))
    # Older revisions may reuse only the exact complete history recorded in
    # has_replayed_global_components. An arbitrary shorter lifecycle/Health
    # prefix is not sufficient evidence for this sporting/Tour state.
    if prefix is None:
        if (
            saved_checkpoint(old, evidence, run_id=run_id, branch_id=branch_id) != root_cp
            or saved_tour(old, run_id=run_id, branch_id=branch_id, checkpoint=root_cp)
            != root_tour
        ):
            raise ValueError("Native competition historical root differs")
    verified_states = []
    previous, cp = prefix if prefix is not None else (root_tour, root_cp)
    event_index = len(cp.events) if prefix is not None else 0
    receipts = state.receipts[len(previous.receipts) :]
    if not receipts and prefix is None:
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
            ctx = (clock, None, world, next(h for h in reversed(health) if h.week.ordinal <= cp.week.ordinal), cp, cp, evidence)
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
                health=health[: receipt.result.get("impact", {}).get("source_health_state_count", cp.week.ordinal + 1)],
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
            next(h for h in reversed(health) if h.week.ordinal <= cp.week.ordinal),
            cp,
            cp,
            evidence,
        )
        if command.action not in {"create-edition", "transition", "season-transition", "next-slot", "next-match"}:
            if authority is None:
                raise ValueError("Native command lacks Edition")
            offsets = {
                "submit": 0,
                "approve": 1,
                "draw": 2,
                "play": 3,
                "confirm-result": authority.edition.main_entrant_count + 2,
            }
            if authority.edition.schema_version.endswith(".v1") and (authority.edition.start_slot + offsets[
                command.action
            ] < previous.slot_cursor or any(
                a.edition.week.ordinal == cp.week.ordinal
                and a.edition.start_slot < authority.edition.start_slot
                and not a.result_confirmed
                for a in previous.editions
            )):
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
                health=next(h for h in reversed(health) if h.week.ordinal <= cp.week.ordinal),
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
        if command.action in {"next-slot", "next-match"}:
            from beta_engine.application.calendar_global_slot_service import prepare_global_slot
            from beta_engine.domain.tournaments.calendar_global_slots import accept_slot
            slot, impact = prepare_global_slot(None, ctx, previous, command, native_inputs=native_inputs)
            selected = impact["selected_match_ids"][0] if command.action == "next-match" else None
            next_cp, _ = accept_slot(cp, slot, match_id=selected)
            native_inputs = (*native_inputs, (slot, next_cp))
            event_index = len(next_cp.events)
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
        if planned.schema_version == "calendar_tour_authority.v5" and not isinstance(cp, GlobalCompetitionCheckpoint):
            next_cp = upgrade(previous, cp, command.expected_saved_head)[1]
        elif cp is root_cp and planned.schema_version == "calendar_tour_authority.v4":
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
        previous_before_tie = previous
        previous = planned.model_copy(
            update={"receipts": planned.receipts + (receipt,)}
        )
        if command.action in {"resolve-group-tie", "withdraw-group"}:
            from beta_engine.application.calendar_native_groups import apply_group_tie, apply_group_withdrawal
            apply = apply_group_tie if command.action == 'resolve-group-tie' else apply_group_withdrawal
            captured = {}
            apply(None, ctx, previous_before_tie, authority, command, persist=False, _successor_out=captured)
            next_cp = captured['checkpoint']
        cp = next_cp
        if isinstance(cp, GlobalCompetitionCheckpoint):
            verified_states.append((cp, previous))
    if event_index != len(checkpoint.events) or cp != checkpoint or previous != state:
        raise ValueError("Native competition differs from complete confirmed history")
    if source_proofs is not None and verified_states:
        raw_inputs = _raw_global_inputs(payload)
        values = source_proofs.setdefault('_global_replayed_values', {})
        tours = source_proofs.setdefault('_global_replayed_tours', {})
        checkpoints = source_proofs.setdefault('_global_replayed_checkpoints', {})
        checkpoint_values = source_proofs.setdefault('_global_checkpoint_json_values', {})
        for verified_cp, verified_tour in verified_states:
            tours[verified_tour.fingerprint] = verified_tour
            fingerprint = verified_cp.fingerprint
            checkpoints[fingerprint] = verified_cp
            while len(checkpoints) > 8:
                checkpoints.pop(next(iter(checkpoints)))
            value_hash = (projection or {}).get('checkpoint_value_hashes', {}).get(fingerprint)
            if value_hash is not None:
                checkpoint_values[fingerprint] = value_hash
            life_indices = [i for i, fp in enumerate(raw_inputs[1])
                if fp == verified_tour.lifecycle_fingerprint]
            health_indices = [i for i, h in enumerate(health)
                if h.week.ordinal <= verified_cp.week.ordinal]
            if life_indices and health_indices:
                values[(verified_cp.fingerprint, verified_tour.fingerprint)] = (
                    raw_inputs[0], raw_inputs[1][:life_indices[-1] + 1],
                    raw_inputs[2][:health_indices[-1] + 1],
                )
        while len(values) > 128:
            values.pop(next(iter(values)))
        while len(tours) > 128:
            tours.pop(next(iter(tours)))
        while len(checkpoint_values) > 128:
            checkpoint_values.pop(next(iter(checkpoint_values)))


def authenticated_global_prefix(payload, checkpoint, state, prefix):
    """Only callers with an actual validated immutable Saved row supply this.

    Compare complete inherited inputs and evidence. A partial slot may gain
    accepted results but cannot rewrite its frozen snapshot or accepted prefix.
    Any difference falls back to the independent complete root replay.
    """
    if prefix is None:
        return None
    from beta_engine.domain.tournaments.calendar_global_slots import GlobalCompetitionCheckpoint, GlobalSlot, GlobalTourState
    old_cp, old_tour, old_payload = prefix
    if not isinstance(checkpoint, GlobalCompetitionCheckpoint) or not isinstance(old_cp, GlobalCompetitionCheckpoint) or not isinstance(old_tour, GlobalTourState):
        return None
    if checkpoint.competition_root != old_cp.competition_root or state.competition_root_tour != old_tour.competition_root_tour or state.receipts[:len(old_tour.receipts)] != old_tour.receipts:
        return None
    before, after = old_payload["content"], payload["content"]
    if any(before.get(k) != after.get(k) for k in ("initial_world", "calendar_standalone_match", "run_prospect_source")):
        return None
    for key in ("player_lifecycle", "player_health_state"):
        old_states = before[key]["states"]
        if after[key]["states"][:len(old_states)] != old_states:
            return None
    if len(checkpoint.events) < len(old_cp.events):
        return None
    for i, event in enumerate(old_cp.events):
        actual = checkpoint.events[i]
        if isinstance(event, GlobalSlot) and event.remaining:
            if not isinstance(actual, GlobalSlot) or actual.model_copy(update={"accepted":event.accepted}) != event:
                return None
            matches = {m.match_id:m for m in actual.accepted}
            if any(matches.get(m.match_id) != m for m in event.accepted):
                return None
        elif actual != event:
            return None
    return old_tour, old_cp

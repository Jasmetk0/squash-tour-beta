"""Audited group tie command over the existing global-slot ledger."""
import json

from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.calendar_global_slots import (
    GlobalSlot,
    inherit_open_slot,
    is_group_edition,
)
from beta_engine.domain.tournaments.calendar_groups import (
    NativeGroupTieDecision,
    TournamentGroupTieResolutionDecision,
    group_progress,
)


def group_slots(checkpoint):
    return tuple(e for e in getattr(checkpoint, 'history_global_slots', getattr(checkpoint, 'events', ()))
                 if isinstance(e, GlobalSlot))


def inspect_groups(state, checkpoint):
    slots = group_slots(checkpoint)
    return {a.edition.edition_id: group_progress(a, slots)
            for a in state.editions if is_group_edition(a)} if state and checkpoint else {}


def apply_group_withdrawal(session, ctx, state, authority, command, *, persist,
                           _successor_out=None, _repository=None):
    from beta_engine.domain.tournaments.calendar_group_withdrawals import (
        NativeGroupWithdrawal, group_withdrawals, group_resolved_matches,
    )
    if (authority is None or not is_group_edition(authority) or authority.draw is None
        or authority.tournament_fingerprint or authority.edition.week != state.week):
        raise ValueError('Withdrawal requires an unfinished drawn group Edition in the current week')
    config = authority.edition.group_configuration
    # Neither hybrid advancement eligibility nor W/O Official group bonuses have
    # an explicit stored policy yet. Preserve the existing fail-closed boundary.
    if config.format_kind != 'groups' or config.played_group_win_points:
        raise ValueError('Native withdrawal currently requires pure groups with zero Official group-win rewards')
    if (set(command.data) - {'player_id', 'reason_category', 'note'}
        or not {'player_id', 'reason_category'} <= set(command.data)):
        raise ValueError('Withdrawal requires a player and reason category, with an optional note')
    cp = ctx[4]
    history = group_slots(cp)
    pid = command.data['player_id']
    scheduled = tuple(m for m in authority.draw.schedule.matches
        if pid in (m.top_player_id, m.bottom_player_id))
    if not scheduled:
        raise ValueError('Withdrawn player is not in the frozen group draw')
    group_index = scheduled[0].group_index
    if any(r.edition_id == authority.edition.edition_id and r.group_index == group_index
           for r in group_withdrawals(history)):
        raise ValueError('This group already has a withdrawal; repeated/double-withdrawal outcomes need explicit review')
    resolved = group_resolved_matches(history)
    if not any(m.match_id in resolved for m in scheduled):
        raise ValueError('Pre-start withdrawal must use the separate Entry/replacement workflow')
    if all(m.match_id in resolved for m in scheduled):
        raise ValueError('Player has no remaining group matches')
    owned = cp.global_slots if getattr(cp, 'schema_version', None) == 'native_fork_competition.v1' else cp.events
    index = next((i for i in reversed(range(len(owned))) if isinstance(owned[i], GlobalSlot)
        and any(s.edition_id == authority.edition.edition_id for s in owned[i].scheduled)), None)
    if index is None:
        source = next(s for s in reversed(history) if any(
            item.edition_id == authority.edition.edition_id for item in s.scheduled))
        slot = inherit_open_slot(source, branch_id=state.branch_id).model_copy(update={'group_tie_decisions': ()})
    else:
        slot = owned[index]
    record = NativeGroupWithdrawal(run_id=state.run_id, branch_id=state.branch_id,
        edition_id=authority.edition.edition_id, group_index=group_index, player_id=pid,
        week=state.week, slot_number=slot.number, source_saved_head=command.expected_saved_head,
        source_checkpoint_fingerprint=cp.fingerprint, command_id=command.command_id,
        operator_label=command.operator_label, audit_reason=command.audit_reason,
        reason_category=command.data['reason_category'], note=command.data.get('note', ''))
    updated = slot.model_copy(update={'schema_version': 'calendar_global_slot.v3',
        'group_withdrawals': (*slot.group_withdrawals, record)})
    if getattr(cp, 'schema_version', None) == 'native_fork_competition.v1':
        successor = cp.with_group_withdrawal(index, updated) if index is not None else cp.with_global_slot(updated)
    else:
        successor = cp.model_copy(update={'events': (*owned[:index], updated, *owned[index+1:])})
    if _successor_out is not None:
        _successor_out['checkpoint'] = successor
    if persist:
        from beta_engine.infrastructure.db.calendar_sporting_checkpoint import replace_checkpoint
        from beta_engine.application.calendar_tour_service import _fault_injection_point
        replace_checkpoint(session, previous=cp, successor=successor,
            _verified_previous=cp, _repository=_repository)
        _fault_injection_point('after_group_withdrawal_write')
    return state.model_copy(update={'checkpoint_fingerprint': successor.fingerprint}), {
        'action': command.action, 'command_id': command.command_id,
        'manual_save_required': True, 'withdrawal': record.model_dump(mode='json'),
        'withdrawal_fingerprint': record.fingerprint, 'checkpoint_fingerprint': successor.fingerprint,
        'remaining_walkover_match_ids': [m.match_id for m in scheduled if m.match_id not in resolved],
    }


def apply_group_tie(session, ctx, state, authority, command, *, persist, _successor_out=None, _repository=None):
    if authority is None or not is_group_edition(authority) or authority.tournament_fingerprint:
        raise ValueError('Tie resolution requires an unfinished native group Edition')
    if set(command.data) != {'case', 'ordered_player_ids'}:
        raise ValueError('Tie resolution requires the exact case and explicit player order')
    cp = ctx[4]
    progress = group_progress(authority, group_slots(cp))
    if not progress['tie_case'] or command.data['case'] != progress['tie_case']:
        raise ValueError('Tie case is stale, foreign, already resolved or absent')
    decision = TournamentGroupTieResolutionDecision.model_validate_json(json.dumps({
        'case': command.data['case'], 'ordered_player_ids': command.data['ordered_player_ids'],
        'admin_reason': command.audit_reason,
    }))
    record = NativeGroupTieDecision(edition_id=authority.edition.edition_id,
        command_id=command.command_id, operator_label=command.operator_label, decision=decision)
    if getattr(cp, 'schema_version', None) == 'native_fork_competition.v1':
        owned = cp.global_slots
        index = next((i for i in reversed(range(len(owned))) if any(
            s.edition_id == authority.edition.edition_id for s in owned[i].scheduled)), None)
        if index is not None:
            slot = owned[index]
            updated = slot.model_copy(update={'group_tie_decisions': (*slot.group_tie_decisions, record)})
            successor = cp.with_group_tie_decision(index, updated)
        else:
            source = next(s for s in reversed(group_slots(cp)) if any(
                item.edition_id == authority.edition.edition_id for item in s.scheduled))
            slot = inherit_open_slot(source, branch_id=state.branch_id).model_copy(update={'group_tie_decisions': ()})
            updated = slot.model_copy(update={'group_tie_decisions': (record,)})
            successor = cp.with_global_slot(updated)
    else:
        slots = cp.events
        index = next(i for i in reversed(range(len(slots))) if isinstance(slots[i], GlobalSlot)
                     and any(s.edition_id == authority.edition.edition_id for s in slots[i].scheduled))
        slot = slots[index]
        updated = slot.model_copy(update={'group_tie_decisions': (*slot.group_tie_decisions, record)})
        successor = cp.model_copy(update={'events': (*slots[:index], updated, *slots[index + 1:])})
    if _successor_out is not None:
        _successor_out['checkpoint'] = successor
    if persist:
        from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
            replace_checkpoint,
        )
        replace_checkpoint(session, previous=cp, successor=successor, _verified_previous=cp, _repository=_repository)
    events = {t.tournament_id: t for t in successor.tournaments}
    editions = tuple(a.model_copy(update={'tournament_fingerprint': events[a.edition.edition_id].fingerprint})
                     if a.edition.edition_id in events and is_group_edition(a) else a for a in state.editions)
    planned = state.model_copy(update={'checkpoint_fingerprint': successor.fingerprint, 'editions': editions})
    completed = {eid: {
        'fingerprint': event.fingerprint, 'winner_player_id': event.winner_player_id,
        'prepared_awards': [a.model_dump(mode='json') for a in event.prepared_awards],
        'match_ids': [m.match_id for m in event.matches],
    } for eid, event in events.items() if eid == authority.edition.edition_id}
    identities = {p.player_id: {'name': p.name, 'country_code': p.nationality}
        for event in events.values() if event.tournament_id in completed
        for m in event.matches for p in m.canonical_projections}
    return planned, {'completed_editions': completed, 'participant_identities': identities,
                     'action': command.action, 'command_id': command.command_id,
                     'manual_save_required': True, 'decision': record.model_dump(mode='json'),
                     'checkpoint_fingerprint': successor.fingerprint,
                     'decision_fingerprint': canonical_hash(record.model_dump(mode='json'))}

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

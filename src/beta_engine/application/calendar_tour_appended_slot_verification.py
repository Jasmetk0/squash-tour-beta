"""Pre-commit verification of one appended native ``next-slot`` increment.

``CalendarTourService.execute`` normally re-runs its complete ``_context``
after writing: it decodes the unchanged Saved HEAD again, strictly decodes and
deep-copies the whole new live checkpoint (every earlier rally log), and
replays every command since the Saved HEAD. This module verifies the same
write against the prefix that the SAME ``BEGIN IMMEDIATE`` transaction fully
authenticated just before the write, and re-reads the actual increment from
SQLite. It returns ``None`` whenever it cannot prove the case; the caller then
runs the original complete post-write ``_context`` unchanged, which accepts or
rejects exactly as before.

Trust boundary
--------------
Trusted: what the pre-write ``_context`` of this same transaction authenticated
(the Saved HEAD lineage and every Saved/live component it checked) and the
private frozen strict models it returned for them. These are the same values
Execute already primes by identity for ``_prepare``; nothing here comes from a
cache, another request or the values handed to the writer.

Re-read and verified here, before the caller commits:

* Physical scope of the write. SQLite ``total_changes`` of this connection must
  grow by exactly two rows between the pre-write context and this check, and
  both the checkpoint and the Tour row must differ from the authenticated
  values. Every INSERT/UPDATE/DELETE, including trigger programs, counts at
  least one change, so no other row (Saved revision, lifecycle, Health, Entry,
  match, Run/Branch/draft) changed. ``BEGIN IMMEDIATE`` holds the writer lock,
  so no other connection can have written.
* Run/Branch, Saved HEAD and Working Draft: the production lineage validator
  runs again and must return the same HEAD, content hash and draft.
* The checkpoint row is read with a fresh SELECT. Its text must start with the
  exact serialization of the authenticated checkpoint up to its final
  ``events`` bracket, followed by exactly one complete JSON event and the
  closing ``]}``. Only that event is decoded, with the same strict per-event
  model as the full reader, and the full checkpoint model validator runs. Its
  canonical hash extends the authenticated prefix digest and must equal the
  row's fingerprint column.
* The Tour row is read with a fresh SELECT and decoded completely.
* Lifecycle, Health, Entry and prospect rows are captured again and must equal
  the authenticated candidate; match evidence is reloaded and compared.
* The independent command replay (``verify_competition_payload``) re-executes
  the new receipt (MatchEngine included) from the authenticated pre-write
  owners and must reproduce exactly the decoded checkpoint and Tour rows;
  Tour origins and lifecycle/Entry coupling are checked as in ``_context``.

Anything else (other actions, forks, legacy schemas, a replaced partial slot,
a different write count, any decode/replay mismatch) uses the full path. Native
Full Simulation children call ``_verify_installed`` without a snapshot and keep
the full path.

After success it leaves the same evidence the full post-write context leaves
in the existing repository caches: the strict decode value of exactly the new
checkpoint bytes, and the completed replay of the exact complete live payload
that the next reader or Save captures (both are keyed by complete actual
content and reused only for identical input).
"""

import json

from sqlalchemy import select

from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
    COMPONENT_KEY as SPORTING_KEY,
)
from beta_engine.infrastructure.db.calendar_tour import COMPONENT_KEY as TOUR_KEY

_CHECKPOINT_KEYS = ['schema_version', 'run_id', 'branch_id', 'competition_root', 'events']
_SLOT_SCHEMAS = frozenset({
    'calendar_global_slot.v1', 'calendar_global_slot.v2',
    'calendar_global_slot.v3', 'calendar_global_slot.v4',
})
_CHANGED_ROWS = 2


def _total_changes(session):
    raw = session.connection().connection.driver_connection
    value = getattr(raw, 'total_changes', None)
    return value if type(value) is int else None


def begin_appended_slot(session, loaded, fingerprints, pre_values):
    """Record the authenticated pre-write snapshot, or None if unsupported."""
    from beta_engine.domain.tournaments.calendar_global_slots import (
        GlobalCompetitionCheckpoint,
        GlobalTourState,
        _appendable_checkpoint_shape,
    )

    ctx, state, signed = loaded
    checkpoint = ctx[4]
    payload = (pre_values or {}).get('payload')
    known = fingerprints.get(id(checkpoint))
    if (
        type(checkpoint) is not GlobalCompetitionCheckpoint
        or not _appendable_checkpoint_shape(checkpoint)
        or list(type(checkpoint).model_fields) != _CHECKPOINT_KEYS
        or type(state) is not GlobalTourState
        or type(signed) is not GlobalTourState
        or not checkpoint.events
        or known is None or known[0] is not checkpoint
        or not isinstance(payload, dict)
    ):
        return None
    changes = _total_changes(session)
    if changes is None:
        return None
    return {
        'transaction': session.get_transaction(),
        'changes': changes,
        'loaded': loaded,
        'fingerprints': dict(fingerprints),
        'checkpoint_fingerprint': known[1],
        'tour_fingerprint': (fingerprints.get(id(state)) or (None, None))[1],
        'payload': payload,
    }


def _fresh_rows(session, run_id, branch_id):
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
        _read_checkpoint_columns,
    )
    from beta_engine.infrastructure.db.models import CalendarTourAuthorityModel

    checkpoint = _read_checkpoint_columns(session, run_id=run_id, branch_id=branch_id)
    model = CalendarTourAuthorityModel
    tour = session.execute(
        select(model.payload_json, model.fingerprint)
        .where(model.run_id == run_id, model.branch_id == branch_id)
    ).one_or_none()
    return checkpoint, tour


def _appended_event(reference, new_raw):
    """The one event appended after ``reference``'s final events element.

    ``reference`` is the serialization of an authenticated checkpoint whose
    last field is ``events`` (checked by ``begin_appended_slot``), so it ends
    with the closing ``]`` of that array and ``}``. The stored text must repeat
    it byte for byte up to that bracket; '[' + remainder + ']' must then be one
    valid JSON array of exactly one object (json.loads rejects trailing data),
    so the stored row is that same object with exactly one more event.
    """
    from beta_engine.domain.tournaments.calendar_global_slots import GlobalSlot

    if not reference.endswith(']}'):
        return None
    head = reference[:-2]
    if (
        len(new_raw) <= len(reference)
        or not new_raw.startswith(head)
        or new_raw[len(head)] != ','
        or not new_raw.endswith(']}')
    ):
        return None
    entries = json.loads('[' + new_raw[len(head) + 1:-2] + ']')
    if len(entries) != 1:
        return None
    entry = entries[0]
    if not isinstance(entry, dict) or entry.get('schema_version') not in _SLOT_SCHEMAS:
        return None
    # The same strict per-event validator parse_checkpoint_json uses.
    return GlobalSlot.model_validate_json(json.dumps(entry))


def verify_appended_slot(service, session, run_id, branch_id, successor, base, *,
                         _fingerprints=None, _save_values=None):
    """The post-write context of a proven append, or None (use the full path)."""
    from beta_engine.infrastructure.db.full_simulation_execution_guard import (
        FullSimulationPauseRequested,
        FullSimulationStopped,
        FullSimulationTargetReached,
    )

    try:
        return _verify(service, session, run_id, branch_id, successor, base,
                       _fingerprints=_fingerprints, _save_values=_save_values)
    except (FullSimulationPauseRequested, FullSimulationStopped, FullSimulationTargetReached):
        # A Full Simulation control fence is never an unproven increment: it
        # must reach the driver exactly as from the complete path.
        raise
    except Exception:  # noqa: BLE001 - fallback only; the full path decides
        # Any unproven case (pydantic ValidationError included). The complete
        # original post-write context then decides and reports acceptance or
        # rejection exactly as before; this path never rejects on its own.
        return None


def _verify(service, session, run_id, branch_id, successor, base, *, _fingerprints, _save_values):
    from beta_engine.application.calendar_native_tour_context import (
        _verified_health_head,
        remember_working_proof,
        working_proof_signature,
    )
    from beta_engine.application.calendar_standalone_match_service import (
        CalendarStandaloneMatchService,
    )
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.domain.tournaments.calendar_global_slots import (
        GlobalCompetitionCheckpoint,
        GlobalTourState,
        _prime_private_fingerprint,
        appended_checkpoint_fingerprint,
        global_replay_projection_scope,
    )
    from beta_engine.domain.tournaments.calendar_tour import parse_tour_json
    from beta_engine.infrastructure.db.calendar_native_competition import (
        authenticated_global_prefix,
        verify_competition_payload,
    )
    from beta_engine.infrastructure.db.calendar_standalone_match_state import (
        load_match_rows,
    )
    from beta_engine.infrastructure.db.calendar_tour import (
        borrow_origin_projection_values,
        retain_origin_projection_values,
        saved_tour,
        verify_tour_origins,
    )
    from beta_engine.infrastructure.db.native_fork_source_projection import (
        decoded_live_calendar_component,
        remember_live_calendar_component,
    )
    from beta_engine.infrastructure.db.player_health_state import capture_saved_health
    from beta_engine.infrastructure.db.player_lifecycle_state import (
        capture_saved_lifecycle,
    )
    from beta_engine.infrastructure.db.run_prospect_source_state import (
        validate_live_run_prospect_source_against_saved,
    )
    from beta_engine.infrastructure.db.tournament_application_submissions import (
        capture_saved_application_submissions,
    )

    repository = service.repository
    (clock_pre, revision_pre, _world_pre, _health_pre, cp_pre, saved, evidence_pre), state_pre, signed = base['loaded']
    if (
        successor.schema_version != 'calendar_tour_authority.v5'
        or session.get_transaction() is not base['transaction']
    ):
        return None
    # 1. Physical write scope: exactly the two coupled rows of this command.
    session.flush()
    changes = _total_changes(session)
    if changes is None or changes - base['changes'] != _CHANGED_ROWS:
        return None
    checkpoint_row, tour_row = _fresh_rows(session, run_id, branch_id)
    if checkpoint_row is None or tour_row is None:
        return None
    new_raw, new_fingerprint = checkpoint_row
    tour_raw, tour_fingerprint = tour_row
    if new_fingerprint == base['checkpoint_fingerprint'] or tour_fingerprint == base['tour_fingerprint']:
        return None

    # 2. Run/Branch, Saved HEAD lineage and Working Draft, re-validated.
    proofs = {}
    borrow_origin_projection_values(repository, proofs)
    clock, revision, world = CalendarStandaloneMatchService(repository)._context(
        session, run_id=run_id, branch_id=branch_id,
        allow_calendar_health=True, allow_calendar_sporting=True,
        allow_completed=True, _sporting_component_proofs=proofs,
    )
    if (
        revision.saved_head_revision_id != revision_pre.saved_head_revision_id
        or revision.saved_revision.revision_id != revision_pre.saved_revision.revision_id
        or revision.saved_revision.content_hash != revision_pre.saved_revision.content_hash
        or revision.working_draft != revision_pre.working_draft
        or clock != clock_pre
    ):
        return None

    # 3. Checkpoint: the authenticated prefix plus one strictly decoded event.
    event = _appended_event(cp_pre.model_dump_json(), new_raw)
    if event is None:
        return None
    with global_replay_projection_scope():
        for value, fingerprint in base['fingerprints'].values():
            _prime_private_fingerprint(value, fingerprint)
        # The stored prefix is byte-identical to the serialization of cp_pre.
        values = {key: getattr(cp_pre, key) for key in ('schema_version', 'run_id', 'branch_id')}
        values['competition_root'] = cp_pre.competition_root
        values['events'] = (*cp_pre.events, event)
        checkpoint = GlobalCompetitionCheckpoint.model_validate(values)
        if (
            (checkpoint.schema_version, checkpoint.run_id, checkpoint.branch_id)
            != (cp_pre.schema_version, run_id, branch_id)
            or checkpoint.competition_root is not cp_pre.competition_root
            or any(a is not b for a, b in zip(checkpoint.events, cp_pre.events))
        ):
            return None
        fingerprint = appended_checkpoint_fingerprint(cp_pre, checkpoint)
        if fingerprint != new_fingerprint:
            return None

        # 4. Tour: the actual row, decoded completely.
        state, decoded_tour_fingerprint = decoded_live_calendar_component(
            repository, run_id=run_id, branch_id=branch_id, kind=TOUR_KEY,
            raw=tour_raw, parse=parse_tour_json, _with_fingerprint=True,
        )
        if (
            type(state) is not GlobalTourState
            or (state.run_id, state.branch_id) != (run_id, branch_id)
            or decoded_tour_fingerprint != tour_fingerprint
            or state.checkpoint_fingerprint != fingerprint
            or len(state.receipts) != len(state_pre.receipts) + 1
            or state.receipts[-1].command_id != successor.receipts[-1].command_id
        ):
            return None

        # The private prefix models must still be exactly the authenticated
        # values: a nested mutable value changed after authentication would
        # change this complete fresh canonical hash (no memo, no scope).
        if (base['tour_fingerprint'] is None
                or canonical_hash(state_pre.model_dump(mode='json')) != base['tour_fingerprint']):
            return None
        saved_tour_component = revision.saved_revision.payload.get('content', {}).get(TOUR_KEY)
        if (not isinstance(saved_tour_component, dict)
                or canonical_hash(signed.model_dump(mode='json')) != saved_tour_component.get('fingerprint')):
            return None

        # 5. Every other live component again. Build the candidate from the
        # Saved payload just re-validated above, exactly as
        # native_working_context does, and require it to equal the
        # authenticated pre-write candidate outside the two written rows.
        payload_pre = base['payload']
        saved_payload = revision.saved_revision.payload
        payload = {**saved_payload, 'content': dict(saved_payload['content'])}
        validate_live_run_prospect_source_against_saved(session, payload, run_id=run_id)
        capture_saved_application_submissions(session, payload, run_id=run_id, branch_id=branch_id)
        capture_saved_lifecycle(session, payload, run_id=run_id, branch_id=branch_id)
        capture_saved_health(session, payload, run_id=run_id, branch_id=branch_id)
        content, content_pre = payload['content'], payload_pre['content']
        if (set(payload) != set(payload_pre)
                or any(payload[key] != payload_pre[key] for key in payload if key != 'content')
                or set(content) != set(content_pre)
                or any(content[key] != content_pre[key] for key in content
                       if key not in (SPORTING_KEY, TOUR_KEY))):
            return None
        # The same component body native_working_context builds for a changed Tour.
        tour_body = state.model_dump(mode='json')
        content[TOUR_KEY] = {'state': tour_body, 'fingerprint': canonical_hash(tour_body)}
        # The complete candidate body, exactly as native_working_context
        # builds it, so the recorded proof below keys the payload that the
        # next reader or Save captures from these same rows.
        checkpoint_body = checkpoint.model_dump(mode='json')
        # Complete fresh canonical hash of the actual value: binds every
        # prefix event object to the authenticated digest (a mutated private
        # prefix cannot pass) and the appended event to the stored column.
        if canonical_hash(checkpoint_body) != fingerprint:
            return None
        content[SPORTING_KEY] = {'state': checkpoint_body, 'fingerprint': fingerprint}
        rows = load_match_rows(session, run_id=run_id, branch_id=branch_id)
        evidence = rows[0] if len(rows) == 1 else None
        if getattr(evidence, 'knockout', evidence) != getattr(evidence_pre, 'knockout', evidence_pre):
            return None

        # 6. Independent replay of the one new receipt from the authenticated owners.
        prefix = (cp_pre, state_pre, payload_pre)
        if authenticated_global_prefix(payload, checkpoint, state, prefix) is None:
            return None
        verify_competition_payload(payload, checkpoint, evidence, verified_global_prefix=prefix)
        # The coupled Tour/lifecycle owner check native_working_context runs.
        if saved_tour(payload, run_id=run_id, branch_id=branch_id, checkpoint=checkpoint,
                      _verified_competition=checkpoint) != state:
            return None
        health = _verified_health_head(payload)
        if checkpoint.week.calendar.season_count > clock.season_count:
            return None

        # 7. Tour origins and lifecycle/Entry coupling, exactly as _context.
        verify_tour_origins(session, state, _origin_cache=proofs.setdefault('_global_origin_inputs', {}),
                            _verified_global_prefix=signed)
        live_life = service._live_lifecycle(session, run_id, branch_id)
        if not live_life:
            return None
        # A changed native Tour expects its actual live lifecycle (as _context).
        service._verify_lifecycle_and_entry(session, run_id, branch_id, state, live_life, live_life)
        retain_origin_projection_values(repository, proofs)
    # Leave the same reusable evidence as the full post-write context: the
    # strict decode value of exactly these checkpoint bytes, and the completed
    # replay of this exact complete live payload (Save and the next reader
    # reuse it only for byte-identical captured input).
    remember_live_calendar_component(repository, run_id=run_id, branch_id=branch_id,
        kind=SPORTING_KEY, raw=new_raw, value=checkpoint, fingerprint=fingerprint)
    remember_working_proof(repository, working_proof_signature(revision, payload))
    # Outputs only after success, so a fallback starts from empty carriers.
    if _fingerprints is not None:
        _fingerprints[id(checkpoint)] = (checkpoint, fingerprint)
        _fingerprints[id(state)] = (state, tour_fingerprint)
        for value in (saved, signed):
            known = base['fingerprints'].get(id(value))
            if known is not None and known[0] is value:
                _fingerprints[id(value)] = known
    if _save_values is not None:
        _save_values['payload'] = payload
    return (clock, revision, world, health, checkpoint, saved, evidence), state, signed

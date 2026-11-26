"""Atomic SQLite + Saved Revision ownership for native population sporting state."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.players.calendar_sporting_checkpoint import (
    CalendarSportingCheckpoint,
    build_calendar_sporting_checkpoint,
)
from beta_engine.infrastructure.db.models import CalendarPlayerSportingCheckpointModel

if TYPE_CHECKING:
    from beta_engine.domain.players.calendar_native_competition import CalendarNativeCompetitionCheckpoint
    from beta_engine.domain.players.calendar_native_sporting_checkpoint import CalendarNativeSportingCheckpoint

COMPONENT_KEY = 'calendar_player_sporting_checkpoint'
_MAX_GLOBAL_PART_BYTES = 16 * 1024 * 1024
_MAX_GLOBAL_PARTS = 128


def _parsed_global_part(body, cache, parse, proven=None):
    """Value-keyed decoding only, confined to one caller's physical read walk.

    ``proven`` (a canonical_text.ProvenSpan of exactly ``body``) supplies the
    proven canonical text: its hash is the key and its characters are the
    strict JSON input. That text decodes to the same value as ``json.dumps(body)``
    (identical tokens and key order, compact separators), so ``parse`` sees the
    same document.
    """
    from beta_engine.domain.run_packages import canonical_hash

    if not isinstance(body, dict):
        raise TypeError('Global checkpoint part must be a versioned object')
    text = None
    if proven is not None:
        from beta_engine.infrastructure.db.canonical_text import span, span_canonical_hash
        key = span_canonical_hash(proven.proof, proven.path)
        if key is not None:
            text = span(proven.proof, proven.path)
        else:
            key = canonical_hash(body)
    else:
        key = canonical_hash(body)
    entry = cache.get(key)
    # A cached model is reused only if its complete canonical dump still hashes
    # to exactly this input's hash: a mutated (or non-round-tripping) model is
    # simply parsed again. Checking at use, not at insertion, spends nothing on
    # the many parts (e.g. a whole cold HEAD) that are never requested twice.
    if entry is not None and entry[1] == key and canonical_hash(entry[2].model_dump(mode='json')) == key:
        return entry[2]
    encoded = text if text is not None else json.dumps(body)
    value = parse(encoded)
    size = len(encoded.encode("utf-8")) if text is None else len(encoded)
    if size <= _MAX_GLOBAL_PART_BYTES:
        cache[key] = (size, key, value)
        while len(cache) > _MAX_GLOBAL_PARTS or sum(item[0] for item in cache.values()) > _MAX_GLOBAL_PART_BYTES:
            cache.pop(next(iter(cache)))
    return value


def parse_checkpoint_json(raw, *, _parsed_global_parts=None, _proven=None):
    """Strict checkpoint model of ``raw``.

    ``_proven`` may be a canonical_text.ProvenSpan whose ``value`` is the
    unmodified decode of exactly ``raw`` (the proven span of a just decoded
    Saved payload). It only replaces decoding ``raw`` again and re-encoding each
    part; every part still runs its strict model validator.
    """
    from beta_engine.domain.players.calendar_native_sporting_checkpoint import (
        CalendarNativeSportingCheckpoint,
    )

    body = _proven.value if _proven is not None else json.loads(raw)
    if not isinstance(body, dict):
        raise ValueError('Calendar sporting checkpoint must be a versioned object')
    if body.get('schema_version') == 'calendar_sporting_checkpoint.v13':
        from beta_engine.domain.tournaments.calendar_global_slots import (
            GlobalCompetitionCheckpoint,
            GlobalSlot,
        )
        from beta_engine.domain.players.calendar_followup_knockout import CalendarFollowupKnockout
        from beta_engine.domain.players.calendar_native_sporting_checkpoint import CalendarNativeSportingWeek

        root, stored_events = body.get('competition_root'), body.get('events', [])
        if (
            isinstance(root, dict) and 'schema_version' not in root
            or isinstance(stored_events, list) and any(
                isinstance(entry, dict) and 'schema_version' not in entry
                for entry in stored_events
            )
        ):
            # The original strict models allow their version field's default.
            # Preserve that noncanonical input contract through the original
            # Union validator; stored canonical histories take the fast path.
            return GlobalCompetitionCheckpoint.model_validate_json(raw)

        from beta_engine.infrastructure.db.canonical_text import ProvenSpan

        def proven_part(path, part):
            return ProvenSpan(_proven.proof, _proven.path + path, part) if _proven is not None else None

        def strict_part(part, parse, proven=None):
            if not isinstance(part, dict):
                raise TypeError('Global checkpoint part must be a versioned object')
            if _parsed_global_parts is not None:
                return _parsed_global_part(part, _parsed_global_parts, parse, proven)
            return parse(json.dumps(part))

        values = dict(body)
        values['competition_root'] = strict_part(body.get('competition_root'), parse_checkpoint_json)
        events = []
        if not isinstance(body.get('events', []), list):
            raise ValueError('Global checkpoint events must be an array')
        for index, entry in enumerate(body.get('events', ())):
            if not isinstance(entry, dict):
                raise TypeError('Global checkpoint event must be a versioned object')
            model = (GlobalSlot if entry.get('schema_version') in {'calendar_global_slot.v1', 'calendar_global_slot.v2', 'calendar_global_slot.v3', 'calendar_global_slot.v4'}
                else CalendarNativeSportingWeek if entry.get('schema_version') == 'calendar_native_sporting_week.v1'
                else CalendarFollowupKnockout)
            events.append(strict_part(entry, model.model_validate_json, proven_part(('events', index), entry)))
        values['events'] = tuple(events)
        # Every nested value runs its ordinary strict JSON validator. Dispatch
        # by explicit schema avoids trial-decoding large histories through each
        # wrong Union alternative. The outer owner/root validator still runs.
        return GlobalCompetitionCheckpoint.model_validate(values)
    if body.get('schema_version') == 'calendar_sporting_checkpoint.v12':
        from beta_engine.domain.players.calendar_native_competition import (
            CalendarNativeCompetitionCheckpoint,
        )
        return CalendarNativeCompetitionCheckpoint.model_validate_json(raw)
    model = (CalendarNativeSportingCheckpoint
             if body.get('schema_version') == 'calendar_sporting_checkpoint.v11'
             else CalendarSportingCheckpoint)
    return model.model_validate_json(raw)


def load_checkpoint(session, *, run_id, branch_id, _verified_source=None, _repository=None):
    row = session.get(CalendarPlayerSportingCheckpointModel, (run_id, branch_id))
    if row is None:
        return None
    if (_verified_source is not None
        and (_verified_source.run_id,_verified_source.branch_id)==(run_id,branch_id)):
        from beta_engine.domain.run_packages import canonical_hash
        from beta_engine.infrastructure.db.native_fork_source_projection import (
            known_live_value_fingerprint, remember_live_value_fingerprint,
        )

        expected = _verified_source.fingerprint
        actual = known_live_value_fingerprint(_repository, run_id=run_id, branch_id=branch_id,
            kind=COMPONENT_KEY, raw=row.payload_json)
        if actual is None:
            actual = canonical_hash(json.loads(row.payload_json))
            remember_live_value_fingerprint(_repository, run_id=run_id, branch_id=branch_id,
                kind=COMPONENT_KEY, raw=row.payload_json, fingerprint=actual)
        if row.fingerprint == expected and actual == expected:
            # Saved serialization sorts mapping keys (e.g. sets_won), while
            # live MatchEngine JSON retains insertion order. Compare canonical
            # values; a known decode result is bound to every actual raw byte,
            # including Run/Branch/component scope. Never trust the hash column.
            return _verified_source
    return _decode_checkpoint_row(row.payload_json, row.fingerprint,
        run_id=run_id, branch_id=branch_id, repository=_repository)


def _decode_checkpoint_row(raw, row_fingerprint, *, run_id, branch_id, repository):
    from beta_engine.infrastructure.db.native_fork_source_projection import decoded_live_calendar_component

    state, fingerprint = decoded_live_calendar_component(repository, run_id=run_id, branch_id=branch_id,
        kind=COMPONENT_KEY, raw=raw, parse=parse_checkpoint_json, _with_fingerprint=True)
    if (state.run_id, state.branch_id, fingerprint) != (run_id, branch_id, row_fingerprint):
        raise ValueError('Calendar sporting checkpoint SQLite identity/hash mismatch')
    return state


@dataclass(frozen=True, slots=True)
class _SaveCheckpointRead:
    transaction: object
    state: CalendarSportingCheckpoint | CalendarNativeSportingCheckpoint | CalendarNativeCompetitionCheckpoint
    fingerprint: str
    payload_digest: bytes


def _read_checkpoint_columns(session: Session, *, run_id, branch_id):
    # Read the actual row even if the ORM identity map has an older value.
    model = CalendarPlayerSportingCheckpointModel
    return session.execute(
        select(model.payload_json, model.fingerprint)
        .where(model.run_id == run_id, model.branch_id == branch_id)
    ).one_or_none()


class PreparedSaveCheckpoint:
    """A private strict decode of exact live row bytes, made BEFORE the writer lock.

    It is not authority, a proof or a cache entry. Only the Save coordinator
    that prepared it holds a reference, and ``read_checkpoint_for_save`` takes
    it at most once. It is used only if the writer transaction then reads the
    same Run/Branch row with byte-identical payload and the same fingerprint
    column; anything else discards it and takes the original strict decode.
    Every other Save gate (draft, HEAD, ancestry, origins, replay, physical
    post-insert checks) is unchanged and independent of where this came from.
    """

    __slots__ = ('run_id', 'branch_id', 'fingerprint', 'payload_digest', '_state', 'retained')

    def __init__(self, *, run_id, branch_id, state, fingerprint, payload_digest, retained=None):
        self.run_id, self.branch_id = run_id, branch_id
        self.fingerprint, self.payload_digest = fingerprint, payload_digest
        self._state = state
        self.retained = retained

    def take(self, *, run_id, branch_id, fingerprint, payload_digest):
        """The private value if it decodes exactly these bytes; consumed either way."""
        state, self._state = self._state, None
        if (state is None
                or type(self.run_id) is not str or type(self.branch_id) is not str
                or (self.run_id, self.branch_id) != (run_id, branch_id)
                or (state.run_id, state.branch_id) != (run_id, branch_id)
                or type(self.fingerprint) is not str or self.fingerprint != fingerprint
                or type(self.payload_digest) is not bytes or self.payload_digest != payload_digest):
            return None
        return state


def prepare_checkpoint_for_save(session_factory, *, run_id, branch_id, repository):
    """Read and privately decode the live row in an ordinary read snapshot.

    Runs before ``BEGIN IMMEDIATE`` so the strict parse (cache miss) does not
    extend the SQLite writer lock. On a cache hit the retained value is taken
    rather than copied (``retained``); only a committed Save that used it
    returns it to the live cache. A concurrent commit simply makes the later
    byte comparison fail and the taken value is dropped.
    """
    from sqlalchemy import text

    with session_factory() as session:
        session.execute(text('BEGIN'))
        row = _read_checkpoint_columns(session, run_id=run_id, branch_id=branch_id)
    if row is None:
        return None
    raw, fingerprint = row
    from beta_engine.infrastructure.db.native_fork_source_projection import take_live_calendar_component
    # A retained strict decode of exactly these bytes becomes this Save's own
    # value: no defensive copy is needed because nothing else can reach it.
    taken = take_live_calendar_component(repository, run_id=run_id, branch_id=branch_id,
        kind=COMPONENT_KEY, raw=raw)
    if taken is not None:
        key, entry = taken
        state = entry[1]
        if (state.run_id, state.branch_id, entry[2]) != (run_id, branch_id, fingerprint):
            return None
        return PreparedSaveCheckpoint(run_id=run_id, branch_id=branch_id, state=state,
            fingerprint=fingerprint, payload_digest=key[3], retained=(key, entry))
    try:
        state = _decode_checkpoint_row(raw, fingerprint,
            run_id=run_id, branch_id=branch_id, repository=repository)
    except (TypeError, ValueError):
        # The writer transaction decodes the actual row again and reports it.
        return None
    return PreparedSaveCheckpoint(run_id=run_id, branch_id=branch_id, state=state,
        fingerprint=fingerprint, payload_digest=hashlib.sha256(raw.encode('utf-8')).digest())


def read_checkpoint_for_save(session: Session, *, run_id, branch_id, repository, prepared=None):
    """Capture one strictly validated read for use within this Save transaction."""
    row = _read_checkpoint_columns(session, run_id=run_id, branch_id=branch_id)
    if row is None:
        if prepared is not None:
            prepared.take(run_id=None, branch_id=None, fingerprint=None, payload_digest=None)
        return None
    raw, fingerprint = row
    digest = hashlib.sha256(raw.encode('utf-8')).digest()
    state = (prepared.take(run_id=run_id, branch_id=branch_id, fingerprint=fingerprint,
                           payload_digest=digest)
             if prepared is not None else None)
    if state is None:
        state = _decode_checkpoint_row(raw, fingerprint,
            run_id=run_id, branch_id=branch_id, repository=repository)
    return _SaveCheckpointRead(session.get_transaction(), state, fingerprint, digest)


def _checkpoint_for_capture(session, *, run_id, branch_id, repository, previous_read):
    if previous_read is None:
        return load_checkpoint(session, run_id=run_id, branch_id=branch_id, _repository=repository)
    row = _read_checkpoint_columns(session, run_id=run_id, branch_id=branch_id)
    if row is None:
        return None
    raw, fingerprint = row
    state = previous_read.state
    # Bind the private decode to the complete current SQLite row. Even a
    # rehashed or reordered row takes the normal strict decode on a byte change.
    if (session.get_transaction() is previous_read.transaction
        and (state.run_id, state.branch_id, fingerprint) == (run_id, branch_id, previous_read.fingerprint)
        and hashlib.sha256(raw.encode('utf-8')).digest() == previous_read.payload_digest):
        return state
    return _decode_checkpoint_row(raw, fingerprint,
        run_id=run_id, branch_id=branch_id, repository=repository)


def put_checkpoint(session, state):
    if session.get(CalendarPlayerSportingCheckpointModel, (state.run_id, state.branch_id)):
        raise ValueError('Calendar sporting checkpoint already exists; cannot overwrite')
    session.add(CalendarPlayerSportingCheckpointModel(
        run_id=state.run_id, branch_id=state.branch_id,
        fingerprint=state.fingerprint, payload_json=state.model_dump_json(),
    ))
    session.flush()


def _knockout(evidence):
    # Prepared points wrap rather than replace the original played authority.
    return getattr(evidence, 'knockout', evidence)


def verify_checkpoint(state, world, evidence, *, _prefix_proofs=None,
                      _verified_saved_prefix=None, _native_inputs=None):
    from beta_engine.domain.players.calendar_native_sporting_checkpoint import (
        CalendarNativeSportingCheckpoint,
        verify_native_sporting_checkpoint,
    )
    if isinstance(state, CalendarNativeSportingCheckpoint):
        if _native_inputs is None:
            raise ValueError('Checkpoint v11 requires its complete Signed native inputs')
        prefix = (_verified_saved_prefix.source_checkpoint
                  if isinstance(_verified_saved_prefix, CalendarNativeSportingCheckpoint)
                  else _verified_saved_prefix)
        verify_checkpoint(state.source_checkpoint, world, evidence,
                          _prefix_proofs=_prefix_proofs, _verified_saved_prefix=prefix)
        verify_native_sporting_checkpoint(
            state, world_package_id=world.world_package_id,
            knockout=_knockout(evidence), **_native_inputs,
        )
        return
    from beta_engine.domain.players.calendar_engine_player import calendar_engine_player
    knockout = _knockout(evidence)
    required = knockout is not None and knockout.schema_version == 'calendar_opening_knockout.v5'
    if not required:
        if state is not None:
            raise ValueError('Orphan calendar sporting checkpoint without its v5 played source')
        return
    if state is None or world is None:
        raise ValueError('Played v5 knockout requires its complete population sporting checkpoint')
    proof_scope=None
    if _prefix_proofs is not None:
        proof_scope=(world.fingerprint,knockout.fingerprint)
        verified=_prefix_proofs.get((*proof_scope,state.fingerprint))
        if verified is not None and verified==state:
            return
    # A trusted, fully validated Saved HEAD can anchor a new checkpoint.
    # Only the newly appended events then need replay. Never trust a prefix
    # from an unvalidated JSON body or across branches/worlds/knockouts.
    # The caller must authenticate the exact previous Saved Revision first.
    prefix = _verified_saved_prefix
    if prefix is not None and not (
        (prefix.run_id, prefix.branch_id) == (state.run_id, state.branch_id)
        and prefix.source_saved_head == state.source_saved_head
        and prefix.source_initial_world_fingerprint == world.fingerprint
        and prefix.source_knockout_fingerprint == knockout.fingerprint
        and prefix.bootstrap_policy == state.bootstrap_policy
        and prefix.continuations == state.continuations[:len(prefix.continuations)]
        and prefix.week_events == state.week_events[:len(prefix.week_events)]
        and prefix.closures == state.closures[:len(prefix.closures)]
    ):
        prefix = None
    if prefix is not None:
        expected = prefix
        suffix = (
            *state.continuations[len(prefix.continuations):],
            *state.week_events[len(prefix.week_events):],
        )
    else:
        expected = build_calendar_sporting_checkpoint(world, knockout, calendar_engine_player)
        suffix = (*state.continuations, *state.week_events)
    if proof_scope is not None:
        _prefix_proofs[(*proof_scope,expected.fingerprint)]=expected
    from beta_engine.domain.players.calendar_continuation_match import (
        append_continuation,
    )
    reserved_ids = {knockout.match_id, *(m.input_context.match_id for m in knockout.matches)}
    from beta_engine.domain.players.calendar_followup_knockout import (
        CalendarFollowupKnockout,
        append_followup_knockout,
    )
    from beta_engine.domain.players.calendar_sporting_week import (
        CalendarSportingWeekAdvance,
        append_sporting_week,
    )
    from beta_engine.domain.players.calendar_tournament_closure import (
        append_native_tournament_closure,
    )
    closures_by_count = {entry.source_week_event_count: entry for entry in state.closures}
    if len(closures_by_count) != len(state.closures):
        raise ValueError('Native tournament result closure has duplicate event boundaries')
    closed_counts = (
        {entry.source_week_event_count for entry in prefix.closures}
        if prefix is not None else set()
    )
    # A closure can be committed at the existing saved event boundary without
    # another MatchEngine event (e.g. Admin confirmation after actual results).
    if (
        prefix is not None
        and len(expected.week_events) in closures_by_count
        and len(expected.week_events) not in closed_counts
    ):
        expected = append_native_tournament_closure(
            expected, closures_by_count[len(expected.week_events)]
        )
        closed_counts.add(len(expected.week_events))
    for entry in suffix:
        if isinstance(entry, CalendarSportingWeekAdvance):
            expected = append_sporting_week(expected, world, knockout, entry)
        elif isinstance(entry, CalendarFollowupKnockout):
            if (entry.command_id == knockout.command_id
                or any(m.match_id in reserved_ids or m.command_id == knockout.command_id
                       for m in entry.matches)):
                raise ValueError('Later knockout reuses original opening knockout identity')
            expected = append_followup_knockout(expected, world, entry)
        else:
            if entry.match_id in reserved_ids or entry.command_id == knockout.command_id:
                raise ValueError('Continuation reuses original knockout identity')
            expected = append_continuation(expected, world, entry)
        index = len(expected.week_events)
        if index in closures_by_count and index not in closed_counts:
            expected = append_native_tournament_closure(expected, closures_by_count[index])
            closed_counts.add(index)
        if proof_scope is not None:
            _prefix_proofs[(*proof_scope,expected.fingerprint)]=expected
    if closed_counts != set(closures_by_count):
        raise ValueError('Native result closure has no matching sporting event')
    if state != expected:
        raise ValueError('Calendar sporting checkpoint differs from population and played terminal evidence')


def saved_checkpoint(payload, evidence, *, run_id, branch_id, _prefix_proofs=None,
                     _verified_saved_prefix=None, _verified_global_prefix=None,
                     _predecoded_checkpoint=None, _payload_proof=None):
    from beta_engine.infrastructure.db.initial_world_state import (
        load_saved_initial_world,
    )
    component = payload.get('content', {}).get(COMPONENT_KEY)
    state = None
    if component is not None:
        if not isinstance(component, dict) or set(component) != {'fingerprint', 'state'}:
            raise ValueError('Malformed Saved calendar sporting checkpoint component')
        if _predecoded_checkpoint is not None:
            # The private live-context caller just strictly decoded and checked
            # the actual SQLite row, and built this body from that owned model.
            # Bind the complete actual value again; only duplicate structural
            # decoding is omitted. Independent full math/source verification
            # below remains mandatory.
            from beta_engine.domain.run_packages import canonical_hash
            from beta_engine.domain.tournaments.calendar_global_slots import GlobalCompetitionCheckpoint
            if (not isinstance(_predecoded_checkpoint, GlobalCompetitionCheckpoint)
                or canonical_hash(component['state']) != _predecoded_checkpoint.fingerprint):
                raise ValueError('Predecoded global checkpoint differs from actual complete component')
            state = _predecoded_checkpoint
        else:
            from beta_engine.infrastructure.db.canonical_text import ProvenSpan, span
            # The proven span of the just decoded payload is exactly the
            # canonical encoding of this state: no re-encode and re-decode.
            proven = (ProvenSpan(_payload_proof, ('content', COMPONENT_KEY, 'state'), component['state'])
                if _payload_proof is not None else None)
            raw = span(_payload_proof, proven.path) if proven is not None else None
            if raw is None:
                proven = None
                raw = json.dumps(component['state'])
            state = parse_checkpoint_json(raw,
                _parsed_global_parts=_prefix_proofs.setdefault('_global_decoded_parts', {}) if _prefix_proofs is not None else None,
                _proven=proven)
        if (state.run_id, state.branch_id, state.fingerprint) != (run_id, branch_id, component['fingerprint']):
            raise ValueError('Saved calendar sporting checkpoint identity/hash mismatch')
    if state is not None and state.schema_version in {'calendar_sporting_checkpoint.v12', 'calendar_sporting_checkpoint.v13'}:
        from beta_engine.infrastructure.db.calendar_native_competition import (
            verify_competition_payload,
        )
        verify_competition_payload(payload, state, evidence, verified_global_prefix=_verified_global_prefix, source_proofs=_prefix_proofs)
        return state
    knockout = _knockout(evidence)
    required = knockout is not None and knockout.schema_version == 'calendar_opening_knockout.v5'
    world = load_saved_initial_world(payload, run_id=run_id, branch_id=branch_id) if required or state else None
    native_inputs = None
    if state is not None and state.schema_version == 'calendar_sporting_checkpoint.v11':
        from beta_engine.domain.tournaments.calendar_tour import (
            effective_policy,
            parse_tour_json,
        )
        from beta_engine.infrastructure.db.player_health_state import load_saved_health
        from beta_engine.infrastructure.db.player_lifecycle_state import (
            load_saved_lifecycle,
        )
        from beta_engine.infrastructure.db.run_prospect_source_state import (
            load_saved_run_prospect_source,
        )

        raw_tour = payload.get('content', {}).get('calendar_tour_authority')
        if not isinstance(raw_tour, dict) or set(raw_tour) != {'fingerprint', 'state'}:
            raise ValueError('Checkpoint v11 requires its Signed Tour policy authority')
        tour = parse_tour_json(json.dumps(raw_tour['state']))
        if (tour.fingerprint != raw_tour['fingerprint']
                or (tour.run_id, tour.branch_id) != (run_id, branch_id)
                or tour.week != state.week
                or tour.checkpoint_fingerprint != state.fingerprint):
            raise ValueError('Native checkpoint differs from its Signed Tour owner')
        native_inputs = dict(
            lifecycle=load_saved_lifecycle(payload, run_id=run_id, branch_id=branch_id),
            health=load_saved_health(payload, run_id=run_id, branch_id=branch_id),
            source=load_saved_run_prospect_source(payload, run_id=run_id),
            policy_for_week=lambda week: effective_policy(tour, week).development,
        )
    verify_checkpoint(state, world, evidence, _prefix_proofs=_prefix_proofs,
        _verified_saved_prefix=_verified_saved_prefix, _native_inputs=native_inputs)
    if state:
        from beta_engine.domain.calendar.run_calendar import RunCalendar
        clock = RunCalendar.from_metadata(payload['run']['run_calendar'])
        last = state.week.calendar
        if isinstance(state, CalendarSportingCheckpoint) and state.continuations and not state.week_events:
            last = state.continuations[-1].week.calendar
        if (last.weeks_per_year, last.season_start_year_week, last.start_year) != (clock.weeks_per_year, clock.season_start_year_week, clock.start_year) or last.season_count > clock.season_count:
            raise ValueError('Saved continuation clock exceeds its Run horizon')
    return state


def capture_checkpoint(session, payload, evidence, *, run_id, branch_id,
                       _defer_full_verification: bool = False, _repository=None,
                       _previous_read=None, _signed_parent_component=None):
    from beta_engine.infrastructure.db.initial_world_state import get_initial_world
    state = _checkpoint_for_capture(session, run_id=run_id, branch_id=branch_id,
        repository=_repository, previous_read=_previous_read)
    world = get_initial_world(session, run_id=run_id, branch_id=branch_id) if state or evidence else None
    # Only the native Tour Save coordinator may defer this replay. It then
    # authenticates the complete freshly captured revision once, atomically,
    # before any Saved Revision is inserted or the Branch pointer moves.
    if not _defer_full_verification:
        verify_checkpoint(state, world, evidence)
    if state is None:
        if _signed_parent_component is not None:
            raise ValueError('Live global sporting checkpoint is missing during Save')
        return None
    if (
        _previous_read is not None
        and state is _previous_read.state
        and state.schema_version == 'calendar_sporting_checkpoint.v13'
        and _signed_parent_component is not None
        and _previous_read.fingerprint == _signed_parent_component['fingerprint']
    ):
        # The complete canonical model hash matched the actual live row when
        # first read; capture then confirmed its exact bytes again. The same
        # hash in the independently authenticated parent binds that component
        # to the same canonical model. Keep the payload value and let Save's
        # ordinary successor and physical checks validate the inserted bytes.
        payload['content'][COMPONENT_KEY] = _signed_parent_component
        return state
    from beta_engine.domain.run_packages import canonical_hash

    body = state.model_dump(mode='json')
    payload['content'][COMPONENT_KEY] = {'fingerprint': canonical_hash(body), 'state': body}
    return state


def restore_checkpoint(session, *, current_payload, target_payload, current, target, run_id, branch_id,
                       _validated_states=None):
    if _validated_states is None:
        expected = saved_checkpoint(current_payload, current, run_id=run_id, branch_id=branch_id)
        replacement = saved_checkpoint(target_payload, target, run_id=run_id, branch_id=branch_id)
    else:
        # The restore coordinator already verified these exact signed snapshots
        # before beginning any live-state mutation. Always check the live owner.
        expected, replacement = _validated_states
    live = load_checkpoint(session, run_id=run_id, branch_id=branch_id)
    if live != expected:
        raise ValueError('Live calendar sporting checkpoint differs from current Saved HEAD')
    row = session.get(CalendarPlayerSportingCheckpointModel, (run_id, branch_id))
    if row is not None:
        session.delete(row)
        session.flush()
    if replacement is not None:
        put_checkpoint(session, replacement)


def replace_checkpoint(session, *, previous, successor, _verified_previous=None, _repository=None):
    # Reuse only the fingerprint of the complete actual bytes already decoded
    # by this repository. The current row, owner/hash and expected-value CAS
    # remain mandatory; different bytes take the original strict decode path.
    live = load_checkpoint(session, run_id=previous.run_id, branch_id=previous.branch_id,
        _verified_source=_verified_previous, _repository=_repository)
    if live != previous or (successor.run_id, successor.branch_id) != (previous.run_id, previous.branch_id):
        raise ValueError('Population sporting checkpoint changed before atomic replacement')
    row = session.get(CalendarPlayerSportingCheckpointModel, (previous.run_id, previous.branch_id))
    row.fingerprint = successor.fingerprint
    row.payload_json = successor.model_dump_json()
    session.flush()

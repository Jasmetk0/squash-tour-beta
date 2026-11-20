"""Authenticate physical reachable origins of global-slot commands on Saved reads."""

import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar

from beta_engine.domain.run_revisions import BRANCH_RESTORE_SAVED_REVISION_KIND
from beta_engine.infrastructure.db.calendar_tour import (
    _origin_inputs,
    remember_verified_origin_projection,
    verify_tour_origins,
)
from beta_engine.infrastructure.db.exact_text_digest import row_text_sha256
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel

_cold_lineage_decodes = ContextVar('cold_lineage_shared_decodes', default=None)


@contextmanager
def cold_lineage_shared_decodes():
    """Oldest-first cold validation: decode each revision reusing its predecessor's log.

    Only the repository's cold prevalidation walk opens this scope. Within it,
    a routing decode requested for a metadata-only validation (whose decoded
    payload is discarded after its gates) may reuse values unchanged since the
    previous revision's decode; see canonical_text.decode_sharing. Values
    are retained for one step only and never leave the scope.
    """
    token = _cold_lineage_decodes.set({'previous': None}) if _cold_lineage_decodes.get() is None else None
    try:
        yield
    finally:
        if token is not None:
            _cold_lineage_decodes.reset(token)


def verify_saved_global_origins(
    repository, session, revision, *, sporting_component_proofs=None,
    _validated_value_signature=None, _reuse_actual_payload=False,
):
    physical = session.get(BranchSavedRevisionModel, revision.revision_id)
    if physical is None:
        raise ValueError('Global slot physical Saved origin is missing')
    cache = sporting_component_proofs.setdefault('_global_origin_inputs', {}) if sporting_component_proofs is not None else {}
    from beta_engine.infrastructure.db.native_fork_runtime_state import (
        actual_dependency_signature, actual_saved_revision_reference, assert_current_saved_row,
    )
    from beta_engine.infrastructure.db.repositories import _saved_revision_validation_signature

    actual_dependency_signature(session, physical, repository=repository)
    assert_current_saved_row(session, physical)
    signature = _saved_revision_validation_signature(physical)
    value_key = (physical.run_id, physical.branch_id, physical.revision_id,
        row_text_sha256(physical, 'payload_json'), False
    ) if _reuse_actual_payload and _validated_value_signature == signature else None

    def seed_actual_payload():
        if value_key in cache:
            return
        from beta_engine.domain.run_revisions import canonical_json

        # Reuse an already decoded actual row only when its FULL original JSON
        # equals every current SQLite byte. Noncanonical encoding or mutation
        # of the private payload takes the ordinary raw parser. This is decode
        # data, never an owner, reachability or mathematical proof.
        try:
            same_value = canonical_json(revision.payload) == physical.payload_json
        except (TypeError, ValueError):
            same_value = False
        if same_value:
            remember_verified_origin_projection(physical, revision.payload, cache)

    state = None
    if _validated_value_signature == signature:
        from beta_engine.infrastructure.db.calendar_native_competition import replayed_global_tour_value
        from beta_engine.infrastructure.db.canonical_text import PROOFS
        # revision.payload is the fresh decode of exactly physical.payload_json
        # (same signature): its Tour span hash equals the re-encoded value hash.
        state = replayed_global_tour_value(revision.payload, sporting_component_proofs,
            run_id=revision.run_id, branch_id=revision.branch_id,
            _payload_proof=PROOFS.prove(physical.payload_json, scope=physical.run_id))
        if state is None and _reuse_actual_payload:
            seed_actual_payload()
    if state is None:
        _, state = _origin_inputs(physical, cache)
    if state is None or state.schema_version != 'calendar_tour_authority.v5':
        raise ValueError('Global slot physical Saved origin changed its owner kind')
    reachable = set()
    parent = revision.parent_revision_id
    while parent:
        if parent in reachable:
            raise ValueError("Global slot Saved source lineage contains a cycle")
        reachable.add(parent)
        row = actual_saved_revision_reference(session, revision.run_id, parent)
        if row is None or row[1] != revision.run_id:
            raise ValueError("Global slot Saved source is missing or foreign")
        parent = row[4]
    ids = {
        r.request["command"]["expected_saved_head"]
        for r in state.receipts[len(state.competition_root_tour.receipts) :]
    }
    ids.update(a.played_saved_head for a in state.editions if a.played_saved_head)
    ids.add(state.competition_root_saved_head)
    if not ids <= reachable:
        raise ValueError("Global slot command source is outside its actual Saved past")
    # A completely verified global parent already authenticates every earlier
    # physical source in its lineage. Revalidating each prefix's entire lineage
    # again turns a season of Saves into repeated overlapping history walks.
    # Its proof is reusable only after actual_dependency_signature above has
    # freshly hashed the complete physical graph in this read snapshot.
    parent_row = session.get(BranchSavedRevisionModel, revision.parent_revision_id)
    parent_decoded = {}
    parent_is_global = parent_row is not None and is_global_slot_row(parent_row, repository=repository,
        _decoded_out=parent_decoded)
    sources_to_verify = (
        (revision.parent_revision_id,) if parent_is_global else sorted(reachable)
    )
    for source_id in sources_to_verify:
        row = session.get(BranchSavedRevisionModel, source_id)
        if (
            source_id not in reachable
            or row is None
            or row.run_id != revision.run_id
            or (source_id in ids and row.branch_id != revision.branch_id)
            or row.sequence >= revision.sequence
        ):
            raise ValueError(
                "Global slot command source is not an actual earlier reachable Saved owner"
            )
        repository._validated_saved_revision_in_session(
            session=session,
            model=row,
            materialize_payload=False,
            sporting_component_proofs=sporting_component_proofs,
            _decoded_payload=parent_decoded.get('value') if source_id == revision.parent_revision_id else None,
        )
    # Even when a parent proves ancestry, the current commands must independently
    # name actual same-Branch ancestors, never a foreign row in a shared past.
    for source_id in ids:
        row = actual_saved_revision_reference(session, revision.run_id, source_id)
        if row is None or row[1:3] != (revision.run_id, revision.branch_id):
            raise ValueError("Global slot command source has a foreign owner")
    prefix_row = parent_row if parent_is_global else None
    if revision.kind == BRANCH_RESTORE_SAVED_REVISION_KIND and _validated_value_signature == signature:
        # Restore appends to the current HEAD, but its sporting history comes
        # from an earlier reachable revision. Authenticate that exact physical
        # owner independently before it can provide the command prefix.
        target_id = revision.change_summary.get("target_saved_revision_id")
        if (
            isinstance(target_id, str)
            and target_id in reachable
            and target_id != revision.parent_revision_id
        ):
            target = session.get(BranchSavedRevisionModel, target_id)
            if (
                target is not None
                and (target.run_id, target.branch_id) == (revision.run_id, revision.branch_id)
                and target.sequence < revision.sequence
                and is_global_slot_row(target, repository=repository)
            ):
                repository._validated_saved_revision_in_session(
                    session=session, model=target, materialize_payload=False,
                    sporting_component_proofs=sporting_component_proofs,
                )
                prefix_row = target
    verified_prefix = None
    if prefix_row is not None:
        assert_current_saved_row(session, prefix_row)
        # Every selected prefix passed its complete physical/source gate.
        # Reuse it only if its actual immutable command values match.
        prefix_value = (sporting_component_proofs or {}).get('_global_verified_origin_tours', {}).get(
            _saved_revision_validation_signature(prefix_row))
        previous = prefix_value[1] if prefix_value is not None and prefix_value[1].fingerprint == prefix_value[0] else None
        if previous is None:
            _, previous = _origin_inputs(prefix_row, cache)
        if (
            previous is not None
            and (previous.run_id, previous.branch_id) == (state.run_id, state.branch_id)
            and state.competition_root_tour == previous.competition_root_tour
            and state.competition_root_saved_head == previous.competition_root_saved_head
            and state.receipts[:len(previous.receipts)] == previous.receipts
        ):
            verified_prefix = previous
    verify_tour_origins(session, state, _reachable_revision_ids=reachable,
        _origin_cache=cache, _verified_global_prefix=verified_prefix)
    if sporting_component_proofs is not None:
        # Retain this private value only AFTER the parent's/current physical
        # source gates finish. The actual complete row signature and a fresh
        # model value hash bind reuse while this one read walk remains active.
        values = sporting_component_proofs.setdefault('_global_verified_origin_tours', {})
        values[signature] = (state.fingerprint, state)
        while len(values) > 128:
            values.pop(next(iter(values)))
        if _validated_value_signature == signature:
            assert_current_saved_row(session, physical)
            if _saved_revision_validation_signature(physical) != signature:
                raise ValueError('Global origin changed during physical validation')
            if _reuse_actual_payload:
                seed_actual_payload()
            else:
                remember_verified_origin_projection(physical, revision.payload, cache)


def _shared_decode(row, shared):
    """Exactly ``json.loads(row.payload_json)``, sharing unchanged values (read-only)."""
    from beta_engine.infrastructure.db.canonical_text import PROOFS, decode_sharing

    text = row.payload_json
    proof = PROOFS.prove(text, scope=row.run_id) if type(text) is str and len(text) >= 1024 * 1024 else None
    if proof is None:
        shared['previous'] = None
        return json.loads(text)
    value = decode_sharing(proof, shared['previous'])
    shared['previous'] = (proof, value)
    return value


def is_global_slot_row(row, *, repository=None, _decoded_out=None, _share_decode=False):
    """Routing only; malformed data still receives the ordinary strict verifier.

    ``_share_decode`` (only meaningful inside cold_lineage_shared_decodes) lets
    the decode handed to ``_decoded_out`` share unchanged values with the
    previous revision's decode. The caller must use that payload read-only
    and discard it after validation.
    """
    signature = row_text_sha256(row, 'payload_json')
    if repository is not None:
        with repository._revision_validation_lock:
            hints = getattr(repository, '_global_kind_hints', {})
            if signature in hints:
                return hints[signature]
    shared = _cold_lineage_decodes.get() if _decoded_out is not None and _share_decode else None
    value = _shared_decode(row, shared) if shared is not None else json.loads(row.payload_json)
    if _decoded_out is not None:
        _decoded_out['value'] = (row.payload_json, value)
    for key in ("content", "calendar_tour_authority", "state"):
        if not isinstance(value, dict):
            value = None
            break
        value = value.get(key)
    result = (
        isinstance(value, dict)
        and value.get("schema_version") == "calendar_tour_authority.v5"
    )
    if repository is not None:
        with repository._revision_validation_lock:
            hints = getattr(repository, '_global_kind_hints', None)
            if hints is None:
                hints = repository._global_kind_hints = {}
            hints[signature] = result
            while len(hints) > 4096:
                hints.pop(next(iter(hints)))
    return result

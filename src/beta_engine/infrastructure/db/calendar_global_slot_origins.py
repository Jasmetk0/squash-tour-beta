"""Authenticate physical reachable origins of global-slot commands on Saved reads."""

import hashlib
import json

from beta_engine.infrastructure.db.calendar_tour import (
    _origin_inputs,
    verify_tour_origins,
)
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel


def verify_saved_global_origins(
    repository, session, revision, *, sporting_component_proofs=None
):
    physical = session.get(BranchSavedRevisionModel, revision.revision_id)
    if physical is None:
        raise ValueError('Global slot physical Saved origin is missing')
    cache = sporting_component_proofs.setdefault('_global_origin_inputs', {}) if sporting_component_proofs is not None else {}
    from beta_engine.infrastructure.db.native_fork_runtime_state import (
        actual_dependency_signature,
    )

    actual_dependency_signature(session, physical, repository=repository)
    _, state = _origin_inputs(physical, cache)
    if state is None or state.schema_version != 'calendar_tour_authority.v5':
        raise ValueError('Global slot physical Saved origin changed its owner kind')
    reachable = set()
    parent = revision.parent_revision_id
    while parent:
        if parent in reachable:
            raise ValueError("Global slot Saved source lineage contains a cycle")
        reachable.add(parent)
        row = session.get(BranchSavedRevisionModel, parent)
        if row is None or row.run_id != revision.run_id:
            raise ValueError("Global slot Saved source is missing or foreign")
        parent = row.parent_revision_id
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
    parent_is_global = parent_row is not None and is_global_slot_row(parent_row, repository=repository)
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
        )
    # Even when a parent proves ancestry, the current commands must independently
    # name actual same-Branch ancestors, never a foreign row in a shared past.
    for source_id in ids:
        row = session.get(BranchSavedRevisionModel, source_id)
        if row is None or (row.run_id, row.branch_id) != (revision.run_id, revision.branch_id):
            raise ValueError("Global slot command source has a foreign owner")
    verify_tour_origins(session, state, _reachable_revision_ids=reachable,
        _origin_cache=cache)


def is_global_slot_row(row, *, repository=None):
    """Routing only; malformed data still receives the ordinary strict verifier."""
    signature = hashlib.sha256(row.payload_json.encode('utf-8')).digest()
    if repository is not None:
        with repository._revision_validation_lock:
            hints = getattr(repository, '_global_kind_hints', {})
            if signature in hints:
                return hints[signature]
    value = json.loads(row.payload_json)
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

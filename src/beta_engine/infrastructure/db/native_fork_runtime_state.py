"""Actual-row authority and suffix replay for independent native fork aggregates."""

import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from beta_engine.application.calendar_tour_service import CalendarTourCommit
from beta_engine.application.native_fork_runtime_reducer import (
    initial_runtime,
    prepare_command,
    source_inputs,
)
from beta_engine.domain.native_fork_runtime import ForkRuntimeCommand, NativeForkRuntime
from beta_engine.domain.run_revisions import canonical_json
from beta_engine.domain.tournaments.calendar_tour import CalendarTourReceipt
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from beta_engine.infrastructure.db.run_prospect_source_state import (
    load_saved_run_prospect_source,
)

KEY = "native_fork_runtime"
SAVED_SCHEMA = "native_fork_saved_root.v2"
DRAFT_SCHEMA = "native_fork_runtime_draft.v1"
_proofs = ContextVar("native_read_proofs", default=None)
_MAX_DEPENDENCY_PROOFS = 256
_MAX_PARSED_RUNTIMES = 8
_MAX_PARSED_RUNTIME_BYTES = 8 * 1024 * 1024


@sqlalchemy_event.listens_for(Engine, "before_cursor_execute")
def _invalidate_physical_read_cache(connection, cursor, statement, parameters, context, executemany):
    memo = _proofs.get()
    if memo is None or statement.lstrip()[:6].upper() == "SELECT":
        return
    # Includes SAVEPOINT/ROLLBACK TO and direct SQL writes, not just ORM flushes.
    key = ("native_dependency_sql_generation", connection.connection.driver_connection)
    memo[key] = memo.get(key, 0) + 1


def _physical_read_cache(session):
    """Reuse actual bytes only inside one unchanged SQLite read snapshot.

    This is not a validation proof or a cross-request cache. Every new transaction
    rereads all dependencies. Own writes (including direct SQL and savepoint
    rollback) invalidate it; pending ORM work disables it until flushed.
    """
    memo = _proofs.get()
    if memo is None or session.new or session.dirty or session.deleted:
        return None
    sqlalchemy_connection = session.connection()
    connection = sqlalchemy_connection.connection.driver_connection
    if not getattr(connection, "in_transaction", False) or type(getattr(connection, "total_changes", None)) is not int:
        return None
    if not sqlalchemy_connection.info.get("native_dependency_trace_installed"):
        # total_changes does not change on ROLLBACK TO. Observe SQLite itself so
        # direct driver savepoints/transactions cannot reuse an earlier snapshot.
        connection_info = sqlalchemy_connection.info
        def trace(statement):
            if statement.lstrip()[:6].upper() != "SELECT":
                # Connection-local, including calls from another Python context.
                # Do not retain SQL text, parameters, rows or request objects.
                connection_info["native_dependency_sqlite_generation"] = connection_info.get("native_dependency_sqlite_generation", 0) + 1
        connection.set_trace_callback(trace)
        sqlalchemy_connection.info["native_dependency_trace_installed"] = True
    snapshot = (
        session.get_transaction(),
        session.get_nested_transaction(), connection, connection.total_changes,
        memo.get(("native_dependency_sql_generation", connection), 0),
        sqlalchemy_connection.info.get("native_dependency_sqlite_generation", 0),
    )
    key = ("native_dependency_physical_rows", session)
    previous = memo.get(key)
    if previous is None or previous[0] != snapshot:
        previous = memo[key] = (snapshot, {"owners": {}, "revisions": {}, "proofs": {}})
    return previous[1]


def snapshot_proofs(session):
    """Completed operation proofs cannot outlive their actual read snapshot."""
    cache = _physical_read_cache(session)
    return cache["proofs"] if cache is not None else {}


def assert_current_saved_row(session, revision):
    """A source ORM identity is not evidence of its current physical bytes."""
    memo = _proofs.get()
    if memo is None or not memo.get("native_actual_reads"):
        return
    from sqlalchemy import select

    fields = _physical_revision_fields()
    cache = _physical_read_cache(session)
    cached = cache["revisions"].get((revision.run_id, revision.revision_id)) if cache is not None else None
    actual = cached[0] if cached is not None else session.execute(
        select(*fields).where(BranchSavedRevisionModel.revision_id == revision.revision_id)
    ).first()
    expected = tuple(getattr(revision, field.key) for field in fields)
    if actual is None or tuple(actual) != expected:
        raise ValueError("Native Saved row differs from its actual stored bytes")


def _physical_revision_fields():
    return tuple(getattr(BranchSavedRevisionModel, key) for key in (
        "revision_id", "run_id", "branch_id", "sequence", "parent_revision_id",
        "kind", "payload_schema_version", "content_hash_algorithm", "content_hash",
        "payload_json", "change_summary_json",
    ))


@contextmanager
def native_read_proof_scope():
    token = _proofs.set({}) if _proofs.get() is None else None
    try:
        yield _proofs.get()
    finally:
        if token is not None:
            _proofs.reset(token)


def load_runtime(payload):
    raw = payload.get("content", {}).get(KEY)
    if not isinstance(raw, dict) or set(raw) != {"state", "fingerprint"}:
        raise ValueError("Malformed native fork runtime component")
    serialized = canonical_json(raw).encode("utf-8")
    signature = hashlib.sha256(serialized).digest()
    memo = _proofs.get()
    cache = memo.setdefault("parsed_native_runtimes", {}) if memo is not None else {}
    prior = cache.pop(signature, None)
    if prior is not None:
        cache[signature] = prior
        return prior[1]
    runtime = NativeForkRuntime.model_validate_json(canonical_json(raw["state"]))
    if runtime.fingerprint != raw["fingerprint"]:
        raise ValueError("Native fork runtime fingerprint differs")
    size = len(serialized)
    if memo is not None and size <= _MAX_PARSED_RUNTIME_BYTES:
        cache[signature] = (size, runtime)
        while len(cache) > _MAX_PARSED_RUNTIMES or sum(item[0] for item in cache.values()) > _MAX_PARSED_RUNTIME_BYTES:
            cache.pop(next(iter(cache)))
    return runtime


def component(runtime):
    return {
        "state": runtime.model_dump(mode="json"),
        "fingerprint": runtime.fingerprint,
    }


def commit_prepared(previous, candidate, request, result, version):
    return NativeForkRuntime.model_validate_json(
        candidate.model_copy(
            update={
                "tour": candidate.tour.model_copy(
                    update={
                        "receipts": candidate.tour.receipts
                        + (
                            CalendarTourReceipt(
                                command_id=request.command.command_id,
                                request=request.model_dump(mode="json"),
                                result=result,
                            ),
                        )
                    }
                ),
                "journal": previous.journal
                + (
                    ForkRuntimeCommand(
                        draft_version_before=version,
                        request=request.model_dump(mode="json"),
                        result=result,
                    ),
                ),
            }
        ).model_dump_json()
    )


def verify_runtime(repository, session, *, runtime, revision, original, working=False):
    reachable = set()
    ancestors = []
    if working:
        reachable.add(revision.revision_id)
        ancestors.append(session.get(BranchSavedRevisionModel, revision.revision_id))
    parent, sequence = revision.parent_revision_id, revision.sequence
    while parent:
        if parent in reachable:
            raise ValueError("Native fork Saved ancestry contains a cycle")
        row = session.get(BranchSavedRevisionModel, parent)
        if row is None or row.run_id != runtime.run_id or row.sequence != sequence - 1:
            raise ValueError(
                "Native fork Saved ancestry is missing, foreign or discontinuous"
            )
        reachable.add(parent)
        ancestors.append(row)
        parent, sequence = row.parent_revision_id, row.sequence
    root_id = runtime.root_saved_revision_id
    if root_id != revision.revision_id:
        if root_id not in reachable:
            raise ValueError("Native fork root is unreachable")
        row = session.get(BranchSavedRevisionModel, root_id)
        if (row.run_id, row.branch_id, row.kind, row.payload_schema_version) != (
            runtime.run_id,
            runtime.branch_id,
            "branch_fork_materialized",
            SAVED_SCHEMA,
        ):
            raise ValueError("Native fork root is not its actual target installation")
        root = repository._validated_saved_revision_in_session(
            session=session, model=row
        )
        signed_root = load_runtime(root.payload)
        if signed_root.baseline != runtime.baseline or signed_root.journal:
            raise ValueError("Native fork root has another baseline/history")
    sources = source_inputs(original, repository, session)
    expected = initial_runtime(runtime.baseline, root_id, sources)
    cache = {}
    journal = [e.model_dump(mode="json") for e in runtime.journal]
    # Reuse a COMPLETE proof of an actual reachable Saved prefix, never a
    # self-declared fingerprint. Only the new suffix needs another MatchEngine run.
    for row in ancestors:
        if (
            row.branch_id != runtime.branch_id
            or row.payload_schema_version != SAVED_SCHEMA
        ):
            continue
        raw = (
            json.loads(row.payload_json)
            .get("content", {})
            .get(KEY, {})
            .get("state", {})
        )
        prefix = raw.get("journal")
        if (
            not isinstance(prefix, list)
            or len(prefix) > len(journal)
            or prefix != journal[: len(prefix)]
        ):
            continue
        record = repository._validated_saved_revision_in_session(
            session=session, model=row
        )
        signed = load_runtime(record.payload)
        if (
            signed.baseline != runtime.baseline
            or signed.root_saved_revision_id != root_id
        ):
            raise ValueError("Native fork Saved prefix has another root")
        expected = signed
        cache[row.revision_id] = (record, signed)
        break
    for event in runtime.journal[len(expected.journal) :]:
        request = CalendarTourCommit.model_validate_json(canonical_json(event.request))
        saved_id = request.command.expected_saved_head
        if saved_id not in reachable:
            raise ValueError("Fork command source is outside its actual Saved past")
        if saved_id not in cache:
            row = session.get(BranchSavedRevisionModel, saved_id)
            if row is None or (row.run_id, row.branch_id) != (
                runtime.run_id,
                runtime.branch_id,
            ):
                raise ValueError("Fork command source has a foreign owner")
            record = repository._validated_saved_revision_in_session(
                session=session, model=row
            )
            cache[saved_id] = (record, load_runtime(record.payload))
        record, signed = cache[saved_id]
        if (
            signed.baseline != runtime.baseline
            or len(signed.journal) > len(expected.journal)
            or signed.journal != expected.journal[: len(signed.journal)]
        ):
            raise ValueError("Fork command source is not its actual Saved prefix")
        per_command = type(sources)(**vars(sources))
        from beta_engine.domain.calendar.run_calendar import RunCalendar

        per_command.execution_calendar = RunCalendar.from_metadata(
            record.payload["run"]["run_calendar"]
        )
        per_command.prospects = load_saved_run_prospect_source(
            record.payload, run_id=runtime.run_id
        )
        preview, candidate, result = prepare_command(
            expected,
            request.command,
            per_command,
            saved_head=saved_id,
            draft_version=event.draft_version_before,
            is_saved=signed == expected,
        )
        if (
            preview["preview_fingerprint"] != request.expected_preview_fingerprint
            or result != event.result
        ):
            raise ValueError("Native fork command differs from actual confirmed replay")
        expected = commit_prepared(
            expected, candidate, request, result, event.draft_version_before
        )
    if expected != runtime:
        raise ValueError(
            "Native fork current facts differ from its actual source and complete replay"
        )
    return runtime


def actual_dependency_signature(session, revision):
    """Exact physical dependency graph, rebuilt before any cross-read proof reuse.

    A self-declared hash is insufficient. Include complete stored bytes, topology,
    actual owner origins, and current source-Branch reachability. Own later Saves
    need not invalidate an immutable prefix; a change to ANY dependency does.
    Only successfully completed proofs enter the bounded repository cache.
    """
    from sqlalchemy import func, select

    from beta_engine.infrastructure.db.models import RunBranchModel

    fields = _physical_revision_fields()
    memo = _proofs.get()
    if memo is not None:
        memo["native_actual_reads"] = True
    read_cache = _physical_read_cache(session)
    owners = read_cache["owners"] if read_cache is not None else {}
    revisions = read_cache["revisions"] if read_cache is not None else {}

    def actual_owner(branch_id):
        key = (revision.run_id, branch_id)
        if key not in owners:
            row = session.execute(
                select(
                    RunBranchModel.branch_id,
                    RunBranchModel.run_id,
                    RunBranchModel.forked_from_branch_id,
                    RunBranchModel.forked_from_saved_revision_id,
                    RunBranchModel.status,
                    RunBranchModel.read_only,
                    RunBranchModel.saved_head_revision_id,
                ).where(
                    RunBranchModel.run_id == revision.run_id,
                    RunBranchModel.branch_id == branch_id,
                )
            ).first()
            owners[key] = tuple(row) if row is not None else None
            loaded = session.identity_map.get((RunBranchModel, (branch_id,), None))
            if loaded is not None and (
                row is None or tuple(getattr(loaded, name) for name in (
                    "branch_id", "run_id", "forked_from_branch_id",
                    "forked_from_saved_revision_id", "status", "read_only",
                    "saved_head_revision_id",
                )) != tuple(row)
            ):
                raise ValueError("Native Branch owner differs from its actual stored bytes")
        return owners[key]

    def actual_revision(revision_id):
        key = (revision.run_id, revision_id)
        if key not in revisions:
            try:
                actual = session.execute(
                    select(
                        *fields,
                        func.json_extract(BranchSavedRevisionModel.payload_json,
                            "$.content.native_fork_baseline.state.selected_source_branch_id"),
                        func.json_type(BranchSavedRevisionModel.payload_json,
                            "$.content.calendar_tour_authority"),
                    ).where(
                        BranchSavedRevisionModel.run_id == revision.run_id,
                        BranchSavedRevisionModel.revision_id == revision_id,
                    )
                ).first()
            except OperationalError as exc:
                if "malformed JSON" in str(exc.orig):
                    raise ValueError("Native Saved row contains malformed JSON") from exc
                raise
            row = tuple(actual[:len(fields)]) if actual is not None else None
            if row is None:
                revisions[key] = (None, None, ())
            else:
                # SQLite extracts only the dependency references. Do not allocate
                # every historical match/journal just to discover these two keys.
                # Every byte still contributes to the physical-row digest below.
                branch_ids = {actual[len(fields)]} if actual[len(fields)] is not None else set()
                if actual[len(fields) + 1] is not None:
                    branch_ids.add(row[2])
                digest = hashlib.sha256()
                for value in row:
                    raw = canonical_json(value).encode("utf-8") if not isinstance(value, str) else value.encode("utf-8")
                    digest.update(b"s" if isinstance(value, str) else b"j")
                    digest.update(len(raw).to_bytes(8, "big"))
                    digest.update(raw)
                revisions[key] = (
                    row, digest.hexdigest(),
                    tuple(branch_ids),
                )
        return revisions[key]

    pending, visited, graph, source_heads = [revision.revision_id], set(), [], {}
    while pending:
        revision_id = pending.pop()
        if revision_id in visited:
            continue
        visited.add(revision_id)
        row, digest, branch_ids = actual_revision(revision_id)
        if revision_id == revision.revision_id and hasattr(revision, "payload_json"):
            expected = tuple(getattr(revision, field.key) for field in fields)
            if row != expected:
                raise ValueError(
                    "Native Saved row differs from its actual stored bytes"
                )
        if row is None:
            graph.append((revision_id, None))
            continue
        owner = actual_owner(row[2])
        graph.append(
            (
                revision_id,
                digest,
                owner[:-1] if owner else None,
            )
        )
        if row[4]:
            pending.append(row[4])
        for branch_id in branch_ids:
            source = actual_owner(branch_id)
            source_heads[branch_id] = source
            if source and source[-1]:
                pending.append(source[-1])
    return (
        revision.revision_id,
        tuple(sorted(graph)),
        tuple(sorted(source_heads.items())),
    )


def has_actual_dependency_proof(repository, signature, *, run_id, branch_id):
    """A history walk must not evict the complete current-HEAD proof."""
    proof_key = _dependency_proof_key(signature)
    with repository._revision_validation_lock:
        heads = getattr(repository, "_native_head_dependency_proofs", {})
        key = (run_id, branch_id)
        if heads.get(key) == proof_key:
            heads[key] = heads.pop(key)  # bounded, recently used Branch heads
            return True
        proofs = getattr(repository, "_native_dependency_proofs", {})
        return proof_key in proofs


def _dependency_proof_key(signature):
    # Keep only a compact cryptographic digest of the COMPLETE actual graph,
    # never mutable payloads. Longer histories can retain their proven prefixes
    # without an unbounded collection of overlapping graph tuples.
    return hashlib.sha256(canonical_json(signature).encode("utf-8")).hexdigest()


def verify_with_actual_dependencies(repository, session, revision, verify):
    """Reuse a complete proof only when its entire actual dependency graph matches."""
    signature = actual_dependency_signature(session, revision)
    if has_actual_dependency_proof(repository, signature, run_id=revision.run_id, branch_id=revision.branch_id):
        return
    verify()
    proof_key = _dependency_proof_key(signature)
    from sqlalchemy import select

    from beta_engine.infrastructure.db.models import RunBranchModel

    actual_head = session.scalar(select(RunBranchModel.saved_head_revision_id).where(
        RunBranchModel.run_id == revision.run_id, RunBranchModel.branch_id == revision.branch_id,
    ))
    with repository._revision_validation_lock:
        proofs = getattr(repository, "_native_dependency_proofs", None)
        if proofs is None:
            proofs = repository._native_dependency_proofs = {}
        proofs[proof_key] = True
        while len(proofs) > _MAX_DEPENDENCY_PROOFS:
            proofs.pop(next(iter(proofs)))
        if actual_head == revision.revision_id:
            heads = getattr(repository, "_native_head_dependency_proofs", None)
            if heads is None:
                heads = repository._native_head_dependency_proofs = {}
            key = (revision.run_id, revision.branch_id)
            heads.pop(key, None)
            heads[key] = proof_key
            while len(heads) > 16:
                heads.pop(next(iter(heads)))

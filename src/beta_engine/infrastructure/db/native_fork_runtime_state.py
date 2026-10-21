"""Actual-row authority and suffix replay for independent native fork aggregates."""

import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar

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
    signature = canonical_json(raw)
    memo = _proofs.get()
    key = ("parsed_native_runtime", signature)
    if memo is not None and key in memo:
        return memo[key]
    runtime = NativeForkRuntime.model_validate_json(canonical_json(raw["state"]))
    if runtime.fingerprint != raw["fingerprint"]:
        raise ValueError("Native fork runtime fingerprint differs")
    if memo is not None:
        memo[key] = runtime
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
    from sqlalchemy import select

    from beta_engine.infrastructure.db.models import RunBranchModel

    fields = (
        BranchSavedRevisionModel.revision_id,
        BranchSavedRevisionModel.run_id,
        BranchSavedRevisionModel.branch_id,
        BranchSavedRevisionModel.sequence,
        BranchSavedRevisionModel.parent_revision_id,
        BranchSavedRevisionModel.kind,
        BranchSavedRevisionModel.payload_schema_version,
        BranchSavedRevisionModel.content_hash_algorithm,
        BranchSavedRevisionModel.content_hash,
        BranchSavedRevisionModel.payload_json,
        BranchSavedRevisionModel.change_summary_json,
    )
    owners = {}

    def actual_owner(branch_id):
        if branch_id not in owners:
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
            owners[branch_id] = tuple(row) if row is not None else None
        return owners[branch_id]

    pending, visited, graph, source_heads = [revision.revision_id], set(), [], {}
    while pending:
        revision_id = pending.pop()
        if revision_id in visited:
            continue
        visited.add(revision_id)
        actual = session.execute(
            select(*fields).where(
                BranchSavedRevisionModel.run_id == revision.run_id,
                BranchSavedRevisionModel.revision_id == revision_id,
            )
        ).first()
        row = tuple(actual) if actual is not None else None
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
                hashlib.sha256(canonical_json(row).encode("utf-8")).hexdigest(),
                owner[:-1] if owner else None,
            )
        )
        if row[4]:
            pending.append(row[4])
        content = json.loads(row[9]).get("content", {})
        baseline = content.get("native_fork_baseline", {}).get("state")
        branch_ids = (
            {baseline.get("selected_source_branch_id")}
            if isinstance(baseline, dict)
            else set()
        )
        if "calendar_tour_authority" in content:
            branch_ids.add(row[2])
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


def verify_with_actual_dependencies(repository, session, revision, verify):
    """Reuse a complete proof only when its entire actual dependency graph matches."""
    signature = actual_dependency_signature(session, revision)
    with repository._revision_validation_lock:
        proofs = getattr(repository, "_native_dependency_proofs", {})
        if signature in proofs:
            return
    verify()
    with repository._revision_validation_lock:
        proofs = getattr(repository, "_native_dependency_proofs", None)
        if proofs is None:
            proofs = repository._native_dependency_proofs = {}
        proofs[signature] = True
        while len(proofs) > 16:
            proofs.pop(next(iter(proofs)))

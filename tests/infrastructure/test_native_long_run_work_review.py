"""Work review blockers: real SQLite corruption and cross-Run cache isolation.

These regressions pass on the owner-merged production base and fail on the
reviewed PR #1803 source. They intentionally remain blocking until repaired;
see docs/NATIVE_LONG_RUN_WORK_REVIEW.md. No HTTP exploit is claimed by the
dependency-helper differential test.
"""

import hashlib
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from beta_engine.application.run_saved_revision_history_service import RunSavedRevisionHistoryService
from beta_engine.domain.run_revisions import (
    canonical_json,
    saved_revision_content_hash,
    saved_revision_hash_envelope,
)
from beta_engine.infrastructure.db import SavedRevisionHistoryConflictError
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from beta_engine.infrastructure.db.native_fork_runtime_state import (
    _proofs,
    actual_dependency_signature,
    native_read_proof_scope,
)
from tests.application.test_saved_revision_history import _create_run_and_fork, _repository
from tests.infrastructure.test_native_dependency_read_snapshot import source  # noqa: F401

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("warm", [False, True], ids=["cold", "warm"])
def test_legacy_noncanonical_text_with_valid_canonical_hash_stays_readable(tmp_path, warm):
    """Rejecting the forged raw-text hash must not reject valid historical rows."""
    database = f"sqlite:///{tmp_path / 'valid-legacy.db'}"
    repository = _repository(database)
    _create_run_and_fork(repository)
    service = RunSavedRevisionHistoryService(repository=repository)
    if warm:
        service.list_history(run_id="run-one", branch_id="branch-one")
    with repository._session_factory.begin() as session:
        row = session.get(BranchSavedRevisionModel, "revision-one")
        row.payload_json = json.dumps(json.loads(row.payload_json), indent=2)
        # Retain the correct existing hash of the decoded canonical envelope.
    if not warm:
        service = RunSavedRevisionHistoryService(repository=_repository(database))
    assert service.list_history(run_id="run-one", branch_id="branch-one").saved_head_revision_id == "revision-one"


@pytest.mark.parametrize("warm", [False, True], ids=["cold", "warm"])
@pytest.mark.parametrize("encoding", ["whitespace", "duplicate_keys", "key_order"])
def test_history_rejects_hash_of_noncanonical_stored_envelope(tmp_path, encoding, warm):
    """A database-declared digest is untrusted even when it hashes stored text."""
    database = f"sqlite:///{tmp_path / 'noncanonical.db'}"
    repository = _repository(database)
    _create_run_and_fork(repository)
    service = RunSavedRevisionHistoryService(repository=repository)
    if warm:
        service.list_history(run_id="run-one", branch_id="branch-one")
    with repository._session_factory.begin() as session:
        row = session.get(BranchSavedRevisionModel, "revision-one")
        payload = json.loads(row.payload_json)
        summary = json.loads(row.change_summary_json)
        fields = {name: getattr(row, name) for name in (
            "revision_id", "run_id", "branch_id", "sequence", "parent_revision_id",
            "kind", "payload_schema_version",
        )}
        if encoding == "whitespace":
            stored = json.dumps(payload, ensure_ascii=False, indent=2)
        elif encoding == "duplicate_keys":
            stored = '{"run":{"display_name":"discarded"},' + canonical_json(payload)[1:]
        else:
            stored = json.dumps(dict(reversed(list(payload.items()))),
                                ensure_ascii=False, separators=(",", ":"))
        assert json.loads(stored) == payload
        assert stored != canonical_json(payload)
        envelope = canonical_json(saved_revision_hash_envelope(
            **fields, payload=payload, change_summary=summary))
        needle = '"payload":' + canonical_json(payload) + ',"payload_schema_version":'
        assert envelope.count(needle) == 1
        stored_envelope = envelope.replace(
            needle, '"payload":' + stored + ',"payload_schema_version":', 1)
        invalid_hash = hashlib.sha256(stored_envelope.encode("utf-8")).hexdigest()
        assert invalid_hash != saved_revision_content_hash(
            **fields, payload=payload, change_summary=summary)
        session.execute(text(
            "UPDATE branch_saved_revisions SET payload_json=:payload, content_hash=:hash "
            "WHERE revision_id=:revision"
        ), {"payload": stored, "hash": invalid_hash, "revision": row.revision_id})
    if not warm:
        service = RunSavedRevisionHistoryService(repository=_repository(database))
    with pytest.raises(SavedRevisionHistoryConflictError, match="content integrity"):
        service.list_history(run_id="run-one", branch_id="branch-one")


@pytest.mark.parametrize("first", ["owner", "foreign"])
def test_dependency_graph_memo_is_scoped_to_run(source, first):  # noqa: F811
    """Equal revision-ID sets alone do not mean equal run-scoped physical rows."""
    _engine, factory = source
    with factory() as session, native_read_proof_scope():
        session.execute(text("BEGIN"))
        owner = session.get(BranchSavedRevisionModel, "saved")
        foreign = SimpleNamespace(run_id="different-run", revision_id=owner.revision_id)
        references = [owner, foreign] if first == "owner" else [foreign, owner]
        for reference in references:
            memoized = actual_dependency_signature(session, reference)
            token = _proofs.set(None)
            try:
                uncached = actual_dependency_signature(session, reference)
            finally:
                _proofs.reset(token)
            assert memoized == uncached, "dependency graph changed according to another Run's cached read"

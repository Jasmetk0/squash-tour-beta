"""Concurrent cold reads share successful exact-byte proofs, never payloads."""

from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier, Lock
import time

import pytest

from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from tests.application.test_run_working_draft_save import _empty_run, _repository

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize('corrupt', [False, True])
def test_concurrent_cold_reads_validate_each_signature_once(tmp_path, monkeypatch, corrupt):
    repository = _repository(f"sqlite:///{tmp_path / 'single-flight.db'}")
    _empty_run(repository)
    repository._revision_validation_cache.clear()
    if corrupt:
        with repository._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, 'revision-one')
            raw = json.loads(row.payload_json)
            raw['run']['display_name'] = 'forged'
            row.payload_json = json.dumps(raw)
    original = repository._to_branch_saved_revision
    count = 0
    lock = Lock()
    barrier = Barrier(4)

    def slow_parse(model, **kwargs):
        nonlocal count
        if kwargs.get('validate_components', True):
            with lock:
                count += 1
            # Keep the first full validation in flight while all requests have
            # crossed the barrier. This reproduces cold browser request fanout.
            time.sleep(0.1)
        return original(model, **kwargs)

    monkeypatch.setattr(repository, '_to_branch_saved_revision', slow_parse)

    def read(_index):
        with repository._session_factory() as session:
            row = session.get(BranchSavedRevisionModel, 'revision-one')
            barrier.wait(timeout=5)
            if corrupt:
                with pytest.raises(ValueError, match='content integrity'):
                    repository._validated_saved_revision_in_session(session=session, model=row)
                return None
            return repository._validated_saved_revision_in_session(session=session, model=row)

    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(read, range(4)))
    if corrupt:
        # A failed check never becomes a proof reusable by another request.
        assert count == 4 and not repository._revision_validation_cache
    else:
        assert count == 1
        assert len({r.content_hash for r in records}) == 1
        records[0].payload['run']['display_name'] = 'caller change'
        assert all(r.payload['run']['display_name'] != 'caller change' for r in records[1:])
        assert all(not r.payload for r in repository._revision_validation_cache.values())


def test_warm_proof_does_not_authenticate_changed_stored_bytes(tmp_path):
    repository = _repository(f"sqlite:///{tmp_path / 'changed.db'}")
    _empty_run(repository)
    repository.get_branch_revision_state(branch_id='branch-one')
    with repository._session_factory.begin() as session:
        row = session.get(BranchSavedRevisionModel, 'revision-one')
        raw = json.loads(row.payload_json)
        raw['run']['display_name'] = 'changed after validation'
        row.payload_json = json.dumps(raw)
    with pytest.raises(ValueError, match='content integrity'):
        repository.get_branch_revision_state(branch_id='branch-one')

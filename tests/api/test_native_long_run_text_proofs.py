"""Real SQLite/API reads with the proven-canonical-text hashes; nothing is mocked.

Every content hash and component hash computed over proven stored text must
equal the ordinary re-encoding, the response must be byte-identical to a read
with the proofs disabled, and changed stored values must still be rejected,
whether they are canonical (re-hashed) or not.
"""

import json

import pytest

from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.run_revisions import canonical_json, saved_revision_content_hash
from beta_engine.domain.tournaments import calendar_global_slots
from beta_engine.infrastructure.db import calendar_native_competition, canonical_text, repositories
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from beta_engine.infrastructure.db.repositories import BranchRevisionStateConflictError
from tests.api.test_native_long_run_cold_lineage import cold_repository, oldest_global_ancestor, read

pytestmark = pytest.mark.smoke


def dump(result):
    return json.dumps(result.model_dump(mode="json") if hasattr(result, "model_dump") else result,
                      sort_keys=True, default=str)


def test_cold_read_hashes_equal_the_ordinary_re_encoding(tmp_path, prepared_slots, monkeypatch):
    checked = {"content": 0, "tour": 0, "component": 0}
    content = repositories._saved_revision_model_content_hash
    tour = calendar_global_slots._incremental_tour_fingerprint
    proven = calendar_native_competition._proven_hash

    def cross_content(model, revision):
        value = content(model, revision)
        assert value == repositories._saved_revision_record_content_hash(revision)
        checked["content"] += 1
        return value

    def cross_tour(value, scope):
        fingerprint = tour(value, scope)
        if fingerprint is not None:
            assert fingerprint == canonical_hash(value.model_dump(mode="json"))
            checked["tour"] += 1
        return fingerprint

    def cross_component(payload_proof, path, value):
        fingerprint = proven(payload_proof, path, value)
        assert fingerprint == canonical_hash(value)
        checked["component"] += 1
        return fingerprint

    with monkeypatch.context() as patch:
        patch.setattr(repositories, "_saved_revision_model_content_hash", cross_content)
        patch.setattr(calendar_global_slots, "_incremental_tour_fingerprint", cross_tour)
        patch.setattr(calendar_native_competition, "_proven_hash", cross_component)
        patch.setattr(canonical_text, "PROOFS", canonical_text.CanonicalTextProofs())
        candidate = dump(read(cold_repository(tmp_path, prepared_slots, "candidate.db")))
    assert min(checked.values()) > 0, checked
    with monkeypatch.context() as patch:
        patch.setattr(canonical_text.CanonicalTextProofs, "prove", lambda self, text, *, scope: None)
        patch.setattr(calendar_global_slots, "_incremental_tour_fingerprint", lambda value, scope: None)
        ordinary = dump(read(cold_repository(tmp_path, prepared_slots, "ordinary.db")))
    assert candidate == ordinary


def rewrite(repository, revision_id, change, *, rehash):
    with repository._session_factory.begin() as session:
        row = session.get(BranchSavedRevisionModel, revision_id)
        body = json.loads(row.payload_json)
        change(body)
        row.payload_json = canonical_json(body)  # a CANONICAL text: proofs apply
        if rehash:
            row.content_hash = saved_revision_content_hash(
                revision_id=row.revision_id, run_id=row.run_id, branch_id=row.branch_id,
                sequence=row.sequence, parent_revision_id=row.parent_revision_id, kind=row.kind,
                payload_schema_version=row.payload_schema_version, payload=body,
                change_summary=json.loads(row.change_summary_json),
            )


def ancestor_with_events(repository):
    """Newest non-HEAD revision whose checkpoint already holds events."""
    with repository._session_factory() as session:
        rows = session.query(BranchSavedRevisionModel).order_by(BranchSavedRevisionModel.sequence).all()
        candidates = [
            r.revision_id for r in rows[:-1]
            if json.loads(r.payload_json).get("content", {}).get("calendar_player_sporting_checkpoint", {})
            .get("state", {}).get("events")
        ]
    assert candidates
    return candidates[-1]


def change_ranking(body):
    state = body["content"]["calendar_tour_authority"]["state"]
    state["rankings"] = state["rankings"][:-1] or [{"forged": True}]
    body["content"]["calendar_tour_authority"]["fingerprint"] = canonical_hash(state)


def change_checkpoint_event(body):
    events = body["content"]["calendar_player_sporting_checkpoint"]["state"]["events"]
    events[0] = {**events[0], "forged": True}
    body["content"]["calendar_player_sporting_checkpoint"]["fingerprint"] = canonical_hash(
        body["content"]["calendar_player_sporting_checkpoint"]["state"])


@pytest.mark.parametrize("when", ["cold", "after_warm"])
@pytest.mark.parametrize("change,rehash", [
    (change_ranking, True), (change_checkpoint_event, True), (change_ranking, False),
])
def test_changed_canonical_ancestor_is_rejected(tmp_path, prepared_slots, monkeypatch, when, change, rehash):
    monkeypatch.setattr(canonical_text, "PROOFS", canonical_text.CanonicalTextProofs())
    repository = cold_repository(tmp_path, prepared_slots, "changed.db")
    if when == "after_warm":
        read(repository)
    target = (ancestor_with_events(repository) if change is change_checkpoint_event
              else oldest_global_ancestor(repository)[0])
    rewrite(repository, target, change, rehash=rehash)
    with pytest.raises(BranchRevisionStateConflictError):
        read(repository)


def test_noncanonical_legacy_spelling_keeps_the_ordinary_verdict(tmp_path, prepared_slots, monkeypatch):
    """Whitespace-only respelling: same decoded value, unchanged declared hash.

    The hash is defined over the decoded value, so the original reader accepts
    this row; without a canonical-text proof the ordinary path decides the same.
    """
    monkeypatch.setattr(canonical_text, "PROOFS", canonical_text.CanonicalTextProofs())
    repository = cold_repository(tmp_path, prepared_slots, "spelling.db")
    expected = dump(read(repository))
    oldest, _ = oldest_global_ancestor(repository)
    with repository._session_factory.begin() as session:
        row = session.get(BranchSavedRevisionModel, oldest)
        row.payload_json = json.dumps(json.loads(row.payload_json), indent=1, sort_keys=True)
    assert dump(read(repository)) == expected

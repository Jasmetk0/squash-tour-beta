"""Pure manifest/graph corruption contracts; no SQLite or mocked authorities."""

from copy import deepcopy

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_branch_archive import (
    Archive,
    ArchiveError,
    decode,
    digest,
    encode,
    pack,
)
from beta_engine.domain.run_revisions import (
    initial_saved_revision_payload,
    saved_revision_content_hash,
)

pytestmark = pytest.mark.pr_critical


@pytest.fixture
def minimal():
    clock = RunCalendar.fax_default().to_metadata()
    payload = initial_saved_revision_payload(
        run_id="run",
        display_name="Archive",
        run_status="working",
        timeline_start_season=2000,
        timeline_end_season=2049,
        branch_id="branch",
        branch_display_name="Timeline 1",
        branch_status="active",
        run_calendar_metadata=clock,
    )
    row = {
        "revision_id": "root",
        "run_id": "run",
        "branch_id": "branch",
        "sequence": 1,
        "parent_revision_id": None,
        "kind": "initial_run_creation",
        "payload_schema_version": "empty_run_saved_revision_v1",
    }
    summary = {"kind": "initial_run_creation"}
    row.update(
        content_hash_algorithm="sha256",
        content_hash=saved_revision_content_hash(
            **row, payload=payload, change_summary=summary
        ),
        payload_json=encode(payload).decode(),
        change_summary_json=encode(summary).decode(),
        created_at="2026-10-30 00:00:00",
    )
    return {
        "run": {
            "run_id": "run",
            "display_name": "Archive",
            "status": "working",
            "timeline_start_season": 2000,
            "timeline_end_season": 2049,
            "viewer_branch_id": "branch",
            "activation_revision_id": "root",
            "metadata_json": encode({"run_calendar": clock}).decode(),
        },
        "branches": [
            {
                "branch_id": "branch",
                "display_name": "Timeline 1",
                "status": "active",
                "branch_seed": None,
                "forked_from_branch_id": None,
                "forked_from_saved_revision_id": None,
                "saved_head_revision_id": "root",
                "metadata_json": "{}",
                "role": "selected",
            }
        ],
        "revisions": [row],
        "audits": [],
        "checkpoints": [],
        "allocator": 1,
        "selected_branch_id": "branch",
        "selected_head_revision_id": "root",
        "omitted_branch_ids": [],
    }


def test_deterministic_manifest_preserves_original_bytes_and_exact_scope(minimal):
    raw = pack(**minimal)
    archive = Archive(raw)
    assert raw == pack(**deepcopy(minimal))
    assert archive.revisions[0].payload_json == minimal["revisions"][0]["payload_json"]
    assert (
        archive.envelope.scope == "custom_selected_saved_branch_with_dependency_history"
    )
    assert archive.size == len(raw) and archive.raw_digest == digest(raw)


@pytest.mark.parametrize(
    "mutation,code",
    [
        (
            lambda x: x["revisions"][0].update(content_hash="0" * 64),
            "invalid_saved_hash",
        ),
        (
            lambda x: x["revisions"][0].update(payload_schema_version="future.v99"),
            "unsupported_saved_schema",
        ),
        (
            lambda x: x["revisions"].append(dict(x["revisions"][0])),
            "duplicate_identity",
        ),
        (
            lambda x: x["branches"][0].update(forked_from_branch_id="missing"),
            "missing_owner",
        ),
        (
            lambda x: x["branches"][0].update(forked_from_branch_id="branch"),
            "branch_cycle",
        ),
        (
            lambda x: x["branches"][0].update(saved_head_revision_id="foreign"),
            "invalid_selection",
        ),
        (lambda x: x["omitted_branch_ids"].append("branch"), "invalid_manifest"),
    ],
)
def test_pure_graph_rejects_original_hash_identity_version_and_lineage(
    minimal, mutation, code
):
    mutation(minimal)
    with pytest.raises(ArchiveError) as error:
        Archive(pack(**minimal))
    assert error.value.code == code


def test_transport_rehash_cannot_repair_an_original_saved_hash(minimal):
    value = decode(minimal["revisions"][0]["payload_json"])
    value["run"]["display_name"] = "forged"
    minimal["revisions"][0]["payload_json"] = encode(value).decode()
    # pack regenerates ALL transport checksums, but retains the original Saved hash.
    with pytest.raises(ArchiveError, match="Original Saved hash failed"):
        Archive(pack(**minimal))


@pytest.mark.parametrize(
    "raw",
    [
        b'{"format":',
        b"NaN",
        b'{"format":"run_branch_archive.v1","format":"run_branch_archive.v1"}',
        b"null",
        b"[]",
    ],
)
def test_strict_json_does_not_accept_truncation_nonfinite_or_duplicate_keys(raw):
    with pytest.raises(ArchiveError):
        Archive(raw)


def test_part_integrity_and_closed_manifest(minimal):
    value = decode(pack(**minimal))
    value["parts"][0]["size"] += 1
    with pytest.raises(ArchiveError) as error:
        Archive(encode(value))
    assert error.value.code == "invalid_part_integrity"

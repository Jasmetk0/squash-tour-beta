"""The Save writer can reuse canonical component text without changing any hash.

The existing read path must keep its independent full-Saved-envelope verifier.
"""
from __future__ import annotations

import json
import random

import pytest
from sqlalchemy import text

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_revisions import (
    canonical_json,
    saved_revision_content_hash,
    _saved_revision_content_hash_from_new_canonical_parts,
)
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from tests.api.test_calendar_tour_flow import (
    command, execute, inspect, save_tour, setup, tour_url,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request


pytestmark = pytest.mark.pr_critical


def _metadata():
    return {
        "revision_id": "revision-\u00e9-mutation",
        "run_id": "run/🟢",
        "branch_id": 'branch"\n\t',
        "sequence": 812,
        "parent_revision_id": "source-17",
        "kind": "calendar_tour_authority",
        "payload_schema_version": "run_saved_revision.v3",
    }


@pytest.mark.parametrize(
    "payload,summary",
    [
        ({}, {}),
        (
            {"z": [None, True, False, -1, 0, 1.25],
             "a": {"unicode": "Žluťoučký 🟢 \\ \""},
             "content": {"clock": {"year": 2026, "week": 52}}},
            {"reason": "o'k", "newline": "a\nb"},
        ),
        (
            {"repeated": "výsledek" * 40000,
             "nested": [{"x": i, "a": [i, 1.0 / (i + 1)]}
                        for i in range(31)]},
            {"revision": [1, 2, 3]},
        ),
        (
            {"content": {"tour": {"rankings": [
                {"player": f"player-{i}", "points": 31 * i}
                for i in range(512)
            ]}}},
            {"kind": "test", "nested": {"ok": True}},
        ),
    ],
)
def test_reusing_new_canonical_parts_matches_full_envelope_exactly(payload, summary):
    metadata = _metadata()
    original = saved_revision_content_hash(
        **metadata, payload=payload, change_summary=summary,
    )
    encoded = _saved_revision_content_hash_from_new_canonical_parts(
        **metadata,
        payload_json=canonical_json(payload),
        change_summary_json=canonical_json(summary),
    )
    assert original == encoded and len(encoded) == 64

    changed = _saved_revision_content_hash_from_new_canonical_parts(
        **{**metadata, "parent_revision_id": "different-ancestor"},
        payload_json=canonical_json(payload),
        change_summary_json=canonical_json(summary),
    )
    assert changed != original
    assert _saved_revision_content_hash_from_new_canonical_parts(
        **metadata,
        payload_json=canonical_json(payload),
        change_summary_json=canonical_json({**summary, "tamper": True}),
    ) != original


def test_new_canonical_parts_match_many_reordered_and_escaped_inputs():
    rng = random.Random(170911)
    for index in range(64):
        pairs = [(f"k{rng.randrange(40)}-{i}", {
            "v": rng.choice([None, "\u00e9", "🌍", True, False, -3]),
            "n": rng.randint(-10000, 10000),
            "unicode": "\n\t\\\" é",
        }) for i in range(10)]
        rng.shuffle(pairs)
        payload = dict(pairs)
        summary = {"idx": index, "pairs": len(pairs)}
        metadata = {**_metadata(), "sequence": index + 1}
        assert saved_revision_content_hash(
            **metadata, payload=payload, change_summary=summary,
        ) == _saved_revision_content_hash_from_new_canonical_parts(
            **metadata,
            payload_json=canonical_json(payload),
            change_summary_json=canonical_json(summary),
        )


def test_real_tour_save_stays_physically_hash_valid_and_tamper_fails_closed(tmp_path):
    database = tmp_path / "canonical-save.db"
    with ApiServer(database_url=f"sqlite:///{database}") as server:
        repository, initial = setup(server, RunCalendar(5, 5, 2040, 2), count=4)
        before = inspect(server)
        assert before["saved"]
        execute(server, command(before, "transition", name="encoded-write-week3"))
        saved = save_tour(server)
        assert saved["revision_id"] != initial["revision_id"]
        assert inspect(server)["state"]["week"]["week"] == 3

        with repository._session_factory() as session:
            stored = session.get(BranchSavedRevisionModel, saved["revision_id"])
            original_json, saved_hash = stored.payload_json, stored.content_hash
            assert saved_hash == saved_revision_content_hash(
                revision_id=stored.revision_id,
                run_id=stored.run_id, branch_id=stored.branch_id,
                sequence=stored.sequence,
                parent_revision_id=stored.parent_revision_id,
                kind=stored.kind,
                payload_schema_version=stored.payload_schema_version,
                payload=json.loads(stored.payload_json),
                change_summary=json.loads(stored.change_summary_json),
            )
        with repository._engine.begin() as connection:
            connection.execute(text(
                "UPDATE branch_saved_revisions SET payload_json=:new "
                "WHERE revision_id=:revision"
            ), {
                "new": original_json.replace('"branch_id":"branch"', '"branch_id":"forged"', 1),
                "revision": saved["revision_id"],
            })
        assert _request("GET", tour_url(server))[0] == 409

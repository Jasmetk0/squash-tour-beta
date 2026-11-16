"""Regression gates for transaction-local, hash-verified Saved JSON reuse.

The production reader may receive a parsed payload only *after* the complete
immutable Saved envelope hash verifies, never from a cross-request cache.
The W52 native-v2 integration and physical tamper probes are measured on the
separate diagnostic PR #1808.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from beta_engine.application.run_calendar_read_authority import (
    resolve_saved_run_calendar,
)
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from tests.api.test_saved_revision_history_api import ApiServer, _create_run


@pytest.mark.pr_critical
def test_verified_saved_calendar_payload_is_hash_checked_and_request_local(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'verified-saved-calendar.db'}"
    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, revision_id = _create_run(
            server, display_name="Žluťoučký Run"
        )

    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            session.execute(text("BEGIN"))
            original = resolve_saved_run_calendar(
                session, run_id=run_id, branch_id=branch_id
            )
            verified = []
            captured_clock = resolve_saved_run_calendar(
                session, run_id=run_id, branch_id=branch_id,
                _verified_payload_out=verified,
            )
            assert captured_clock == original
            assert len(verified) == 1
            row = session.get(BranchSavedRevisionModel, revision_id)
            assert verified[0] == json.loads(row.payload_json)
            assert verified[0]["run"]["run_id"] == run_id

        # Direct physical-row tampering is not a legitimate Saved write. It
        # must fail the exact same content-hash validation before any payload
        # can be handed to the progress reader.
        with Session(engine) as session:
            with session.begin():
                row = session.get(BranchSavedRevisionModel, revision_id)
                modified = row.payload_json.replace(
                    '"display_name":', '"corrupted_display_name":', 1
                )
                assert modified != row.payload_json
                row.payload_json = modified

        with Session(engine) as session:
            session.execute(text("BEGIN"))
            verified_after_tamper = []
            with pytest.raises(ValueError, match="hash|Hash"):
                resolve_saved_run_calendar(
                    session, run_id=run_id, branch_id=branch_id,
                    _verified_payload_out=verified_after_tamper,
                )
            assert verified_after_tamper == []
    finally:
        engine.dispose()

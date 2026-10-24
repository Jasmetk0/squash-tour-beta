"""Negative-only mutations of isolated backups of a genuinely produced fixture."""

import json
import sqlite3
from copy import deepcopy

import pytest

from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.run_revisions import saved_revision_content_hash
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from tests.api.test_saved_revision_history_api import ApiServer


def reject_rehashed_terminal_history(database, closed, directory):
    """No positive sporting state is constructed or inserted by this helper."""
    marker = closed.payload['run']['native_branch_closures'][closed.branch_id]
    source_id = marker['source_revision_id']
    for field, value in (
        ('branch_id', 'foreign-branch'),
        ('played_saved_head', 'missing-physical-origin'),
        ('closing_eligibility_ordinal', marker['closing_ranking']['eligibility_boundary_ordinal'] - 1),
        ('main_points', 999999),
    ):
        clone = directory / f'forged-{field}.sqlite'
        with sqlite3.connect(database) as original, sqlite3.connect(clone) as target:
            original.backup(target)
        with ApiServer(database_url=f'sqlite:///{clone}') as isolated:
            repository = isolated.app.state.runtime.repository
            with repository._session_factory.begin() as session:
                row = session.get(BranchSavedRevisionModel, source_id)
                body = json.loads(row.payload_json)
                component = body['content']['calendar_tour_authority']
                state = component['state']
                receipt = next(r for r in state['receipts'] if r['request']['command']['action'] == 'confirm-result')
                receipt['result']['results'][0][field] = value
                # Rehash every modified enclosing stored layer. Validation must
                # still rebuild the actual Edition rather than trust these bytes.
                component['fingerprint'] = canonical_hash(state)
                row.payload_json = json.dumps(body)
                row.content_hash = saved_revision_content_hash(
                    revision_id=row.revision_id, run_id=row.run_id, branch_id=row.branch_id,
                    sequence=row.sequence, parent_revision_id=row.parent_revision_id,
                    kind=row.kind, payload_schema_version=row.payload_schema_version,
                    payload=body, change_summary=json.loads(row.change_summary_json))
            with pytest.raises((ValueError, TypeError)):
                repository.get_branch_saved_revision(revision_id=source_id)
        clone.unlink()
    # Keep the result unchanged but rehash a false horizon in its actual
    # physical pre-play source. Own-result hashing cannot detect this dependency.
    clone = directory / 'forged-physical-played-calendar.sqlite'
    with sqlite3.connect(database) as original, sqlite3.connect(clone) as target:
        original.backup(target)
    with ApiServer(database_url=f'sqlite:///{clone}') as isolated:
        repository = isolated.app.state.runtime.repository
        with repository._session_factory.begin() as session:
            saved = session.get(BranchSavedRevisionModel, source_id)
            result_body = json.loads(saved.payload_json)
            tour = result_body['content']['calendar_tour_authority']['state']
            played_id = next(a['played_saved_head'] for a in tour['editions'] if a['result_confirmed'])
            row = session.get(BranchSavedRevisionModel, played_id)
            body = json.loads(row.payload_json)
            body['run']['run_calendar']['season_count'] += 1
            row.payload_json = json.dumps(body)
            row.content_hash = saved_revision_content_hash(
                revision_id=row.revision_id, run_id=row.run_id, branch_id=row.branch_id,
                sequence=row.sequence, parent_revision_id=row.parent_revision_id,
                kind=row.kind, payload_schema_version=row.payload_schema_version,
                payload=body, change_summary=json.loads(row.change_summary_json))
        with pytest.raises(ValueError):
            repository.get_branch_saved_revision(revision_id=source_id)
    clone.unlink()
    # A plausible, internally rehashed final summary also needs actual ancestry.
    clone = directory / 'forged-closing-summary.sqlite'
    with sqlite3.connect(database) as original, sqlite3.connect(clone) as target:
        original.backup(target)
    with ApiServer(database_url=f'sqlite:///{clone}') as isolated:
        repository = isolated.app.state.runtime.repository
        with repository._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, closed.revision_id)
            body = deepcopy(closed.payload)
            marker = body['run']['native_branch_closures'][closed.branch_id]
            marker['season_summary']['awarded_points'] += 1
            marker['season_summary_fingerprint'] = canonical_hash(marker['season_summary'])
            marker['fingerprint'] = canonical_hash({k:v for k,v in marker.items() if k!='fingerprint'})
            row.payload_json = json.dumps(body)
            row.content_hash = saved_revision_content_hash(
                revision_id=row.revision_id, run_id=row.run_id, branch_id=row.branch_id,
                sequence=row.sequence, parent_revision_id=row.parent_revision_id,
                kind=row.kind, payload_schema_version=row.payload_schema_version,
                payload=body, change_summary=json.loads(row.change_summary_json))
        with pytest.raises(ValueError, match='closure|Closing|Saved|saved|facts'):
            repository.get_branch_saved_revision(revision_id=closed.revision_id)
    clone.unlink()

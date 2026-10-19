"""Native Save publishes exact metadata proofs only after successful commit."""

import pytest
from sqlalchemy import event

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel, RunBranchModel
from tests.api.test_calendar_tour_flow import (
    ApiServer, setup, inspect, execute, command, tour_url,
)
from tests.api.test_saved_revision_history_api import _request

pytestmark = pytest.mark.pr_critical


def test_native_save_reuses_verified_bytes_only_after_commit(tmp_path, monkeypatch):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'save-proof.db'}") as server:
        setup(server, RunCalendar(52, 35, 2030, 3))
        view = inspect(server)
        execute(server, command(view, 'policy', name='future-policy', data={
            'effective_week': {**view['state']['week'], 'week': 5},
            'ranking': {'policy_id': 'reviewed-future', 'best_n': 1},
        }))
        view = inspect(server)
        repository = server.app.state.runtime.repository
        before = set(repository._revision_validation_cache)
        from beta_engine.infrastructure.db import calendar_tour
        original = calendar_tour.saved_tour
        folds = []

        def counted(payload, **scope):
            component = payload.get('content', {}).get('calendar_tour_authority')
            if component and component['fingerprint'] == view['tour_fingerprint']:
                folds.append(1)
            return original(payload, **scope)

        monkeypatch.setattr(calendar_tour, 'saved_tour', counted)
        body = {'expected_draft_version': view['draft_version'],
                'expected_calendar_tour_fingerprint': view['tour_fingerprint']}

        def fail_commit(session):
            if session.bind is not repository._engine:
                return
            branch = session.get(RunBranchModel, 'branch')
            if branch and branch.saved_head_revision_id != view['saved_head_revision_id']:
                assert set(repository._revision_validation_cache) == before
                raise ValueError('Controlled commit failure after Saved validation')

        event.listen(repository._session_factory.class_, 'before_commit', fail_commit)
        try:
            code, failed = _request('POST', tour_url(server) + '/save', body)
            assert code == 409, failed
        finally:
            event.remove(repository._session_factory.class_, 'before_commit', fail_commit)
        assert set(repository._revision_validation_cache) == before
        assert inspect(server)['saved_head_revision_id'] == view['saved_head_revision_id']
        assert folds == [1]
        code, saved = _request('POST', tour_url(server) + '/save', body)
        assert code == 201, saved
        # The successful retry verifies its captured source once. Reloading the
        # committed draft must hash/read it independently without folding again.
        assert folds == [1, 1]
        new_head = saved['saved_revision']['revision_id']
        proofs = repository._revision_validation_cache
        assert any(key[0] == new_head for key in proofs)
        assert all(not proof.payload for proof in proofs.values())
        assert inspect(server)['saved']
        # After a real transition, the unsaved live owner differs from Saved.
        # Its already authenticated predecessor must anchor suffix validation
        # instead of replaying all older matches again on every Admin read.
        from beta_engine.infrastructure.db import calendar_sporting_checkpoint
        original_verify = calendar_sporting_checkpoint.verify_checkpoint
        prefixes = []

        def verify_live(state, world, evidence, **kwargs):
            if state is not None and state.week.week == 3:
                prefixes.append(kwargs.get('_verified_saved_prefix'))
            return original_verify(state, world, evidence, **kwargs)

        monkeypatch.setattr(calendar_sporting_checkpoint, 'verify_checkpoint', verify_live)
        execute(server, command(inspect(server), 'transition', name='live-week3'))
        assert not inspect(server)['saved']
        assert prefixes and all(prefix is not None and prefix.week.week == 2
                                for prefix in prefixes)
        # A rehashed forged successor still fails against the authenticated
        # prefix and the independently replayed real weekly suffix.
        import json
        from beta_engine.domain.run_packages import canonical_hash
        from beta_engine.infrastructure.db.models import CalendarPlayerSportingCheckpointModel
        with repository._session_factory.begin() as session:
            row = session.get(CalendarPlayerSportingCheckpointModel, ('run', 'branch'))
            original_row = row.payload_json, row.fingerprint
            raw = json.loads(row.payload_json)
            raw['players'][0]['current_form'] += 1
            row.payload_json, row.fingerprint = json.dumps(raw), canonical_hash(raw)
        assert _request('GET', tour_url(server))[0] == 409
        with repository._session_factory.begin() as session:
            row = session.get(CalendarPlayerSportingCheckpointModel, ('run', 'branch'))
            row.payload_json, row.fingerprint = original_row
        # Even a freshly published proof cannot authenticate changed SQL bytes.
        with repository._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, new_head)
            row.payload_json = row.payload_json.replace('reviewed-future', 'forged-future')
        assert _request('GET', tour_url(server))[0] == 409

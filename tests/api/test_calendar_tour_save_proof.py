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
        # Even a freshly published proof cannot authenticate changed SQL bytes.
        with repository._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, new_head)
            row.payload_json = row.payload_json.replace('reviewed-future', 'forged-future')
        assert _request('GET', tour_url(server))[0] == 409

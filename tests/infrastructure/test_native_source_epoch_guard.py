"""Real SQL guard component; pure lifecycle fixtures do not certify a full Tour."""

import pytest

from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import PlayerLifecycleWeekStateModel
from beta_engine.infrastructure.db.player_lifecycle_state import put_lifecycle
from beta_engine.infrastructure.db.run_prospect_source_state import (
    native_birth_requires_source_epochs,
)
from tests.domain.test_calendar_native_sporting_checkpoint import prepared

pytestmark = pytest.mark.pr_critical


def test_run_shared_epoch_guard_detects_any_branch_and_rejects_corrupt_native_row(
    tmp_path,
):
    _, context = prepared()
    first, born = context["lifecycle"]
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'epoch-guard.db'}")
    )
    PlayerLifecycleWeekStateModel.__table__.create(engine)
    sessions = create_session_factory(engine)
    try:
        with sessions.begin() as session:
            put_lifecycle(session, first)
            put_lifecycle(
                session, first.model_copy(update={"branch_id": "alternative"})
            )
            assert not native_birth_requires_source_epochs(session, run_id=first.run_id)
            put_lifecycle(session, born)
            # There is no Branch filter: another Branch cannot invalidate this
            # activated birthday's Run-shared source snapshot.
            assert native_birth_requires_source_epochs(session, run_id=first.run_id)
            assert not native_birth_requires_source_epochs(session, run_id="foreign")
        with sessions.begin() as session:
            row = session.get(
                PlayerLifecycleWeekStateModel,
                (born.run_id, born.branch_id, born.week.ordinal),
            )
            row.fingerprint = "0" * 64
        with (
            sessions() as session,
            pytest.raises(ValueError, match="identity|fingerprint|hash"),
        ):
            native_birth_requires_source_epochs(session, run_id=first.run_id)
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "raw",
    [
        '{"schema_version":"player_lifecycle_calendar_state.v4","players":[{"schema_version":"fake"}]}',
        '{"players":[{"schema_version":"player_lifecycle_calendar_state.v4"}]}',
        '{"schema_version":"incorrect","schema_version":"player_lifecycle_calendar_state.v4"}',
        '{"schema_version":"player_lifecycle_calendar_state.v4","schema_version":"incorrect"}',
        '{"schema_version":"player_lifecycle_calendar_state.v\\u0034"}',
        '{"schema_version":null,"players":[]}',
        '{"schema_version":17}',
        '{"schema_version":{"nested":"v4"}}',
        '{"schema_version":"player_lifecycle_calendar_state.v3","blob":"' + 'p'*120000 + '"}',
    ],
)
def test_lifecycle_schema_projection_agrees_with_json_decoder(raw):
    import json

    from beta_engine.infrastructure.db.player_lifecycle_state import (
        lifecycle_schema_version,
    )

    assert lifecycle_schema_version(raw) == json.loads(raw).get("schema_version")


def test_lifecycle_schema_projection_still_validates_entire_native_body():
    from beta_engine.infrastructure.db.player_lifecycle_state import (
        _parse_lifecycle_json,
        lifecycle_schema_version,
    )

    _, context = prepared()
    first, born = context["lifecycle"]
    for model in (first, born):
        raw = model.model_dump_json()
        assert lifecycle_schema_version(raw) == model.schema_version
        assert _parse_lifecycle_json(raw) == model

    # A correct routing field is not a permission to ignore malformed content.
    with pytest.raises(ValueError):
        _parse_lifecycle_json(
            '{"schema_version":"player_lifecycle_calendar_state.v4","players":[{"player_id":"broken"}]}'
        )


def test_lifecycle_schema_projection_preserves_invalid_json_failure():
    import json

    from beta_engine.infrastructure.db.player_lifecycle_state import (
        lifecycle_schema_version,
    )

    for raw in ("{missing", "null", "[]", "[1, 2]", '"not an object"'):
        with pytest.raises((TypeError, ValueError, AttributeError)):
            lifecycle_schema_version(raw)

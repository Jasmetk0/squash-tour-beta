"""Schema projections only select the original complete JSON validators.

These tests are not hash/provenance proofs: production Saved checks still run.
"""
import json

import pytest

from beta_engine.domain.json_schema_routing import schema_version_for_json
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.player_health_state import _parse_health_json
from tests.domain.test_calendar_health import state as health_state


pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("raw", [
    '{"schema_version":"calendar_tour_authority.v5","state":[1,2,3]}',
    '{"inner":{"schema_version":"calendar_tour_authority.v5"}}',
    '{"schema_version":"calendar_tour_authority.v5","schema_version":"wrong"}',
    '{"schema_version":"wrong","schema_version":"calendar_tour_authority.v5"}',
    '{"schema_version":"calendar_tour_authority.v\\u0035"}',
    '{"schema_version":null}',
    '{"schema_version":17,"players":[]}',
    '{"schema_version":{"arbitrary":true}}',
    '{"schema_version":"player_health_calendar_state.v3","long":"' + 'x'*120000 + '"}',
])
def test_projection_has_the_same_version_as_python_json_decoder(raw):
    assert schema_version_for_json(raw) == json.loads(raw).get("schema_version")


def test_real_health_model_remains_equal_after_version_projection():
    health = health_state(RunCalendar(52, 35, 2030, 3))
    raw = health.model_dump_json()
    assert schema_version_for_json(raw) == health.schema_version
    assert _parse_health_json(raw) == health
    invalid = json.loads(raw)
    invalid["players"] = [{"player_id": "unknown", "invalid": True}]
    with pytest.raises(ValueError):
        _parse_health_json(json.dumps(invalid))


def test_tour_parser_still_calls_original_complete_validator(monkeypatch):
    from beta_engine.domain.tournaments.calendar_tour import (
        CalendarTourState, parse_tour_json,
    )
    from beta_engine.domain.tournaments.calendar_native_tour import (
        CalendarNativeTourState, CalendarNativeCompetitionTourState,
    )
    from beta_engine.domain.tournaments.calendar_global_slots import GlobalTourState

    models = {
        "calendar_tour_authority.v5": GlobalTourState,
        "calendar_tour_authority.v4": CalendarNativeCompetitionTourState,
        "calendar_tour_authority.v3": CalendarNativeTourState,
        "legacy": CalendarTourState,
    }
    called = []
    for name, model in models.items():
        def validate(cls, raw, *, selected=name):
            called.append((selected, raw))
            return selected
        monkeypatch.setattr(model, "model_validate_json", classmethod(validate))

    for version, expected in [
        ("calendar_tour_authority.v5", "calendar_tour_authority.v5"),
        ("calendar_tour_authority.v4", "calendar_tour_authority.v4"),
        ("calendar_tour_authority.v3", "calendar_tour_authority.v3"),
        ("legacy", "legacy"),
    ]:
        raw = json.dumps({"schema_version": version, "editions": [{"id": "x"}]})
        assert parse_tour_json(raw) == expected
        assert called.pop() == (expected, raw)


def test_invalid_nonobject_root_still_reaches_original_strict_validator():
    from beta_engine.domain.tournaments.calendar_tour import parse_tour_json

    for raw in ("null", "[]", '"string"', "123"):
        assert schema_version_for_json(raw) is None
        with pytest.raises(ValueError):
            _parse_health_json(raw)
        with pytest.raises(ValueError):
            parse_tour_json(raw)
    with pytest.raises(ValueError):
        schema_version_for_json("{not JSON")

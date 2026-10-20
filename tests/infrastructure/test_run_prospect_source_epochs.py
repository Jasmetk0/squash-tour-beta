"""Component tests for strict v2 source-epoch parsing; not HTTP acceptance."""
from copy import deepcopy

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.run_prospect_source_state import (
    RUN_PROSPECT_EPOCH_SCHEMA,
    RUN_PROSPECT_SOURCE_COMPONENT_KEY,
    RUN_PROSPECT_SOURCE_SCHEMA,
    RunProspectSourceEpochs,
    RunProspectSourceSnapshot,
    _epoch_component,
    _fingerprint,
    _snapshot_component,
    load_saved_run_prospect_source,
)

pytestmark = pytest.mark.pr_critical


def _row(clock, season, week, identity):
    position = clock.season_to_calendar(season, week)
    return {
        "prospect_id": identity,
        "birth_year": position.calendar_year - 15,
        "birth_year_week": position.year_week,
        "season_start_year": clock.start_year + season,
        "season_week": week,
        "calendar_year": position.calendar_year,
        "year_week": position.year_week,
        "age": 15,
    }


def _snapshot(*rows):
    rows = tuple(sorted(rows, key=lambda r: r["prospect_id"]))
    return RunProspectSourceSnapshot(
        schema_version=RUN_PROSPECT_SOURCE_SCHEMA,
        run_id="run",
        records=rows,
        fingerprint=_fingerprint(run_id="run", records=rows),
    )


@pytest.mark.parametrize("clock", [RunCalendar.earth_default(
    start_year=2030, season_count=3
), RunCalendar.fax_default(start_year=2030, season_count=3)])
def test_historical_v1_source_remains_exactly_effective_before_v2_append(clock):
    first = _snapshot(_row(clock, 0, 2, "athlete-a"))
    second = _snapshot(
        _row(clock, 0, 2, "athlete-a"),
        _row(clock, 1, 4, "athlete-b"),
    )
    activation = 8
    raw = _epoch_component(((0, first), (activation, second)), "run")
    assert raw["schema_version"] == RUN_PROSPECT_EPOCH_SCHEMA
    payload = {
        "run": {"run_calendar": clock.to_metadata()},
        "content": {RUN_PROSPECT_SOURCE_COMPONENT_KEY: raw},
    }
    source = load_saved_run_prospect_source(payload, run_id="run")
    assert isinstance(source, RunProspectSourceEpochs)
    assert source.for_week(0).fingerprint == first.fingerprint
    assert source.for_week(activation - 1).fingerprint == first.fingerprint
    assert source.for_week(activation).fingerprint == second.fingerprint
    assert source.for_week(clock.weeks_per_year + 3).fingerprint == second.fingerprint
    assert source.records == second.records
    assert source.fingerprint == raw["fingerprint"]
    assert load_saved_run_prospect_source({
        "content": {RUN_PROSPECT_SOURCE_COMPONENT_KEY: _snapshot_component(first)}
    }, run_id="run") == first

    tampered = deepcopy(payload)
    tampered["content"][RUN_PROSPECT_SOURCE_COMPONENT_KEY]["epochs"][0]["source"]["records"][0]["age"] = 16
    with pytest.raises(ValueError, match="fingerprint"):
        load_saved_run_prospect_source(tampered, run_id="run")

    tampered = deepcopy(payload)
    tampered["content"][RUN_PROSPECT_SOURCE_COMPONENT_KEY]["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="fingerprint"):
        load_saved_run_prospect_source(tampered, run_id="run")

    tampered = deepcopy(payload)
    tampered["content"][RUN_PROSPECT_SOURCE_COMPONENT_KEY]["epochs"][1]["effective_from_ordinal"] = 0
    with pytest.raises(ValueError, match="chronological"):
        load_saved_run_prospect_source(tampered, run_id="run")

    with pytest.raises(ValueError, match="foreign Run"):
        load_saved_run_prospect_source(payload, run_id="other")


@pytest.mark.parametrize("width,offset", [(52, 1), (61, 37)])
def test_v2_rejects_retroactive_and_rewritten_or_deleted_source_even_if_rehashed(width, offset):
    clock = RunCalendar(width, offset, 2030, 3)
    first = _snapshot(_row(clock, 0, 2, "athlete-a"))
    too_early = _snapshot(
        _row(clock, 0, 2, "athlete-a"),
        _row(clock, 0, 3, "athlete-b"),
    )
    def load(added):
        return load_saved_run_prospect_source({
            "run": {"run_calendar": clock.to_metadata()},
            "content": {
                RUN_PROSPECT_SOURCE_COMPONENT_KEY: _epoch_component(
                    ((0, first), (8, added)), "run"
                )
            },
        }, run_id="run")
    with pytest.raises(ValueError, match="completed weeks"):
        load(too_early)
    with pytest.raises(ValueError, match="edited or deleted"):
        load(_snapshot(_row(clock, 1, 4, "athlete-b")))
    changed_old = _snapshot(
        _row(clock, 0, 3, "athlete-a"),
        _row(clock, 1, 4, "athlete-b"),
    )
    with pytest.raises(ValueError, match="edited or deleted"):
        load(changed_old)

"""Run W/O-aware 15th-birthday preflight; pure replay against Saved source bytes."""
from dataclasses import dataclass

import pytest

from beta_engine.application.calendar_native_prospect_intake import (
    preview_native_prospect_intake,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.prospect_sporting_profile import (
    materialize_prospect_sporting_profile,
)

pytestmark = pytest.mark.pr_critical


@dataclass(frozen=True)
class SignedSource:
    records: tuple[dict, ...]
    fingerprint: str = "f" * 64


def source_at(clock, target, *, pid="prospect-1", prepared=True, **overrides):
    actual = target.calendar_position
    row = dict(
        prospect_id=pid, display_name="New Athlete",
        country_code="CZE", status="prospect",
        birth_year=actual.calendar_year - 15,
        birth_year_week=actual.year_week,
        calendar_year=actual.calendar_year,
        year_week=actual.year_week, age=15,
        season_start_year=clock.start_year + target.season_index,
        season_week=target.week,
        profile={}, development={}, potential={},
    )
    if prepared:
        p = materialize_prospect_sporting_profile(
            player_id=pid, profile_seed="profile",
            development_seed="development", potential_seed="potential",
        )
        row["profile"] = {
            "canonical_sporting_profile": p.model_dump(mode="json"),
            "canonical_sporting_profile_fingerprint": p.fingerprint,
        }
        row["development"] = {
            "sporting_profile_fingerprint": p.fingerprint,
            "development_timing": p.development_timing,
            "source_development_seed_digest": p.source_development_seed_digest,
        }
        row["potential"] = {
            "sporting_profile_fingerprint": p.fingerprint,
            "potential_ovr": p.potential_ovr,
            "potential_identity": p.potential_identity,
            "potential_provenance": p.potential_provenance,
            "source_potential_seed_digest": p.source_potential_seed_digest,
        }
    return row | overrides


def preflight(clock, current, source):
    return preview_native_prospect_intake(
        current=current, run_id="run", branch_id="branch",
        saved_head_revision_id="saved-head", checkpoint_fingerprint="c" * 64,
        source=source, initial_player_ids={"initial-player"},
        current_player_ids={"initial-player"},
    )


@pytest.mark.parametrize("w,offset,week", [
    (52, 1, 52), (52, 35, 52), (61, 37, 61), (80, 15, 80),
    (52, 1, 1), (61, 37, 30),
])
def test_exact_native_calendar_15th_birthday_across_seasons(w, offset, week):
    clock = RunCalendar(w, offset, 2030, 3)
    current = RunWeekPosition(calendar=clock, season_index=0, week=week)
    target = clock.position_at_ordinal(current.ordinal + 1)
    next_week = RunWeekPosition(
        calendar=clock, season_index=target.season_index,
        week=target.season_week,
    )
    due = source_at(clock, next_week)
    out = preflight(clock, current, SignedSource((due,)))
    assert out["due_count"] == 1
    assert out["due"][0]["player_id"] == "prospect-1"
    assert out["target_week"]["week"] == target.season_week
    assert out["target_week"]["season_index"] == target.season_index
    assert out["native_activation_supported"] is False
    assert out["blocked"] is True
    assert out == preflight(clock, current, SignedSource((due,)))


def test_past_and_future_birthdays_are_not_preemptively_activated():
    clock = RunCalendar(52, 35, 2030, 3)
    current = RunWeekPosition(calendar=clock, season_index=0, week=3)
    earlier = RunWeekPosition(calendar=clock, season_index=0, week=2)
    future = RunWeekPosition(calendar=clock, season_index=0, week=5)
    source = SignedSource((
        source_at(clock, earlier, pid="earlier"),
        source_at(clock, future, pid="future"),
    ))
    out = preflight(clock, current, source)
    assert out["due"] == []
    assert out["problems"] == []
    assert out["blocked"] is True


@pytest.mark.parametrize("damage,code", [
    ({"season_week": 4}, "source_calendar_disagreement"),
    ({"year_week": 1}, "source_calendar_disagreement"),
    ({"birth_year_week": 53}, "invalid_run_birth_week"),
    ({"age": 16}, "source_calendar_disagreement"),
    ({"country_code": "XX"}, "country_identity_invalid"),
    ({"status": "retired"}, "unsupported_lifecycle_status"),
])
def test_incompatible_birth_or_source_fails_closed(damage, code):
    clock = RunCalendar(52, 35, 2030, 3)
    start = RunWeekPosition(calendar=clock, season_index=0, week=1)
    target = RunWeekPosition(calendar=clock, season_index=0, week=2)
    row = source_at(clock, target, **damage)
    result = preflight(clock, start, SignedSource((row,)))
    assert result["due_count"] == 0
    assert result["problems"] == [{"prospect_id": "prospect-1", "code": code}]


def test_missing_and_foreign_sporting_profile_cannot_be_inferred():
    clock = RunCalendar(80, 15, 2030, 2)
    start = RunWeekPosition(calendar=clock, season_index=0, week=1)
    target = RunWeekPosition(calendar=clock, season_index=0, week=2)
    missing = source_at(clock, target, prepared=False)
    foreign = source_at(clock, target, pid="prospect-2")
    foreign["profile"]["canonical_sporting_profile"]["player_id"] = "other"
    for row in (missing, foreign):
        result = preflight(clock, start, SignedSource((row,)))
        assert result["due_count"] == 0
        assert result["problems"][0]["code"] == "prospect_sporting_profile_unready"


def test_empty_snapshot_and_horizon_protection():
    clock = RunCalendar(52, 1, 2000, 1)
    start = RunWeekPosition(calendar=clock, season_index=0, week=1)
    result = preflight(clock, start, None)
    assert result["due_count"] == 0 and result["blocked"] is False
    assert result["source_fingerprint"] is None
    last = RunWeekPosition(calendar=clock, season_index=0, week=52)
    with pytest.raises(ValueError, match="beyond the Run horizon"):
        preflight(clock, last, None)

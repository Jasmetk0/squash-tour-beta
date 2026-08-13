from __future__ import annotations

import json

import pytest

from beta_engine.application.season_category_points_service import SeasonCategoryPointsService
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.tournaments import SeasonCalendarBuildRequest
from beta_engine.infrastructure.points_config import normalize_ranking_points_table


def service(tmp_path):
    return SeasonCategoryPointsService(
        template_service=TournamentTemplatesConfigService(),
        registry_path=tmp_path / "category_points.json",
    )


def test_validation_preserves_zero_missing_and_normalizes_legacy_keys():
    assert normalize_ranking_points_table({"winner": 0, "semifinalist": 4}) == {"champion": 0, "semifinal": 4}
    assert "finalist" not in normalize_ranking_points_table({"winner": 0})
    for invalid in (True, -1, 1.5, "2"):
        with pytest.raises(ValueError):
            normalize_ranking_points_table({"winner": invalid})
    with pytest.raises(ValueError, match="unknown ranking point stage"):
        normalize_ranking_points_table({"champoin": 1})
    with pytest.raises(ValueError, match="authored more than once"):
        normalize_ranking_points_table({"winner": 1, "champion": 2})


def test_first_season_baseline_and_copy_semantics(tmp_path):
    subject = service(tmp_path)
    first = subject.initialize("2000/01")
    platinum = next(row for row in first.categories if row.category == "PLATINUM")
    assert platinum.provenance == "seeded_from_baseline"
    assert platinum.ranking_points_table["champion"] == 2500
    assert "winner" not in platinum.ranking_points_table
    assert not any(key.startswith("qualification") for key in platinum.ranking_points_table)

    second = subject.initialize("2001/02")
    copied = next(row for row in second.categories if row.category == "PLATINUM")
    assert copied.ranking_points_table == platinum.ranking_points_table
    assert copied.provenance == "prefilled_from_previous_season"
    assert copied.source_season == "2000/01"
    subject.update("2001/02", "PLATINUM", {"champion": 1200, "finalist": 0})
    assert subject.resolve_table("2000/01", "PLATINUM")["champion"] == 2500
    subject.update("2000/01", "PLATINUM", {"champion": 999})
    assert subject.resolve_table("2001/02", "PLATINUM") == {"champion": 1200, "finalist": 0}
    assert subject.initialize("2001/02").categories == subject.get("2001/02").categories


def test_initialization_validates_before_atomic_write(tmp_path):
    baseline = tmp_path / "bad.json"
    baseline.write_text(json.dumps({"point_distributions": {"world_tour_platinum": {"winner": True}}}))
    subject = SeasonCategoryPointsService(TournamentTemplatesConfigService(), tmp_path / "registry.json", baseline)
    with pytest.raises(ValueError):
        subject.initialize("2000/01")
    assert not subject.registry_path.exists()


def test_editions_snapshot_target_season_not_previous_edition(tmp_path):
    points = service(tmp_path)
    points.initialize("2000/01")
    points.initialize("2001/02")
    category = sorted(row.category for row in points.get("2000/01").categories)[0]
    points.update("2001/02", category, {"champion": 1200, "finalist": 750})
    calendars = SeasonCalendarService(TournamentTemplatesConfigService(), tmp_path / "calendars.json", points)
    request = SeasonCalendarBuildRequest(seed=1, dry_run=False, max_events=1)
    old = calendars.build_calendar(season="2000/01", request=request).calendar.events[0]
    new = calendars.build_calendar(season="2001/02", request=request).calendar.events[0]
    assert old.ranking_points_table["champion"] == points.resolve_table("2000/01", category)["champion"]
    assert new.ranking_points_table == {"champion": 1200, "finalist": 750}
    points.update("2001/02", category, {"champion": 1300})
    assert calendars.get_calendar(season="2001/02").calendar.events[0].ranking_points_table == {"champion": 1200, "finalist": 750}
    after = calendars.build_calendar(season="2001/02", request=request.model_copy(update={"overwrite_existing": True})).calendar.events[0]
    assert after.ranking_points_table == {"champion": 1300}
    assert not after.points_table_complete


def test_dry_run_uses_initialization_candidate_without_mutation(tmp_path):
    points = service(tmp_path)
    calendar_path = tmp_path / "calendars.json"
    calendars = SeasonCalendarService(TournamentTemplatesConfigService(), calendar_path, points)
    result = calendars.build_calendar(season="2000/01", request=SeasonCalendarBuildRequest(seed=1, dry_run=True, max_events=1))
    event = result.calendar.events[0]
    candidate = points.preview_initialization("2000/01")
    expected = next(row.ranking_points_table for row in candidate.categories if row.category == event.category)
    assert event.ranking_points_table == expected
    assert not points.registry_path.exists()
    assert not calendar_path.exists()


def test_persisted_build_initializes_authority_and_ignores_changed_baseline(tmp_path):
    points = service(tmp_path)
    calendars = SeasonCalendarService(TournamentTemplatesConfigService(), tmp_path / "calendars.json", points)
    request = SeasonCalendarBuildRequest(seed=1, dry_run=False, max_events=1)
    edition = calendars.build_calendar(season="2000/01", request=request).calendar.events[0]
    assert points.get("2000/01").initialized
    baseline = json.loads(points.baseline_points_path.read_text(encoding="utf-8"))
    # A disposable baseline proves it is initialization-only without mutating the shared source.
    changed = tmp_path / "changed_points.json"
    distribution = next(iter(baseline["point_distributions"].values()))
    distribution["winner"] = 999999
    changed.write_text(json.dumps(baseline), encoding="utf-8")
    points.baseline_points_path = changed
    rebuilt = calendars.build_calendar(season="2000/01", request=request.model_copy(update={"overwrite_existing": True})).calendar.events[0]
    assert rebuilt.ranking_points_table == edition.ranking_points_table


def test_legacy_persisted_edition_loads_without_rewrite(tmp_path):
    calendars = SeasonCalendarService(TournamentTemplatesConfigService(), tmp_path / "calendars.json")
    request = SeasonCalendarBuildRequest(seed=1, dry_run=False, max_events=1)
    calendars.build_calendar(season="2000/01", request=request)
    payload = json.loads(calendars.calendar_registry_path.read_text(encoding="utf-8"))
    event = payload["calendars_by_season"]["2000/01"]["events"][0]
    for field in ("ranking_status", "ranking_points_table", "ranking_configuration_legacy"):
        event.pop(field)
    calendars.calendar_registry_path.write_text(json.dumps(payload), encoding="utf-8")
    before = calendars.calendar_registry_path.read_bytes()
    loaded = calendars.get_calendar(season="2000/01")
    assert loaded.calendar.events[0].ranking_configuration_legacy is True
    assert calendars.calendar_registry_path.read_bytes() == before

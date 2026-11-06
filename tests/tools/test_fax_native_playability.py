"""Actual copied-FAX 80-Edition operability gaps, without writing sport data.

This is deliberately an adapter gap audit, not proof of 80 completed Editions.
"""
from collections import Counter
import json
from pathlib import Path

import pytest

from beta_engine.application.pre_alpha_fax_acceptance_calendar_source import (
    PreAlphaFaxAcceptanceCalendarSource,
)
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_category_points_service import SeasonCategoryPointsService
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.calendar.run_calendar import RunCalendar
from tools.audit_fax_native_playability import (
    SCHEMA, audit, build_current_source_report, classify_event, main,
)

pytestmark = pytest.mark.smoke


def _source(*, registry: Path):
    templates = TournamentTemplatesConfigService(
        config_path=Path("config/tournament_templates/mvp_templates.json")
    )
    return PreAlphaFaxAcceptanceCalendarSource(
        template_service=templates,
        calendar_validation_service=SeasonCalendarService(
            template_service=templates,
            category_points_service=SeasonCategoryPointsService(
                templates, registry_path=registry
            ),
        ),
    )


def _supported_fixture(original):
    # A purposely synthetic comparison that preserves unique source identity
    # but changes field geometry in the test ONLY. Never export as a FAX fix.
    return original.model_copy(update={
        "main_draw_size": 4,
        "qualification_draw_size": 0,
        "qualifier_spots": 0,
        "wild_cards": 0,
        "byes": 0,
        "duration_in_season_weeks": 1,
        "season_week": 10,
        "start_season_week": 10,
        "end_season_week": 10,
        "ranking_points_table": {
            "champion": 100, "finalist": 60, "semifinal": 30,
        },
    })


@pytest.mark.pr_critical
def test_actual_80_fax_calendar_gap_classifies_every_original_edition_with_exact_source_hash(tmp_path):
    registry = tmp_path / "no-authorized-points-registry.json"
    report = build_current_source_report(category_registry_path=registry)
    repeat = build_current_source_report(category_registry_path=registry)
    assert report == repeat
    assert report["schema_version"] == SCHEMA
    assert report["source_edition_count"] == 80
    assert report["structurally_blocked_edition_count"] > 0
    assert report["actually_played_edition_count_proven"] == 0
    assert report["playability_certified"] is False
    assert len(report["source_calendar_fingerprint"]) == 64
    assert not registry.exists(), "The default scan must not create category-point authority"
    rows = report["editions"]
    assert len({item["event_id"] for item in rows}) == 80
    assert rows == sorted(rows, key=lambda item: (
        item["source_season_week"], item["event_id"]
    ))
    assert sorted(item["event_id"] for item in rows) == [
        f"FAX-ACCEPT-WT-{index:03d}" for index in range(1, 81)
    ]
    # Do not casually collapse Platinum-32/Gold-24 with Q into supported 4/8.
    assert any(item["source_main_draw_size"] > 8 for item in rows)
    assert any(item["source_qualification_draw_size"] > 0 for item in rows)
    assert report["blocker_counts"]["main_field_not_supported_by_native_v2_executor"] > 0
    assert report["blocker_counts"]["qualification_structure_not_modelled_by_native_v2"] > 0
    assert report["blocker_counts"]["required_category_point_awards_missing"] > 0
    assert report["blocker_counts"]["announcement_not_future_from_native_bootstrap"] > 0
    assert sum(report["category_counts"].values()) == 80
    assert Counter(code for row in rows for code in row["blocker_codes"]) == Counter(
        report["blocker_counts"]
    )


@pytest.mark.pr_critical
def test_native_structural_probe_uses_real_domain_model_without_silent_qualification(tmp_path):
    original = _source(registry=tmp_path / "no-points.json").build_calendar().events[10]
    clock = RunCalendar(61, 37, 2000, 50)
    compatible = _supported_fixture(original)
    inspected = classify_event(compatible, initial_native_week=2, clock=clock)
    assert inspected["structurally_compatible_only"]
    assert inspected["blocker_codes"] == []
    assert inspected["native_v2_domain_error"] is None

    with_qualification = compatible.model_copy(update={
        "qualification_draw_size": 8, "qualifier_spots": 2,
    })
    q = classify_event(with_qualification, initial_native_week=2, clock=clock)
    assert not q["structurally_compatible_only"]
    assert "qualification_structure_not_modelled_by_native_v2" in q["blocker_codes"]
    assert q["source_qualification_draw_size"] == 8

    award_defect = compatible.model_copy(update={
        "ranking_points_table": {"champion": 100, "finalist": 60},
    })
    missing = classify_event(award_defect, initial_native_week=2, clock=clock)
    assert "required_category_point_awards_missing" in missing["blocker_codes"]
    assert missing["missing_required_category_stages"] == ["semifinal"]

    invalid_order = compatible.model_copy(update={
        "ranking_points_table": {"champion": 100, "finalist": 60, "semifinal": 95},
    })
    invalid = classify_event(invalid_order, initial_native_week=2, clock=clock)
    assert "native_v2_domain_rejected_event" in invalid["blocker_codes"]
    assert invalid["native_v2_domain_error"]


def test_source_first_weeks_cannot_be_retroactively_announced_or_rescheduled(tmp_path):
    event = _supported_fixture(
        _source(registry=tmp_path / "no-points.json").build_calendar().events[0]
    )
    clock = RunCalendar(61, 37, 2000, 50)
    for week in (1, 2, 3):
        early = event.model_copy(update={"season_week": week})
        result = classify_event(early, initial_native_week=2, clock=clock)
        assert "announcement_not_future_from_native_bootstrap" in result["blocker_codes"]
    possible = classify_event(event.model_copy(update={"season_week": 4}),
                              initial_native_week=2, clock=clock)
    assert "announcement_not_future_from_native_bootstrap" not in possible["blocker_codes"]
    # A different explicit bootstrap week changes only timing classification.
    w4 = classify_event(event.model_copy(update={"season_week": 4}),
                        initial_native_week=3, clock=clock)
    assert "announcement_not_future_from_native_bootstrap" in w4["blocker_codes"]
    with pytest.raises(ValueError, match="Initial native Tour week"):
        classify_event(event, initial_native_week=61, clock=clock)


def test_full_80_audit_rejects_tampered_duplicate_foreign_or_wrong_clock_sources(tmp_path):
    source = _source(registry=tmp_path / "no-points.json").build_calendar()
    fingerprint = source.metadata.build_fingerprint
    assert fingerprint is not None
    events = list(source.events)
    with pytest.raises(ValueError, match="80-Edition"):
        audit(events[:-1], source_fingerprint=fingerprint)
    with pytest.raises(ValueError, match="Duplicate"):
        audit([*events[:-1], events[0]], source_fingerprint=fingerprint)
    with pytest.raises(ValueError, match="World Tour"):
        audit([events[0].model_copy(update={"tour_level": "ELITE_TOUR"}), *events[1:]],
              source_fingerprint=fingerprint)
    with pytest.raises(ValueError, match="64-character"):
        audit(events, source_fingerprint="abcdef")
    with pytest.raises(ValueError, match="W61"):
        audit(events, source_fingerprint=fingerprint, calendar=RunCalendar(52, 37, 2000, 50))
    with pytest.raises(ValueError, match="original 2000/2001"):
        audit([events[0].model_copy(update={"season": "2001/2002"}), *events[1:]],
              source_fingerprint=fingerprint)


def test_actual_source_report_does_not_touch_authoritative_template_or_points_bytes(tmp_path):
    registry = tmp_path / "points.json"
    registry.write_text('{"seasons": {}}', encoding="utf-8")
    templates = Path("config/tournament_templates/mvp_templates.json")
    before_template = templates.read_bytes()
    before_registry = registry.read_bytes()
    report = build_current_source_report(category_registry_path=registry)
    assert report["source_edition_count"] == 80
    assert templates.read_bytes() == before_template
    assert registry.read_bytes() == before_registry
    assert list(tmp_path.iterdir()) == [registry]


def test_json_cli_returns_nonzero_for_incomplete_release_readiness_without_modifying_inputs(tmp_path):
    registry = tmp_path / "missing.json"
    output = tmp_path / "fax-audit.json"
    assert main(["--category-points", str(registry), "--output", str(output)]) == 2
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report == build_current_source_report(category_registry_path=registry)
    assert report["source_edition_count"] == 80
    assert not report["playability_certified"]
    assert list(tmp_path.iterdir()) == [output]
    assert main(["--category-points", str(registry), "--output", str(output)]) == 2
    assert json.loads(output.read_text(encoding="utf-8")) == report

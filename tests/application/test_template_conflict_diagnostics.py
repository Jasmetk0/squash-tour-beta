from beta_engine.application.template_conflict_diagnostics import (
    build_selected_template_conflict_diagnostics_overview,
    build_template_conflict_diagnostics_overview,
    build_template_conflict_summary_preview,
)
from beta_engine.domain.tournaments import SeasonTemplateSlotConflictPreview


def test_build_template_conflict_summary_preview_unavailable_shape():
    summary = build_template_conflict_summary_preview(None)
    assert summary["available"] is False
    assert summary["read_only"] is True
    assert summary["non_blocking"] is True
    assert summary["status"] is None
    assert summary["warning_count"] == 0
    assert summary["info_count"] == 0
    assert summary["conflict_count"] == 0
    assert summary["conflict_codes"] == []


def test_build_template_conflict_summary_preview_available_shape():
    preview = SeasonTemplateSlotConflictPreview(
        template_id="default_msa_template_preview",
        template_exists=True,
        status="warnings",
        warning_count=2,
        info_count=1,
        conflict_count=3,
        conflict_codes=["template_conflict_week_overloaded", "template_conflict_premium_overlap"],
        busiest_week=9,
        busiest_week_slot_count=4,
    )
    summary = build_template_conflict_summary_preview(preview)
    assert summary["available"] is True
    assert summary["status"] == "warnings"
    assert summary["warning_count"] == 2
    assert summary["info_count"] == 1
    assert summary["conflict_count"] == 3
    assert summary["conflict_codes"] == ["template_conflict_week_overloaded", "template_conflict_premium_overlap"]
    assert summary["busiest_week"] == 9
    assert summary["busiest_week_slot_count"] == 4


def test_build_template_conflict_diagnostics_overview_prefers_summary_over_preview():
    preview = SeasonTemplateSlotConflictPreview(status="warnings", conflict_count=3)
    overview = build_template_conflict_diagnostics_overview(
        preflight_preview=preview,
        preflight_summary={"status": "info", "conflict_count": 9},
    )
    assert overview.preflight_status == "info"
    assert overview.preflight_conflict_count == 9


def test_build_selected_template_conflict_diagnostics_overview_present():
    overview = build_selected_template_conflict_diagnostics_overview(
        template_exists=True,
        status="warnings",
        conflict_count=3,
    )
    assert overview.selected_report_available is True
    assert overview.selected_status == "warnings"
    assert overview.selected_conflict_count == 3


def test_build_selected_template_conflict_diagnostics_overview_missing():
    overview = build_selected_template_conflict_diagnostics_overview(
        template_exists=False,
        status="warnings",
        conflict_count=1,
    )
    assert overview.selected_report_available is False
    assert overview.selected_status is None
    assert overview.selected_conflict_count == 0


def test_build_template_conflict_diagnostics_overview_malformed_summary_falls_back_to_preview():
    preview = SeasonTemplateSlotConflictPreview(status="warnings", conflict_count=3)
    overview = build_template_conflict_diagnostics_overview(
        preflight_preview=preview,
        preflight_summary={"status": 42, "conflict_count": "bad"},
    )
    assert overview.preflight_status == "warnings"
    assert overview.preflight_conflict_count == 3


def test_build_template_conflict_diagnostics_overview_malformed_summary_without_preview_safe_defaults():
    overview = build_template_conflict_diagnostics_overview(
        preflight_summary={"status": 42, "conflict_count": "bad"},
    )
    assert overview.preflight_status is None
    assert overview.preflight_conflict_count == 0


def test_build_template_conflict_diagnostics_overview_normalizes_string_and_float_counts():
    overview = build_template_conflict_diagnostics_overview(
        preflight_summary={"status": "warnings", "conflict_count": "3"},
        dry_run_summary={"status": "info", "conflict_count": 4.0},
    )
    assert overview.preflight_conflict_count == 3
    assert overview.dry_run_conflict_count == 4


def test_build_template_conflict_diagnostics_overview_bool_count_does_not_coerce_to_one():
    overview = build_template_conflict_diagnostics_overview(
        preflight_summary={"status": "warnings", "conflict_count": True},
    )
    assert overview.preflight_conflict_count == 0

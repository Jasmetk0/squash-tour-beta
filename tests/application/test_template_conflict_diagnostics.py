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


def test_build_template_conflict_summary_preview_availability_messages():
    unavailable = build_template_conflict_summary_preview(None)
    preview = SeasonTemplateSlotConflictPreview(status="warnings", conflict_count=1)
    available = build_template_conflict_summary_preview(preview)
    assert "unavailable" in unavailable["message"]
    assert "available" in available["message"]


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


def test_build_selected_template_conflict_diagnostics_overview_normalizes_status_case_and_whitespace():
    overview = build_selected_template_conflict_diagnostics_overview(
        template_exists=True,
        status=" Warnings ",
        conflict_count=3,
    )
    assert overview.selected_report_available is True
    assert overview.selected_status == "warnings"
    assert overview.selected_conflict_count == 3


def test_build_selected_template_conflict_diagnostics_overview_rejects_invalid_status():
    overview = build_selected_template_conflict_diagnostics_overview(
        template_exists=True,
        status="blocked",
        conflict_count=3,
    )
    assert overview.selected_report_available is True
    assert overview.selected_status is None
    assert overview.selected_conflict_count == 3


def test_build_selected_template_conflict_diagnostics_overview_normalizes_string_and_float_counts():
    overview_from_string = build_selected_template_conflict_diagnostics_overview(
        template_exists=True,
        status="warnings",
        conflict_count="3",
    )
    overview_from_float = build_selected_template_conflict_diagnostics_overview(
        template_exists=True,
        status="warnings",
        conflict_count=3.0,
    )
    assert overview_from_string.selected_conflict_count == 3
    assert overview_from_float.selected_conflict_count == 3


def test_build_selected_template_conflict_diagnostics_overview_rejects_bool_count():
    overview = build_selected_template_conflict_diagnostics_overview(
        template_exists=True,
        status="warnings",
        conflict_count=True,
    )
    assert overview.selected_report_available is True
    assert overview.selected_status == "warnings"
    assert overview.selected_conflict_count == 0


def test_build_selected_template_conflict_diagnostics_overview_missing():
    overview = build_selected_template_conflict_diagnostics_overview(
        template_exists=False,
        status="warnings",
        conflict_count=99,
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


def test_template_conflict_diagnostics_overview_contract_is_read_only_non_blocking():
    # These fields are part of the safety contract: conflict diagnostics may inform admins
    # but must not enable mutation or block/permit commands.
    selected = build_selected_template_conflict_diagnostics_overview(
        template_exists=True,
        status="warnings",
        conflict_count=2,
    )
    preflight_preview = SeasonTemplateSlotConflictPreview(status="warnings", conflict_count=1)
    dry_run_preview = SeasonTemplateSlotConflictPreview(status="info", conflict_count=0)
    combined = build_template_conflict_diagnostics_overview(
        selected_report_available=selected.selected_report_available,
        selected_status=selected.selected_status,
        selected_conflict_count=selected.selected_conflict_count,
        preflight_preview=preflight_preview,
        preflight_summary=build_template_conflict_summary_preview(preflight_preview),
        dry_run_preview=dry_run_preview,
        dry_run_summary=build_template_conflict_summary_preview(dry_run_preview),
    )
    assert combined.read_only is True
    assert combined.non_blocking is True
    assert combined.mutation_behavior == "unavailable"
    assert combined.blocking_behavior == "non_blocking"
